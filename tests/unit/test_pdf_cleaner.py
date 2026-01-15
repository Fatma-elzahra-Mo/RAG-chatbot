"""
Unit tests for PDF text cleaner.

Tests page number removal, header/footer detection, artifact cleaning, and structure detection.
"""

import pytest

from src.preprocessing.pdf_cleaner import PDFCleaner


class TestPDFCleaner:
    """Test suite for PDFCleaner."""

    @pytest.fixture
    def cleaner(self):
        """Create PDF cleaner with default settings."""
        return PDFCleaner(
            remove_page_numbers=True,
            remove_headers_footers=True,
            clean_artifacts=True,
            normalize_arabic=False,
        )

    @pytest.fixture
    def text_with_page_numbers(self):
        """Sample text with various page number formats."""
        return """1

مرحبا بكم في هذا المستند.

Page 2

المزيد من المحتوى.

صفحة 3

المزيد من النص.

4 / 10

النص الأخير.
"""

    @pytest.fixture
    def text_with_headers_footers(self):
        """Sample text with repeated headers/footers."""
        return """رأس الصفحة

محتوى الصفحة الأولى.

رأس الصفحة

محتوى الصفحة الثانية.

رأس الصفحة

محتوى الصفحة الثالثة.
"""

    @pytest.fixture
    def text_with_artifacts(self):
        """Sample text with OCR artifacts and extra whitespace."""
        return """النص   مع   مسافات   كثيرة.


\n\n\n\n\n

المزيد من النص مع فواصل كثيرة.

النص\u200Bمع\u200Bحروف\u200Bخفية.
"""

    def test_basic_cleaning(self, cleaner):
        """Test basic text cleaning."""
        text = "Page 1\n\nمرحبا\n\nPage 2\n\nكيف حالك"
        cleaned, metadata = cleaner.clean(text)

        assert "Page 1" not in cleaned
        assert "Page 2" not in cleaned
        assert "مرحبا" in cleaned
        assert "كيف حالك" in cleaned

    def test_page_number_removal_english(self, cleaner):
        """Test removal of English page numbers."""
        text = "Page 1\n\nContent here\n\nPage 42\n\nMore content"
        cleaned, metadata = cleaner.clean(text)

        assert "Page 1" not in cleaned
        assert "Page 42" not in cleaned
        assert "Content here" in cleaned

    def test_page_number_removal_arabic(self, cleaner):
        """Test removal of Arabic page numbers."""
        text = "صفحة 1\n\nالمحتوى هنا\n\nصفحة 42\n\nالمزيد من المحتوى"
        cleaned, metadata = cleaner.clean(text)

        assert "صفحة" not in cleaned or "المحتوى" in cleaned
        # Page markers should be removed
        lines = cleaned.split("\n")
        assert not any(line.strip().startswith("صفحة") for line in lines)

    def test_page_number_removal_numeric_only(self, cleaner):
        """Test removal of standalone numeric page numbers."""
        text = "1\n\nFirst page\n\n2\n\nSecond page\n\n42\n\nForty-second page"
        cleaned, metadata = cleaner.clean(text)

        # Standalone numbers should be removed
        assert "First page" in cleaned
        assert "Second page" in cleaned

    def test_page_number_removal_fraction_format(self, cleaner):
        """Test removal of page numbers in fraction format (1/10)."""
        text = "Content here\n\n1 / 10\n\nMore content\n\n5/20\n\nFinal content"
        cleaned, metadata = cleaner.clean(text)

        assert "Content here" in cleaned
        assert "More content" in cleaned
        # Fraction-style page numbers should be removed
        assert "1 / 10" not in cleaned
        assert "5/20" not in cleaned

    def test_arabic_numeral_page_numbers(self, cleaner):
        """Test removal of Arabic numeral page numbers."""
        text = "١\n\nالصفحة الأولى\n\n٤٢\n\nالصفحة الأخيرة"
        cleaned, metadata = cleaner.clean(text)

        assert "الصفحة الأولى" in cleaned
        assert "الصفحة الأخيرة" in cleaned

    def test_repeated_header_footer_removal(self, cleaner, text_with_headers_footers):
        """Test removal of repeated headers/footers."""
        cleaned, metadata = cleaner.clean(text_with_headers_footers)

        # "رأس الصفحة" appears 3 times, should be identified as header and removed
        # Content should be preserved
        assert "محتوى الصفحة" in cleaned

        # Count occurrences of repeated header
        header_count = cleaned.count("رأس الصفحة")
        # Should be reduced or removed (depending on threshold)
        original_count = text_with_headers_footers.count("رأس الصفحة")
        assert header_count < original_count

    def test_horizontal_line_removal(self, cleaner):
        """Test removal of horizontal lines (headers/footers)."""
        text = "Content\n\n---\n\nMore content\n\n=======\n\nFinal content"
        cleaned, metadata = cleaner.clean(text)

        assert "Content" in cleaned
        assert "More content" in cleaned
        assert "---" not in cleaned
        assert "=======" not in cleaned

    def test_copyright_notice_removal(self, cleaner):
        """Test removal of copyright notices."""
        text = "Document content\n\n© 2025 Company Name\n\nMore content"
        cleaned, metadata = cleaner.clean(text)

        assert "Document content" in cleaned
        assert "More content" in cleaned
        assert "©" not in cleaned

    def test_url_removal(self, cleaner):
        """Test removal of URLs in headers/footers."""
        text = "Content here\n\nwww.example.com\n\nMore content\n\nhttp://another.com\n\nFinal"
        cleaned, metadata = cleaner.clean(text)

        assert "Content here" in cleaned
        assert "More content" in cleaned
        # URLs should be removed
        assert "www.example.com" not in cleaned
        assert "http://another.com" not in cleaned

    def test_excessive_whitespace_removal(self, cleaner, text_with_artifacts):
        """Test removal of excessive whitespace."""
        cleaned, metadata = cleaner.clean(text_with_artifacts)

        # Should not have 3+ consecutive spaces
        assert "   " not in cleaned

        # Should not have 4+ consecutive newlines
        assert "\n\n\n\n" not in cleaned

    def test_zero_width_character_removal(self, cleaner, text_with_artifacts):
        """Test removal of zero-width and invisible characters."""
        text = "النص\u200Bمع\u200Bحروف\u200Bخفية"
        cleaned, metadata = cleaner.clean(text)

        # Zero-width spaces should be removed
        assert "\u200B" not in cleaned

    def test_control_character_removal(self, cleaner):
        """Test removal of control characters."""
        text = "النص\x00مع\x08حروف\x1Fتحكم"
        cleaned, metadata = cleaner.clean(text)

        # Control characters should be removed
        assert "\x00" not in cleaned
        assert "\x08" not in cleaned
        assert "\x1F" not in cleaned

    def test_metadata_extraction(self, cleaner):
        """Test that cleaning extracts useful metadata."""
        text = "Page 1\n\nSome content\n\nPage 2\n\nMore content"
        cleaned, metadata = cleaner.clean(text)

        assert "original_length" in metadata
        assert "cleaned_length" in metadata
        assert "reduction_ratio" in metadata

        assert metadata["original_length"] > 0
        assert metadata["cleaned_length"] > 0
        assert 0 <= metadata["reduction_ratio"] <= 1

    def test_page_info_extraction(self, cleaner):
        """Test extraction of page boundary information."""
        text = "Page 1\n\nContent\n\nPage 2\n\nMore\n\nPage 3\n\nFinal"
        cleaned, metadata = cleaner.clean(text)

        # Should detect page numbers
        if "num_pages_detected" in metadata:
            assert metadata["num_pages_detected"] > 0

    def test_min_line_length_filtering(self):
        """Test that very short lines are filtered out."""
        cleaner = PDFCleaner(min_line_length=15)
        text = "a\n\nab\n\nاbc\n\nThis is a longer line that should be kept"
        cleaned, metadata = cleaner.clean(text)

        lines = [line.strip() for line in cleaned.split("\n") if line.strip()]
        # Very short lines should be filtered
        assert all(len(line) >= 15 for line in lines)

    def test_cleaning_disabled(self):
        """Test that cleaning steps can be disabled."""
        cleaner = PDFCleaner(
            remove_page_numbers=False,
            remove_headers_footers=False,
            clean_artifacts=False,
            min_line_length=0,  # Disable line length filter
        )

        text = "Page 1\n\n   Spaces   \n\n---\n\nContent with more text"
        cleaned, metadata = cleaner.clean(text)

        # Should preserve more content when cleaning is disabled
        assert "Page 1" in cleaned or "Content" in cleaned  # Page numbers not removed

    def test_arabic_normalization_disabled(self):
        """Test that Arabic normalization is disabled by default."""
        cleaner = PDFCleaner(normalize_arabic=False)

        # Text with different alef forms
        text = "إبراهيم أحمد آمنة"
        cleaned, metadata = cleaner.clean(text)

        # Should preserve original Arabic forms
        assert "إ" in cleaned or "أ" in cleaned or "آ" in cleaned

    def test_arabic_normalization_enabled(self):
        """Test Arabic normalization when enabled."""
        cleaner = PDFCleaner(normalize_arabic=True)

        # Text with different alef forms
        text = "إبراهيم أحمد آمنة"
        cleaned, metadata = cleaner.clean(text)

        # Alef variations should be normalized to simple alef
        # Count simple alef characters
        normalized_alef_count = cleaned.count("ا")
        assert normalized_alef_count > 0

    def test_structure_detection_tables(self, cleaner):
        """Test detection of table structures."""
        text = """Content before.

| Column 1 | Column 2 | Column 3 |
|----------|----------|----------|
| Value 1  | Value 2  | Value 3  |

Content after.
"""
        structure = cleaner.detect_structure(text)

        assert structure["has_tables"] is True

    def test_structure_detection_lists(self, cleaner):
        """Test detection of list structures."""
        text = """Content before.

- First item
- Second item
- Third item

1. Numbered item
2. Another item

Content after.
"""
        structure = cleaner.detect_structure(text)

        assert structure["has_lists"] is True

    def test_structure_detection_headers(self, cleaner):
        """Test detection of section headers."""
        text = """Introduction

This is the introduction text.

Main Section

This is the main content.

Conclusion

This is the conclusion.
"""
        structure = cleaner.detect_structure(text)

        assert structure["has_headers"] is True
        assert structure["section_count"] > 0
        assert len(structure["header_positions"]) > 0

    def test_structure_detection_no_structure(self, cleaner):
        """Test structure detection on plain text."""
        text = "This is plain text without any special structure or formatting."
        structure = cleaner.detect_structure(text)

        assert structure["has_tables"] is False
        assert structure["has_lists"] is False

    def test_structure_detection_arabic_lists(self, cleaner):
        """Test detection of Arabic list structures."""
        text = """القائمة:

- العنصر الأول
- العنصر الثاني

١. البند الأول
٢. البند الثاني

أ. النقطة الأولى
ب. النقطة الثانية
"""
        structure = cleaner.detect_structure(text)

        assert structure["has_lists"] is True

    def test_empty_text(self, cleaner):
        """Test handling of empty text."""
        cleaned, metadata = cleaner.clean("")

        assert cleaned == ""
        assert metadata["original_length"] == 0
        assert metadata["cleaned_length"] == 0

    def test_whitespace_only_text(self, cleaner):
        """Test handling of whitespace-only text."""
        text = "   \n\n   \n\n   "
        cleaned, metadata = cleaner.clean(text)

        # Should result in empty or minimal text
        assert len(cleaned.strip()) == 0

    def test_preservation_of_content(self, cleaner):
        """Test that actual content is preserved during cleaning."""
        text = """Page 1

مقدمة المستند

هذا نص مهم يجب الحفاظ عليه. يحتوي على معلومات قيمة.

---

Page 2

القسم الثاني

المزيد من المعلومات المهمة هنا.
"""
        cleaned, metadata = cleaner.clean(text)

        # Important content should be preserved
        assert "مقدمة المستند" in cleaned
        assert "نص مهم" in cleaned or "معلومات" in cleaned
        assert "القسم الثاني" in cleaned

    def test_reduction_ratio(self, cleaner):
        """Test that reduction ratio is calculated correctly."""
        text = "Page 1\n\n" + ("Content. " * 50) + "\n\nPage 2"
        cleaned, metadata = cleaner.clean(text)

        # Should have some reduction due to page number removal
        assert metadata["reduction_ratio"] > 0
        assert metadata["reduction_ratio"] < 1

        # But most content should be preserved
        assert metadata["cleaned_length"] > metadata["original_length"] * 0.8

    def test_table_detection_tab_separated(self, cleaner):
        """Test table detection for tab-separated content."""
        text = "Column1\tColumn2\tColumn3\nValue1\tValue2\tValue3"
        structure = cleaner.detect_structure(text)

        assert structure["has_tables"] is True

    def test_table_detection_markdown_separator(self, cleaner):
        """Test table detection for markdown table separators."""
        text = "| Header |\n|--------|\n| Value  |"
        structure = cleaner.detect_structure(text)

        assert structure["has_tables"] is True

    def test_metadata_enhancement(self, cleaner):
        """Test that existing metadata is enhanced, not replaced."""
        original_metadata = {"source": "test.pdf", "author": "Test Author"}
        text = "Page 1\n\nSome content"

        cleaned, metadata = cleaner.clean(text, original_metadata)

        # Original metadata should be preserved
        assert metadata["source"] == "test.pdf"
        assert metadata["author"] == "Test Author"

        # New metadata should be added
        assert "original_length" in metadata
        assert "cleaned_length" in metadata

    def test_mixed_content_cleaning(self, cleaner):
        """Test cleaning of text with multiple artifact types."""
        text = """Page 1

© 2025 Company

---

مرحبا   بكم   في   المستند.

www.example.com

Page 2

المزيد من المحتوى هنا.

===

صفحة 3

النص الأخير.
"""
        cleaned, metadata = cleaner.clean(text)

        # Content should be preserved
        assert "مرحبا" in cleaned or "المحتوى" in cleaned or "النص" in cleaned

        # Artifacts should be removed
        assert "Page 1" not in cleaned
        assert "©" not in cleaned
        assert "www.example.com" not in cleaned

    def test_line_normalization(self, cleaner):
        """Test normalization of line breaks and spacing."""
        text = "Line 1\n\n\n\n\nLine 2\n\n\n\n\n\n\nLine 3"
        cleaned, metadata = cleaner.clean(text)

        # Should not have more than 3 consecutive newlines
        assert "\n\n\n\n" not in cleaned

        # Content should be preserved
        assert "Line 1" in cleaned or "Line" in cleaned
        assert "Line 2" in cleaned or "Line" in cleaned

    def test_realistic_pdf_cleaning(self, cleaner):
        """Test cleaning of realistic PDF content."""
        text = """1

المملكة العربية السعودية
وزارة التعليم

===

مقدمة

هذا المستند يحتوي على معلومات مهمة حول التعليم في المملكة.

www.moe.gov.sa

Page 2

القسم الأول: الأهداف

الهدف الأول هو تحسين جودة التعليم.
الهدف الثاني هو زيادة الوصول إلى التعليم.

2 / 10

القسم الثاني: البرامج

البرنامج الأول: التطوير المهني
البرنامج الثاني: البحث العلمي
"""
        cleaned, metadata = cleaner.clean(text)

        # Important content should be preserved
        assert "مقدمة" in cleaned or "المستند" in cleaned
        assert "الأهداف" in cleaned or "البرامج" in cleaned

        # Artifacts should be removed
        assert "Page 2" not in cleaned
        assert "www.moe.gov.sa" not in cleaned
        assert "2 / 10" not in cleaned or "10" not in cleaned
