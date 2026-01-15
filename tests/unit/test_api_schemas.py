"""
Unit tests for API schemas.

Tests Pydantic model validation for all request/response schemas.
"""

import pytest

from src.models.schemas import (
    ChatRequest,
    ChatResponse,
    DocumentIngestRequest,
    DocumentIngestResponse,
    HealthResponse,
    SessionClearResponse,
    Source,
)


class TestChatRequest:
    """Test ChatRequest schema."""

    def test_chat_request_valid(self):
        """Test valid chat request."""
        req = ChatRequest(query="مرحبا", session_id="test123")
        assert req.query == "مرحبا"
        assert req.session_id == "test123"
        assert req.use_rag is True

    def test_chat_request_minimal(self):
        """Test minimal chat request (only query)."""
        req = ChatRequest(query="Hello")
        assert req.query == "Hello"
        assert req.session_id is None
        assert req.use_rag is True

    def test_chat_request_empty_query_fails(self):
        """Test that empty query fails validation."""
        with pytest.raises(ValueError):
            ChatRequest(query="")

    def test_chat_request_use_rag_false(self):
        """Test chat request with use_rag=False."""
        req = ChatRequest(query="Test", use_rag=False)
        assert req.use_rag is False


class TestChatResponse:
    """Test ChatResponse schema."""

    def test_chat_response_valid(self):
        """Test valid chat response."""
        resp = ChatResponse(
            response="مرحبا بك",
            sources=[],
            query_type="greeting",
        )
        assert resp.response == "مرحبا بك"
        assert resp.sources == []
        assert resp.query_type == "greeting"
        assert resp.session_id is None

    def test_chat_response_with_sources(self):
        """Test chat response with sources."""
        source = Source(content="Test content", metadata={"page": 1})
        resp = ChatResponse(
            response="Answer",
            sources=[source],
            query_type="rag",
            session_id="test123",
        )
        assert len(resp.sources) == 1
        assert resp.sources[0].content == "Test content"
        assert resp.session_id == "test123"


class TestSource:
    """Test Source schema."""

    def test_source_valid(self):
        """Test valid source."""
        source = Source(content="Test content", metadata={"key": "value"})
        assert source.content == "Test content"
        assert source.metadata == {"key": "value"}

    def test_source_empty_metadata(self):
        """Test source with empty metadata."""
        source = Source(content="Test")
        assert source.metadata == {}


class TestDocumentIngestRequest:
    """Test DocumentIngestRequest schema."""

    def test_document_ingest_request_valid(self):
        """Test valid document ingest request."""
        req = DocumentIngestRequest(
            texts=["Document 1", "Document 2"], metadatas=[{"page": 1}, {"page": 2}]
        )
        assert len(req.texts) == 2
        assert len(req.metadatas) == 2

    def test_document_ingest_request_no_metadata(self):
        """Test document ingest request without metadata."""
        req = DocumentIngestRequest(texts=["Document 1"])
        assert len(req.texts) == 1
        assert req.metadatas is None

    def test_document_ingest_request_empty_texts_fails(self):
        """Test that empty texts list fails validation."""
        with pytest.raises(ValueError):
            DocumentIngestRequest(texts=[])


class TestDocumentIngestResponse:
    """Test DocumentIngestResponse schema."""

    def test_document_ingest_response_valid(self):
        """Test valid document ingest response."""
        resp = DocumentIngestResponse(
            message="Success", documents_ingested=5, chunks_created=20
        )
        assert resp.message == "Success"
        assert resp.documents_ingested == 5
        assert resp.chunks_created == 20


class TestSessionClearResponse:
    """Test SessionClearResponse schema."""

    def test_session_clear_response_valid(self):
        """Test valid session clear response."""
        resp = SessionClearResponse(message="Cleared", session_id="test123")
        assert resp.message == "Cleared"
        assert resp.session_id == "test123"


class TestHealthResponse:
    """Test HealthResponse schema."""

    def test_health_response_valid(self):
        """Test valid health response."""
        resp = HealthResponse(
            status="healthy", version="1.0.0", components={"qdrant": "ok", "embeddings": "ok"}
        )
        assert resp.status == "healthy"
        assert resp.version == "1.0.0"
        assert resp.components["qdrant"] == "ok"

    def test_health_response_degraded(self):
        """Test degraded health response."""
        resp = HealthResponse(
            status="degraded",
            version="1.0.0",
            components={"qdrant": "error", "embeddings": "ok"},
        )
        assert resp.status == "degraded"
        assert resp.components["qdrant"] == "error"
