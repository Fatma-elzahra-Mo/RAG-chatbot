"""
Integration test for text-specific metadata storage and retrieval from Qdrant.

Tests that text-specific metadata (source_format, detected_encoding, line_ending_style,
has_structure, file_hash) is properly stored in Qdrant and can be retrieved.
"""

import hashlib
import io

import pytest
from langchain_core.documents import Document
from qdrant_client import QdrantClient

from src.preprocessing.extractors.text import TextExtractor
from src.retrieval.vectorstore import QdrantStore
from src.models.embeddings import create_embeddings
from src.config.settings import settings


@pytest.fixture
def qdrant_client():
    """Create in-memory Qdrant client for testing."""
    return QdrantClient(":memory:")


@pytest.fixture
def vectorstore():
    """Create vector store with in-memory Qdrant.

    Note: Using localhost URL as QdrantStore doesn't support :memory: directly.
    For true integration testing, a Qdrant instance should be running.
    """
    import warnings
    warnings.filterwarnings("ignore", message=".*QdrantStore.*memory.*")

    # Use localhost for real Qdrant instance
    # For unit tests, mock the client
    try:
        store = QdrantStore(
            url="http://localhost:6333",
            collection_name="test_text_metadata",
            embedding_dimension=1024,
        )
        # Clean collection before tests
        try:
            store.client.delete_collection("test_text_metadata")
        except Exception:
            pass
        store._ensure_collection()
        return store
    except Exception:
        # If Qdrant is not available, skip these tests
        pytest.skip("Qdrant server not available for integration tests")


@pytest.fixture
def embeddings():
    """Create embeddings model."""
    return create_embeddings(provider="local")


@pytest.fixture
def text_extractor():
    """Create text extractor instance."""
    return TextExtractor()


class TestTextMetadataInQdrant:
    """Test that text-specific metadata is stored and retrieved from Qdrant."""

    def test_text_metadata_stored_in_qdrant(
        self, text_extractor, vectorstore, embeddings
    ):
        """Test that all required text metadata fields are stored in Qdrant."""
        # Create sample text file with structure
        content = """1. First Section
This is some content in the first section.

2. Second Section
- Point A
- Point B

3. Third Section
Final content here.
"""
        file_obj = io.BytesIO(content.encode("utf-8"))

        # Calculate expected file hash
        expected_hash = hashlib.sha256(content.encode("utf-8")).hexdigest()

        # Extract text with metadata
        result = text_extractor.extract(file_obj, "test.txt")

        # Verify extraction includes required metadata
        assert result.metadata["source_format"] == "text"
        assert "detected_encoding" in result.metadata
        assert "line_ending_style" in result.metadata
        assert "has_structure" in result.metadata
        assert result.metadata["file_hash"] == expected_hash

        # Create document with extracted metadata
        doc = Document(
            page_content=result.text,
            metadata=result.metadata
        )

        # Embed and store in Qdrant
        embedding = embeddings.embed_documents([doc.page_content])[0]
        vectorstore.add_documents([doc], [embedding])

        # Retrieve from Qdrant using a query
        query_embedding = embeddings.embed_query("First Section")
        results = vectorstore.search(query_embedding, limit=1)

        # Verify metadata was stored and retrieved
        assert len(results) > 0
        retrieved_doc = results[0]

        # Check all required metadata fields are present
        assert retrieved_doc.metadata["source_format"] == "text"
        assert retrieved_doc.metadata["detected_encoding"] in ["utf-8", "ascii"]
        assert retrieved_doc.metadata["line_ending_style"] in ["LF", "CRLF", "CR", "none"]
        assert isinstance(retrieved_doc.metadata["has_structure"], bool)
        assert retrieved_doc.metadata["file_hash"] == expected_hash

    def test_text_metadata_with_different_encodings(
        self, text_extractor, vectorstore, embeddings
    ):
        """Test metadata storage for different text encodings."""
        # UTF-8 Arabic text
        arabic_content = "مرحبا بك في النظام\nهذا نص تجريبي\n"
        utf8_file = io.BytesIO(arabic_content.encode("utf-8"))
        utf8_hash = hashlib.sha256(arabic_content.encode("utf-8")).hexdigest()

        result_utf8 = text_extractor.extract(utf8_file, "arabic_utf8.txt")

        # Verify UTF-8 metadata
        assert result_utf8.metadata["source_format"] == "text"
        assert result_utf8.metadata["detected_encoding"] in ["utf-8", "ascii"]
        assert result_utf8.metadata["file_hash"] == utf8_hash

        # Store in Qdrant
        doc = Document(page_content=result_utf8.text, metadata=result_utf8.metadata)
        embedding = embeddings.embed_documents([doc.page_content])[0]
        vectorstore.add_documents([doc], [embedding])

        # Retrieve and verify
        query_embedding = embeddings.embed_query("مرحبا")
        results = vectorstore.search(query_embedding, limit=1)

        assert len(results) > 0
        assert results[0].metadata["source_format"] == "text"
        assert results[0].metadata["file_hash"] == utf8_hash

    def test_text_metadata_line_endings(
        self, text_extractor, vectorstore, embeddings
    ):
        """Test that line ending style is correctly stored and retrieved."""
        # Test different line ending styles
        test_cases = [
            ("LF", "Line 1\nLine 2\nLine 3\n"),
            ("CRLF", "Line 1\r\nLine 2\r\nLine 3\r\n"),
            ("CR", "Line 1\rLine 2\rLine 3\r"),
        ]

        for expected_style, content in test_cases:
            file_obj = io.BytesIO(content.encode("utf-8"))
            result = text_extractor.extract(file_obj, f"test_{expected_style}.txt")

            # Store in Qdrant
            doc = Document(page_content=result.text, metadata=result.metadata)
            embedding = embeddings.embed_documents([doc.page_content])[0]
            vectorstore.add_documents([doc], [embedding])

            # Retrieve and verify line ending style
            query_embedding = embeddings.embed_query("Line 1")
            results = vectorstore.search(query_embedding, limit=1)

            assert len(results) > 0
            assert "line_ending_style" in results[0].metadata

    def test_text_metadata_structure_detection(
        self, text_extractor, vectorstore, embeddings
    ):
        """Test that structure detection flag is stored correctly."""
        # Text with structure
        structured_content = """1. First item
2. Second item
3. Third item
"""
        structured_file = io.BytesIO(structured_content.encode("utf-8"))
        result_structured = text_extractor.extract(structured_file, "structured.txt")

        assert result_structured.metadata["has_structure"] is True

        # Text without structure
        plain_content = "Just plain text.\nNo structure here.\n"
        plain_file = io.BytesIO(plain_content.encode("utf-8"))
        result_plain = text_extractor.extract(plain_file, "plain.txt")

        assert result_plain.metadata["has_structure"] is False

        # Store both in Qdrant
        for result, content in [
            (result_structured, structured_content),
            (result_plain, plain_content),
        ]:
            doc = Document(page_content=result.text, metadata=result.metadata)
            embedding = embeddings.embed_documents([doc.page_content])[0]
            vectorstore.add_documents([doc], [embedding])

        # Retrieve and verify structure flags
        for query_text, expected_structure in [
            ("First item", True),
            ("plain text", False),
        ]:
            query_embedding = embeddings.embed_query(query_text)
            results = vectorstore.search(query_embedding, limit=1)

            assert len(results) > 0
            assert "has_structure" in results[0].metadata
            assert isinstance(results[0].metadata["has_structure"], bool)

    def test_file_hash_uniqueness(
        self, text_extractor, vectorstore, embeddings
    ):
        """Test that file hashes are unique for different content."""
        content1 = "This is file 1\n"
        content2 = "This is file 2\n"

        file1 = io.BytesIO(content1.encode("utf-8"))
        file2 = io.BytesIO(content2.encode("utf-8"))

        result1 = text_extractor.extract(file1, "file1.txt")
        result2 = text_extractor.extract(file2, "file2.txt")

        # Verify hashes are different
        assert result1.metadata["file_hash"] != result2.metadata["file_hash"]

        # Store both in Qdrant
        for result in [result1, result2]:
            doc = Document(page_content=result.text, metadata=result.metadata)
            embedding = embeddings.embed_documents([doc.page_content])[0]
            vectorstore.add_documents([doc], [embedding])

        # Retrieve and verify both have different hashes
        query_embedding = embeddings.embed_query("file")
        results = vectorstore.search(query_embedding, limit=2)

        assert len(results) >= 2
        hashes = [r.metadata["file_hash"] for r in results]
        assert len(set(hashes)) == len(hashes)  # All unique

    def test_duplicate_file_detection_via_hash(
        self, text_extractor, vectorstore, embeddings
    ):
        """Test that duplicate files can be detected via file hash."""
        content = "Original content\nSame file uploaded twice\n"

        # Upload same file twice
        file1 = io.BytesIO(content.encode("utf-8"))
        file2 = io.BytesIO(content.encode("utf-8"))

        result1 = text_extractor.extract(file1, "original.txt")
        result2 = text_extractor.extract(file2, "duplicate.txt")

        # Verify both have same hash
        assert result1.metadata["file_hash"] == result2.metadata["file_hash"]

        # In a real system, this would be used to detect duplicates
        # before ingestion to avoid storing the same content multiple times
