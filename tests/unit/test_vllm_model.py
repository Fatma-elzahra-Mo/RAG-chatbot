"""
Unit tests for vLLM model wrapper.

Tests vLLM LLM integration including:
- Initialization with different configurations
- Connection health checking
- Message invocation (sync and async)
- Streaming responses
- Error handling
"""

import pytest
from unittest.mock import Mock, patch, MagicMock, AsyncMock
from langchain_core.messages import HumanMessage, AIMessage
import httpx

from src.models.vllm_model import (
    VLLMLLMWrapper,
    VLLMConnectionError,
    create_vllm_llm,
)


class TestVLLMLLMWrapper:
    """Test suite for VLLMLLMWrapper."""

    @pytest.mark.unit
    def test_initialization_default_settings(self):
        """Test initialization with default settings."""
        with patch("src.models.vllm_model.settings") as mock_settings:
            mock_settings.vllm_base_url = "http://localhost:8000/v1"
            mock_settings.vllm_model = "test-model"
            mock_settings.vllm_temperature = 0.7
            mock_settings.vllm_max_tokens = 512

            with patch.object(VLLMLLMWrapper, "_verify_server_health"):
                with patch("src.models.vllm_model.ChatOpenAI") as mock_chat:
                    llm = VLLMLLMWrapper()

                    assert llm.base_url == "http://localhost:8000/v1"
                    assert llm.model_name == "test-model"
                    assert llm.temperature == 0.7
                    assert llm.max_tokens == 512
                    mock_chat.assert_called_once()

    @pytest.mark.unit
    def test_initialization_custom_settings(self):
        """Test initialization with custom settings."""
        with patch.object(VLLMLLMWrapper, "_verify_server_health"):
            with patch("src.models.vllm_model.ChatOpenAI"):
                llm = VLLMLLMWrapper(
                    base_url="http://custom:9000/v1",
                    model_name="custom-model",
                    temperature=0.5,
                    max_tokens=1024,
                )

                assert llm.base_url == "http://custom:9000/v1"
                assert llm.model_name == "custom-model"
                assert llm.temperature == 0.5
                assert llm.max_tokens == 1024

    @pytest.mark.unit
    def test_initialization_skip_health_check(self):
        """Test initialization can skip health check."""
        with patch("src.models.vllm_model.ChatOpenAI"):
            with patch.object(VLLMLLMWrapper, "_verify_server_health") as mock_verify:
                llm = VLLMLLMWrapper(verify_connection=False)

                mock_verify.assert_not_called()
                assert llm is not None

    @pytest.mark.unit
    def test_verify_server_health_success(self):
        """Test successful server health check."""
        with patch("httpx.get") as mock_get:
            mock_response = Mock()
            mock_response.status_code = 200
            mock_get.return_value = mock_response

            with patch("src.models.vllm_model.ChatOpenAI"):
                llm = VLLMLLMWrapper(
                    base_url="http://localhost:8000/v1",
                    verify_connection=True,
                )

                assert llm is not None
                mock_get.assert_called()

    @pytest.mark.unit
    def test_verify_server_health_failure_connection_error(self):
        """Test health check raises VLLMConnectionError on connection failure."""
        with patch("httpx.get", side_effect=httpx.ConnectError("Connection refused")):
            with pytest.raises(VLLMConnectionError, match="vLLM server"):
                VLLMLLMWrapper(
                    base_url="http://localhost:8000/v1",
                    verify_connection=True,
                )

    @pytest.mark.unit
    def test_verify_server_health_failure_timeout(self):
        """Test health check raises VLLMConnectionError on timeout."""
        with patch("httpx.get", side_effect=httpx.TimeoutException("Timeout")):
            with pytest.raises(VLLMConnectionError, match="not responding"):
                VLLMLLMWrapper(
                    base_url="http://localhost:8000/v1",
                    verify_connection=True,
                )

    @pytest.mark.unit
    def test_verify_server_health_tries_multiple_endpoints(self):
        """Test health check tries multiple endpoints."""
        with patch("httpx.get") as mock_get:
            # First two endpoints fail, third succeeds
            mock_get.side_effect = [
                httpx.ConnectError("Failed"),
                httpx.ConnectError("Failed"),
                Mock(status_code=200),
            ]

            with patch("src.models.vllm_model.ChatOpenAI"):
                llm = VLLMLLMWrapper(
                    base_url="http://localhost:8000/v1",
                    verify_connection=True,
                )

                assert llm is not None
                assert mock_get.call_count == 3

    @pytest.mark.unit
    def test_invoke_success(self):
        """Test successful message invocation."""
        with patch.object(VLLMLLMWrapper, "_verify_server_health"):
            with patch("src.models.vllm_model.ChatOpenAI") as mock_chat:
                # Mock successful response
                mock_response = AIMessage(content="Test response")
                mock_chat.return_value.invoke.return_value = mock_response

                llm = VLLMLLMWrapper()
                messages = [HumanMessage(content="Test query")]
                response = llm.invoke(messages)

                assert response.content == "Test response"
                mock_chat.return_value.invoke.assert_called_once_with(messages)

    @pytest.mark.unit
    def test_invoke_arabic_text(self):
        """Test invocation with Arabic text."""
        with patch.object(VLLMLLMWrapper, "_verify_server_health"):
            with patch("src.models.vllm_model.ChatOpenAI") as mock_chat:
                mock_response = AIMessage(content="هذه إجابة تجريبية")
                mock_chat.return_value.invoke.return_value = mock_response

                llm = VLLMLLMWrapper()
                messages = [HumanMessage(content="ما هي عاصمة مصر؟")]
                response = llm.invoke(messages)

                assert response.content == "هذه إجابة تجريبية"
                assert "ا" in response.content  # Verify Arabic encoding

    @pytest.mark.unit
    def test_invoke_connection_error(self):
        """Test invoke raises VLLMConnectionError on connection failure."""
        with patch.object(VLLMLLMWrapper, "_verify_server_health"):
            with patch("src.models.vllm_model.ChatOpenAI") as mock_chat:
                mock_chat.return_value.invoke.side_effect = Exception(
                    "connection error: Failed to connect"
                )

                llm = VLLMLLMWrapper()
                messages = [HumanMessage(content="Test")]

                with pytest.raises(VLLMConnectionError, match="vLLM request failed"):
                    llm.invoke(messages)

    @pytest.mark.unit
    def test_invoke_timeout_error(self):
        """Test invoke raises VLLMConnectionError on timeout."""
        with patch.object(VLLMLLMWrapper, "_verify_server_health"):
            with patch("src.models.vllm_model.ChatOpenAI") as mock_chat:
                mock_chat.return_value.invoke.side_effect = Exception("timeout exceeded")

                llm = VLLMLLMWrapper()
                messages = [HumanMessage(content="Test")]

                with pytest.raises(VLLMConnectionError, match="vLLM request failed"):
                    llm.invoke(messages)

    @pytest.mark.unit
    def test_invoke_other_error_propagates(self):
        """Test invoke propagates non-connection errors."""
        with patch.object(VLLMLLMWrapper, "_verify_server_health"):
            with patch("src.models.vllm_model.ChatOpenAI") as mock_chat:
                mock_chat.return_value.invoke.side_effect = ValueError("Invalid input")

                llm = VLLMLLMWrapper()
                messages = [HumanMessage(content="Test")]

                with pytest.raises(ValueError, match="Invalid input"):
                    llm.invoke(messages)

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_ainvoke_success(self):
        """Test async message invocation."""
        with patch.object(VLLMLLMWrapper, "_verify_server_health"):
            with patch("src.models.vllm_model.ChatOpenAI") as mock_chat:
                mock_response = AIMessage(content="Async response")
                mock_chat.return_value.ainvoke = AsyncMock(return_value=mock_response)

                llm = VLLMLLMWrapper()
                messages = [HumanMessage(content="Test query")]
                response = await llm.ainvoke(messages)

                assert response.content == "Async response"

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_ainvoke_connection_error(self):
        """Test async invoke raises VLLMConnectionError on connection failure."""
        with patch.object(VLLMLLMWrapper, "_verify_server_health"):
            with patch("src.models.vllm_model.ChatOpenAI") as mock_chat:
                mock_chat.return_value.ainvoke = AsyncMock(
                    side_effect=Exception("connection error")
                )

                llm = VLLMLLMWrapper()
                messages = [HumanMessage(content="Test")]

                with pytest.raises(VLLMConnectionError, match="async request failed"):
                    await llm.ainvoke(messages)

    @pytest.mark.unit
    def test_stream_success(self):
        """Test streaming response."""
        with patch.object(VLLMLLMWrapper, "_verify_server_health"):
            with patch("src.models.vllm_model.ChatOpenAI") as mock_chat:
                # Mock streaming chunks
                chunks = [
                    AIMessage(content="Chunk 1"),
                    AIMessage(content="Chunk 2"),
                    AIMessage(content="Chunk 3"),
                ]
                mock_chat.return_value.stream.return_value = iter(chunks)

                llm = VLLMLLMWrapper()
                messages = [HumanMessage(content="Test query")]
                result = list(llm.stream(messages))

                assert len(result) == 3
                assert result[0].content == "Chunk 1"
                assert result[2].content == "Chunk 3"

    @pytest.mark.unit
    def test_stream_connection_error(self):
        """Test stream raises VLLMConnectionError on connection failure."""
        with patch.object(VLLMLLMWrapper, "_verify_server_health"):
            with patch("src.models.vllm_model.ChatOpenAI") as mock_chat:
                mock_chat.return_value.stream.side_effect = Exception("connection timeout")

                llm = VLLMLLMWrapper()
                messages = [HumanMessage(content="Test")]

                with pytest.raises(VLLMConnectionError, match="streaming failed"):
                    list(llm.stream(messages))

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_astream_success(self):
        """Test async streaming response."""
        with patch.object(VLLMLLMWrapper, "_verify_server_health"):
            with patch("src.models.vllm_model.ChatOpenAI") as mock_chat:
                # Mock async streaming
                async def async_generator():
                    for content in ["Chunk 1", "Chunk 2"]:
                        yield AIMessage(content=content)

                mock_chat.return_value.astream.return_value = async_generator()

                llm = VLLMLLMWrapper()
                messages = [HumanMessage(content="Test query")]
                result = []
                async for chunk in llm.astream(messages):
                    result.append(chunk)

                assert len(result) == 2
                assert result[0].content == "Chunk 1"

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_astream_connection_error(self):
        """Test async stream raises VLLMConnectionError on connection failure."""
        with patch.object(VLLMLLMWrapper, "_verify_server_health"):
            with patch("src.models.vllm_model.ChatOpenAI") as mock_chat:
                async def async_error():
                    raise Exception("connection error")
                    yield  # Make it an async generator

                mock_chat.return_value.astream.return_value = async_error()

                llm = VLLMLLMWrapper()
                messages = [HumanMessage(content="Test")]

                with pytest.raises(VLLMConnectionError, match="async streaming failed"):
                    async for _ in llm.astream(messages):
                        pass


class TestVLLMFactoryFunction:
    """Test suite for vLLM factory function."""

    @pytest.mark.unit
    def test_create_vllm_llm_default(self):
        """Test factory function with defaults."""
        with patch.object(VLLMLLMWrapper, "_verify_server_health"):
            with patch("src.models.vllm_model.ChatOpenAI"):
                llm = create_vllm_llm(provider="local")

                assert llm is not None
                assert isinstance(llm, VLLMLLMWrapper)

    @pytest.mark.unit
    def test_create_vllm_llm_custom_config(self):
        """Test factory function with custom configuration."""
        with patch.object(VLLMLLMWrapper, "_verify_server_health"):
            with patch("src.models.vllm_model.ChatOpenAI"):
                llm = create_vllm_llm(
                    provider="huggingface",
                    base_url="http://custom:8000/v1",
                    model_name="custom-model",
                )

                assert llm.base_url == "http://custom:8000/v1"
                assert llm.model_name == "custom-model"

    @pytest.mark.unit
    def test_create_vllm_llm_skip_verification(self):
        """Test factory function can skip connection verification."""
        with patch("src.models.vllm_model.ChatOpenAI"):
            with patch.object(VLLMLLMWrapper, "_verify_server_health") as mock_verify:
                llm = create_vllm_llm(provider="local", verify_connection=False)

                mock_verify.assert_not_called()
                assert llm is not None


class TestVLLMErrorMessages:
    """Test suite for vLLM error messages."""

    @pytest.mark.unit
    def test_connection_error_includes_server_url(self):
        """Test connection error includes server URL in message."""
        with patch("httpx.get", side_effect=httpx.ConnectError("Connection refused")):
            try:
                VLLMLLMWrapper(
                    base_url="http://localhost:9999/v1",
                    verify_connection=True,
                )
            except VLLMConnectionError as e:
                # Error message should contain server URL
                assert "localhost:9999" in str(e) or "localhost" in str(e)

    @pytest.mark.unit
    def test_connection_error_includes_model_name(self):
        """Test connection error includes model name in message."""
        with patch("httpx.get", side_effect=httpx.ConnectError("Connection refused")):
            try:
                VLLMLLMWrapper(
                    base_url="http://localhost:8000/v1",
                    model_name="test-model-name",
                    verify_connection=True,
                )
            except VLLMConnectionError as e:
                assert "test-model-name" in str(e)

    @pytest.mark.unit
    def test_invoke_error_includes_context(self):
        """Test invoke error includes helpful context."""
        with patch.object(VLLMLLMWrapper, "_verify_server_health"):
            with patch("src.models.vllm_model.ChatOpenAI") as mock_chat:
                mock_chat.return_value.invoke.side_effect = Exception("Connection failed")

                llm = VLLMLLMWrapper(
                    base_url="http://custom:8000/v1",
                    model_name="custom-model",
                )

                try:
                    llm.invoke([HumanMessage(content="Test")])
                except VLLMConnectionError as e:
                    error_msg = str(e)
                    assert "http://custom:8000/v1" in error_msg
                    assert "custom-model" in error_msg


class TestVLLMConfigurationPatterns:
    """Test suite for common vLLM configuration patterns."""

    @pytest.mark.unit
    def test_llama_model_configuration(self):
        """Test Llama model configuration."""
        with patch.object(VLLMLLMWrapper, "_verify_server_health"):
            with patch("src.models.vllm_model.ChatOpenAI") as mock_chat:
                llm = VLLMLLMWrapper(
                    model_name="meta-llama/Llama-2-7b-chat-hf",
                    temperature=0.7,
                    max_tokens=512,
                )

                # Verify ChatOpenAI was called with correct parameters
                call_kwargs = mock_chat.call_args[1]
                assert call_kwargs["model"] == "meta-llama/Llama-2-7b-chat-hf"
                assert call_kwargs["temperature"] == 0.7
                assert call_kwargs["max_tokens"] == 512

    @pytest.mark.unit
    def test_mistral_model_configuration(self):
        """Test Mistral model configuration."""
        with patch.object(VLLMLLMWrapper, "_verify_server_health"):
            with patch("src.models.vllm_model.ChatOpenAI"):
                llm = VLLMLLMWrapper(
                    model_name="mistralai/Mistral-7B-Instruct-v0.2",
                    temperature=0.5,
                )

                assert llm.model_name == "mistralai/Mistral-7B-Instruct-v0.2"
                assert llm.temperature == 0.5

    @pytest.mark.unit
    def test_timeout_configuration(self):
        """Test custom timeout configuration."""
        with patch.object(VLLMLLMWrapper, "_verify_server_health"):
            with patch("src.models.vllm_model.ChatOpenAI") as mock_chat:
                llm = VLLMLLMWrapper(timeout=60.0)

                call_kwargs = mock_chat.call_args[1]
                assert call_kwargs["timeout"] == 60.0
