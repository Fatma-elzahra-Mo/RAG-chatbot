"""
Unit tests for Arabic sentence-aware chunker.
"""

import pytest
from langchain_core.documents import Document

from src.preprocessing.chunker import ArabicSentenceChunker


class TestArabicSentenceChunker:
    """Test suite for ArabicSentenceChunker."""

    @pytest.fixture
    def chunker(self):
        """Create chunker with test-friendly parameters."""
        return ArabicSentenceChunker(max_chunk_size=100, overlap=20, min_chunk_size=10)

    def test_simple_chunking(self, chunker):
        """Test basic chunking with Arabic sentences."""
        text = "السلام عليكم. كيف حالك؟ أنا بخير."
        chunks = chunker.chunk(text)
        assert len(chunks) > 0
        assert all(isinstance(c, str) for c in chunks)

    def test_respects_max_size(self, chunker):
        """Test that chunks respect maximum size limit."""
        text = "مرحبا. " * 50
        chunks = chunker.chunk(text)
        assert all(len(c) <= chunker.max_chunk_size for c in chunks)

    def test_respects_min_size(self):
        """Test that chunks below minimum size are discarded."""
        chunker = ArabicSentenceChunker(max_chunk_size=100, min_chunk_size=10)
        text = "ا. ب. ج."
        chunks = chunker.chunk(text)
        assert all(len(c) >= chunker.min_chunk_size for c in chunks)

    def test_overlap_between_chunks(self, chunker):
        """Test that chunks have overlapping content."""
        text = "الجملة الأولى. " * 10
        chunks = chunker.chunk(text)
        if len(chunks) > 1:
            # Verify overlap exists between consecutive chunks
            assert any(
                chunks[i][-10:] in chunks[i + 1] for i in range(len(chunks) - 1)
            )

    def test_empty_string(self, chunker):
        """Test handling of empty string."""
        chunks = chunker.chunk("")
        assert len(chunks) == 0

    def test_single_sentence(self, chunker):
        """Test chunking of single sentence."""
        text = "هذه جملة واحدة."
        chunks = chunker.chunk(text)
        assert len(chunks) == 1
        assert "هذه جملة واحدة" in chunks[0]

    def test_chunk_documents(self, chunker):
        """Test chunking of LangChain documents."""
        docs = [
            Document(page_content="السلام عليكم. كيف حالك؟", metadata={"source": "test"}),
        ]
        chunked = chunker.chunk_documents(docs)
        assert len(chunked) > 0
        assert all(isinstance(d, Document) for d in chunked)
        assert all("chunk_index" in d.metadata for d in chunked)
        assert all("total_chunks" in d.metadata for d in chunked)
        assert all(d.metadata["source"] == "test" for d in chunked)

    def test_metadata_preservation(self, chunker):
        """Test that original metadata is preserved in chunks."""
        docs = [
            Document(
                page_content="مرحبا. كيف حالك؟",
                metadata={"source": "test", "author": "user"},
            ),
        ]
        chunked = chunker.chunk_documents(docs)
        for doc in chunked:
            assert doc.metadata["source"] == "test"
            assert doc.metadata["author"] == "user"

    def test_long_text_chunking(self, chunker):
        """Test chunking of text longer than max_chunk_size."""
        text = "مرحبا بك في هذا النص الطويل. " * 20
        chunks = chunker.chunk(text)
        assert len(chunks) > 1
        assert all(len(c) <= chunker.max_chunk_size for c in chunks)

    def test_arabic_delimiters(self, chunker):
        """Test recognition of Arabic-specific sentence delimiters."""
        text = "السؤال الأول؟ السؤال الثاني؟ السؤال الثالث؟"
        chunks = chunker.chunk(text)
        assert len(chunks) > 0
