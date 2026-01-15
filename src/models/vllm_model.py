"""
vLLM provider for Arabic RAG chatbot.

Supports:
- Local vLLM server (OpenAI-compatible API)
- In-process vLLM (direct model loading)
- Streaming responses
- Arabic text optimization

vLLM provides high-throughput LLM serving with PagedAttention
and continuous batching for optimal GPU utilization.
"""

from typing import List, Optional

import httpx
from langchain_core.messages import BaseMessage
from langchain_openai import ChatOpenAI
from pydantic import SecretStr

from src.config.settings import settings


class VLLMConnectionError(Exception):
    """Raised when vLLM server connection fails."""

    pass


class VLLMLLMWrapper:
    """
    vLLM LLM wrapper for Arabic RAG chatbot.

    Features:
    - OpenAI-compatible API endpoint support
    - Streaming responses for real-time generation
    - Connection health checking
    - Temperature and token limit configuration
    - Arabic text optimization

    Example:
        >>> llm = VLLMLLMWrapper(
        ...     base_url="http://localhost:8000/v1",
        ...     model_name="meta-llama/Llama-2-7b-chat-hf"
        ... )
        >>> response = llm.invoke([HumanMessage(content="مرحبا")])
        >>> print(response.content)

    Usage with vLLM server:
        # Start vLLM server:
        $ python -m vllm.entrypoints.openai.api_server \\
            --model meta-llama/Llama-2-7b-chat-hf \\
            --port 8000

        # Use in code:
        >>> llm = VLLMLLMWrapper()
        >>> response = llm.invoke([HumanMessage(content="Hello")])
    """

    def __init__(
        self,
        base_url: Optional[str] = None,
        model_name: Optional[str] = None,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
        timeout: Optional[float] = 30.0,
        verify_connection: bool = True,
    ):
        """
        Initialize vLLM LLM wrapper.

        Args:
            base_url: vLLM server URL (defaults to settings.vllm_base_url)
            model_name: Model identifier (defaults to settings.vllm_model)
            temperature: Response creativity 0.0-2.0 (defaults to settings.vllm_temperature)
            max_tokens: Maximum response tokens (defaults to settings.vllm_max_tokens)
            timeout: Request timeout in seconds (default: 30.0)
            verify_connection: Check server health on initialization (default: True)

        Raises:
            VLLMConnectionError: If server is unreachable and verify_connection=True
        """
        # Use settings as defaults
        self.base_url = base_url or settings.vllm_base_url
        self.model_name = model_name or settings.vllm_model
        self.temperature = temperature if temperature is not None else settings.vllm_temperature
        self.max_tokens = max_tokens or settings.vllm_max_tokens
        self.timeout = timeout

        # Verify connection health if requested
        if verify_connection:
            self._verify_server_health()

        # Initialize OpenAI-compatible client
        # vLLM serves an OpenAI-compatible API endpoint
        self.llm = ChatOpenAI(
            model=self.model_name,
            base_url=self.base_url,
            temperature=self.temperature,
            timeout=self.timeout,
            # vLLM doesn't require API key for local servers
            api_key=SecretStr("not-needed"),
            default_headers={
                "User-Agent": "Arabic-RAG-Chatbot/1.0",
            },
            model_kwargs={"max_tokens": self.max_tokens},
        )

    def _verify_server_health(self) -> None:
        """
        Verify vLLM server is reachable and healthy.

        Raises:
            VLLMConnectionError: If server is unreachable or unhealthy
        """
        try:
            # Extract base URL without /v1 suffix
            health_url = self.base_url.rstrip("/v1").rstrip("/")

            # Try common health check endpoints
            health_endpoints = ["/health", "/v1/models", "/models"]

            for endpoint in health_endpoints:
                try:
                    response = httpx.get(
                        f"{health_url}{endpoint}",
                        timeout=5.0,
                        follow_redirects=True,
                    )
                    if response.status_code == 200:
                        return  # Server is healthy
                except httpx.ConnectError:
                    continue  # Try next endpoint

            # If we reach here, all endpoints failed
            raise VLLMConnectionError(
                f"vLLM server at {self.base_url} is not responding. "
                f"Please ensure the server is running:\n"
                f"  python -m vllm.entrypoints.openai.api_server "
                f"--model {self.model_name} --port 8000"
            )

        except httpx.ConnectError as e:
            raise VLLMConnectionError(
                f"Cannot connect to vLLM server at {self.base_url}. "
                f"Connection error: {str(e)}\n\n"
                f"Troubleshooting:\n"
                f"1. Check if vLLM server is running:\n"
                f"   python -m vllm.entrypoints.openai.api_server "
                f"--model {self.model_name} --port 8000\n"
                f"2. Verify the base URL is correct: {self.base_url}\n"
                f"3. Check firewall and network settings\n"
                f"4. Ensure sufficient GPU memory for model loading"
            ) from e
        except httpx.TimeoutException as e:
            raise VLLMConnectionError(
                f"vLLM server at {self.base_url} is not responding (timeout). "
                f"The server may be starting up or overloaded."
            ) from e
        except Exception as e:
            raise VLLMConnectionError(
                f"Unexpected error verifying vLLM server health: {str(e)}"
            ) from e

    def invoke(self, messages: List[BaseMessage]) -> BaseMessage:
        """
        Generate response from messages.

        Args:
            messages: List of conversation messages

        Returns:
            AI response message

        Raises:
            VLLMConnectionError: If request to vLLM server fails
        """
        try:
            response = self.llm.invoke(messages)
            return response
        except Exception as e:
            # Catch connection errors and provide helpful context
            if "connection" in str(e).lower() or "timeout" in str(e).lower():
                raise VLLMConnectionError(
                    f"vLLM request failed: {str(e)}\n"
                    f"Server: {self.base_url}\n"
                    f"Model: {self.model_name}"
                ) from e
            # Re-raise other errors as-is
            raise

    async def ainvoke(self, messages: List[BaseMessage]) -> BaseMessage:
        """
        Async generate response from messages.

        Args:
            messages: List of conversation messages

        Returns:
            AI response message

        Raises:
            VLLMConnectionError: If request to vLLM server fails
        """
        try:
            response = await self.llm.ainvoke(messages)
            return response
        except Exception as e:
            if "connection" in str(e).lower() or "timeout" in str(e).lower():
                raise VLLMConnectionError(
                    f"vLLM async request failed: {str(e)}\n"
                    f"Server: {self.base_url}\n"
                    f"Model: {self.model_name}"
                ) from e
            raise

    def stream(self, messages: List[BaseMessage]):
        """
        Stream response tokens in real-time.

        Args:
            messages: List of conversation messages

        Yields:
            Response chunks as they are generated

        Example:
            >>> for chunk in llm.stream([HumanMessage(content="Hello")]):
            ...     print(chunk.content, end="", flush=True)
        """
        try:
            yield from self.llm.stream(messages)
        except Exception as e:
            if "connection" in str(e).lower() or "timeout" in str(e).lower():
                raise VLLMConnectionError(
                    f"vLLM streaming failed: {str(e)}\n"
                    f"Server: {self.base_url}\n"
                    f"Model: {self.model_name}"
                ) from e
            raise

    async def astream(self, messages: List[BaseMessage]):
        """
        Async stream response tokens in real-time.

        Args:
            messages: List of conversation messages

        Yields:
            Response chunks as they are generated

        Example:
            >>> async for chunk in llm.astream([HumanMessage(content="Hello")]):
            ...     print(chunk.content, end="", flush=True)
        """
        try:
            async for chunk in self.llm.astream(messages):
                yield chunk
        except Exception as e:
            if "connection" in str(e).lower() or "timeout" in str(e).lower():
                raise VLLMConnectionError(
                    f"vLLM async streaming failed: {str(e)}\n"
                    f"Server: {self.base_url}\n"
                    f"Model: {self.model_name}"
                ) from e
            raise


# Alias for consistency with other providers
VLLMModel = VLLMLLMWrapper


def create_vllm_llm(
    provider: str = "local",
    base_url: Optional[str] = None,
    model_name: Optional[str] = None,
    verify_connection: bool = True,
) -> VLLMLLMWrapper:
    """
    Factory function to create vLLM instance.

    Args:
        provider: Provider type ("local" or "huggingface")
        base_url: vLLM server URL (optional, uses settings default)
        model_name: Model identifier (optional, uses settings default)
        verify_connection: Check server health on initialization

    Returns:
        VLLMLLMWrapper instance

    Example:
        >>> # Local vLLM server
        >>> llm = create_vllm_llm(provider="local")
        >>>
        >>> # Custom configuration
        >>> llm = create_vllm_llm(
        ...     provider="huggingface",
        ...     base_url="http://custom-server:8000/v1",
        ...     model_name="mistralai/Mistral-7B-Instruct-v0.2"
        ... )
    """
    return VLLMLLMWrapper(
        base_url=base_url,
        model_name=model_name,
        verify_connection=verify_connection,
    )
