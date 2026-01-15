"""Pytest configuration and shared fixtures for testing."""

import pytest
from qdrant_client import QdrantClient
from unittest.mock import Mock

# Sample Arabic test data
ARABIC_TEST_DATA = {
    "greetings": ["مرحبا", "السلام عليكم", "صباح الخير"],
    "questions": [
        "ما هي عاصمة مصر؟",
        "من هو أول رئيس لمصر؟",
        "كم عدد سكان القاهرة؟",
    ],
    "answers": [
        "القاهرة هي عاصمة جمهورية مصر العربية.",
        "محمد نجيب هو أول رئيس لمصر.",
        "يبلغ عدد سكان القاهرة حوالي 10 مليون نسمة.",
    ],
}


@pytest.fixture
def sample_arabic_text() -> str:
    """Provide sample Arabic text for testing."""
    return "هذا نص تجريبي باللغة العربية للاختبار."


@pytest.fixture
def sample_query() -> str:
    """Provide sample query for testing."""
    return "ما هي أفضل الممارسات؟"


@pytest.fixture
def qdrant_memory_client():
    """In-memory Qdrant client for testing."""
    return QdrantClient(":memory:")


@pytest.fixture
def arabic_test_texts():
    """Sample Arabic texts for testing."""
    return ARABIC_TEST_DATA


@pytest.fixture
def mock_openai_response():
    """Mock OpenAI API response."""
    mock = Mock()
    mock.content = "هذه إجابة تجريبية"
    return mock
