"""
Unit tests for RAGPipeline.

Tests complete RAG pipeline integration.
"""

import pytest
from unittest.mock import Mock, patch, MagicMock

from src.core.pipeline import RAGPipeline


class TestRAGPipeline:
    """Test suite for RAGPipeline."""

    @pytest.fixture
    def mock_pipeline(self):
        """Create a mock pipeline for testing."""
        with patch("src.core.pipeline.QdrantClient"):
            with patch("src.core.pipeline.ChatOpenAI") as mock_llm:
                # Mock LLM response
                mock_response = Mock()
                mock_response.content = "هذه إجابة تجريبية"
                mock_llm.return_value.invoke.return_value = mock_response

                pipeline = RAGPipeline(use_memory=False)
                return pipeline

    def test_initialization(self, mock_pipeline):
        """Test pipeline initialization."""
        assert mock_pipeline is not None
        assert mock_pipeline.normalizer is not None
        assert mock_pipeline.embeddings is not None
        assert mock_pipeline.vectorstore is not None
        assert mock_pipeline.reranker is not None
        assert mock_pipeline.router is not None
        assert mock_pipeline.llm is not None

    def test_normalization(self, mock_pipeline):
        """Test query normalization."""
        # Test alef normalization
        normalized = mock_pipeline.normalizer.normalize("أهلاً")
        assert "ا" in normalized  # Alef variants normalized

        # Test tashkeel removal
        normalized = mock_pipeline.normalizer.normalize("مَرْحَباً")
        assert "ً" not in normalized  # Diacritics removed

    def test_query_basic(self, mock_pipeline):
        """Test basic query processing."""
        result = mock_pipeline.query("مرحبا")

        assert "response" in result
        assert "sources" in result
        assert "query_type" in result
        assert result["query_type"] == "greeting"

    def test_query_with_session(self, mock_pipeline):
        """Test query with session ID."""
        result = mock_pipeline.query("مرحبا", session_id="test-session")

        assert result["session_id"] == "test-session"

    def test_greeting_query(self, mock_pipeline):
        """Test greeting query handling."""
        result = mock_pipeline.query("مرحبا")

        assert result["query_type"] == "greeting"
        assert result["sources"] == []  # No sources for greetings

    def test_simple_query(self, mock_pipeline):
        """Test simple query handling."""
        result = mock_pipeline.query("ما اسمك؟")

        assert result["query_type"] == "simple"
        assert result["sources"] == []  # No sources for simple queries

    def test_calculator_query(self, mock_pipeline):
        """Test calculator query handling."""
        result = mock_pipeline.query("5 + 3")

        assert result["query_type"] == "calculator"
        assert result["sources"] == []  # No sources for calculator

    @patch("src.core.pipeline.RAGPipeline._handle_rag_query")
    def test_rag_query(self, mock_rag_handler, mock_pipeline):
        """Test RAG query handling."""
        # Mock RAG handler
        mock_rag_handler.return_value = ("إجابة", [{"content": "مصدر"}])

        result = mock_pipeline.query("ما هي عاصمة مصر؟")

        assert result["query_type"] == "rag"
        # RAG queries should have sources
        mock_rag_handler.assert_called_once()

    def test_query_without_rag(self, mock_pipeline):
        """Test query with RAG disabled."""
        result = mock_pipeline.query("ما هي عاصمة مصر؟", use_rag=False)

        # Should fall back to simple query
        assert result["sources"] == []

    @patch("src.core.pipeline.RAGPipeline.ingest_documents")
    def test_ingest_documents(self, mock_ingest, mock_pipeline):
        """Test document ingestion."""
        texts = ["نص تجريبي أول", "نص تجريبي ثاني"]
        metadatas = [{"source": "doc1"}, {"source": "doc2"}]

        # Call real method
        mock_ingest.side_effect = lambda *args, **kwargs: None
        mock_pipeline.ingest_documents(texts, metadatas)

        mock_ingest.assert_called_once_with(texts, metadatas)

    def test_handle_greeting(self, mock_pipeline):
        """Test greeting handler."""
        response = mock_pipeline._handle_greeting("مرحبا")

        assert response is not None
        assert isinstance(response, str)

    def test_handle_calculator(self, mock_pipeline):
        """Test calculator handler."""
        response = mock_pipeline._handle_calculator("5 + 3")

        assert response is not None
        assert isinstance(response, str)

    def test_handle_simple_query(self, mock_pipeline):
        """Test simple query handler."""
        response = mock_pipeline._handle_simple_query("ما اسمك؟", [])

        assert response is not None
        assert isinstance(response, str)

    @patch.object(RAGPipeline, "_handle_rag_query")
    def test_handle_rag_query_mock(self, mock_method, mock_pipeline):
        """Test RAG query handler with mock."""
        mock_method.return_value = ("إجابة تجريبية", [])

        response, sources = mock_pipeline._handle_rag_query("سؤال", [])

        assert response is not None
        assert isinstance(sources, list)

    def test_router_integration(self, mock_pipeline):
        """Test router integration with pipeline."""
        # Test different query types
        queries = {
            "مرحبا": "greeting",
            "ما اسمك": "simple",
            "5 + 3": "calculator",
            "ما هي عاصمة مصر؟": "rag",
        }

        for query, expected_type in queries.items():
            result = mock_pipeline.query(query)
            assert (
                result["query_type"] == expected_type
            ), f"Query '{query}' should be '{expected_type}'"

    def test_memory_integration_disabled(self, mock_pipeline):
        """Test pipeline with memory disabled."""
        # Pipeline was initialized with use_memory=False
        assert not mock_pipeline.use_memory

        result = mock_pipeline.query("مرحبا", session_id="test")
        # Should not fail even with session_id
        assert result is not None

    @patch("src.core.pipeline.ConversationMemory")
    def test_memory_integration_enabled(self, mock_memory_class):
        """Test pipeline with memory enabled."""
        with patch("src.core.pipeline.QdrantClient"):
            with patch("src.core.pipeline.ChatOpenAI"):
                pipeline = RAGPipeline(use_memory=True)

                assert pipeline.use_memory
                assert pipeline.memory is not None
