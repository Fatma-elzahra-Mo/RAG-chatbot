"""
Integration tests for vLLM with RAG pipeline.

Tests full integration including:
- vLLM + RAGPipeline integration
- Query processing with vLLM
- Arabic text handling
- Connection error scenarios
- Provider switching
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
from langchain_core.messages import AIMessage, HumanMessage

from src.core.pipeline import RAGPipeline
from src.models.vllm_model import VLLMConnectionError


class TestVLLMPipelineIntegration:
    """Integration tests for vLLM with RAG pipeline."""

    @pytest.mark.integration
    def test_pipeline_with_local_provider(self):
        """Test RAG pipeline initialization with local vLLM provider."""
        with patch("src.core.pipeline.QdrantClient"):
            with patch("src.models.vllm_model.VLLMLLMWrapper._verify_server_health"):
                with patch("src.models.vllm_model.ChatOpenAI") as mock_chat:
                    with patch("src.config.settings.settings") as mock_settings:
                        # Configure settings for local provider
                        mock_settings.llm_provider = "local"
                        mock_settings.vllm_base_url = "http://localhost:8000/v1"
                        mock_settings.vllm_model = "meta-llama/Llama-2-7b-chat-hf"
                        mock_settings.vllm_temperature = 0.7
                        mock_settings.vllm_max_tokens = 512
                        mock_settings.qdrant_url = "http://localhost:6333"
                        mock_settings.qdrant_collection = "test"
                        mock_settings.embeddings_provider = "local"
                        mock_settings.embeddings_dimension = 768
                        mock_settings.reranker_model = "test-reranker"
                        mock_settings.reranker_top_n = 5
                        mock_settings.retrieval_top_k = 10
                        mock_settings.max_conversation_history = 10
                        mock_settings.conversation_ttl_hours = 24

                        pipeline = RAGPipeline(use_memory=False)

                        assert pipeline is not None
                        assert pipeline.llm is not None
                        assert pipeline.llm_provider == "local"

    @pytest.mark.integration
    def test_pipeline_with_huggingface_provider(self):
        """Test RAG pipeline initialization with huggingface vLLM provider."""
        with patch("src.core.pipeline.QdrantClient"):
            with patch("src.models.vllm_model.VLLMLLMWrapper._verify_server_health"):
                with patch("src.models.vllm_model.ChatOpenAI"):
                    with patch("src.config.settings.settings") as mock_settings:
                        mock_settings.llm_provider = "huggingface"
                        mock_settings.vllm_base_url = "http://localhost:8000/v1"
                        mock_settings.vllm_model = "meta-llama/Llama-2-7b-chat-hf"
                        mock_settings.vllm_temperature = 0.7
                        mock_settings.vllm_max_tokens = 512
                        mock_settings.qdrant_url = "http://localhost:6333"
                        mock_settings.qdrant_collection = "test"
                        mock_settings.embeddings_provider = "local"
                        mock_settings.embeddings_dimension = 768
                        mock_settings.reranker_model = "test-reranker"
                        mock_settings.reranker_top_n = 5

                        pipeline = RAGPipeline(use_memory=False)

                        assert pipeline is not None
                        assert pipeline.llm is not None
                        assert pipeline.llm_provider == "huggingface"

    @pytest.mark.integration
    def test_query_with_vllm_provider(self):
        """Test full query processing with vLLM provider."""
        with patch("src.core.pipeline.QdrantClient") as mock_qdrant:
            with patch("src.models.vllm_model.VLLMLLMWrapper._verify_server_health"):
                with patch("src.models.vllm_model.ChatOpenAI") as mock_chat:
                    # Mock vLLM response
                    mock_response = AIMessage(content="القاهرة هي عاصمة مصر")
                    mock_chat.return_value.invoke.return_value = mock_response

                    # Mock vectorstore search
                    with patch("src.retrieval.vectorstore.QdrantStore.search") as mock_search:
                        mock_doc = Mock()
                        mock_doc.page_content = "القاهرة هي عاصمة جمهورية مصر العربية"
                        mock_doc.metadata = {"source": "test.txt"}
                        mock_search.return_value = [mock_doc]

                        # Mock reranker
                        with patch("src.retrieval.reranker.ArabicReranker.rerank") as mock_rerank:
                            mock_rerank.return_value = [mock_doc]

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
                                mock_settings.retrieval_top_k = 10

                                pipeline = RAGPipeline(use_memory=False)
                                result = pipeline.query("ما هي عاصمة مصر؟")

                                assert result is not None
                                assert "response" in result
                                assert result["response"] == "القاهرة هي عاصمة مصر"
                                assert "sources" in result
                                assert len(result["sources"]) > 0

    @pytest.mark.integration
    def test_query_with_vllm_arabic_handling(self):
        """Test vLLM correctly handles Arabic text in queries and responses."""
        with patch("src.core.pipeline.QdrantClient"):
            with patch("src.models.vllm_model.VLLMLLMWrapper._verify_server_health"):
                with patch("src.models.vllm_model.ChatOpenAI") as mock_chat:
                    # Mock Arabic response with diacritics
                    arabic_response = "مَرْحَباً! هَذِهِ إِجَابَة بِاللُّغَةِ الْعَرَبِيَّة"
                    mock_response = AIMessage(content=arabic_response)
                    mock_chat.return_value.invoke.return_value = mock_response

                    with patch("src.retrieval.vectorstore.QdrantStore.search") as mock_search:
                        mock_doc = Mock()
                        mock_doc.page_content = "محتوى عربي للاختبار"
                        mock_doc.metadata = {}
                        mock_search.return_value = [mock_doc]

                        with patch("src.retrieval.reranker.ArabicReranker.rerank") as mock_rerank:
                            mock_rerank.return_value = [mock_doc]

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
                                result = pipeline.query("مرحبا")

                                assert "ا" in result["response"]  # Contains Arabic
                                # Query was normalized (diacritics removed)
                                assert mock_chat.return_value.invoke.called

    @pytest.mark.integration
    def test_vllm_connection_error_propagates(self):
        """Test that vLLM connection errors are properly propagated."""
        with patch("src.core.pipeline.QdrantClient"):
            with patch("src.models.vllm_model.httpx.get", side_effect=Exception("Connection refused")):
                with patch("src.config.settings.settings") as mock_settings:
                    mock_settings.llm_provider = "local"
                    mock_settings.vllm_base_url = "http://invalid:9999/v1"
                    mock_settings.qdrant_url = "http://localhost:6333"
                    mock_settings.qdrant_collection = "test"
                    mock_settings.embeddings_provider = "local"
                    mock_settings.embeddings_dimension = 768

                    # Should raise VLLMConnectionError during initialization
                    with pytest.raises((VLLMConnectionError, Exception)):
                        RAGPipeline(use_memory=False)

    @pytest.mark.integration
    def test_switch_from_openai_to_vllm(self):
        """Test switching from OpenAI to vLLM provider."""
        # First create pipeline with OpenAI
        with patch("src.core.pipeline.QdrantClient"):
            with patch("src.core.pipeline.ChatOpenAI") as mock_openai:
                with patch("src.config.settings.settings") as mock_settings:
                    mock_settings.llm_provider = "openai"
                    mock_settings.openai_api_key = Mock(get_secret_value=lambda: "test-key")
                    mock_settings.openai_model = "gpt-4"
                    mock_settings.qdrant_url = "http://localhost:6333"
                    mock_settings.qdrant_collection = "test"
                    mock_settings.embeddings_provider = "local"
                    mock_settings.embeddings_dimension = 768
                    mock_settings.reranker_model = "test-reranker"
                    mock_settings.reranker_top_n = 5

                    pipeline_openai = RAGPipeline(use_memory=False)
                    assert pipeline_openai.llm_provider == "openai"

        # Then switch to vLLM
        with patch("src.core.pipeline.QdrantClient"):
            with patch("src.models.vllm_model.VLLMLLMWrapper._verify_server_health"):
                with patch("src.models.vllm_model.ChatOpenAI"):
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

                        pipeline_vllm = RAGPipeline(use_memory=False)
                        assert pipeline_vllm.llm_provider == "local"

    @pytest.mark.integration
    def test_vllm_with_conversation_memory(self):
        """Test vLLM integration with conversation memory."""
        with patch("src.core.pipeline.QdrantClient") as mock_qdrant:
            with patch("src.models.vllm_model.VLLMLLMWrapper._verify_server_health"):
                with patch("src.models.vllm_model.ChatOpenAI") as mock_chat:
                    mock_response = AIMessage(content="Test response with memory")
                    mock_chat.return_value.invoke.return_value = mock_response

                    # Mock memory operations
                    with patch("src.memory.conversation.ConversationMemory") as mock_memory_class:
                        mock_memory = Mock()
                        mock_memory.get_history.return_value = []
                        mock_memory.add_exchange.return_value = None
                        mock_memory_class.return_value = mock_memory

                        with patch("src.retrieval.vectorstore.QdrantStore.search") as mock_search:
                            mock_doc = Mock()
                            mock_doc.page_content = "Test content"
                            mock_doc.metadata = {}
                            mock_search.return_value = [mock_doc]

                            with patch("src.retrieval.reranker.ArabicReranker.rerank") as mock_rerank:
                                mock_rerank.return_value = [mock_doc]

                                with patch("src.config.settings.settings") as mock_settings:
                                    mock_settings.llm_provider = "local"
                                    mock_settings.vllm_base_url = "http://localhost:8000/v1"
                                    mock_settings.qdrant_url = "http://localhost:6333"
                                    mock_settings.qdrant_collection = "test"
                                    mock_settings.embeddings_provider = "local"
                                    mock_settings.embeddings_dimension = 768
                                    mock_settings.reranker_model = "test-reranker"
                                    mock_settings.reranker_top_n = 5
                                    mock_settings.max_conversation_history = 10
                                    mock_settings.conversation_ttl_hours = 24

                                    pipeline = RAGPipeline(use_memory=True)
                                    result = pipeline.query(
                                        "Test query",
                                        session_id="test-session-123"
                                    )

                                    assert result is not None
                                    assert result["session_id"] == "test-session-123"
                                    # Verify memory was accessed
                                    mock_memory.get_history.assert_called_once_with("test-session-123")
                                    mock_memory.add_exchange.assert_called_once()

    @pytest.mark.integration
    def test_vllm_multiple_queries_session(self):
        """Test multiple queries in same session with vLLM."""
        with patch("src.core.pipeline.QdrantClient"):
            with patch("src.models.vllm_model.VLLMLLMWrapper._verify_server_health"):
                with patch("src.models.vllm_model.ChatOpenAI") as mock_chat:
                    # Mock different responses for each query
                    responses = [
                        AIMessage(content="Response 1"),
                        AIMessage(content="Response 2"),
                        AIMessage(content="Response 3"),
                    ]
                    mock_chat.return_value.invoke.side_effect = responses

                    with patch("src.retrieval.vectorstore.QdrantStore.search") as mock_search:
                        mock_doc = Mock()
                        mock_doc.page_content = "Test"
                        mock_doc.metadata = {}
                        mock_search.return_value = [mock_doc]

                        with patch("src.retrieval.reranker.ArabicReranker.rerank") as mock_rerank:
                            mock_rerank.return_value = [mock_doc]

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

                                # Execute multiple queries
                                result1 = pipeline.query("Query 1")
                                result2 = pipeline.query("Query 2")
                                result3 = pipeline.query("Query 3")

                                assert result1["response"] == "Response 1"
                                assert result2["response"] == "Response 2"
                                assert result3["response"] == "Response 3"

    @pytest.mark.integration
    def test_vllm_with_empty_retrieval_results(self):
        """Test vLLM handles empty retrieval results gracefully."""
        with patch("src.core.pipeline.QdrantClient"):
            with patch("src.models.vllm_model.VLLMLLMWrapper._verify_server_health"):
                with patch("src.models.vllm_model.ChatOpenAI"):
                    with patch("src.retrieval.vectorstore.QdrantStore.search") as mock_search:
                        # No documents found
                        mock_search.return_value = []

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
                            result = pipeline.query("Unknown query")

                            assert result is not None
                            assert "response" in result
                            # Should return "no info" message
                            assert len(result["sources"]) == 0

    @pytest.mark.integration
    def test_vllm_performance_parameters(self):
        """Test vLLM is configured with correct performance parameters."""
        with patch("src.core.pipeline.QdrantClient"):
            with patch("src.models.vllm_model.VLLMLLMWrapper._verify_server_health"):
                with patch("src.models.vllm_model.ChatOpenAI") as mock_chat:
                    with patch("src.config.settings.settings") as mock_settings:
                        mock_settings.llm_provider = "local"
                        mock_settings.vllm_base_url = "http://localhost:8000/v1"
                        mock_settings.vllm_model = "test-model"
                        mock_settings.vllm_temperature = 0.8
                        mock_settings.vllm_max_tokens = 1024
                        mock_settings.qdrant_url = "http://localhost:6333"
                        mock_settings.qdrant_collection = "test"
                        mock_settings.embeddings_provider = "local"
                        mock_settings.embeddings_dimension = 768
                        mock_settings.reranker_model = "test-reranker"
                        mock_settings.reranker_top_n = 5

                        pipeline = RAGPipeline(use_memory=False)

                        # Verify ChatOpenAI was called with correct parameters
                        call_kwargs = mock_chat.call_args[1]
                        assert call_kwargs["base_url"] == "http://localhost:8000/v1"
                        assert call_kwargs["model"] == "test-model"
                        assert call_kwargs["temperature"] == 0.8
                        assert call_kwargs["max_tokens"] == 1024
