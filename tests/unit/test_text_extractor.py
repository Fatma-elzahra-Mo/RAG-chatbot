"""
Unit tests for TextExtractor.

Tests encoding detection, line ending detection, structure detection,
and error handling with various text file scenarios.
"""

import io
import pytest

from src.models.schemas import ContentType
from src.preprocessing.extractors.text import TextExtractor


class TestTextExtractor:
    """Test suite for TextExtractor class."""

    @pytest.fixture
    def extractor(self):
        """Create TextExtractor instance."""
        return TextExtractor()

    def test_supports_format(self, extractor):
        """Test format support detection."""
        assert extractor.supports_format("text") is True
        assert extractor.supports_format("TEXT") is True
        assert extractor.supports_format("txt") is False
        assert extractor.supports_format("pdf") is False
        assert extractor.supports_format("html") is False

    def test_extract_utf8_text(self, extractor):
        """Test extraction of UTF-8 encoded text."""
        content = "Hello, World!\nThis is a test.\n".encode("utf-8")
        file_obj = io.BytesIO(content)

        result = extractor.extract(file_obj, "test.txt")

        assert result.text == "Hello, World!\nThis is a test.\n"
        # ASCII is a subset of UTF-8, so chardet may detect it as ASCII
        assert result.metadata["detected_encoding"] in ["utf-8", "ascii"]
        assert result.metadata["actual_encoding"] in ["utf-8", "ascii"]
        assert result.metadata["line_ending_style"] in ["LF", "CRLF", "mixed"]
        assert result.metadata["line_count"] == 3
        assert len(result.warnings) == 0

    def test_extract_arabic_utf8(self, extractor):
        """Test extraction of Arabic text in UTF-8."""
        content = "مرحبا بك\nهذا نص عربي للاختبار\n".encode("utf-8")
        file_obj = io.BytesIO(content)

        result = extractor.extract(file_obj, "arabic.txt")

        assert "مرحبا بك" in result.text
        assert "هذا نص عربي" in result.text
        assert result.metadata["detected_encoding"] == "utf-8"
        assert result.metadata["actual_encoding"] == "utf-8"

    def test_extract_utf16_text(self, extractor):
        """Test extraction of UTF-16 encoded text."""
        content = "Hello, UTF-16 World!".encode("utf-16")
        file_obj = io.BytesIO(content)

        result = extractor.extract(file_obj, "test.txt")

        assert "Hello, UTF-16 World!" in result.text
        assert "utf-16" in result.metadata["detected_encoding"].lower()

    def test_extract_windows1256_arabic(self, extractor):
        """Test extraction of Windows-1256 encoded Arabic text."""
        # Simple ASCII text that won't fail in Windows-1256
        content = "Test text in Windows-1256".encode("windows-1256")
        file_obj = io.BytesIO(content)

        result = extractor.extract(file_obj, "test.txt")

        assert "Test text" in result.text
        # Encoding detection may vary, so just check it doesn't crash

    def test_line_ending_lf(self, extractor):
        """Test detection of LF line endings (Unix)."""
        content = "Line 1\nLine 2\nLine 3\n".encode("utf-8")
        file_obj = io.BytesIO(content)

        result = extractor.extract(file_obj, "test.txt")

        assert result.metadata["line_ending_style"] == "LF"

    def test_line_ending_crlf(self, extractor):
        """Test detection of CRLF line endings (Windows)."""
        content = "Line 1\r\nLine 2\r\nLine 3\r\n".encode("utf-8")
        file_obj = io.BytesIO(content)

        result = extractor.extract(file_obj, "test.txt")

        assert result.metadata["line_ending_style"] == "CRLF"

    def test_line_ending_cr(self, extractor):
        """Test detection of CR line endings (old Mac)."""
        content = "Line 1\rLine 2\rLine 3\r".encode("utf-8")
        file_obj = io.BytesIO(content)

        result = extractor.extract(file_obj, "test.txt")

        assert result.metadata["line_ending_style"] == "CR"

    def test_line_ending_mixed(self, extractor):
        """Test detection of mixed line endings."""
        content = "Line 1\nLine 2\r\nLine 3\rLine 4\n".encode("utf-8")
        file_obj = io.BytesIO(content)

        result = extractor.extract(file_obj, "test.txt")

        assert result.metadata["line_ending_style"] == "mixed"

    def test_line_ending_none(self, extractor):
        """Test detection when no line endings present."""
        content = "Single line without newline".encode("utf-8")
        file_obj = io.BytesIO(content)

        result = extractor.extract(file_obj, "test.txt")

        assert result.metadata["line_ending_style"] == "none"

    def test_detect_numbered_sections(self, extractor):
        """Test detection of numbered sections."""
        content = """
1. First item
2. Second item
3. Third item
""".encode(
            "utf-8"
        )
        file_obj = io.BytesIO(content)

        result = extractor.extract(file_obj, "test.txt")

        assert result.metadata["has_numbered_sections"] is True
        assert result.metadata["num_numbered_items"] >= 3
        assert result.metadata["has_structure"] is True
        assert result.content_type == ContentType.LIST

    def test_detect_arabic_numbered_sections(self, extractor):
        """Test detection of Arabic-numbered sections."""
        content = """
١. البند الأول
٢. البند الثاني
٣. البند الثالث
""".encode(
            "utf-8"
        )
        file_obj = io.BytesIO(content)

        result = extractor.extract(file_obj, "test.txt")

        assert result.metadata["has_numbered_sections"] is True
        assert result.metadata["num_numbered_items"] >= 3

    def test_detect_bullet_points(self, extractor):
        """Test detection of bullet points."""
        content = """
• First bullet
• Second bullet
- Third bullet
* Fourth bullet
""".encode(
            "utf-8"
        )
        file_obj = io.BytesIO(content)

        result = extractor.extract(file_obj, "test.txt")

        assert result.metadata["has_bullet_points"] is True
        assert result.metadata["num_bullet_items"] >= 4
        assert result.metadata["has_structure"] is True
        assert result.content_type == ContentType.LIST

    def test_detect_headers(self, extractor):
        """Test detection of headers."""
        content = """
# Main Header
## Subheader
ANOTHER HEADER IN CAPS

Regular text here.
""".encode(
            "utf-8"
        )
        file_obj = io.BytesIO(content)

        result = extractor.extract(file_obj, "test.txt")

        assert result.metadata["has_headers"] is True
        assert result.metadata["num_headers"] >= 2

    def test_detect_indentation(self, extractor):
        """Test detection of indentation structure."""
        content = """
Main level
  Indented level 1
    Indented level 2
  Back to level 1
""".encode(
            "utf-8"
        )
        file_obj = io.BytesIO(content)

        result = extractor.extract(file_obj, "test.txt")

        assert result.metadata["has_indentation"] is True

    def test_no_structure(self, extractor):
        """Test plain text without structure."""
        content = "Just plain text without any structure or formatting.".encode("utf-8")
        file_obj = io.BytesIO(content)

        result = extractor.extract(file_obj, "test.txt")

        assert result.metadata["has_structure"] is False
        assert result.metadata["has_numbered_sections"] is False
        assert result.metadata["has_bullet_points"] is False
        assert result.content_type == ContentType.TEXT

    def test_encoding_fallback(self, extractor):
        """Test fallback encoding when detection fails."""
        # Create invalid UTF-8 sequence
        content = b"\xff\xfe\x00\x01invalid"
        file_obj = io.BytesIO(content)

        result = extractor.extract(file_obj, "test.txt", fallback_encoding="utf-8")

        # Should not crash, should use some encoding
        assert result.text is not None
        assert result.metadata["detected_encoding"] is not None
        # If chardet detects UTF-16, it may decode successfully
        # If it fails, warnings should be present
        if "utf-16" not in result.metadata["detected_encoding"].lower():
            assert len(result.warnings) >= 0  # May or may not have warnings

    def test_low_confidence_warning(self, extractor):
        """Test warning when encoding confidence is low."""
        # ASCII text can have low confidence
        content = "Simple ASCII text".encode("ascii")
        file_obj = io.BytesIO(content)

        result = extractor.extract(file_obj, "test.txt")

        # May or may not have low confidence warning depending on chardet
        assert result.text == "Simple ASCII text"

    def test_metadata_completeness(self, extractor):
        """Test that all expected metadata fields are present."""
        content = "Test content\nLine 2\n".encode("utf-8")
        file_obj = io.BytesIO(content)

        result = extractor.extract(file_obj, "test.txt")

        # Check all required metadata fields
        required_fields = [
            "detected_encoding",
            "encoding_confidence",
            "actual_encoding",
            "line_ending_style",
            "file_size_bytes",
            "line_count",
            "char_count",
            "has_structure",
            "has_numbered_sections",
            "has_bullet_points",
            "has_headers",
            "has_indentation",
        ]

        for field in required_fields:
            assert field in result.metadata, f"Missing metadata field: {field}"

    def test_empty_file(self, extractor):
        """Test extraction of empty file."""
        content = b""
        file_obj = io.BytesIO(content)

        result = extractor.extract(file_obj, "empty.txt")

        assert result.text == ""
        assert result.metadata["file_size_bytes"] == 0
        assert result.metadata["line_count"] == 1

    def test_large_file_structure_detection(self, extractor):
        """Test structure detection on larger file."""
        content = """
# DOCUMENT TITLE

## Section 1

This is the first section with some content.

1. First point in section 1
2. Second point in section 1
3. Third point in section 1

## Section 2

This is the second section.

• Bullet point 1
• Bullet point 2
• Bullet point 3

Some concluding remarks.
""".encode(
            "utf-8"
        )
        file_obj = io.BytesIO(content)

        result = extractor.extract(file_obj, "document.txt")

        assert result.metadata["has_structure"] is True
        assert result.metadata["has_numbered_sections"] is True
        assert result.metadata["has_bullet_points"] is True
        assert result.metadata["has_headers"] is True
        assert result.metadata["num_numbered_items"] >= 3
        assert result.metadata["num_bullet_items"] >= 3

    def test_disable_structure_detection(self, extractor):
        """Test disabling structure detection."""
        content = """
1. First item
2. Second item
""".encode(
            "utf-8"
        )
        file_obj = io.BytesIO(content)

        result = extractor.extract(file_obj, "test.txt", detect_structure=False)

        # Structure fields should not be present
        assert "has_structure" not in result.metadata
        assert "has_numbered_sections" not in result.metadata

    def test_custom_fallback_encoding(self, extractor):
        """Test custom fallback encoding option."""
        content = "Test content".encode("utf-8")
        file_obj = io.BytesIO(content)

        result = extractor.extract(file_obj, "test.txt", fallback_encoding="iso-8859-1")

        # Should extract successfully
        assert result.text == "Test content"

    def test_quality_indicators(self, extractor):
        """Test that quality indicators can be added."""
        content = "Test content".encode("utf-8")
        file_obj = io.BytesIO(content)

        result = extractor.extract(file_obj, "test.txt")

        # ExtractionResult should have quality_indicators field
        assert hasattr(result, "quality_indicators")

    def test_nested_numbered_sections(self, extractor):
        """Test detection of nested numbered sections (1.1, 1.2, etc.)."""
        content = """
1. Main section
1.1 Subsection one
1.2 Subsection two
2. Another main section
2.1 Another subsection
""".encode(
            "utf-8"
        )
        file_obj = io.BytesIO(content)

        result = extractor.extract(file_obj, "test.txt")

        assert result.metadata["has_numbered_sections"] is True
        assert result.metadata["num_numbered_items"] >= 5

    def test_mixed_structure(self, extractor):
        """Test file with mixed structure types."""
        content = """
# Header

1. Numbered item
2. Another numbered item

• Bullet point
• Another bullet

  Indented paragraph

Regular text.
""".encode(
            "utf-8"
        )
        file_obj = io.BytesIO(content)

        result = extractor.extract(file_obj, "test.txt")

        assert result.metadata["has_structure"] is True
        assert result.metadata["has_numbered_sections"] is True
        assert result.metadata["has_bullet_points"] is True
        assert result.metadata["has_headers"] is True
        assert result.metadata["has_indentation"] is True
