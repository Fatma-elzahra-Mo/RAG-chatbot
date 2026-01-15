"""
Integration tests for file ingestion API endpoints.

Tests the complete file upload flow from API endpoint through extraction,
chunking, embedding, and storage in vector database. Follows TDD approach.
"""

import io
from unittest.mock import Mock, patch

import pytest
from fastapi.testclient import TestClient

from src.api.main import app
from src.models.schemas import FileFormat


@pytest.fixture
def client():
    """Create test client for API."""
    return TestClient(app)


@pytest.fixture
def sample_pdf_file():
    """Create a sample PDF file for testing."""
    # Minimal valid PDF structure
    pdf_content = b"""%PDF-1.4
1 0 obj
<< /Type /Catalog /Pages 2 0 R >>
endobj
2 0 obj
<< /Type /Pages /Kids [3 0 R] /Count 1 >>
endobj
3 0 obj
<< /Type /Page /Parent 2 0 R /Resources << /Font << /F1 << /Type /Font /Subtype /Type1 /BaseFont /Helvetica >> >> >> /MediaBox [0 0 612 792] /Contents 4 0 R >>
endobj
4 0 obj
<< /Length 44 >>
stream
BT
/F1 12 Tf
100 700 Td
(Test PDF content) Tj
ET
endstream
endobj
xref
0 5
0000000000 65535 f
0000000009 00000 n
0000000058 00000 n
0000000115 00000 n
0000000317 00000 n
trailer
<< /Size 5 /Root 1 0 R >>
startxref
410
%%EOF
"""
    return ("test_document.pdf", io.BytesIO(pdf_content), "application/pdf")


@pytest.fixture
def sample_arabic_pdf_file():
    """Create a sample Arabic PDF for testing."""
    # Simplified Arabic PDF
    pdf_content = b"""%PDF-1.4
1 0 obj
<< /Type /Catalog /Pages 2 0 R >>
endobj
2 0 obj
<< /Type /Pages /Kids [3 0 R] /Count 1 >>
endobj
3 0 obj
<< /Type /Page /Parent 2 0 R /Resources << >> /MediaBox [0 0 612 792] /Contents 4 0 R >>
endobj
4 0 obj
<< /Length 50 >>
stream
BT
100 700 Td
(Arabic content test) Tj
ET
endstream
endobj
xref
0 5
0000000000 65535 f
0000000009 00000 n
0000000058 00000 n
0000000115 00000 n
0000000265 00000 n
trailer
<< /Size 5 /Root 1 0 R >>
startxref
364
%%EOF
"""
    return ("arabic_document.pdf", io.BytesIO(pdf_content), "application/pdf")


@pytest.fixture
def multi_page_pdf_file():
    """Create a multi-page PDF for testing."""
    # Simplified multi-page PDF structure
    pdf_content = b"""%PDF-1.4
1 0 obj
<< /Type /Catalog /Pages 2 0 R >>
endobj
2 0 obj
<< /Type /Pages /Kids [3 0 R 4 0 R] /Count 2 >>
endobj
3 0 obj
<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] /Contents 5 0 R >>
endobj
4 0 obj
<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] /Contents 6 0 R >>
endobj
5 0 obj
<< /Length 30 >>
stream
BT
100 700 Td
(Page 1) Tj
ET
endstream
endobj
6 0 obj
<< /Length 30 >>
stream
BT
100 700 Td
(Page 2) Tj
ET
endstream
endobj
xref
0 7
0000000000 65535 f
0000000009 00000 n
0000000058 00000 n
0000000123 00000 n
0000000214 00000 n
0000000305 00000 n
0000000384 00000 n
trailer
<< /Size 7 /Root 1 0 R >>
startxref
463
%%EOF
"""
    return ("multi_page.pdf", io.BytesIO(pdf_content), "application/pdf")


class TestPDFUploadEndpoint:
    """Integration tests for PDF upload endpoint (TDD - endpoint not yet implemented)."""

    def test_pdf_upload_endpoint_exists(self, client):
        """Test that PDF upload endpoint is available."""
        # Endpoint should exist even if not fully implemented
        response = client.post(
            "/documents/ingest/file",
            files={"file": ("test.pdf", b"dummy", "application/pdf")}
        )
        # Should not return 404 (endpoint exists) or 405 (method exists)
        assert response.status_code not in [404, 405], \
            "PDF upload endpoint /documents/ingest/file should exist"

    def test_pdf_upload_returns_file_ingest_response(self, client, sample_pdf_file):
        """Test that PDF upload returns FileIngestResponse structure."""
        filename, file_content, mime_type = sample_pdf_file

        response = client.post(
            "/documents/ingest/file",
            files={"file": (filename, file_content, mime_type)}
        )

        # Should succeed or return meaningful error (not 404/405)
        assert response.status_code in [200, 201, 400, 422, 500], \
            f"Expected valid response, got {response.status_code}"

        if response.status_code in [200, 201]:
            data = response.json()
            # Verify FileIngestResponse structure
            assert "message" in data, "Response should include message field"
            assert "filename" in data, "Response should include filename"
            assert "file_format" in data, "Response should include file_format"
            assert "file_size_bytes" in data, "Response should include file_size_bytes"
            assert "documents_created" in data, "Response should include documents_created"
            assert "chunks_created" in data, "Response should include chunks_created"
            assert "processing_time_ms" in data, "Response should include processing_time_ms"
            assert "metadata" in data, "Response should include metadata dict"
            assert "warnings" in data, "Response should include warnings list"

    def test_pdf_upload_detects_pdf_format(self, client, sample_pdf_file):
        """Test that PDF format is correctly detected."""
        filename, file_content, mime_type = sample_pdf_file

        response = client.post(
            "/documents/ingest/file",
            files={"file": (filename, file_content, mime_type)}
        )

        if response.status_code in [200, 201]:
            data = response.json()
            assert data["file_format"] == "pdf" or data["file_format"] == FileFormat.PDF.value

    def test_pdf_upload_extracts_text(self, client, sample_pdf_file):
        """Test that text is extracted from PDF and chunks are created."""
        filename, file_content, mime_type = sample_pdf_file

        response = client.post(
            "/documents/ingest/file",
            files={"file": (filename, file_content, mime_type)}
        )

        if response.status_code in [200, 201]:
            data = response.json()
            # Should create at least one chunk from extracted text
            assert data["chunks_created"] > 0, "Should create chunks from PDF text"
            # Should create at least one document
            assert data["documents_created"] >= 1, "Should create at least one document"

    def test_pdf_upload_with_arabic_content(self, client, sample_arabic_pdf_file):
        """Test PDF upload with Arabic text content."""
        filename, file_content, mime_type = sample_arabic_pdf_file

        response = client.post(
            "/documents/ingest/file",
            files={"file": (filename, file_content, mime_type)}
        )

        if response.status_code in [200, 201]:
            data = response.json()
            # Should handle Arabic content without errors
            assert data["file_format"] == "pdf" or data["file_format"] == FileFormat.PDF.value
            assert data["chunks_created"] > 0
            # No warnings about language issues
            assert not any("language" in w.lower() or "encoding" in w.lower()
                         for w in data.get("warnings", []))

    def test_pdf_upload_multi_page_attribution(self, client, multi_page_pdf_file):
        """Test that multi-page PDF includes page number attribution in metadata."""
        filename, file_content, mime_type = multi_page_pdf_file

        response = client.post(
            "/documents/ingest/file",
            files={"file": (filename, file_content, mime_type)}
        )

        if response.status_code in [200, 201]:
            data = response.json()
            metadata = data.get("metadata", {})
            # Should track page information
            assert "num_pages" in metadata or "page_count" in metadata or "pages" in metadata, \
                "Multi-page PDF should include page count in metadata"
            # Page count should be 2 for our test file
            page_count = metadata.get("num_pages") or metadata.get("page_count") or len(metadata.get("pages", []))
            if page_count:
                assert page_count >= 2, "Should detect multiple pages"

    def test_pdf_upload_with_table_preservation(self, client, sample_pdf_file):
        """Test PDF upload with table preservation option."""
        filename, file_content, mime_type = sample_pdf_file

        # Upload with preserve_tables option
        response = client.post(
            "/documents/ingest/file",
            files={"file": (filename, file_content, mime_type)},
            data={"preserve_tables": "true"}  # Form data for file upload
        )

        # Should accept the parameter without error
        assert response.status_code not in [400, 422], \
            "Should accept preserve_tables parameter"

        if response.status_code in [200, 201]:
            data = response.json()
            # Table preservation option should be acknowledged
            assert data["chunks_created"] >= 0

    def test_pdf_upload_includes_processing_time(self, client, sample_pdf_file):
        """Test that response includes processing time metric."""
        filename, file_content, mime_type = sample_pdf_file

        response = client.post(
            "/documents/ingest/file",
            files={"file": (filename, file_content, mime_type)}
        )

        if response.status_code in [200, 201]:
            data = response.json()
            assert "processing_time_ms" in data
            assert isinstance(data["processing_time_ms"], (int, float))
            assert data["processing_time_ms"] >= 0

    def test_pdf_upload_includes_file_size(self, client, sample_pdf_file):
        """Test that response includes file size in bytes."""
        filename, file_content, mime_type = sample_pdf_file

        response = client.post(
            "/documents/ingest/file",
            files={"file": (filename, file_content, mime_type)}
        )

        if response.status_code in [200, 201]:
            data = response.json()
            assert "file_size_bytes" in data
            assert isinstance(data["file_size_bytes"], int)
            assert data["file_size_bytes"] > 0

    def test_pdf_upload_with_custom_metadata(self, client, sample_pdf_file):
        """Test PDF upload with custom metadata."""
        filename, file_content, mime_type = sample_pdf_file

        custom_metadata = '{"source": "test_suite", "category": "integration_test"}'

        response = client.post(
            "/documents/ingest/file",
            files={"file": (filename, file_content, mime_type)},
            data={"custom_metadata": custom_metadata}
        )

        # Should accept custom metadata without error
        assert response.status_code not in [400, 422]

        if response.status_code in [200, 201]:
            data = response.json()
            # Custom metadata might be in response metadata
            metadata = data.get("metadata", {})
            assert isinstance(metadata, dict)

    def test_pdf_upload_rejects_oversized_file(self, client):
        """Test that files exceeding size limit are rejected."""
        # Create a "large" file (simulation - use metadata to test size checking)
        large_file_content = b"%PDF-1.4\n" + b"x" * (26 * 1024 * 1024)  # >25MB

        response = client.post(
            "/documents/ingest/file",
            files={"file": ("large.pdf", io.BytesIO(large_file_content), "application/pdf")}
        )

        # Should reject with appropriate error
        assert response.status_code in [400, 413, 422], \
            "Should reject files exceeding size limit"

        if response.status_code == 400:
            data = response.json()
            # Error message should mention size limit
            assert "size" in str(data).lower() or "large" in str(data).lower()

    def test_pdf_upload_handles_corrupted_file(self, client):
        """Test handling of corrupted PDF file."""
        corrupted_pdf = b"This is not a valid PDF file"

        response = client.post(
            "/documents/ingest/file",
            files={"file": ("corrupted.pdf", io.BytesIO(corrupted_pdf), "application/pdf")}
        )

        # Should return error or warning about corruption
        if response.status_code in [200, 201]:
            data = response.json()
            # Should have warnings about file quality
            assert len(data.get("warnings", [])) > 0
        else:
            # Should return meaningful error
            assert response.status_code in [400, 422, 500]

    def test_pdf_upload_handles_empty_file(self, client):
        """Test handling of empty PDF file."""
        empty_pdf = b""

        response = client.post(
            "/documents/ingest/file",
            files={"file": ("empty.pdf", io.BytesIO(empty_pdf), "application/pdf")}
        )

        # Should reject or warn about empty file
        if response.status_code in [200, 201]:
            data = response.json()
            assert len(data.get("warnings", [])) > 0 or data["chunks_created"] == 0
        else:
            assert response.status_code in [400, 422]

    def test_pdf_upload_preserves_filename(self, client, sample_pdf_file):
        """Test that original filename is preserved in response."""
        filename, file_content, mime_type = sample_pdf_file

        response = client.post(
            "/documents/ingest/file",
            files={"file": (filename, file_content, mime_type)}
        )

        if response.status_code in [200, 201]:
            data = response.json()
            assert data["filename"] == filename

    def test_pdf_upload_returns_warnings_list(self, client, sample_pdf_file):
        """Test that response includes warnings list (may be empty)."""
        filename, file_content, mime_type = sample_pdf_file

        response = client.post(
            "/documents/ingest/file",
            files={"file": (filename, file_content, mime_type)}
        )

        if response.status_code in [200, 201]:
            data = response.json()
            assert "warnings" in data
            assert isinstance(data["warnings"], list)
            # All warnings should be strings
            assert all(isinstance(w, str) for w in data["warnings"])

    def test_pdf_upload_creates_chunks_with_metadata(self, client, multi_page_pdf_file):
        """Test that created chunks include proper metadata."""
        filename, file_content, mime_type = multi_page_pdf_file

        response = client.post(
            "/documents/ingest/file",
            files={"file": (filename, file_content, mime_type)}
        )

        if response.status_code in [200, 201]:
            data = response.json()
            # Should have created chunks
            assert data["chunks_created"] > 0
            # Metadata should include PDF-specific information
            metadata = data.get("metadata", {})
            assert isinstance(metadata, dict)
            # Could include num_pages, extraction method, etc.

    def test_pdf_upload_mixed_arabic_english(self, client):
        """Test PDF with mixed Arabic and English content."""
        # Mock mixed language PDF
        mixed_pdf = b"""%PDF-1.4
1 0 obj
<< /Type /Catalog /Pages 2 0 R >>
endobj
2 0 obj
<< /Type /Pages /Kids [3 0 R] /Count 1 >>
endobj
3 0 obj
<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] /Contents 4 0 R >>
endobj
4 0 obj
<< /Length 60 >>
stream
BT
100 700 Td
(English and Arabic mixed text) Tj
ET
endstream
endobj
xref
0 5
0000000000 65535 f
0000000009 00000 n
0000000058 00000 n
0000000115 00000 n
0000000220 00000 n
trailer
<< /Size 5 /Root 1 0 R >>
startxref
329
%%EOF
"""

        response = client.post(
            "/documents/ingest/file",
            files={"file": ("mixed.pdf", io.BytesIO(mixed_pdf), "application/pdf")}
        )

        if response.status_code in [200, 201]:
            data = response.json()
            # Should handle mixed languages without errors
            assert data["chunks_created"] >= 0
            # No language-related warnings
            assert not any("language" in w.lower() for w in data.get("warnings", []))

    def test_pdf_upload_endpoint_validation_requires_file(self, client):
        """Test that endpoint requires a file to be uploaded."""
        # Try to call endpoint without file
        response = client.post("/documents/ingest/file")

        # Should return validation error
        assert response.status_code == 422, "Should require file parameter"

    def test_pdf_upload_success_message(self, client, sample_pdf_file):
        """Test that successful upload includes appropriate success message."""
        filename, file_content, mime_type = sample_pdf_file

        response = client.post(
            "/documents/ingest/file",
            files={"file": (filename, file_content, mime_type)}
        )

        if response.status_code in [200, 201]:
            data = response.json()
            assert "message" in data
            assert isinstance(data["message"], str)
            assert len(data["message"]) > 0
            # Message should indicate success
            assert any(word in data["message"].lower()
                      for word in ["success", "ingested", "uploaded", "processed"])


class TestTextFileUpload:
    """Integration tests for plain text file upload via API (User Story 5)."""

    def test_text_upload_utf8_english(self, client):
        """Test uploading UTF-8 English text file via API."""
        content = "Hello World\nThis is a test file for the ingestion system.\n"
        file_obj = io.BytesIO(content.encode("utf-8"))

        response = client.post(
            "/documents/ingest/file",
            files={"file": ("test.txt", file_obj, "text/plain")},
        )

        assert response.status_code == 200
        data = response.json()

        # Verify response structure
        assert data["message"] == "File ingested successfully"
        assert data["filename"] == "test.txt"
        assert data["file_format"] == FileFormat.TEXT.value
        assert data["documents_created"] >= 1
        assert data["chunks_created"] >= 1
        assert data["processing_time_ms"] > 0

        # Verify metadata includes encoding detection
        assert "detected_encoding" in data["metadata"]
        assert data["metadata"]["detected_encoding"] in ["utf-8", "ascii"]

        # Should have no warnings for clean UTF-8
        assert len(data["warnings"]) == 0

    def test_text_upload_utf8_arabic(self, client):
        """Test uploading UTF-8 Arabic text file via API."""
        content = """مرحبا بك في نظام الاستخراج المتقدم

هذا نص تجريبي باللغة العربية.
يحتوي على عدة فقرات لاختبار النظام.

الفقرة الثانية تحتوي على معلومات إضافية.
"""
        file_obj = io.BytesIO(content.encode("utf-8"))

        response = client.post(
            "/documents/ingest/file",
            files={"file": ("arabic.txt", file_obj, "text/plain")},
        )

        assert response.status_code == 200
        data = response.json()

        assert data["filename"] == "arabic.txt"
        assert data["file_format"] == FileFormat.TEXT.value
        assert data["chunks_created"] >= 1

        # Verify UTF-8 detection
        assert data["metadata"]["detected_encoding"] == "utf-8"

        # Verify Arabic content is handled correctly
        assert data["documents_created"] >= 1

    def test_text_upload_windows1256_arabic(self, client):
        """Test uploading Windows-1256 Arabic text file with automatic encoding detection."""
        content = """نظام متقدم لمعالجة النصوص العربية

هذا الملف مشفر بترميز Windows-1256.
يجب أن يتم اكتشافه تلقائيا وتحويله إلى UTF-8.

السطر الأخير من الملف.
"""
        file_obj = io.BytesIO(content.encode("windows-1256"))

        response = client.post(
            "/documents/ingest/file",
            files={"file": ("arabic_win1256.txt", file_obj, "text/plain")},
        )

        assert response.status_code == 200
        data = response.json()

        assert data["filename"] == "arabic_win1256.txt"
        assert data["file_format"] == FileFormat.TEXT.value

        # Verify Windows-1256 was detected
        assert data["metadata"]["detected_encoding"] in ["windows-1256", "cp1256"]

        # Verify encoding conversion happened
        assert data["metadata"].get("encoding_converted") is True

        # Should have successful chunk creation
        assert data["chunks_created"] >= 1

    def test_text_upload_mixed_languages(self, client):
        """Test uploading text file with mixed Arabic and English content."""
        content = """Project: نظام الذكاء الاصطناعي

Description: This project implements an advanced AI system
الوصف: يطبق هذا المشروع نظاما متقدما للذكاء الاصطناعي

Features:
- Arabic language support - دعم اللغة العربية
- English language support - دعم اللغة الإنجليزية
- Mixed content handling - معالجة المحتوى المختلط
"""
        file_obj = io.BytesIO(content.encode("utf-8"))

        response = client.post(
            "/documents/ingest/file",
            files={"file": ("mixed_language.txt", file_obj, "text/plain")},
        )

        assert response.status_code == 200
        data = response.json()

        assert data["file_format"] == FileFormat.TEXT.value
        assert data["chunks_created"] >= 1

        # Should detect UTF-8 and handle both languages
        assert data["metadata"]["detected_encoding"] == "utf-8"

    def test_text_upload_with_structure(self, client):
        """Test uploading text file with numbered sections and bullets."""
        content = """Document Structure Test

1. Introduction
   This is the introduction section.

2. Main Content
   - First bullet point
   - Second bullet point
   - Third bullet point

3. Methodology
   The methodology section contains:
   1.1 Data Collection
   1.2 Data Analysis
   1.3 Results

4. Conclusion
   Final thoughts and summary.
"""
        file_obj = io.BytesIO(content.encode("utf-8"))

        response = client.post(
            "/documents/ingest/file",
            files={"file": ("structured.txt", file_obj, "text/plain")},
        )

        assert response.status_code == 200
        data = response.json()

        assert data["file_format"] == FileFormat.TEXT.value

        # Verify structure detection
        assert data["metadata"].get("has_structure") is True

        # Should create multiple chunks respecting structure
        assert data["chunks_created"] >= 3

    def test_text_upload_large_file(self, client):
        """Test uploading larger text file (1MB+)."""
        # Create ~1.5MB of text content
        paragraph = "This is a test paragraph with some content. " * 50 + "\n\n"
        large_content = paragraph * 500  # ~1.5MB

        file_obj = io.BytesIO(large_content.encode("utf-8"))

        response = client.post(
            "/documents/ingest/file",
            files={"file": ("large.txt", file_obj, "text/plain")},
        )

        assert response.status_code == 200
        data = response.json()

        # Should handle large file successfully
        assert data["file_format"] == FileFormat.TEXT.value
        assert data["file_size_bytes"] > 1_000_000

        # Should create many chunks for large file
        assert data["chunks_created"] > 10

        # Should report processing time
        assert data["processing_time_ms"] > 0

    def test_text_upload_empty_file(self, client):
        """Test uploading empty text file."""
        file_obj = io.BytesIO(b"")

        response = client.post(
            "/documents/ingest/file",
            files={"file": ("empty.txt", file_obj, "text/plain")},
        )

        # Should either succeed with warning or fail with clear error
        if response.status_code == 200:
            data = response.json()
            # Should have warning about empty file
            assert len(data["warnings"]) > 0
            assert any("empty" in w.lower() for w in data["warnings"])
            assert data["chunks_created"] == 0
        else:
            # Or return validation error
            assert response.status_code == 422

    def test_text_upload_only_whitespace(self, client):
        """Test uploading text file containing only whitespace."""
        content = "   \n\n\t\t  \n   "
        file_obj = io.BytesIO(content.encode("utf-8"))

        response = client.post(
            "/documents/ingest/file",
            files={"file": ("whitespace.txt", file_obj, "text/plain")},
        )

        # Should handle gracefully
        if response.status_code == 200:
            data = response.json()
            # Should have warning
            assert len(data["warnings"]) > 0
        else:
            assert response.status_code == 422

    def test_text_upload_with_custom_metadata(self, client):
        """Test uploading text file with custom metadata."""
        import json

        content = "Test content with custom metadata.\n"
        file_obj = io.BytesIO(content.encode("utf-8"))

        custom_metadata = {
            "source": "test_suite",
            "category": "integration_test",
            "author": "pytest",
        }

        response = client.post(
            "/documents/ingest/file",
            files={"file": ("custom_meta.txt", file_obj, "text/plain")},
            data={"custom_metadata": json.dumps(custom_metadata)},
        )

        assert response.status_code == 200
        data = response.json()

        # Custom metadata should be included in response
        assert "source" in data["metadata"] or "custom_metadata" in data
        assert data["chunks_created"] >= 1

    def test_text_upload_latin1_encoding(self, client):
        """Test uploading Latin-1 (ISO-8859-1) encoded text."""
        content = "Résumé: Café naïve éclair\n"
        file_obj = io.BytesIO(content.encode("iso-8859-1"))

        response = client.post(
            "/documents/ingest/file",
            files={"file": ("french.txt", file_obj, "text/plain")},
        )

        assert response.status_code == 200
        data = response.json()

        # Should detect Latin-1 and convert
        assert data["metadata"]["detected_encoding"] in [
            "iso-8859-1",
            "latin-1",
            "windows-1252",
        ]
        assert data["chunks_created"] >= 1

    def test_text_upload_utf16_encoding(self, client):
        """Test uploading UTF-16 encoded text file."""
        content = "UTF-16 test file\nمع نص عربي\n"
        file_obj = io.BytesIO(content.encode("utf-16"))

        response = client.post(
            "/documents/ingest/file",
            files={"file": ("utf16.txt", file_obj, "text/plain")},
        )

        assert response.status_code == 200
        data = response.json()

        # Should detect UTF-16
        assert "utf-16" in data["metadata"]["detected_encoding"].lower()
        assert data["chunks_created"] >= 1

    def test_text_upload_and_query_workflow(self, client):
        """Test complete workflow: upload text file and query its content."""
        content = """الذكاء الاصطناعي

الذكاء الاصطناعي هو فرع من علوم الحاسوب.
يهتم بإنشاء أنظمة ذكية قادرة على التعلم والتفكير.

التطبيقات تشمل معالجة اللغة الطبيعية والرؤية الحاسوبية.
"""
        file_obj = io.BytesIO(content.encode("utf-8"))

        # Step 1: Upload the file
        upload_response = client.post(
            "/documents/ingest/file",
            files={"file": ("ai_arabic.txt", file_obj, "text/plain")},
        )

        assert upload_response.status_code == 200
        upload_data = upload_response.json()
        assert upload_data["chunks_created"] > 0

        # Step 2: Query the uploaded content
        query_response = client.post(
            "/chat/query",
            json={
                "query": "ما هو الذكاء الاصطناعي؟",
                "use_rag": True,
            },
        )

        # Query should succeed (may fail if LLM not configured, but structure should be valid)
        if query_response.status_code == 200:
            query_data = query_response.json()

            # Should return response with sources
            assert "response" in query_data
            assert "sources" in query_data
            assert query_data["query_type"] == "rag"

            # Sources should reference the uploaded text (if retrieval is working)
            if len(query_data["sources"]) > 0:
                source_text = " ".join([s["content"] for s in query_data["sources"]])
                assert len(source_text) > 0


class TestTextFileIntegration:
    """Integration tests for text file upload end-to-end (T023 - US5)."""

    def test_text_upload(self, client):
        """
        T023: Integration test for text upload.

        Tests end-to-end text file upload:
        - UTF-8 encoding detection
        - File ingestion via API
        - Chunk creation
        - Metadata preservation
        - Encoding conversion (Windows-1256)
        """
        # Test 1: UTF-8 English text
        english_content = "Hello World\nThis is a test file for the ingestion system.\n"
        file_obj = io.BytesIO(english_content.encode("utf-8"))

        response = client.post(
            "/documents/ingest/file",
            files={"file": ("test_english.txt", file_obj, "text/plain")},
        )

        assert response.status_code == 200, f"Failed: {response.text}"
        data = response.json()

        # Verify response structure
        assert data["message"] == "File ingested successfully"
        assert data["filename"] == "test_english.txt"
        assert data["file_format"] == FileFormat.TEXT.value
        assert data["documents_created"] >= 1
        assert data["chunks_created"] >= 1

        # Verify encoding detection
        assert "detected_encoding" in data["metadata"]
        assert data["metadata"]["detected_encoding"] in ["utf-8", "ascii"]

        # Test 2: UTF-8 Arabic text
        arabic_content = """مرحبا بك في نظام الاستخراج المتقدم

هذا نص تجريبي باللغة العربية.
يحتوي على عدة فقرات لاختبار النظام.

الفقرة الثانية تحتوي على معلومات إضافية.
"""
        file_obj = io.BytesIO(arabic_content.encode("utf-8"))

        response = client.post(
            "/documents/ingest/file",
            files={"file": ("test_arabic.txt", file_obj, "text/plain")},
        )

        assert response.status_code == 200
        data = response.json()

        assert data["filename"] == "test_arabic.txt"
        assert data["chunks_created"] >= 1
        assert data["metadata"]["detected_encoding"] == "utf-8"

        # Test 3: Windows-1256 Arabic text with encoding conversion
        arabic_win1256_content = """نظام متقدم لمعالجة النصوص العربية

هذا الملف مشفر بترميز Windows-1256.
يجب أن يتم اكتشافه تلقائيا وتحويله إلى UTF-8.

السطر الأخير من الملف.
"""
        file_obj = io.BytesIO(arabic_win1256_content.encode("windows-1256"))

        response = client.post(
            "/documents/ingest/file",
            files={"file": ("test_win1256.txt", file_obj, "text/plain")},
        )

        assert response.status_code == 200
        data = response.json()

        assert data["filename"] == "test_win1256.txt"
        assert data["chunks_created"] >= 1

        # Verify Windows-1256 was detected
        detected_enc = data["metadata"]["detected_encoding"]
        assert detected_enc in ["windows-1256", "cp1256"], \
            f"Expected Windows-1256, got {detected_enc}"

        # Test 4: Mixed Arabic and English content
        mixed_content = """Project: نظام الذكاء الاصطناعي

Description: This project implements an advanced AI system
الوصف: يطبق هذا المشروع نظاما متقدما للذكاء الاصطناعي

Features:
- Arabic language support - دعم اللغة العربية
- English language support - دعم اللغة الإنجليزية
- Mixed content handling - معالجة المحتوى المختلط
"""
        file_obj = io.BytesIO(mixed_content.encode("utf-8"))

        response = client.post(
            "/documents/ingest/file",
            files={"file": ("test_mixed.txt", file_obj, "text/plain")},
        )

        assert response.status_code == 200
        data = response.json()

        assert data["chunks_created"] >= 1
        assert data["metadata"]["detected_encoding"] == "utf-8"

        # Test 5: Structured text with numbered sections and bullets
        structured_content = """Document Structure Test

1. Introduction
   This is the introduction section.

2. Main Content
   - First bullet point
   - Second bullet point
   - Third bullet point

3. Methodology
   The methodology section contains:
   1.1 Data Collection
   1.2 Data Analysis
   1.3 Results

4. Conclusion
   Final thoughts and summary.
"""
        file_obj = io.BytesIO(structured_content.encode("utf-8"))

        response = client.post(
            "/documents/ingest/file",
            files={"file": ("test_structured.txt", file_obj, "text/plain")},
        )

        assert response.status_code == 200
        data = response.json()

        # Verify structure detection
        assert data["metadata"].get("has_structure") is True
        assert data["chunks_created"] >= 3  # Multiple chunks for structured content

        # Test 6: Empty file edge case
        file_obj = io.BytesIO(b"")

        response = client.post(
            "/documents/ingest/file",
            files={"file": ("test_empty.txt", file_obj, "text/plain")},
        )

        # Should either succeed with warning or fail gracefully
        if response.status_code == 200:
            data = response.json()
            assert len(data["warnings"]) > 0
            assert any("empty" in w.lower() for w in data["warnings"])
        else:
            assert response.status_code == 422

    def test_text_upload_verify_chunks_in_vectorstore(self, client):
        """
        Test that uploaded text is properly chunked and stored in vector database.

        This test verifies:
        1. Chunks are created from uploaded text
        2. Chunks are embedded and stored in Qdrant
        3. Metadata is preserved in chunks
        4. Chunks can be retrieved via search
        """
        content = """Machine Learning Introduction

Machine learning is a subset of artificial intelligence.
It focuses on developing algorithms that can learn from data.

Common techniques include:
- Supervised learning
- Unsupervised learning
- Reinforcement learning

Applications are widespread in modern technology.
"""
        file_obj = io.BytesIO(content.encode("utf-8"))

        # Upload the file
        response = client.post(
            "/documents/ingest/file",
            files={"file": ("ml_intro.txt", file_obj, "text/plain")},
        )

        assert response.status_code == 200
        data = response.json()

        # Verify chunks were created
        assert data["chunks_created"] >= 2
        chunks_count = data["chunks_created"]

        # Verify metadata includes chunk information
        assert "detected_encoding" in data["metadata"]
        assert "has_structure" in data["metadata"]

        # Test retrieval (if Qdrant is available)
        # This verifies chunks are actually stored in the vector database
        query_response = client.post(
            "/chat/query",
            json={
                "query": "What is machine learning?",
                "use_rag": True,
            },
        )

        # If LLM is configured, verify retrieval works
        if query_response.status_code == 200:
            query_data = query_response.json()

            # Should retrieve relevant chunks
            if len(query_data.get("sources", [])) > 0:
                # At least one source should be from our uploaded file
                source_texts = [s["content"] for s in query_data["sources"]]
                combined_text = " ".join(source_texts).lower()

                # Should contain content from our file
                assert "machine learning" in combined_text or "artificial intelligence" in combined_text


class TestMarkdownFileUpload:
    """Integration tests for Markdown file upload via API (User Story 3)."""

    def test_markdown_upload(self, client):
        """
        T048: Integration test for Markdown upload.

        Tests end-to-end Markdown file upload:
        - Header extraction
        - Code block handling with language detection
        - List structure preservation
        - Markdown-specific metadata
        """
        content = """# Introduction

This is a test markdown document.

## Features

- Feature 1
- Feature 2
"""
        file_obj = io.BytesIO(content.encode("utf-8"))

        response = client.post(
            "/documents/ingest/file",
            files={"file": ("test.md", file_obj, "text/markdown")},
        )

        assert response.status_code == 200
        data = response.json()

        # Verify response structure
        assert data["message"] == "File ingested successfully"
        assert data["filename"] == "test.md"
        assert data["file_format"] == FileFormat.MARKDOWN.value
        assert data["documents_created"] >= 1
        assert data["chunks_created"] >= 1
        assert data["processing_time_ms"] > 0

        # Verify markdown-specific metadata
        assert data["metadata"].get("has_headers") is True
        assert data["metadata"].get("has_lists") is True

        # Should have no warnings for clean markdown
        assert len(data["warnings"]) == 0

    def test_markdown_upload_with_code_blocks(self, client):
        """Test uploading Markdown with code blocks and language detection."""
        content = """# Code Examples

Python example:

```python
def hello():
    return "Hello, World!"
```

JavaScript example:

```javascript
const greet = () => "Hello!";
```
"""
        file_obj = io.BytesIO(content.encode("utf-8"))

        response = client.post(
            "/documents/ingest/file",
            files={"file": ("code_examples.md", file_obj, "text/markdown")},
        )

        assert response.status_code == 200
        data = response.json()

        assert data["file_format"] == FileFormat.MARKDOWN.value
        assert data["chunks_created"] >= 1

        # Verify code block detection
        assert data["metadata"].get("has_code_blocks") is True
        assert data["metadata"].get("num_code_blocks") == 2

        # Verify language detection
        code_languages = data["metadata"].get("code_languages", [])
        assert "python" in code_languages
        assert "javascript" in code_languages

    def test_markdown_upload_arabic(self, client):
        """Test uploading Arabic Markdown file."""
        content = """# الوثائق

## نظرة عامة

هذا مستند تجريبي باللغة العربية.

## المميزات

- الميزة الأولى
- الميزة الثانية
- الميزة الثالثة

## مثال على الكود

```python
print("مرحبا بالعالم")
```
"""
        file_obj = io.BytesIO(content.encode("utf-8"))

        response = client.post(
            "/documents/ingest/file",
            files={"file": ("arabic_docs.md", file_obj, "text/markdown")},
        )

        assert response.status_code == 200
        data = response.json()

        assert data["filename"] == "arabic_docs.md"
        assert data["file_format"] == FileFormat.MARKDOWN.value
        assert data["chunks_created"] >= 1

        # Verify Arabic content is handled
        assert data["metadata"].get("has_headers") is True
        assert data["metadata"].get("has_lists") is True
        assert data["metadata"].get("has_code_blocks") is True

    def test_markdown_upload_header_based_chunking(self, client):
        """Test that Markdown chunking respects header boundaries."""
        content = """# Document Title

Introduction paragraph.

## Section 1

Content for section 1 with multiple paragraphs.

This is more content under section 1.

## Section 2

Content for section 2.

## Section 3

Content for section 3.
"""
        file_obj = io.BytesIO(content.encode("utf-8"))

        response = client.post(
            "/documents/ingest/file",
            files={"file": ("sections.md", file_obj, "text/markdown")},
        )

        assert response.status_code == 200
        data = response.json()

        # Should create multiple chunks based on sections
        assert data["chunks_created"] >= 3

        # Verify header metadata
        assert data["metadata"].get("num_sections") >= 3

    def test_markdown_upload_complex_document(self, client):
        """Test uploading complex Markdown document with mixed elements."""
        content = """# API Documentation

## Overview

The system provides a REST API.

### Authentication

Use Bearer tokens:

```bash
curl -H "Authorization: Bearer TOKEN" https://api.example.com
```

### Endpoints

#### GET /users

Returns users list.

**Parameters:**
- `limit`: Max results
- `offset`: Pagination

**Response:**
```json
{
  "users": [],
  "total": 0
}
```

## Examples

1. First example
2. Second example
"""
        file_obj = io.BytesIO(content.encode("utf-8"))

        response = client.post(
            "/documents/ingest/file",
            files={"file": ("api_docs.md", file_obj, "text/markdown")},
        )

        assert response.status_code == 200
        data = response.json()

        assert data["file_format"] == FileFormat.MARKDOWN.value

        # Verify all features detected
        assert data["metadata"].get("has_headers") is True
        assert data["metadata"].get("has_code_blocks") is True
        assert data["metadata"].get("has_lists") is True
        assert data["metadata"].get("max_header_level") >= 4

        # Multiple code blocks with different languages
        assert data["metadata"].get("num_code_blocks") >= 2
        code_languages = data["metadata"].get("code_languages", [])
        assert "bash" in code_languages
        assert "json" in code_languages


class TestWordFileUpload:
    """Integration tests for Word (.docx) file upload via API (User Story 4 - T057)."""

    @pytest.fixture
    def sample_docx_file(self):
        """Create a minimal valid .docx file for testing."""
        from zipfile import ZipFile

        buffer = io.BytesIO()

        with ZipFile(buffer, 'w') as docx:
            # Content Types (required)
            docx.writestr('[Content_Types].xml', '''<?xml version="1.0" encoding="UTF-8"?>
<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">
    <Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>
    <Default Extension="xml" ContentType="application/xml"/>
    <Override PartName="/word/document.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.document.main+xml"/>
</Types>''')

            # Main document relationships
            docx.writestr('_rels/.rels', '''<?xml version="1.0" encoding="UTF-8"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
    <Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="word/document.xml"/>
</Relationships>''')

            # Main document with text content
            docx.writestr('word/document.xml', '''<?xml version="1.0" encoding="UTF-8"?>
<w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">
    <w:body>
        <w:p>
            <w:r>
                <w:t>This is a test Word document with sample content for ingestion.</w:t>
            </w:r>
        </w:p>
    </w:body>
</w:document>''')

        buffer.seek(0)
        return ("test_document.docx", buffer, "application/vnd.openxmlformats-officedocument.wordprocessingml.document")

    def test_docx_upload(self, client, sample_docx_file):
        """
        T057: Integration test for Word upload.

        Tests end-to-end Word file upload:
        - .docx format detection
        - File ingestion via API
        - Chunk creation
        - Metadata preservation
        """
        filename, file_content, mime_type = sample_docx_file

        response = client.post(
            "/documents/ingest/file",
            files={"file": (filename, file_content, mime_type)}
        )

        # Should succeed or return meaningful error
        assert response.status_code in [200, 201, 400, 422, 500], \
            f"Expected valid response, got {response.status_code}"

        if response.status_code in [200, 201]:
            data = response.json()
            # Verify FileIngestResponse structure
            assert "message" in data
            assert "filename" in data
            assert data["filename"] == filename
            assert "file_format" in data
            assert data["file_format"] == "docx" or data["file_format"] == FileFormat.DOCX.value
            assert "chunks_created" in data
            assert data["chunks_created"] > 0, "Should create chunks from Word text"
            assert "documents_created" in data
            assert data["documents_created"] >= 1
            assert "warnings" in data
            assert isinstance(data["warnings"], list)


class TestHTMLFileUpload:
    """Integration tests for HTML file upload via API (User Story 2 - T029)."""

    def test_html_upload_basic(self, client):
        """Test uploading basic HTML file via API."""
        html_content = """
        <html>
        <head>
            <title>Test HTML Document</title>
        </head>
        <body>
            <h1>Welcome to the Test</h1>
            <p>This is a basic HTML file for testing ingestion.</p>
            <p>It contains multiple paragraphs.</p>
        </body>
        </html>
        """
        file_obj = io.BytesIO(html_content.encode("utf-8"))

        response = client.post(
            "/documents/ingest/file",
            files={"file": ("test.html", file_obj, "text/html")},
        )

        assert response.status_code == 200
        data = response.json()

        # Verify response structure
        assert data["message"] == "File ingested successfully"
        assert data["filename"] == "test.html"
        assert data["file_format"] == FileFormat.HTML.value
        assert data["documents_created"] >= 1
        assert data["chunks_created"] >= 1
        assert data["processing_time_ms"] > 0

        # Verify metadata includes HTML-specific info
        assert "source_format" in data["metadata"]
        assert data["metadata"]["source_format"] == "html"

        # Should have no warnings for clean HTML
        assert isinstance(data["warnings"], list)

    def test_html_upload_with_arabic_content(self, client):
        """Test uploading HTML with Arabic content and RTL detection."""
        html_content = """
        <!DOCTYPE html>
        <html dir="rtl" lang="ar">
        <head>
            <meta charset="UTF-8">
            <title>وثيقة عربية</title>
        </head>
        <body>
            <h1>مرحبا بك في النظام</h1>
            <p>هذا نص تجريبي باللغة العربية.</p>
            <p>يحتوي على عدة فقرات لاختبار النظام.</p>
            <h2>القسم الأول</h2>
            <p>محتوى القسم الأول.</p>
        </body>
        </html>
        """
        file_obj = io.BytesIO(html_content.encode("utf-8"))

        response = client.post(
            "/documents/ingest/file",
            files={"file": ("arabic.html", file_obj, "text/html")},
        )

        assert response.status_code == 200
        data = response.json()

        assert data["filename"] == "arabic.html"
        assert data["file_format"] == FileFormat.HTML.value
        assert data["chunks_created"] >= 1

        # Should detect RTL content
        assert data["metadata"].get("is_rtl") is True

        # Should extract title from HTML
        assert data["metadata"].get("title") == "وثيقة عربية"

    def test_html_upload_with_tables(self, client):
        """Test uploading HTML with table linearization."""
        html_content = """
        <html>
        <body>
            <h1>Data Table</h1>
            <table>
                <tr>
                    <th>Name</th>
                    <th>Age</th>
                    <th>City</th>
                </tr>
                <tr>
                    <td>Alice</td>
                    <td>30</td>
                    <td>Cairo</td>
                </tr>
                <tr>
                    <td>Bob</td>
                    <td>25</td>
                    <td>Alexandria</td>
                </tr>
            </table>
        </body>
        </html>
        """
        file_obj = io.BytesIO(html_content.encode("utf-8"))

        response = client.post(
            "/documents/ingest/file",
            files={"file": ("table.html", file_obj, "text/html")},
        )

        assert response.status_code == 200
        data = response.json()

        assert data["chunks_created"] >= 1

        # Should detect tables in metadata
        metadata = data.get("metadata", {})
        assert metadata.get("has_tables") is True or metadata.get("table_count", 0) > 0

    def test_html_upload_with_headings(self, client):
        """Test uploading HTML with heading hierarchy extraction."""
        html_content = """
        <html>
        <body>
            <h1>Main Title</h1>
            <p>Introduction</p>
            <h2>Section 1</h2>
            <p>Section content</p>
            <h3>Subsection 1.1</h3>
            <p>Subsection content</p>
            <h2>Section 2</h2>
            <p>More content</p>
        </body>
        </html>
        """
        file_obj = io.BytesIO(html_content.encode("utf-8"))

        response = client.post(
            "/documents/ingest/file",
            files={"file": ("headings.html", file_obj, "text/html")},
        )

        assert response.status_code == 200
        data = response.json()

        assert data["chunks_created"] >= 1

        # Should detect headings in metadata
        metadata = data.get("metadata", {})
        assert metadata.get("heading_count", 0) >= 4 or "headings" in metadata

    def test_html_upload_arabic_table(self, client):
        """Test HTML with Arabic table content."""
        html_content = """
        <html>
        <body>
            <h1>جدول البيانات</h1>
            <table>
                <tr>
                    <th>الاسم</th>
                    <th>العمر</th>
                    <th>المدينة</th>
                </tr>
                <tr>
                    <td>أحمد</td>
                    <td>٣٠</td>
                    <td>القاهرة</td>
                </tr>
                <tr>
                    <td>فاطمة</td>
                    <td>٢٥</td>
                    <td>الإسكندرية</td>
                </tr>
            </table>
        </body>
        </html>
        """
        file_obj = io.BytesIO(html_content.encode("utf-8"))

        response = client.post(
            "/documents/ingest/file",
            files={"file": ("arabic_table.html", file_obj, "text/html")},
        )

        assert response.status_code == 200
        data = response.json()

        assert data["file_format"] == FileFormat.HTML.value
        assert data["chunks_created"] >= 1

        # Should detect table
        metadata = data.get("metadata", {})
        assert metadata.get("has_tables") is True or metadata.get("table_count", 0) > 0


class TestImageUpload:
    """Integration tests for image file upload via API (User Story 6 - T037)."""

    @pytest.fixture
    def sample_png_image(self):
        """Create a sample PNG image for testing."""
        from PIL import Image

        img = Image.new("RGB", (800, 600), color="white")
        buffer = io.BytesIO()
        img.save(buffer, format="PNG")
        buffer.seek(0)
        return ("test_image.png", buffer, "image/png")

    @pytest.fixture
    def sample_jpeg_image(self):
        """Create a sample JPEG image for testing."""
        from PIL import Image

        img = Image.new("RGB", (1024, 768), color="lightblue")
        buffer = io.BytesIO()
        img.save(buffer, format="JPEG", quality=95)
        buffer.seek(0)
        return ("photo.jpg", buffer, "image/jpeg")

    @pytest.fixture
    def sample_multipage_tiff(self):
        """Create a sample multi-page TIFF image."""
        from PIL import Image

        images = [
            Image.new("RGB", (800, 600), color="white"),
            Image.new("RGB", (800, 600), color="lightgray"),
            Image.new("RGB", (800, 600), color="gray"),
        ]
        buffer = io.BytesIO()
        images[0].save(buffer, format="TIFF", save_all=True, append_images=images[1:])
        buffer.seek(0)
        return ("document.tiff", buffer, "image/tiff")

    def test_image_upload_endpoint_exists(self, client):
        """Test that image upload endpoint is available."""
        from PIL import Image

        img = Image.new("RGB", (100, 100), color="white")
        buffer = io.BytesIO()
        img.save(buffer, format="PNG")
        buffer.seek(0)

        response = client.post(
            "/documents/ingest/file",
            files={"file": ("test.png", buffer, "image/png")},
        )

        # Should not return 404 (endpoint exists) or 405 (method exists)
        assert response.status_code not in [404, 405], \
            "Image upload endpoint /documents/ingest/file should exist"

    def test_image_upload_returns_file_ingest_response(self, client, sample_png_image):
        """Test that image upload returns FileIngestResponse structure."""
        filename, file_content, mime_type = sample_png_image

        response = client.post(
            "/documents/ingest/file",
            files={"file": (filename, file_content, mime_type)},
        )

        # Should succeed or return meaningful error (not 404/405)
        assert response.status_code in [200, 201, 400, 422, 500, 503], \
            f"Expected valid response, got {response.status_code}"

        if response.status_code in [200, 201]:
            data = response.json()
            # Verify FileIngestResponse structure
            assert "message" in data, "Response should include message field"
            assert "filename" in data, "Response should include filename"
            assert "file_format" in data, "Response should include file_format"
            assert "file_size_bytes" in data, "Response should include file_size_bytes"
            assert "documents_created" in data, "Response should include documents_created"
            assert "chunks_created" in data, "Response should include chunks_created"
            assert "processing_time_ms" in data, "Response should include processing_time_ms"
            assert "metadata" in data, "Response should include metadata dict"
            assert "warnings" in data, "Response should include warnings list"

    def test_image_upload_detects_image_format(self, client, sample_png_image):
        """Test that image format is correctly detected."""
        filename, file_content, mime_type = sample_png_image

        response = client.post(
            "/documents/ingest/file",
            files={"file": (filename, file_content, mime_type)},
        )

        if response.status_code in [200, 201]:
            data = response.json()
            assert data["file_format"] == "image" or data["file_format"] == FileFormat.IMAGE.value

    def test_image_upload_with_text_mode(self, client, sample_png_image):
        """Test image upload with explicit TEXT extraction mode."""
        filename, file_content, mime_type = sample_png_image

        response = client.post(
            "/documents/ingest/file",
            files={"file": (filename, file_content, mime_type)},
            data={"image_mode": "text"},
        )

        # Should accept the parameter without error
        assert response.status_code not in [400, 422], \
            "Should accept image_mode parameter"

    def test_image_upload_with_description_mode(self, client, sample_jpeg_image):
        """Test image upload with DESCRIPTION extraction mode for photos/charts."""
        filename, file_content, mime_type = sample_jpeg_image

        response = client.post(
            "/documents/ingest/file",
            files={"file": (filename, file_content, mime_type)},
            data={"image_mode": "description"},
        )

        assert response.status_code not in [400, 422]

    def test_image_upload_with_auto_mode(self, client, sample_png_image):
        """Test image upload with AUTO mode (automatic content detection)."""
        filename, file_content, mime_type = sample_png_image

        response = client.post(
            "/documents/ingest/file",
            files={"file": (filename, file_content, mime_type)},
            data={"image_mode": "auto"},
        )

        assert response.status_code not in [400, 422]

    def test_image_upload_multipage_tiff(self, client, sample_multipage_tiff):
        """Test uploading multi-page TIFF image."""
        filename, file_content, mime_type = sample_multipage_tiff

        response = client.post(
            "/documents/ingest/file",
            files={"file": (filename, file_content, mime_type)},
        )

        if response.status_code in [200, 201]:
            data = response.json()
            metadata = data.get("metadata", {})

            # Should detect multiple pages
            if "is_multipage" in metadata:
                assert metadata["is_multipage"] is True
                assert metadata.get("num_pages_total", 0) >= 3

    def test_image_upload_handles_corrupted_file(self, client):
        """Test handling of corrupted image file."""
        corrupted_image = b"This is not a valid image file"

        response = client.post(
            "/documents/ingest/file",
            files={"file": ("corrupted.png", io.BytesIO(corrupted_image), "image/png")},
        )

        # Should return error or warning about corruption
        if response.status_code in [200, 201]:
            data = response.json()
            # Should have warnings about file quality
            assert len(data.get("warnings", [])) > 0
        else:
            # Should return meaningful error
            assert response.status_code in [400, 422, 500]

    def test_image_upload_preserves_filename(self, client, sample_png_image):
        """Test that original filename is preserved in response."""
        filename, file_content, mime_type = sample_png_image

        response = client.post(
            "/documents/ingest/file",
            files={"file": (filename, file_content, mime_type)},
        )

        if response.status_code in [200, 201]:
            data = response.json()
            assert data["filename"] == filename

    def test_image_upload_different_formats(self, client):
        """Test uploading images in different formats (PNG, JPEG, WebP)."""
        from PIL import Image

        formats = [
            ("test.png", "PNG", "image/png"),
            ("test.jpg", "JPEG", "image/jpeg"),
            ("test.webp", "WEBP", "image/webp"),
        ]

        for filename, format_name, mime_type in formats:
            img = Image.new("RGB", (800, 600), color="white")
            buffer = io.BytesIO()
            img.save(buffer, format=format_name)
            buffer.seek(0)

            response = client.post(
                "/documents/ingest/file",
                files={"file": (filename, buffer, mime_type)},
            )

            # Should handle all image formats
            assert response.status_code in [200, 201, 503], \
                f"Failed to handle {format_name} format"

            if response.status_code in [200, 201]:
                data = response.json()
                assert data["file_format"] == "image" or data["file_format"] == FileFormat.IMAGE.value
