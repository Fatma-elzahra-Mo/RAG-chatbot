"""
Unit tests for plain text extractor.

Tests UTF-8, Windows-1256 (Arabic), encoding detection, structure preservation,
and automatic encoding conversion for plain text files.

Following TDD approach - these tests should FAIL until implementation is complete.
"""

import io
import pytest

from src.models.schemas import ExtractionResult, ContentType, FileFormat
from src.preprocessing.extractors.text import TextExtractor


class TestTextExtractorBasics:
    """Test basic text extraction functionality."""

    @pytest.fixture
    def extractor(self):
        """Create text extractor instance."""
        return TextExtractor()

    def test_extractor_supports_text_format(self, extractor):
        """Test that extractor declares support for text format."""
        assert extractor.supports_format("text")
        assert extractor.supports_format("txt")

    def test_extractor_does_not_support_other_formats(self, extractor):
        """Test that extractor rejects non-text formats."""
        assert not extractor.supports_format("pdf")
        assert not extractor.supports_format("html")
        assert not extractor.supports_format("docx")


class TestUTF8Encoding:
    """Test extraction of UTF-8 encoded text files."""

    @pytest.fixture
    def extractor(self):
        """Create text extractor instance."""
        return TextExtractor()

    def test_extract_simple_utf8_english(self, extractor):
        """Test extraction of simple English UTF-8 text."""
        content = "Hello World\nThis is a test file.\n"
        file_obj = io.BytesIO(content.encode("utf-8"))

        result = extractor.extract(file_obj, "test.txt")

        assert isinstance(result, ExtractionResult)
        assert result.text == content
        assert result.content_type == ContentType.TEXT
        assert result.metadata.get("detected_encoding") == "utf-8"
        assert len(result.warnings) == 0

    def test_extract_utf8_arabic(self, extractor):
        """Test extraction of Arabic UTF-8 text."""
        content = "مرحبا بك في النظام\nهذا نص تجريبي باللغة العربية\n"
        file_obj = io.BytesIO(content.encode("utf-8"))

        result = extractor.extract(file_obj, "arabic.txt")

        assert result.text == content
        assert result.metadata.get("detected_encoding") == "utf-8"
        assert "مرحبا" in result.text
        assert "العربية" in result.text
        assert len(result.warnings) == 0

    def test_extract_utf8_mixed_languages(self, extractor):
        """Test extraction of mixed Arabic and English text."""
        content = "Project Name: المشروع العربي\nDescription: نظام متقدم for testing\n"
        file_obj = io.BytesIO(content.encode("utf-8"))

        result = extractor.extract(file_obj, "mixed.txt")

        assert result.text == content
        assert "Project Name" in result.text
        assert "المشروع" in result.text
        assert "testing" in result.text
        assert result.metadata.get("detected_encoding") == "utf-8"

    def test_extract_utf8_with_bom(self, extractor):
        """Test extraction of UTF-8 file with BOM (Byte Order Mark)."""
        content = "Text with BOM\n"
        # UTF-8 BOM: EF BB BF
        file_obj = io.BytesIO(b"\xef\xbb\xbf" + content.encode("utf-8"))

        result = extractor.extract(file_obj, "bom.txt")

        # BOM should be stripped from result
        assert result.text.strip() == content.strip()
        assert result.metadata.get("detected_encoding") in ["utf-8", "utf-8-sig"]


class TestWindows1256Encoding:
    """Test extraction of Windows-1256 encoded Arabic text files."""

    @pytest.fixture
    def extractor(self):
        """Create text extractor instance."""
        return TextExtractor()

    def test_extract_windows1256_arabic(self, extractor):
        """Test extraction of Windows-1256 (Arabic) encoded text."""
        content = "مرحبا بك في النظام\nاختبار الترميز العربي\n"
        file_obj = io.BytesIO(content.encode("windows-1256"))

        result = extractor.extract(file_obj, "arabic_windows.txt")

        # Should auto-detect Windows-1256 and convert to UTF-8
        assert "مرحبا" in result.text
        assert "الترميز" in result.text
        assert result.metadata.get("detected_encoding") in ["windows-1256", "cp1256"]
        # Should have conversion warning or metadata
        assert result.metadata.get("encoding_converted") is True or len(result.warnings) > 0

    def test_extract_windows1256_with_special_chars(self, extractor):
        """Test Windows-1256 with special Arabic characters."""
        # Include special Arabic punctuation and digits
        content = "السعر: ١٠٠ دولار، التاريخ: ٢٠٢٥/٠١/١٥\n"
        file_obj = io.BytesIO(content.encode("windows-1256"))

        result = extractor.extract(file_obj, "special_chars.txt")

        assert "السعر" in result.text
        assert "دولار" in result.text
        assert result.metadata.get("detected_encoding") in ["windows-1256", "cp1256"]


class TestEncodingDetection:
    """Test automatic encoding detection using chardet."""

    @pytest.fixture
    def extractor(self):
        """Create text extractor instance."""
        return TextExtractor()

    def test_detect_utf8_automatically(self, extractor):
        """Test that UTF-8 is detected when not explicitly specified."""
        content = "English text with UTF-8 encoding\n"
        file_obj = io.BytesIO(content.encode("utf-8"))

        result = extractor.extract(file_obj, "auto_detect.txt")

        assert result.text == content
        assert result.metadata.get("detected_encoding") in ["utf-8", "ascii"]

    def test_detect_windows1256_automatically(self, extractor):
        """Test that Windows-1256 is detected automatically."""
        content = "نص عربي بترميز ويندوز\nاختبار الكشف التلقائي\n"
        file_obj = io.BytesIO(content.encode("windows-1256"))

        result = extractor.extract(file_obj, "auto_arabic.txt")

        assert "نص عربي" in result.text
        assert result.metadata.get("detected_encoding") in ["windows-1256", "cp1256"]

    def test_detect_latin1_automatically(self, extractor):
        """Test detection of ISO-8859-1 (Latin-1) encoding."""
        content = "Résumé café naïve\n"  # French text with accents
        file_obj = io.BytesIO(content.encode("iso-8859-1"))

        result = extractor.extract(file_obj, "french.txt")

        assert "Résumé" in result.text
        assert "café" in result.text
        assert result.metadata.get("detected_encoding") in ["iso-8859-1", "latin-1", "windows-1252"]

    def test_detect_utf16_automatically(self, extractor):
        """Test detection of UTF-16 encoding."""
        content = "UTF-16 encoded text\nمع نص عربي\n"
        file_obj = io.BytesIO(content.encode("utf-16"))

        result = extractor.extract(file_obj, "utf16.txt")

        assert "UTF-16" in result.text
        assert "عربي" in result.text
        assert "utf-16" in result.metadata.get("detected_encoding", "").lower()

    def test_encoding_confidence_in_metadata(self, extractor):
        """Test that encoding detection confidence is included in metadata."""
        content = "مرحبا بك في النظام\n" * 5  # Longer text for better confidence
        file_obj = io.BytesIO(content.encode("utf-8"))

        result = extractor.extract(file_obj, "confident.txt")

        # Should include confidence score
        assert "encoding_confidence" in result.metadata
        assert isinstance(result.metadata["encoding_confidence"], (int, float))
        assert 0 <= result.metadata["encoding_confidence"] <= 1


class TestEncodingConversion:
    """Test automatic encoding conversion to UTF-8."""

    @pytest.fixture
    def extractor(self):
        """Create text extractor instance."""
        return TextExtractor()

    def test_conversion_windows1256_to_utf8(self, extractor):
        """Test conversion from Windows-1256 to UTF-8."""
        content = "نص عربي للتحويل\n"
        file_obj = io.BytesIO(content.encode("windows-1256"))

        result = extractor.extract(file_obj, "convert.txt")

        # Result text should be valid UTF-8
        assert "نص عربي" in result.text
        # Verify it's valid UTF-8 by encoding/decoding
        result.text.encode("utf-8").decode("utf-8")
        assert result.metadata.get("encoding_converted") is True

    def test_conversion_latin1_to_utf8(self, extractor):
        """Test conversion from Latin-1 to UTF-8."""
        content = "Café résumé\n"
        file_obj = io.BytesIO(content.encode("iso-8859-1"))

        result = extractor.extract(file_obj, "convert_latin.txt")

        assert "Café" in result.text
        # Verify UTF-8 validity
        result.text.encode("utf-8").decode("utf-8")

    def test_no_conversion_needed_for_utf8(self, extractor):
        """Test that UTF-8 content is not re-converted."""
        content = "Already UTF-8\nمع نص عربي\n"
        file_obj = io.BytesIO(content.encode("utf-8"))

        result = extractor.extract(file_obj, "already_utf8.txt")

        assert result.text == content
        # Should not have conversion flag
        assert result.metadata.get("encoding_converted") in [False, None]


class TestStructurePreservation:
    """Test preservation of text structure (numbered sections, bullets)."""

    @pytest.fixture
    def extractor(self):
        """Create text extractor instance."""
        return TextExtractor()

    def test_preserve_numbered_sections(self, extractor):
        """Test that numbered sections are preserved."""
        content = """1. First Section
   Introduction text here.

2. Second Section
   More content here.

3. Third Section
   Final content.
"""
        file_obj = io.BytesIO(content.encode("utf-8"))

        result = extractor.extract(file_obj, "numbered.txt")

        assert result.text == content
        assert "1. First Section" in result.text
        assert "2. Second Section" in result.text
        assert "3. Third Section" in result.text
        # Should detect structure
        assert result.metadata.get("has_structure") is True

    def test_preserve_bullet_points(self, extractor):
        """Test that bullet points are preserved."""
        content = """Items:
- First item
- Second item
  * Nested item
  * Another nested
- Third item
"""
        file_obj = io.BytesIO(content.encode("utf-8"))

        result = extractor.extract(file_obj, "bullets.txt")

        assert result.text == content
        assert "- First item" in result.text
        assert "* Nested item" in result.text
        assert result.metadata.get("has_structure") is True

    def test_preserve_mixed_structure(self, extractor):
        """Test preservation of mixed numbering and bullets."""
        content = """1. Section One
   - Point A
   - Point B

2. Section Two
   * Point X
   * Point Y
"""
        file_obj = io.BytesIO(content.encode("utf-8"))

        result = extractor.extract(file_obj, "mixed.txt")

        assert result.text == content
        assert "1. Section One" in result.text
        assert "- Point A" in result.text
        assert "* Point Y" in result.text
        assert result.metadata.get("has_structure") is True

    def test_detect_no_structure(self, extractor):
        """Test detection when content has no special structure."""
        content = "Just plain paragraph text.\nNo structure here.\nJust content.\n"
        file_obj = io.BytesIO(content.encode("utf-8"))

        result = extractor.extract(file_obj, "plain.txt")

        assert result.text == content
        assert result.metadata.get("has_structure") is False


class TestLineEndings:
    """Test handling of different line ending styles."""

    @pytest.fixture
    def extractor(self):
        """Create text extractor instance."""
        return TextExtractor()

    def test_unix_line_endings(self, extractor):
        """Test Unix line endings (LF - \\n)."""
        content = "Line 1\nLine 2\nLine 3\n"
        file_obj = io.BytesIO(content.encode("utf-8"))

        result = extractor.extract(file_obj, "unix.txt")

        assert result.text == content
        assert result.metadata.get("line_ending_style") == "unix"

    def test_windows_line_endings(self, extractor):
        """Test Windows line endings (CRLF - \\r\\n)."""
        content = "Line 1\r\nLine 2\r\nLine 3\r\n"
        file_obj = io.BytesIO(content.encode("utf-8"))

        result = extractor.extract(file_obj, "windows.txt")

        # Line endings should be normalized to \n or preserved
        assert "Line 1" in result.text
        assert "Line 2" in result.text
        assert result.metadata.get("line_ending_style") == "windows"

    def test_mac_line_endings(self, extractor):
        """Test old Mac line endings (CR - \\r)."""
        content = "Line 1\rLine 2\rLine 3\r"
        file_obj = io.BytesIO(content.encode("utf-8"))

        result = extractor.extract(file_obj, "mac.txt")

        assert "Line 1" in result.text
        assert "Line 2" in result.text
        assert result.metadata.get("line_ending_style") == "mac"

    def test_mixed_line_endings(self, extractor):
        """Test mixed line endings (should be detected and warned)."""
        content = "Line 1\nLine 2\r\nLine 3\rLine 4\n"
        file_obj = io.BytesIO(content.encode("utf-8"))

        result = extractor.extract(file_obj, "mixed.txt")

        assert result.metadata.get("line_ending_style") == "mixed"
        # Should have a warning about mixed line endings
        assert any("line ending" in w.lower() for w in result.warnings)


class TestEdgeCases:
    """Test edge cases and error handling."""

    @pytest.fixture
    def extractor(self):
        """Create text extractor instance."""
        return TextExtractor()

    def test_empty_file(self, extractor):
        """Test extraction from empty file."""
        file_obj = io.BytesIO(b"")

        result = extractor.extract(file_obj, "empty.txt")

        assert result.text == ""
        assert result.content_type == ContentType.TEXT
        # Should have warning about empty file
        assert any("empty" in w.lower() for w in result.warnings)

    def test_very_large_file(self, extractor):
        """Test extraction from large file (>5MB)."""
        # Create 6MB of text
        large_content = "A" * (6 * 1024 * 1024)
        file_obj = io.BytesIO(large_content.encode("utf-8"))

        result = extractor.extract(file_obj, "large.txt", max_size_mb=10)

        # Should extract successfully
        assert len(result.text) > 5_000_000
        # May have warning about large file
        assert result.metadata.get("file_size_mb") > 5

    def test_file_exceeds_size_limit(self, extractor):
        """Test that files exceeding size limit are rejected."""
        # Create 30MB of text (exceeds typical 25MB limit)
        huge_content = "B" * (30 * 1024 * 1024)
        file_obj = io.BytesIO(huge_content.encode("utf-8"))

        with pytest.raises(ValueError, match="exceeds maximum"):
            extractor.extract(file_obj, "huge.txt", max_size_mb=25)

    def test_binary_content_warning(self, extractor):
        """Test warning when file contains significant binary content."""
        # Mix of text and binary
        content = b"Some text\x00\x01\x02\x03\x04\x05more text\x00\x00"
        file_obj = io.BytesIO(content)

        result = extractor.extract(file_obj, "binary.txt")

        # Should have warning about binary content
        assert any("binary" in w.lower() or "non-text" in w.lower() for w in result.warnings)

    def test_invalid_encoding(self, extractor):
        """Test handling of invalid/corrupted encoding."""
        # Invalid UTF-8 sequence
        content = b"Valid text\xff\xfe\xfdmore text"
        file_obj = io.BytesIO(content)

        result = extractor.extract(file_obj, "corrupt.txt")

        # Should have text (with replacement characters) and warning
        assert len(result.text) > 0
        assert any("encoding" in w.lower() or "decode" in w.lower() for w in result.warnings)

    def test_only_whitespace(self, extractor):
        """Test file containing only whitespace."""
        content = "   \n\n\t\t  \n   "
        file_obj = io.BytesIO(content.encode("utf-8"))

        result = extractor.extract(file_obj, "whitespace.txt")

        assert result.text == content
        # Should have warning about only whitespace
        assert any("whitespace" in w.lower() or "empty" in w.lower() for w in result.warnings)


class TestMetadataExtraction:
    """Test extraction of file metadata."""

    @pytest.fixture
    def extractor(self):
        """Create text extractor instance."""
        return TextExtractor()

    def test_metadata_includes_encoding(self, extractor):
        """Test that metadata includes detected encoding."""
        content = "Test content\n"
        file_obj = io.BytesIO(content.encode("utf-8"))

        result = extractor.extract(file_obj, "meta.txt")

        assert "detected_encoding" in result.metadata
        assert result.metadata["detected_encoding"] in ["utf-8", "ascii"]

    def test_metadata_includes_line_count(self, extractor):
        """Test that metadata includes line count."""
        content = "Line 1\nLine 2\nLine 3\n"
        file_obj = io.BytesIO(content.encode("utf-8"))

        result = extractor.extract(file_obj, "lines.txt")

        assert "line_count" in result.metadata
        assert result.metadata["line_count"] == 3

    def test_metadata_includes_char_count(self, extractor):
        """Test that metadata includes character count."""
        content = "Hello World"
        file_obj = io.BytesIO(content.encode("utf-8"))

        result = extractor.extract(file_obj, "chars.txt")

        assert "char_count" in result.metadata
        assert result.metadata["char_count"] == len(content)

    def test_metadata_includes_structure_flag(self, extractor):
        """Test that metadata includes structure detection flag."""
        content = "1. First\n2. Second\n"
        file_obj = io.BytesIO(content.encode("utf-8"))

        result = extractor.extract(file_obj, "structure.txt")

        assert "has_structure" in result.metadata
        assert isinstance(result.metadata["has_structure"], bool)


class TestQualityIndicators:
    """Test extraction quality indicators."""

    @pytest.fixture
    def extractor(self):
        """Create text extractor instance."""
        return TextExtractor()

    def test_quality_indicators_present(self, extractor):
        """Test that quality indicators are provided."""
        content = "مرحبا بك في النظام\n"
        file_obj = io.BytesIO(content.encode("utf-8"))

        result = extractor.extract(file_obj, "quality.txt")

        assert result.quality_indicators is not None
        assert isinstance(result.quality_indicators, dict)

    def test_quality_high_for_clean_utf8(self, extractor):
        """Test that clean UTF-8 files get high quality score."""
        content = "Clean UTF-8 content\nNo issues here\n"
        file_obj = io.BytesIO(content.encode("utf-8"))

        result = extractor.extract(file_obj, "clean.txt")

        assert result.quality_indicators.get("extraction_quality") == "high"

    def test_quality_medium_for_converted_encoding(self, extractor):
        """Test that converted encodings get medium quality score."""
        content = "نص عربي\n"
        file_obj = io.BytesIO(content.encode("windows-1256"))

        result = extractor.extract(file_obj, "converted.txt")

        # Medium quality due to encoding conversion
        assert result.quality_indicators.get("extraction_quality") in ["medium", "high"]

    def test_quality_low_for_corrupted_content(self, extractor):
        """Test that corrupted content gets low quality score."""
        content = b"Text\xff\xfe\xfdcorrupt\x00\x01"
        file_obj = io.BytesIO(content)

        result = extractor.extract(file_obj, "corrupt.txt")

        # Low quality due to corruption
        assert result.quality_indicators.get("extraction_quality") == "low"


class TestExtractionOptions:
    """Test optional extraction parameters."""

    @pytest.fixture
    def extractor(self):
        """Create text extractor instance."""
        return TextExtractor()

    def test_custom_encoding_hint(self, extractor):
        """Test providing encoding hint as option."""
        content = "نص عربي\n"
        file_obj = io.BytesIO(content.encode("windows-1256"))

        result = extractor.extract(file_obj, "hint.txt", encoding_hint="windows-1256")

        assert "نص عربي" in result.text
        assert result.metadata.get("encoding_hint_used") is True

    def test_disable_structure_detection(self, extractor):
        """Test disabling structure detection via option."""
        content = "1. First\n2. Second\n"
        file_obj = io.BytesIO(content.encode("utf-8"))

        result = extractor.extract(file_obj, "no_struct.txt", detect_structure=False)

        assert result.text == content
        # Structure detection was disabled
        assert result.metadata.get("structure_detection_enabled") is False

    def test_max_size_enforcement(self, extractor):
        """Test that max_size_mb option is enforced."""
        large_content = "X" * (2 * 1024 * 1024)  # 2MB
        file_obj = io.BytesIO(large_content.encode("utf-8"))

        # Should fail with 1MB limit
        with pytest.raises(ValueError, match="exceeds maximum"):
            extractor.extract(file_obj, "toolarge.txt", max_size_mb=1)
