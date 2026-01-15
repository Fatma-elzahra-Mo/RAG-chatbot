"""
Unit tests for ArabicReranker.

Tests reranking functionality with ARA-Reranker-V1.
"""

import pytest
from langchain_core.documents import Document

from src.retrieval.reranker import ArabicReranker


class TestArabicReranker:
    """Test suite for ArabicReranker."""

    @pytest.fixture
    def reranker(self):
        """Create reranker instance for testing."""
        return ArabicReranker(top_n=3, device="cpu")

    @pytest.fixture
    def sample_documents(self):
        """Create sample documents for testing."""
        return [
            Document(
                page_content="القاهرة هي عاصمة جمهورية مصر العربية وأكبر مدنها",
                metadata={"source": "doc1"},
            ),
            Document(
                page_content="مصر دولة عربية تقع في شمال أفريقيا",
                metadata={"source": "doc2"},
            ),
            Document(
                page_content="الإسكندرية مدينة ساحلية تقع على البحر الأبيض المتوسط",
                metadata={"source": "doc3"},
            ),
            Document(
                page_content="النيل هو أطول نهر في العالم ويمر عبر مصر",
                metadata={"source": "doc4"},
            ),
        ]

    def test_initialization(self, reranker):
        """Test reranker initialization."""
        assert reranker.top_n == 3
        assert reranker.device == "cpu"
        assert reranker.model is not None

    def test_rerank_basic(self, reranker, sample_documents):
        """Test basic reranking functionality."""
        query = "ما هي عاصمة مصر؟"

        reranked = reranker.rerank(query, sample_documents, top_n=2)

        # Should return 2 documents
        assert len(reranked) == 2

        # Most relevant doc should be first (contains "القاهرة" and "عاصمة")
        assert "القاهرة" in reranked[0].page_content
        assert "عاصمة" in reranked[0].page_content

    def test_rerank_empty_documents(self, reranker):
        """Test reranking with empty document list."""
        query = "ما هي عاصمة مصر؟"
        reranked = reranker.rerank(query, [])

        assert reranked == []

    def test_rerank_with_scores(self, reranker, sample_documents):
        """Test reranking with score output."""
        query = "ما هي عاصمة مصر؟"

        reranked_with_scores = reranker.rerank_with_scores(query, sample_documents)

        # Should return list of (document, score) tuples
        assert len(reranked_with_scores) == 3
        assert all(isinstance(item, tuple) for item in reranked_with_scores)
        assert all(len(item) == 2 for item in reranked_with_scores)

        # Scores should be descending
        scores = [score for _, score in reranked_with_scores]
        assert scores == sorted(scores, reverse=True)

    def test_rerank_custom_top_n(self, reranker, sample_documents):
        """Test reranking with custom top_n."""
        query = "ما هي عاصمة مصر؟"

        # Override default top_n
        reranked = reranker.rerank(query, sample_documents, top_n=1)

        assert len(reranked) == 1

    def test_rerank_relevance_order(self, reranker, sample_documents):
        """Test that reranking improves relevance order."""
        query = "عاصمة مصر"

        # Get reranked documents
        reranked = reranker.rerank(query, sample_documents)

        # First document should be most relevant (about Cairo as capital)
        assert "القاهرة" in reranked[0].page_content
        assert "عاصمة" in reranked[0].page_content

    def test_rerank_preserves_metadata(self, reranker, sample_documents):
        """Test that reranking preserves document metadata."""
        query = "ما هي عاصمة مصر؟"

        reranked = reranker.rerank(query, sample_documents)

        # All documents should have metadata
        assert all(doc.metadata for doc in reranked)
        assert all("source" in doc.metadata for doc in reranked)
