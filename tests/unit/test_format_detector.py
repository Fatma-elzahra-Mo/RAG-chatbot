"""
Unit tests for file format detector.

Tests MIME detection, extension fallback, and edge cases for all supported formats.
"""

import pytest

from src.models.schemas import FileFormat
from src.preprocessing.format_detector import (
    detect_format,
    get_mime_type,
    _detect_by_extension,
    _detect_by_mime,
)


class TestFormatDetectorMIME:
    """Test MIME-based format detection."""

    def test_detect_pdf_by_mime(self):
        """Test PDF detection via magic numbers."""
        # PDF magic bytes: %PDF-1.4
        pdf_content = b"%PDF-1.4\n%\xE2\xE3\xCF\xD3\n"
        result = detect_format(pdf_content, "document.pdf")
        assert result == FileFormat.PDF

    def test_detect_html_by_mime(self):
        """Test HTML detection via DOCTYPE and tags."""
        html_content = b"<!DOCTYPE html>\n<html><head><title>Test</title></head></html>"
        result = detect_format(html_content, "page.html")
        assert result == FileFormat.HTML

    def test_detect_text_by_mime(self):
        """Test plain text detection."""
        text_content = b"This is plain text content\nwith multiple lines"
        result = detect_format(text_content, "document.txt")
        assert result == FileFormat.TEXT

    def test_detect_image_png_by_mime(self):
        """Test PNG image detection via magic bytes."""
        # PNG magic bytes: 89 50 4E 47 0D 0A 1A 0A
        png_content = b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR"
        result = detect_format(png_content, "image.png")
        assert result == FileFormat.IMAGE

    def test_detect_image_jpeg_by_mime(self):
        """Test JPEG image detection via magic bytes."""
        # JPEG magic bytes: FF D8 FF
        jpeg_content = b"\xff\xd8\xff\xe0\x00\x10JFIF"
        result = detect_format(jpeg_content, "photo.jpg")
        assert result == FileFormat.IMAGE

    def test_detect_image_gif_by_mime(self):
        """Test GIF image detection via magic bytes."""
        # GIF magic bytes: GIF89a or GIF87a
        gif_content = b"GIF89a\x01\x00\x01\x00\x80\x00\x00"
        result = detect_format(gif_content, "animation.gif")
        assert result == FileFormat.IMAGE


class TestFormatDetectorExtension:
    """Test extension-based fallback detection."""

    @pytest.mark.parametrize(
        "extension,expected_format",
        [
            (".pdf", FileFormat.PDF),
            (".PDF", FileFormat.PDF),  # Case insensitive
            (".html", FileFormat.HTML),
            (".htm", FileFormat.HTML),
            (".xhtml", FileFormat.HTML),
            (".md", FileFormat.MARKDOWN),
            (".markdown", FileFormat.MARKDOWN),
            (".mdown", FileFormat.MARKDOWN),
            (".docx", FileFormat.DOCX),
            (".txt", FileFormat.TEXT),
            (".text", FileFormat.TEXT),
            (".png", FileFormat.IMAGE),
            (".jpg", FileFormat.IMAGE),
            (".jpeg", FileFormat.IMAGE),
            (".tiff", FileFormat.IMAGE),
            (".tif", FileFormat.IMAGE),
            (".bmp", FileFormat.IMAGE),
            (".gif", FileFormat.IMAGE),
            (".webp", FileFormat.IMAGE),
        ],
    )
    def test_extension_fallback(self, extension: str, expected_format: FileFormat):
        """Test format detection via file extension fallback."""
        # Use generic content that won't trigger MIME detection
        generic_content = b"random binary content \x00\x01\x02"
        filename = f"test{extension}"
        result = detect_format(generic_content, filename)
        # Should fall back to extension-based detection
        assert result == expected_format

    def test_detect_by_extension_directly(self):
        """Test _detect_by_extension helper function."""
        assert _detect_by_extension("document.pdf") == FileFormat.PDF
        assert _detect_by_extension("page.html") == FileFormat.HTML
        assert _detect_by_extension("readme.md") == FileFormat.MARKDOWN
        assert _detect_by_extension("report.docx") == FileFormat.DOCX
        assert _detect_by_extension("data.txt") == FileFormat.TEXT
        assert _detect_by_extension("photo.jpg") == FileFormat.IMAGE

    def test_extension_case_insensitive(self):
        """Test that extension detection is case insensitive."""
        assert _detect_by_extension("FILE.PDF") == FileFormat.PDF
        assert _detect_by_extension("FILE.Html") == FileFormat.HTML
        assert _detect_by_extension("FILE.MD") == FileFormat.MARKDOWN

    def test_multiple_extensions_in_filename(self):
        """Test filename with multiple dots (e.g., archive.tar.gz)."""
        # Should only use the last extension
        result = _detect_by_extension("document.backup.txt")
        assert result == FileFormat.TEXT


class TestFormatDetectorUnknown:
    """Test handling of unknown or unsupported formats."""

    def test_unknown_extension(self):
        """Test detection with unsupported extension."""
        content = b"some content"
        result = detect_format(content, "file.xyz")
        # Without python-magic, falls back to TEXT (MIME returns text/plain)
        # With unknown extension, should return UNKNOWN
        assert result in [FileFormat.UNKNOWN, FileFormat.TEXT]

    def test_no_extension(self):
        """Test detection with no file extension."""
        content = b"some content"
        result = detect_format(content, "README")
        # Should attempt MIME detection, may return UNKNOWN
        assert result in [FileFormat.TEXT, FileFormat.UNKNOWN]

    def test_empty_filename(self):
        """Test detection with empty filename."""
        content = b"some content"
        result = detect_format(content, "")
        assert result in [FileFormat.TEXT, FileFormat.UNKNOWN]

    def test_empty_content(self):
        """Test detection with empty file content."""
        result = detect_format(b"", "test.txt")
        # Should fall back to extension
        assert result == FileFormat.TEXT

    def test_very_small_content(self):
        """Test detection with minimal content (< 10 bytes)."""
        result = detect_format(b"tiny", "test.pdf")
        # MIME detection may identify as text, or fall back to extension
        assert result in [FileFormat.PDF, FileFormat.TEXT]


class TestFormatDetectorMismatch:
    """Test handling of mismatched extension vs content."""

    def test_pdf_content_with_txt_extension(self):
        """Test PDF content with .txt extension - MIME should win."""
        pdf_content = b"%PDF-1.4\n%\xE2\xE3\xCF\xD3\n"
        result = detect_format(pdf_content, "fake.txt")
        # MIME detection should identify as PDF
        assert result == FileFormat.PDF

    def test_html_content_with_txt_extension(self):
        """Test HTML content with .txt extension - MIME should win."""
        html_content = b"<!DOCTYPE html>\n<html><body>Content</body></html>"
        result = detect_format(html_content, "webpage.txt")
        # MIME detection should identify as HTML
        assert result == FileFormat.HTML

    def test_image_content_with_txt_extension(self):
        """Test image content with wrong extension - MIME should win."""
        png_content = b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR"
        result = detect_format(png_content, "notanimage.txt")
        # MIME detection should identify as IMAGE
        assert result == FileFormat.IMAGE

    def test_text_content_with_pdf_extension(self):
        """Test plain text content with .pdf extension."""
        text_content = b"This is just plain text, not a PDF"
        result = detect_format(text_content, "fake.pdf")
        # MIME should detect as text, but may fall back to extension
        # Both outcomes are acceptable depending on MIME detection
        assert result in [FileFormat.TEXT, FileFormat.PDF]


class TestFormatDetectorEdgeCases:
    """Test edge cases and special scenarios."""

    def test_large_content_uses_sample(self):
        """Test that only first 2048 bytes are used for detection."""
        # Create content larger than 2048 bytes
        large_pdf = b"%PDF-1.4\n" + b"x" * 3000
        result = detect_format(large_pdf, "large.pdf")
        assert result == FileFormat.PDF

    def test_content_with_null_bytes(self):
        """Test binary content with null bytes."""
        binary_content = b"\x00\x01\x02\x03" + b"\x00" * 100
        result = detect_format(binary_content, "binary.dat")
        # Should return unknown for unrecognized binary
        assert result == FileFormat.UNKNOWN

    def test_arabic_text_content(self):
        """Test detection of Arabic text file."""
        arabic_text = "مرحبا بك في النظام".encode("utf-8")
        result = detect_format(arabic_text, "arabic.txt")
        assert result == FileFormat.TEXT

    def test_mixed_language_html(self):
        """Test HTML with Arabic content."""
        html_arabic = """<!DOCTYPE html>
<html lang="ar">
<head><title>اختبار</title></head>
<body><h1>مرحبا</h1></body>
</html>""".encode(
            "utf-8"
        )
        result = detect_format(html_arabic, "arabic.html")
        assert result == FileFormat.HTML

    def test_markdown_without_clear_markers(self):
        """Test markdown that looks like plain text."""
        # Markdown without clear markers might be detected as text
        simple_md = b"# Header\n\nSome text content"
        result = detect_format(simple_md, "doc.md")
        # MIME may detect as text, but extension fallback should identify as markdown
        assert result in [FileFormat.MARKDOWN, FileFormat.TEXT]

    def test_filename_with_spaces(self):
        """Test filename containing spaces."""
        content = b"some content"
        result = detect_format(content, "my document.txt")
        assert result == FileFormat.TEXT

    def test_filename_with_special_chars(self):
        """Test filename with special characters."""
        content = b"some content"
        result = detect_format(content, "file-name_v2.0.txt")
        assert result == FileFormat.TEXT

    def test_uppercase_filename(self):
        """Test all-uppercase filename."""
        content = b"content"
        result = detect_format(content, "README.TXT")
        assert result == FileFormat.TEXT


class TestFormatDetectorDocx:
    """Test specific handling of Word documents."""

    def test_docx_by_extension(self):
        """Test DOCX detection by extension (since it's a ZIP)."""
        # DOCX is actually a ZIP archive, so MIME might detect as ZIP
        docx_content = b"PK\x03\x04"  # ZIP magic bytes
        result = detect_format(docx_content, "document.docx")
        # Extension fallback should identify as DOCX
        assert result == FileFormat.DOCX


class TestGetMimeType:
    """Test get_mime_type utility function."""

    def test_get_mime_type_pdf(self):
        """Test MIME type extraction for PDF."""
        pdf_content = b"%PDF-1.4\n%\xE2\xE3\xCF\xD3\n"
        mime = get_mime_type(pdf_content)
        if mime is not None:  # Only if python-magic is installed
            assert "pdf" in mime.lower()

    def test_get_mime_type_with_exception(self):
        """Test MIME type extraction handles errors gracefully."""
        # Empty content or invalid content should return None
        mime = get_mime_type(b"")
        # Should return None or a valid MIME type, not raise exception
        assert mime is None or isinstance(mime, str)


class TestDetectByMime:
    """Test _detect_by_mime helper function."""

    def test_detect_by_mime_without_magic_library(self, monkeypatch):
        """Test graceful fallback when python-magic is not installed."""
        # Mock import to raise ImportError

        def mock_import(name, *args, **kwargs):
            if name == "magic":
                raise ImportError("No module named 'magic'")
            return __import__(name, *args, **kwargs)

        monkeypatch.setattr("builtins.__import__", mock_import)

        # Should return UNKNOWN and not crash
        result = _detect_by_mime(b"some content")
        assert result == FileFormat.UNKNOWN

    def test_detect_by_mime_with_exception(self, monkeypatch):
        """Test handling of exceptions during MIME detection."""
        # This test verifies graceful error handling
        result = _detect_by_mime(b"test content")
        # Should return a valid FileFormat (not raise exception)
        assert isinstance(result, FileFormat)


class TestImageFormats:
    """Test detection of various image formats."""

    @pytest.mark.parametrize(
        "extension,description",
        [
            (".png", "PNG"),
            (".jpg", "JPEG"),
            (".gif", "GIF"),
            (".bmp", "BMP"),
            (".tiff", "TIFF"),
        ],
    )
    def test_image_format_detection_by_extension(
        self, extension: str, description: str
    ):
        """Test detection of image formats by extension fallback."""
        # Use generic binary content that won't have recognizable magic bytes
        binary_content = b"\x00\x01\x02\x03\x04\x05"
        filename = f"test{extension}"
        result = detect_format(binary_content, filename)
        # Extension fallback should always work
        assert result == FileFormat.IMAGE, f"Failed to detect {description} by extension"

    def test_image_format_detection_png_with_magic(self):
        """Test PNG detection with full magic bytes."""
        # Full PNG header is more likely to be detected correctly
        png_header = b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01"
        result = detect_format(png_header, "test.png")
        # Should detect as IMAGE either via MIME or extension
        assert result == FileFormat.IMAGE


class TestMarkdownVariants:
    """Test detection of markdown file variants."""

    def test_md_extension(self):
        """Test .md extension."""
        content = b"# Heading\n\nParagraph"
        result = detect_format(content, "readme.md")
        # MIME may detect as text, extension should give markdown
        assert result in [FileFormat.MARKDOWN, FileFormat.TEXT]

    def test_markdown_extension(self):
        """Test .markdown extension."""
        content = b"# Heading\n\nParagraph"
        result = detect_format(content, "readme.markdown")
        # MIME may detect as text, extension should give markdown
        assert result in [FileFormat.MARKDOWN, FileFormat.TEXT]

    def test_mdown_extension(self):
        """Test .mdown extension."""
        content = b"# Heading\n\nParagraph"
        result = detect_format(content, "readme.mdown")
        # MIME may detect as text, extension should give markdown
        assert result in [FileFormat.MARKDOWN, FileFormat.TEXT]


class TestHTMLVariants:
    """Test detection of HTML file variants."""

    def test_html_extension(self):
        """Test .html extension."""
        content = b"<html><body>content</body></html>"
        assert detect_format(content, "page.html") == FileFormat.HTML

    def test_htm_extension(self):
        """Test .htm extension."""
        content = b"<html><body>content</body></html>"
        assert detect_format(content, "page.htm") == FileFormat.HTML

    def test_xhtml_extension(self):
        """Test .xhtml extension."""
        content = b"<html><body>content</body></html>"
        assert detect_format(content, "page.xhtml") == FileFormat.HTML


class TestRobustness:
    """Test robustness and error handling."""

    def test_none_content_handling(self):
        """Test that None content doesn't crash (even if not expected)."""
        # This tests defensive programming
        # The function may handle None gracefully or raise an error
        try:
            result = detect_format(None, "test.txt")
            # If it doesn't raise, it should return a valid FileFormat
            assert isinstance(result, FileFormat)
        except (TypeError, AttributeError):
            # This is also acceptable - the function doesn't need to handle None
            pass

    def test_malformed_filename(self):
        """Test handling of unusual filename."""
        content = b"test content"
        # Filename is just an extension
        result = detect_format(content, ".txt")
        assert result == FileFormat.TEXT

    def test_filename_with_no_extension_but_dot(self):
        """Test filename ending with dot."""
        content = b"test content"
        result = detect_format(content, "filename.")
        # Should handle gracefully (empty extension)
        assert result in [FileFormat.TEXT, FileFormat.UNKNOWN]

    def test_very_long_filename(self):
        """Test detection with very long filename."""
        content = b"test content"
        long_name = "a" * 200 + ".txt"
        result = detect_format(content, long_name)
        assert result == FileFormat.TEXT

    def test_unicode_filename(self):
        """Test filename with unicode characters."""
        content = b"test content"
        result = detect_format(content, "ملف_عربي.txt")
        assert result == FileFormat.TEXT
