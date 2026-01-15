"""
Unit tests for BGE-M3 embeddings wrapper.
"""

import pytest

from src.retrieval.embeddings import BGEEmbeddings


class TestBGEEmbeddings:
    """Test suite for BGEEmbeddings."""

    @pytest.fixture
    def embeddings(self):
        """Create BGE embeddings instance."""
        # Note: This will download the model on first run
        return BGEEmbeddings(device="cpu")

    def test_embed_query(self, embeddings):
        """Test embedding of a single query."""
        vector = embeddings.embed_query("ما هي عاصمة مصر؟")
        assert isinstance(vector, list)
        assert len(vector) == 1024
        assert all(isinstance(v, float) for v in vector)

    def test_embed_documents(self, embeddings):
        """Test batch embedding of multiple documents."""
        texts = ["مرحبا", "كيف حالك", "أنا بخير"]
        vectors = embeddings.embed_documents(texts)
        assert len(vectors) == len(texts)
        assert all(len(v) == 1024 for v in vectors)
        assert all(isinstance(v, list) for v in vectors)

    def test_empty_text(self, embeddings):
        """Test embedding of empty text."""
        vector = embeddings.embed_query("")
        assert isinstance(vector, list)
        assert len(vector) == 1024

    def test_arabic_text(self, embeddings):
        """Test embedding of Arabic text."""
        arabic_text = "اللغة العربية جميلة"
        vector = embeddings.embed_query(arabic_text)
        assert len(vector) == 1024
        assert not all(v == 0 for v in vector)

    def test_vector_normalization(self, embeddings):
        """Test that vectors are normalized (if enabled)."""
        vector = embeddings.embed_query("مرحبا")
        # For normalized vectors, L2 norm should be close to 1.0
        import math

        l2_norm = math.sqrt(sum(v**2 for v in vector))
        assert 0.95 <= l2_norm <= 1.05

    def test_consistent_embeddings(self, embeddings):
        """Test that same text produces same embeddings."""
        text = "مرحبا بك"
        vector1 = embeddings.embed_query(text)
        vector2 = embeddings.embed_query(text)
        assert vector1 == vector2
