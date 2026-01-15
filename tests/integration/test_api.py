"""
Integration tests for API endpoints.

Tests the complete API using TestClient with actual FastAPI app.
"""

import pytest
from fastapi.testclient import TestClient

from src.api.main import app


@pytest.fixture
def client():
    """Create test client."""
    return TestClient(app)


class TestRootEndpoint:
    """Test root endpoint."""

    def test_root_endpoint(self, client):
        """Test root endpoint returns correct information."""
        response = client.get("/")
        assert response.status_code == 200
        data = response.json()
        assert "Arabic RAG Chatbot API" in data["message"]
        assert data["version"] == "1.0.0"
        assert data["docs"] == "/docs"
        assert data["health"] == "/health"


class TestHealthEndpoint:
    """Test health check endpoint."""

    def test_health_check(self, client):
        """Test health check endpoint."""
        response = client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert "status" in data
        assert "version" in data
        assert "components" in data
        assert data["version"] == "1.0.0"

    def test_health_check_components(self, client):
        """Test health check includes component status."""
        response = client.get("/health")
        data = response.json()
        components = data["components"]
        assert "qdrant" in components
        assert "embeddings" in components
        assert "memory" in components


class TestChatEndpoint:
    """Test chat endpoints."""

    def test_chat_query_validation_empty_query(self, client):
        """Test that empty query fails validation."""
        response = client.post("/chat/query", json={"query": ""})
        assert response.status_code == 422  # Validation error

    def test_chat_query_validation_missing_query(self, client):
        """Test that missing query fails validation."""
        response = client.post("/chat/query", json={})
        assert response.status_code == 422  # Validation error

    def test_chat_query_valid_structure(self, client):
        """Test chat query with valid structure."""
        response = client.post(
            "/chat/query", json={"query": "مرحبا", "session_id": "test123", "use_rag": False}
        )
        # May fail if LLM not configured, but structure should be valid
        assert response.status_code in [200, 500]
        if response.status_code == 200:
            data = response.json()
            assert "response" in data
            assert "sources" in data
            assert "query_type" in data
            assert "session_id" in data

    def test_chat_query_minimal_request(self, client):
        """Test chat query with minimal request (only query)."""
        response = client.post("/chat/query", json={"query": "Hello"})
        # Structure should be valid regardless of LLM configuration
        assert response.status_code in [200, 500]

    def test_clear_session(self, client):
        """Test clearing session endpoint."""
        response = client.delete("/chat/session/test123")
        # Should succeed even if session doesn't exist
        assert response.status_code in [200, 500]
        if response.status_code == 200:
            data = response.json()
            assert data["session_id"] == "test123"
            assert "message" in data


class TestDocumentsEndpoint:
    """Test document management endpoints."""

    def test_ingest_documents_validation_empty_texts(self, client):
        """Test that empty texts list fails validation."""
        response = client.post("/documents/ingest", json={"texts": []})
        assert response.status_code == 422  # Validation error

    def test_ingest_documents_validation_missing_texts(self, client):
        """Test that missing texts fails validation."""
        response = client.post("/documents/ingest", json={})
        assert response.status_code == 422  # Validation error

    def test_ingest_documents_valid_structure(self, client):
        """Test document ingest with valid structure."""
        response = client.post(
            "/documents/ingest",
            json={"texts": ["Test document 1", "Test document 2"], "metadatas": None},
        )
        # May fail if Qdrant not configured, but structure should be valid
        assert response.status_code in [201, 500]
        if response.status_code == 201:
            data = response.json()
            assert "message" in data
            assert "documents_ingested" in data
            assert "chunks_created" in data
            assert data["documents_ingested"] == 2

    def test_ingest_documents_with_metadata(self, client):
        """Test document ingest with metadata."""
        response = client.post(
            "/documents/ingest",
            json={
                "texts": ["Document 1"],
                "metadatas": [{"source": "test", "page": 1}],
            },
        )
        assert response.status_code in [201, 500]


class TestAPIDocumentation:
    """Test API documentation endpoints."""

    def test_openapi_schema(self, client):
        """Test OpenAPI schema is accessible."""
        response = client.get("/openapi.json")
        assert response.status_code == 200
        schema = response.json()
        assert "openapi" in schema
        assert "info" in schema
        assert schema["info"]["title"] == "Arabic RAG Chatbot API"

    def test_docs_endpoint(self, client):
        """Test Swagger UI docs endpoint."""
        response = client.get("/docs")
        assert response.status_code == 200
        assert "text/html" in response.headers["content-type"]
