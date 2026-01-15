"""
Integration test for plain text file ingestion.

Tests the complete flow from text extraction through chunking and vector storage.
"""

import io
import pytest
from qdrant_client import QdrantClient

from src.core.pipeline import RAGPipeline
from src.models.schemas import FileFormat


class TestPlainTextIngestion:
    """Integration tests for plain text file ingestion."""

    @pytest.fixture
    def pipeline(self):
        """Create RAG pipeline with in-memory Qdrant."""
        client = QdrantClient(":memory:")
        return RAGPipeline(qdrant_url=None, use_memory=False)

    def test_ingest_utf8_arabic_text(self, pipeline):
        """Test ingestion of UTF-8 Arabic text file."""
        content = """مقدمة عن الذكاء الاصطناعي
هذا نص تجريبي باللغة العربية يحتوي على عدة أسطر.

الذكاء الاصطناعي هو محاكاة عمليات الذكاء البشري بواسطة الآلات،
وخاصة أنظمة الكمبيوتر. تشمل هذه العمليات التعلم واكتساب المعلومات
والاستدلال والتصحيح الذاتي.
"""
        file_obj = io.BytesIO(content.encode("utf-8"))

        response = pipeline.ingest_file(file_obj, "arabic_intro.txt")

        # Verify successful ingestion
        assert response.message == "File ingested successfully"
        assert response.file_format == FileFormat.TEXT
        assert response.chunks_created > 0
        assert response.documents_created == 1

        # Verify text-specific metadata
        assert "detected_encoding" in response.metadata
        assert response.metadata["detected_encoding"] in ["utf-8", "ascii"]
        assert "line_ending_style" in response.metadata
        assert "has_structure" in response.metadata
        assert response.metadata["source_format"] == "text"

    def test_ingest_structured_text(self, pipeline):
        """Test ingestion of structured text with numbering."""
        content = """Project Requirements

1. First Requirement
   This is the detailed description of the first requirement.

2. Second Requirement
   This is the detailed description of the second requirement.

3. Third Requirement
   This is the detailed description of the third requirement.
"""
        file_obj = io.BytesIO(content.encode("utf-8"))

        response = pipeline.ingest_file(file_obj, "requirements.txt")

        # Verify successful ingestion
        assert response.message == "File ingested successfully"
        assert response.chunks_created > 0

        # Verify structure detection
        assert response.metadata.get("has_structure") is True
        assert response.metadata.get("has_numbered_sections") is True

    def test_ingest_mixed_language_text(self, pipeline):
        """Test ingestion of mixed Arabic-English text."""
        content = """Project: المشروع العربي

Introduction:
This is a bilingual document combining Arabic and English text.

المقدمة:
هذا مستند ثنائي اللغة يجمع بين النصوص العربية والإنجليزية.

Features:
- Feature 1: Bilingual support
- Feature 2: UTF-8 encoding
- الميزة 3: دعم اللغة العربية
"""
        file_obj = io.BytesIO(content.encode("utf-8"))

        response = pipeline.ingest_file(file_obj, "bilingual.txt")

        # Verify successful ingestion
        assert response.message == "File ingested successfully"
        assert response.chunks_created > 0

        # Verify metadata
        assert response.metadata["detected_encoding"] in ["utf-8", "ascii"]
        assert response.metadata.get("has_structure") is True
        assert response.metadata.get("has_bullet_points") is True

    def test_text_chunks_have_metadata(self, pipeline):
        """Test that text chunks inherit file metadata."""
        content = "Test content for metadata verification.\nSecond line.\nThird line.\n"
        file_obj = io.BytesIO(content.encode("utf-8"))

        response = pipeline.ingest_file(file_obj, "meta_test.txt")

        assert response.message == "File ingested successfully"
        assert response.chunks_created > 0

        # The metadata in response should contain text-specific fields
        # These will be propagated to all chunks in Qdrant
        assert "detected_encoding" in response.metadata
        assert "line_ending_style" in response.metadata
        assert "source_format" in response.metadata
        assert response.metadata["source_format"] == "text"

    def test_empty_text_file(self, pipeline):
        """Test handling of empty text file."""
        file_obj = io.BytesIO(b"")

        response = pipeline.ingest_file(file_obj, "empty.txt")

        # Should fail gracefully
        assert "No text content extracted" in response.message or "empty" in response.message.lower()
        assert response.chunks_created == 0

    def test_large_text_file(self, pipeline):
        """Test ingestion of larger text file."""
        # Create a ~5KB text file
        content = "مرحبا بالعالم - Hello World\n" * 200
        file_obj = io.BytesIO(content.encode("utf-8"))

        response = pipeline.ingest_file(file_obj, "large.txt")

        # Verify successful ingestion with multiple chunks
        assert response.message == "File ingested successfully"
        assert response.chunks_created > 1  # Should create multiple chunks
        assert response.file_size_bytes > 5000
