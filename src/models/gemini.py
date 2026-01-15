"""
LLM providers for Arabic RAG chatbot.

Supports:
- Google Gemini (direct API)
- OpenRouter (unified API for 300+ models)
"""

from typing import List, Optional

from langchain_core.messages import BaseMessage
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_openai import ChatOpenAI

from src.config.settings import settings


class GeminiLLM:
    """
    Gemini LLM wrapper for Arabic RAG chatbot.

    Features:
    - Supports gemini-1.5-flash, gemini-1.5-pro, gemini-2.0-flash-exp
    - Optimized for Egyptian Arabic responses
    - Streaming support for real-time responses
    - Temperature and safety settings configurable

    Example:
        >>> llm = GeminiLLM(model_name="gemini-2.0-flash-exp")
        >>> response = llm.invoke([HumanMessage(content="مرحبا")])
        >>> print(response.content)
    """

    def __init__(
        self,
        model_name: Optional[str] = None,
        temperature: Optional[float] = None,
        api_key: Optional[str] = None,
    ):
        """
        Initialize Gemini LLM.

        Args:
            model_name: Gemini model to use (defaults to settings.gemini_model)
            temperature: Response creativity (defaults to settings.gemini_temperature)
            api_key: Google API key (defaults to settings.gemini_api_key)
        """
        # Use settings as defaults
        self.model_name = model_name or settings.gemini_model
        self.temperature = temperature if temperature is not None else settings.gemini_temperature

        # Get API key from settings if not provided
        api_key = api_key or (
            settings.gemini_api_key.get_secret_value()
            if settings.gemini_api_key
            else None
        )

        if not api_key:
            raise ValueError(
                "Gemini API key required. Set GEMINI_API_KEY in .env or pass api_key parameter."
            )

        self.llm = ChatGoogleGenerativeAI(
            model=self.model_name,
            temperature=self.temperature,
            google_api_key=api_key,
            convert_system_message_to_human=True,  # Gemini doesn't support system messages directly
        )

    def invoke(self, messages: List[BaseMessage]) -> BaseMessage:
        """
        Generate response from messages.

        Args:
            messages: List of conversation messages

        Returns:
            AI response message
        """
        response = self.llm.invoke(messages)
        return response

    async def ainvoke(self, messages: List[BaseMessage]) -> BaseMessage:
        """
        Async generate response from messages.

        Args:
            messages: List of conversation messages

        Returns:
            AI response message
        """
        response = await self.llm.ainvoke(messages)
        return response

    def stream(self, messages: List[BaseMessage]):
        """
        Stream response tokens.

        Args:
            messages: List of conversation messages

        Yields:
            Response chunks
        """
        for chunk in self.llm.stream(messages):
            yield chunk

    async def astream(self, messages: List[BaseMessage]):
        """
        Async stream response tokens.

        Args:
            messages: List of conversation messages

        Yields:
            Response chunks
        """
        async for chunk in self.llm.astream(messages):
            yield chunk


class OpenRouterLLM:
    """
    OpenRouter LLM wrapper for Arabic RAG chatbot.

    Features:
    - Access to 300+ models via unified API
    - No rate limits like Gemini free tier
    - Supports Claude, GPT-4, Gemini, Llama, etc.

    Example:
        >>> llm = OpenRouterLLM(model_name="google/gemini-flash-1.5")
        >>> response = llm.invoke([HumanMessage(content="مرحبا")])
        >>> print(response.content)
    """

    def __init__(
        self,
        model_name: Optional[str] = None,
        temperature: Optional[float] = None,
        api_key: Optional[str] = None,
    ):
        """
        Initialize OpenRouter LLM.

        Args:
            model_name: Model to use (defaults to settings.openrouter_model)
            temperature: Response creativity (defaults to settings.openrouter_temperature)
            api_key: OpenRouter API key (defaults to settings.openrouter_api_key)
        """
        self.model_name = model_name or settings.openrouter_model
        self.temperature = temperature if temperature is not None else settings.openrouter_temperature

        api_key = api_key or (
            settings.openrouter_api_key.get_secret_value()
            if settings.openrouter_api_key
            else None
        )

        if not api_key:
            raise ValueError(
                "OpenRouter API key required. Set OPENROUTER_API_KEY in .env or pass api_key parameter."
            )

        self.llm = ChatOpenAI(
            model=self.model_name,
            temperature=self.temperature,
            api_key=api_key,
            base_url=settings.openrouter_base_url,
            default_headers={
                "HTTP-Referer": "https://we-assistant.local",
                "X-Title": "WE Arabic RAG Chatbot",
            },
        )

    def invoke(self, messages: List[BaseMessage]) -> BaseMessage:
        """Generate response from messages."""
        return self.llm.invoke(messages)

    async def ainvoke(self, messages: List[BaseMessage]) -> BaseMessage:
        """Async generate response from messages."""
        return await self.llm.ainvoke(messages)

    def stream(self, messages: List[BaseMessage]):
        """Stream response tokens."""
        for chunk in self.llm.stream(messages):
            yield chunk

    async def astream(self, messages: List[BaseMessage]):
        """Async stream response tokens."""
        async for chunk in self.llm.astream(messages):
            yield chunk


def create_llm(provider: str = None):
    """
    Factory function to create LLM instance.

    Args:
        provider: LLM provider ("gemini", "openrouter", "openai", "local")
                  Defaults to settings.llm_provider

    Returns:
        LLM instance
    """
    provider = provider or settings.llm_provider

    if provider == "gemini":
        return GeminiLLM(
            model_name=settings.gemini_model,
            temperature=settings.gemini_temperature,
        )
    elif provider == "openrouter":
        return OpenRouterLLM(
            model_name=settings.openrouter_model,
            temperature=settings.openrouter_temperature,
        )
    else:
        raise ValueError(f"Unsupported provider: {provider}. Use 'gemini' or 'openrouter'.")
