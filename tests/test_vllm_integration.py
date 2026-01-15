"""
QA Test Suite: Document vLLM Integration Failure.

This test file documents the current state where vLLM providers
(local and huggingface) are configured in settings but not implemented
in the pipeline, causing ValueError when used.

After implementation, these tests should pass.
"""

import pytest
from unittest.mock import patch, Mock
from src.config.settings import Settings
from src.core.pipeline import RAGPipeline


class TestVLLMIntegrationIssue:
    """
    Test suite documenting the vLLM integration issue.

    Current State:
    - settings.py allows llm_provider="local" and "huggingface"
    - pipeline.py only implements "gemini", "openai", "openrouter"
    - Using unsupported providers raises ValueError at line 138
    """

    @pytest.mark.unit
    def test_local_provider_raises_value_error(self):
        """
        Test that llm_provider='local' currently raises ValueError.

        Expected Behavior (after fix):
        - Should initialize vLLM with local server configuration
        - Should connect to http://localhost:8000/v1
        """
        with patch("src.core.pipeline.QdrantClient"):
            # Override settings to use local provider
            with patch("src.config.settings.settings") as mock_settings:
                mock_settings.llm_provider = "local"
                mock_settings.qdrant_url = "http://localhost:6333"
                mock_settings.qdrant_collection = "test"
                mock_settings.embeddings_provider = "local"
                mock_settings.embeddings_dimension = 768
                mock_settings.reranker_model = "test-reranker"
                mock_settings.reranker_top_n = 5
                mock_settings.retrieval_top_k = 10
                mock_settings.max_conversation_history = 10
                mock_settings.conversation_ttl_hours = 24

                # This should raise ValueError with current implementation
                with pytest.raises(ValueError, match="Unsupported LLM provider: local"):
                    RAGPipeline(use_memory=False)

    @pytest.mark.unit
    def test_huggingface_provider_raises_value_error(self):
        """
        Test that llm_provider='huggingface' currently raises ValueError.

        Expected Behavior (after fix):
        - Should initialize vLLM with HuggingFace model configuration
        - Should load model from HuggingFace Hub
        """
        with patch("src.core.pipeline.QdrantClient"):
            with patch("src.config.settings.settings") as mock_settings:
                mock_settings.llm_provider = "huggingface"
                mock_settings.qdrant_url = "http://localhost:6333"
                mock_settings.qdrant_collection = "test"
                mock_settings.embeddings_provider = "local"
                mock_settings.embeddings_dimension = 768
                mock_settings.reranker_model = "test-reranker"
                mock_settings.reranker_top_n = 5
                mock_settings.retrieval_top_k = 10
                mock_settings.max_conversation_history = 10
                mock_settings.conversation_ttl_hours = 24

                # This should raise ValueError with current implementation
                with pytest.raises(ValueError, match="Unsupported LLM provider: huggingface"):
                    RAGPipeline(use_memory=False)

    @pytest.mark.unit
    def test_settings_allows_local_provider(self):
        """
        Verify that Settings accepts 'local' as valid llm_provider.

        This confirms the configuration mismatch - settings allow it,
        but pipeline doesn't implement it.
        """
        settings = Settings(llm_provider="local")
        assert settings.llm_provider == "local"

    @pytest.mark.unit
    def test_settings_allows_huggingface_provider(self):
        """
        Verify that Settings accepts 'huggingface' as valid llm_provider.

        This confirms the configuration mismatch - settings allow it,
        but pipeline doesn't implement it.
        """
        settings = Settings(llm_provider="huggingface")
        assert settings.llm_provider == "huggingface"

    @pytest.mark.unit
    def test_settings_pattern_includes_unsupported_providers(self):
        """
        Document that settings validation pattern includes providers
        that are not implemented in the pipeline.

        Pattern: ^(openai|gemini|openrouter|huggingface|local)$
        Implemented: openai, gemini, openrouter
        Missing: huggingface, local
        """
        # Valid according to settings pattern
        valid_providers = ["openai", "gemini", "openrouter", "huggingface", "local"]

        for provider in valid_providers:
            settings = Settings(llm_provider=provider)
            assert settings.llm_provider == provider


class TestVLLMIntegrationAfterFix:
    """
    Test suite for vLLM functionality after implementation.

    These tests will initially be skipped/fail but should pass
    after vLLM implementation is complete.
    """

    @pytest.mark.unit
    @pytest.mark.skip(reason="vLLM not yet implemented")
    def test_local_provider_initialization(self):
        """
        Test that local provider initializes vLLM correctly.

        Should:
        - Create vLLM instance with OpenAI-compatible endpoint
        - Use settings.vllm_base_url (default: http://localhost:8000/v1)
        - Configure temperature and max_tokens
        """
        with patch("src.core.pipeline.QdrantClient"):
            with patch("src.models.vllm_model.ChatOpenAI") as mock_vllm:
                mock_response = Mock()
                mock_response.content = "Test response"
                mock_vllm.return_value.invoke.return_value = mock_response

                with patch("src.config.settings.settings") as mock_settings:
                    mock_settings.llm_provider = "local"
                    mock_settings.vllm_base_url = "http://localhost:8000/v1"
                    mock_settings.vllm_model = "test-model"
                    mock_settings.vllm_temperature = 0.7
                    mock_settings.vllm_max_tokens = 512
                    mock_settings.qdrant_url = "http://localhost:6333"
                    mock_settings.qdrant_collection = "test"
                    mock_settings.embeddings_provider = "local"
                    mock_settings.embeddings_dimension = 768
                    mock_settings.reranker_model = "test-reranker"
                    mock_settings.reranker_top_n = 5

                    pipeline = RAGPipeline(use_memory=False)

                    assert pipeline.llm is not None
                    assert pipeline.llm_provider == "local"

    @pytest.mark.unit
    @pytest.mark.skip(reason="vLLM not yet implemented")
    def test_huggingface_provider_initialization(self):
        """
        Test that huggingface provider initializes vLLM correctly.

        Should:
        - Create vLLM instance with in-process model loading
        - Use settings.vllm_model for HuggingFace model name
        - Support both local and remote vLLM servers
        """
        with patch("src.core.pipeline.QdrantClient"):
            with patch("src.models.vllm_model.ChatOpenAI") as mock_vllm:
                mock_response = Mock()
                mock_response.content = "Test response"
                mock_vllm.return_value.invoke.return_value = mock_response

                with patch("src.config.settings.settings") as mock_settings:
                    mock_settings.llm_provider = "huggingface"
                    mock_settings.vllm_base_url = "http://localhost:8000/v1"
                    mock_settings.vllm_model = "meta-llama/Llama-2-7b-chat-hf"
                    mock_settings.qdrant_url = "http://localhost:6333"
                    mock_settings.qdrant_collection = "test"
                    mock_settings.embeddings_provider = "local"
                    mock_settings.embeddings_dimension = 768
                    mock_settings.reranker_model = "test-reranker"
                    mock_settings.reranker_top_n = 5

                    pipeline = RAGPipeline(use_memory=False)

                    assert pipeline.llm is not None
                    assert pipeline.llm_provider == "huggingface"

    @pytest.mark.integration
    @pytest.mark.skip(reason="vLLM not yet implemented")
    def test_vllm_connection_error_handling(self):
        """
        Test graceful error handling when vLLM server is unavailable.

        Should:
        - Catch connection errors
        - Provide clear error message
        - Suggest troubleshooting steps
        """
        with patch("src.core.pipeline.QdrantClient"):
            with patch("src.config.settings.settings") as mock_settings:
                mock_settings.llm_provider = "local"
                mock_settings.vllm_base_url = "http://localhost:9999/v1"  # Wrong port
                mock_settings.qdrant_url = "http://localhost:6333"
                mock_settings.qdrant_collection = "test"
                mock_settings.embeddings_provider = "local"
                mock_settings.embeddings_dimension = 768

                # Should raise informative error, not generic connection error
                with pytest.raises(
                    (ConnectionError, ValueError),
                    match="(vLLM server|connection|unavailable)"
                ):
                    RAGPipeline(use_memory=False)

    @pytest.mark.integration
    @pytest.mark.skip(reason="vLLM not yet implemented")
    def test_vllm_query_with_arabic_text(self):
        """
        Test that vLLM provider handles Arabic text correctly.

        Integration test ensuring:
        - Arabic text encoding works
        - Response generation succeeds
        - Output is properly formatted
        """
        with patch("src.core.pipeline.QdrantClient"):
            with patch("src.models.vllm_model.ChatOpenAI") as mock_vllm:
                # Mock Arabic response
                mock_response = Mock()
                mock_response.content = "هذه إجابة تجريبية بالعربية"
                mock_vllm.return_value.invoke.return_value = mock_response

                with patch("src.config.settings.settings") as mock_settings:
                    mock_settings.llm_provider = "local"
                    mock_settings.vllm_base_url = "http://localhost:8000/v1"
                    mock_settings.qdrant_url = "http://localhost:6333"
                    mock_settings.qdrant_collection = "test"
                    mock_settings.embeddings_provider = "local"
                    mock_settings.embeddings_dimension = 768
                    mock_settings.reranker_model = "test-reranker"
                    mock_settings.reranker_top_n = 5

                    pipeline = RAGPipeline(use_memory=False)
                    result = pipeline.query("ما هي عاصمة مصر؟")

                    assert result is not None
                    assert "response" in result
                    assert len(result["response"]) > 0
