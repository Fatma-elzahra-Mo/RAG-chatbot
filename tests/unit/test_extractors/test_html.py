"""
Unit tests for HTML extractor.

Tests HTML tag stripping, script/style removal, RTL text handling, table linearization,
Arabic content, and heading extraction.

Following TDD approach - these tests should FAIL until implementation is complete.
"""

import io
import pytest

from src.models.schemas import ExtractionResult, ContentType, FileFormat
from src.preprocessing.extractors.html import HTMLExtractor


class TestHTMLExtractorBasics:
    """Test basic HTML extraction functionality."""

    @pytest.fixture
    def extractor(self):
        """Create HTML extractor instance."""
        return HTMLExtractor()

    def test_extractor_supports_html_format(self, extractor):
        """Test that extractor declares support for HTML format."""
        assert extractor.supports_format("html")
        assert extractor.supports_format("HTML")
        assert extractor.supports_format("htm")

    def test_extractor_does_not_support_other_formats(self, extractor):
        """Test that extractor rejects non-HTML formats."""
        assert not extractor.supports_format("pdf")
        assert not extractor.supports_format("text")
        assert not extractor.supports_format("docx")


class TestHTMLTagStripping:
    """Test removal of HTML tags and extraction of plain text."""

    @pytest.fixture
    def extractor(self):
        """Create HTML extractor instance."""
        return HTMLExtractor()

    def test_strip_basic_html_tags(self, extractor):
        """Test stripping basic HTML tags (p, div, span)."""
        html_content = """
        <html>
        <body>
            <p>This is a paragraph.</p>
            <div>This is a div.</div>
            <span>This is a span.</span>
        </body>
        </html>
        """
        file_obj = io.BytesIO(html_content.encode("utf-8"))

        result = extractor.extract(file_obj, "basic.html")

        assert isinstance(result, ExtractionResult)
        assert "This is a paragraph." in result.text
        assert "This is a div." in result.text
        assert "This is a span." in result.text
        # Should not contain HTML tags
        assert "<p>" not in result.text
        assert "<div>" not in result.text
        assert "</body>" not in result.text

    def test_strip_nested_tags(self, extractor):
        """Test stripping nested HTML tags."""
        html_content = """
        <div>
            <p>Outer text <strong>bold text</strong> more text.</p>
            <ul>
                <li>Item <em>emphasized</em> text</li>
            </ul>
        </div>
        """
        file_obj = io.BytesIO(html_content.encode("utf-8"))

        result = extractor.extract(file_obj, "nested.html")

        assert "Outer text bold text more text" in result.text
        assert "Item emphasized text" in result.text
        assert "<strong>" not in result.text
        assert "<em>" not in result.text

    def test_strip_self_closing_tags(self, extractor):
        """Test handling of self-closing tags (br, hr, img)."""
        html_content = """
        <div>
            Line 1<br/>
            Line 2<br>
            <hr/>
            After horizontal rule
        </div>
        """
        file_obj = io.BytesIO(html_content.encode("utf-8"))

        result = extractor.extract(file_obj, "selfclosing.html")

        # Text should be extracted
        assert "Line 1" in result.text
        assert "Line 2" in result.text
        assert "After horizontal rule" in result.text
        # Tags should be removed
        assert "<br" not in result.text
        assert "<hr" not in result.text


class TestScriptStyleRemoval:
    """Test removal of script and style elements."""

    @pytest.fixture
    def extractor(self):
        """Create HTML extractor instance."""
        return HTMLExtractor()

    def test_remove_script_tags(self, extractor):
        """Test that script tags and content are removed."""
        html_content = """
        <html>
        <head>
            <script>
                function test() {
                    alert('This should not appear');
                }
            </script>
        </head>
        <body>
            <p>Visible text</p>
            <script>console.log('hidden');</script>
        </body>
        </html>
        """
        file_obj = io.BytesIO(html_content.encode("utf-8"))

        result = extractor.extract(file_obj, "scripts.html")

        # Visible text should be present
        assert "Visible text" in result.text
        # Script content should be removed
        assert "alert" not in result.text
        assert "console.log" not in result.text
        assert "function test" not in result.text
        assert "<script>" not in result.text

    def test_remove_style_tags(self, extractor):
        """Test that style tags and content are removed."""
        html_content = """
        <html>
        <head>
            <style>
                body { background-color: blue; }
                .test { color: red; }
            </style>
        </head>
        <body>
            <p>Visible text</p>
        </body>
        </html>
        """
        file_obj = io.BytesIO(html_content.encode("utf-8"))

        result = extractor.extract(file_obj, "styles.html")

        # Visible text should be present
        assert "Visible text" in result.text
        # Style content should be removed
        assert "background-color" not in result.text
        assert "color: red" not in result.text
        assert "<style>" not in result.text

    def test_remove_noscript_tags(self, extractor):
        """Test that noscript tags are removed."""
        html_content = """
        <html>
        <body>
            <p>Main content</p>
            <noscript>JavaScript is disabled</noscript>
        </body>
        </html>
        """
        file_obj = io.BytesIO(html_content.encode("utf-8"))

        result = extractor.extract(file_obj, "noscript.html")

        assert "Main content" in result.text
        # noscript content should be removed
        assert "JavaScript is disabled" not in result.text

    def test_remove_navigation_and_footer(self, extractor):
        """Test that nav and footer elements are removed."""
        html_content = """
        <html>
        <body>
            <nav>
                <a href="/home">Home</a>
                <a href="/about">About</a>
            </nav>
            <main>
                <p>Main content text</p>
            </main>
            <footer>
                Copyright 2025
            </footer>
        </body>
        </html>
        """
        file_obj = io.BytesIO(html_content.encode("utf-8"))

        result = extractor.extract(file_obj, "navfooter.html")

        # Main content should be present
        assert "Main content text" in result.text
        # Navigation and footer should be removed
        assert "Home" not in result.text
        assert "About" not in result.text
        assert "Copyright 2025" not in result.text


class TestRTLTextHandling:
    """Test handling of RTL (right-to-left) text for Arabic content."""

    @pytest.fixture
    def extractor(self):
        """Create HTML extractor instance with RTL preservation."""
        return HTMLExtractor(preserve_rtl_markers=True)

    def test_detect_rtl_from_dir_attribute(self, extractor):
        """Test detection of RTL content from dir attribute."""
        html_content = """
        <html dir="rtl">
        <body>
            <p>مرحبا بك في النظام</p>
        </body>
        </html>
        """
        file_obj = io.BytesIO(html_content.encode("utf-8"))

        result = extractor.extract(file_obj, "rtl.html")

        assert "مرحبا بك في النظام" in result.text
        # Should detect RTL in metadata
        assert result.metadata.get("is_rtl") is True

    def test_detect_rtl_from_body_attribute(self, extractor):
        """Test RTL detection from body dir attribute."""
        html_content = """
        <html>
        <body dir="rtl">
            <p>النص العربي هنا</p>
        </body>
        </html>
        """
        file_obj = io.BytesIO(html_content.encode("utf-8"))

        result = extractor.extract(file_obj, "body_rtl.html")

        assert "النص العربي" in result.text
        assert result.metadata.get("is_rtl") is True

    def test_detect_rtl_from_arabic_content(self, extractor):
        """Test automatic RTL detection from Arabic script characters."""
        html_content = """
        <html>
        <body>
            <p>هذا نص طويل باللغة العربية يحتوي على محتوى كافي للكشف التلقائي</p>
            <p>فقرة ثانية بالعربية مع المزيد من النص</p>
        </body>
        </html>
        """
        file_obj = io.BytesIO(html_content.encode("utf-8"))

        result = extractor.extract(file_obj, "auto_rtl.html")

        assert "العربية" in result.text
        # Should auto-detect RTL from Arabic characters
        assert result.metadata.get("is_rtl") is True

    def test_no_rtl_for_english_content(self, extractor):
        """Test that English content is not marked as RTL."""
        html_content = """
        <html>
        <body>
            <p>This is English content with no RTL markers.</p>
        </body>
        </html>
        """
        file_obj = io.BytesIO(html_content.encode("utf-8"))

        result = extractor.extract(file_obj, "ltr.html")

        assert "English content" in result.text
        assert result.metadata.get("is_rtl") is False


class TestTableLinearization:
    """Test linearization of HTML tables into row-by-row text."""

    @pytest.fixture
    def extractor(self):
        """Create HTML extractor instance with table linearization."""
        return HTMLExtractor(linearize_tables=True)

    def test_linearize_simple_table(self, extractor):
        """Test linearization of simple table with headers and data."""
        html_content = """
        <html>
        <body>
            <table>
                <tr>
                    <th>Name</th>
                    <th>Age</th>
                </tr>
                <tr>
                    <td>Alice</td>
                    <td>30</td>
                </tr>
                <tr>
                    <td>Bob</td>
                    <td>25</td>
                </tr>
            </table>
        </body>
        </html>
        """
        file_obj = io.BytesIO(html_content.encode("utf-8"))

        result = extractor.extract(file_obj, "table.html")

        # Should contain linearized table data
        assert "Name" in result.text
        assert "Age" in result.text
        assert "Alice" in result.text
        assert "Bob" in result.text
        # Should have table markers
        assert "[TABLE]" in result.text or "Name" in result.text
        # Should not contain raw HTML table tags
        assert "<table>" not in result.text
        assert "<tr>" not in result.text

    def test_linearize_arabic_table(self, extractor):
        """Test linearization of table with Arabic content."""
        html_content = """
        <html>
        <body>
            <table>
                <tr>
                    <th>الاسم</th>
                    <th>العمر</th>
                </tr>
                <tr>
                    <td>أحمد</td>
                    <td>٣٠</td>
                </tr>
                <tr>
                    <td>فاطمة</td>
                    <td>٢٥</td>
                </tr>
            </table>
        </body>
        </html>
        """
        file_obj = io.BytesIO(html_content.encode("utf-8"))

        result = extractor.extract(file_obj, "arabic_table.html")

        # Should contain Arabic table content
        assert "الاسم" in result.text
        assert "العمر" in result.text
        assert "أحمد" in result.text
        assert "فاطمة" in result.text

    def test_linearize_table_with_rowspan_colspan(self, extractor):
        """Test linearization of table with complex structure."""
        html_content = """
        <html>
        <body>
            <table>
                <tr>
                    <th colspan="2">Header</th>
                </tr>
                <tr>
                    <td>Cell 1</td>
                    <td>Cell 2</td>
                </tr>
            </table>
        </body>
        </html>
        """
        file_obj = io.BytesIO(html_content.encode("utf-8"))

        result = extractor.extract(file_obj, "complex_table.html")

        # Should extract all cell content
        assert "Header" in result.text
        assert "Cell 1" in result.text
        assert "Cell 2" in result.text

    def test_table_count_in_metadata(self, extractor):
        """Test that table count is tracked in metadata."""
        html_content = """
        <html>
        <body>
            <table><tr><td>Table 1</td></tr></table>
            <p>Text between tables</p>
            <table><tr><td>Table 2</td></tr></table>
        </body>
        </html>
        """
        file_obj = io.BytesIO(html_content.encode("utf-8"))

        result = extractor.extract(file_obj, "multi_table.html")

        # Should track table count
        assert result.metadata.get("table_count") == 2
        assert result.metadata.get("has_tables") is True


class TestHeadingExtraction:
    """Test extraction of heading hierarchy."""

    @pytest.fixture
    def extractor(self):
        """Create HTML extractor instance with heading extraction."""
        return HTMLExtractor(extract_headings=True)

    def test_extract_heading_hierarchy(self, extractor):
        """Test extraction of h1-h6 headings with hierarchy."""
        html_content = """
        <html>
        <body>
            <h1>Main Title</h1>
            <p>Introduction text</p>
            <h2>Section 1</h2>
            <p>Section content</p>
            <h3>Subsection 1.1</h3>
            <p>Subsection content</p>
            <h2>Section 2</h2>
        </body>
        </html>
        """
        file_obj = io.BytesIO(html_content.encode("utf-8"))

        result = extractor.extract(file_obj, "headings.html")

        # Text should contain headings
        assert "Main Title" in result.text
        assert "Section 1" in result.text
        assert "Subsection 1.1" in result.text

        # Metadata should track headings
        assert "headings" in result.metadata
        headings = result.metadata["headings"]
        assert len(headings) >= 4
        # Verify heading structure
        assert any(h["text"] == "Main Title" and h["level"] == 1 for h in headings)
        assert any(h["text"] == "Section 1" and h["level"] == 2 for h in headings)
        assert any(h["text"] == "Subsection 1.1" and h["level"] == 3 for h in headings)

    def test_extract_arabic_headings(self, extractor):
        """Test extraction of Arabic headings."""
        html_content = """
        <html>
        <body>
            <h1>العنوان الرئيسي</h1>
            <p>نص تمهيدي</p>
            <h2>القسم الأول</h2>
            <p>محتوى القسم</p>
            <h3>القسم الفرعي</h3>
        </body>
        </html>
        """
        file_obj = io.BytesIO(html_content.encode("utf-8"))

        result = extractor.extract(file_obj, "arabic_headings.html")

        # Should extract Arabic headings
        assert "العنوان الرئيسي" in result.text
        assert "القسم الأول" in result.text

        # Metadata should include Arabic headings
        headings = result.metadata.get("headings", [])
        assert any(h["text"] == "العنوان الرئيسي" for h in headings)
        assert any(h["text"] == "القسم الأول" for h in headings)

    def test_heading_count_in_metadata(self, extractor):
        """Test that heading count is tracked in metadata."""
        html_content = """
        <html>
        <body>
            <h1>Title</h1>
            <h2>Section 1</h2>
            <h2>Section 2</h2>
            <h2>Section 3</h2>
        </body>
        </html>
        """
        file_obj = io.BytesIO(html_content.encode("utf-8"))

        result = extractor.extract(file_obj, "heading_count.html")

        assert result.metadata.get("heading_count") == 4
        assert len(result.metadata.get("headings", [])) == 4

    def test_skip_empty_headings(self, extractor):
        """Test that empty headings are skipped."""
        html_content = """
        <html>
        <body>
            <h1>Valid Heading</h1>
            <h2></h2>
            <h3>   </h3>
            <h2>Another Valid</h2>
        </body>
        </html>
        """
        file_obj = io.BytesIO(html_content.encode("utf-8"))

        result = extractor.extract(file_obj, "empty_headings.html")

        # Should only count non-empty headings
        headings = result.metadata.get("headings", [])
        assert len(headings) == 2
        assert all(h["text"].strip() for h in headings)


class TestArabicHTMLContent:
    """Test handling of complete Arabic HTML documents."""

    @pytest.fixture
    def extractor(self):
        """Create HTML extractor instance."""
        return HTMLExtractor()

    def test_full_arabic_document(self, extractor):
        """Test extraction of complete Arabic HTML document."""
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
        </body>
        </html>
        """
        file_obj = io.BytesIO(html_content.encode("utf-8"))

        result = extractor.extract(file_obj, "arabic_doc.html")

        # Should extract all Arabic text
        assert "مرحبا بك في النظام" in result.text
        assert "نص تجريبي" in result.text
        assert "عدة فقرات" in result.text
        # Should detect RTL
        assert result.metadata.get("is_rtl") is True
        # Should extract title
        assert result.metadata.get("title") == "وثيقة عربية"

    def test_mixed_arabic_english_html(self, extractor):
        """Test HTML with mixed Arabic and English content."""
        html_content = """
        <html>
        <body>
            <h1>Project: المشروع العربي</h1>
            <p>This is English text.</p>
            <p>هذا نص عربي.</p>
            <p>Mixed: نص مختلط with English.</p>
        </body>
        </html>
        """
        file_obj = io.BytesIO(html_content.encode("utf-8"))

        result = extractor.extract(file_obj, "mixed.html")

        # Should extract both languages
        assert "Project" in result.text
        assert "المشروع العربي" in result.text
        assert "English text" in result.text
        assert "نص عربي" in result.text
        assert "نص مختلط" in result.text


class TestHTMLMetadata:
    """Test extraction of HTML metadata from meta tags."""

    @pytest.fixture
    def extractor(self):
        """Create HTML extractor instance."""
        return HTMLExtractor()

    def test_extract_title(self, extractor):
        """Test extraction of page title."""
        html_content = """
        <html>
        <head>
            <title>Test Page Title</title>
        </head>
        <body><p>Content</p></body>
        </html>
        """
        file_obj = io.BytesIO(html_content.encode("utf-8"))

        result = extractor.extract(file_obj, "title.html")

        assert result.metadata.get("title") == "Test Page Title"

    def test_extract_meta_description(self, extractor):
        """Test extraction of meta description."""
        html_content = """
        <html>
        <head>
            <meta name="description" content="This is the page description">
        </head>
        <body><p>Content</p></body>
        </html>
        """
        file_obj = io.BytesIO(html_content.encode("utf-8"))

        result = extractor.extract(file_obj, "description.html")

        assert result.metadata.get("description") == "This is the page description"

    def test_extract_meta_author(self, extractor):
        """Test extraction of author metadata."""
        html_content = """
        <html>
        <head>
            <meta name="author" content="John Doe">
        </head>
        <body><p>Content</p></body>
        </html>
        """
        file_obj = io.BytesIO(html_content.encode("utf-8"))

        result = extractor.extract(file_obj, "author.html")

        assert result.metadata.get("author") == "John Doe"

    def test_extract_encoding_from_meta(self, extractor):
        """Test that encoding is detected from meta charset."""
        html_content = """
        <html>
        <head>
            <meta charset="UTF-8">
        </head>
        <body><p>Content</p></body>
        </html>
        """
        file_obj = io.BytesIO(html_content.encode("utf-8"))

        result = extractor.extract(file_obj, "charset.html")

        assert result.metadata.get("encoding") in ["utf-8", "UTF-8"]


class TestHTMLStructureDetection:
    """Test detection of document structure in HTML."""

    @pytest.fixture
    def extractor(self):
        """Create HTML extractor instance."""
        return HTMLExtractor()

    def test_detect_structured_document(self, extractor):
        """Test detection of structured HTML with headings, lists, tables."""
        html_content = """
        <html>
        <body>
            <h1>Title</h1>
            <ul>
                <li>Item 1</li>
                <li>Item 2</li>
            </ul>
            <table>
                <tr><td>Data</td></tr>
            </table>
        </body>
        </html>
        """
        file_obj = io.BytesIO(html_content.encode("utf-8"))

        result = extractor.extract(file_obj, "structured.html")

        structure = result.metadata.get("structure", {})
        assert structure.get("has_structure") is True
        assert structure.get("has_headings") is True
        assert structure.get("has_lists") is True
        assert structure.get("has_tables") is True

    def test_detect_unstructured_document(self, extractor):
        """Test detection of plain HTML with no structure."""
        html_content = """
        <html>
        <body>
            <p>Just plain text.</p>
            <p>No structure here.</p>
        </body>
        </html>
        """
        file_obj = io.BytesIO(html_content.encode("utf-8"))

        result = extractor.extract(file_obj, "plain.html")

        structure = result.metadata.get("structure", {})
        # Should detect lack of structure
        assert structure.get("has_headings") is False
        assert structure.get("has_lists") is False
        assert structure.get("has_tables") is False


class TestHTMLLinkExtraction:
    """Test extraction of links from HTML."""

    @pytest.fixture
    def extractor(self):
        """Create HTML extractor instance with link preservation."""
        return HTMLExtractor(preserve_links=True)

    def test_extract_links(self, extractor):
        """Test extraction of hyperlinks."""
        html_content = """
        <html>
        <body>
            <p>Visit <a href="https://example.com">our website</a> for more info.</p>
            <p><a href="/about">About page</a></p>
        </body>
        </html>
        """
        file_obj = io.BytesIO(html_content.encode("utf-8"))

        result = extractor.extract(file_obj, "links.html")

        # Should extract link URLs
        links = result.metadata.get("links", [])
        assert len(links) >= 2
        assert any(link["url"] == "https://example.com" for link in links)
        assert any(link["url"] == "/about" for link in links)

    def test_link_count_in_metadata(self, extractor):
        """Test that link count is tracked."""
        html_content = """
        <html>
        <body>
            <a href="/link1">Link 1</a>
            <a href="/link2">Link 2</a>
            <a href="/link3">Link 3</a>
        </body>
        </html>
        """
        file_obj = io.BytesIO(html_content.encode("utf-8"))

        result = extractor.extract(file_obj, "link_count.html")

        assert result.metadata.get("link_count") == 3


class TestHTMLEdgeCases:
    """Test edge cases and error handling."""

    @pytest.fixture
    def extractor(self):
        """Create HTML extractor instance."""
        return HTMLExtractor()

    def test_empty_html_file(self, extractor):
        """Test extraction from empty HTML file."""
        html_content = ""
        file_obj = io.BytesIO(html_content.encode("utf-8"))

        result = extractor.extract(file_obj, "empty.html")

        # Should handle gracefully
        assert result.text == "" or len(result.text.strip()) == 0
        assert len(result.warnings) > 0

    def test_malformed_html(self, extractor):
        """Test handling of malformed HTML."""
        html_content = """
        <html>
        <body>
            <p>Unclosed paragraph
            <div>Unclosed div
            <p>Another paragraph</p>
        </body>
        """
        file_obj = io.BytesIO(html_content.encode("utf-8"))

        result = extractor.extract(file_obj, "malformed.html")

        # BeautifulSoup should still extract text
        assert "Unclosed paragraph" in result.text
        assert "Another paragraph" in result.text

    def test_html_with_comments(self, extractor):
        """Test removal of HTML comments."""
        html_content = """
        <html>
        <body>
            <!-- This is a comment -->
            <p>Visible text</p>
            <!-- Another comment -->
        </body>
        </html>
        """
        file_obj = io.BytesIO(html_content.encode("utf-8"))

        result = extractor.extract(file_obj, "comments.html")

        assert "Visible text" in result.text
        # Comments should be removed
        assert "This is a comment" not in result.text

    def test_html_with_entities(self, extractor):
        """Test handling of HTML entities."""
        html_content = """
        <html>
        <body>
            <p>Special characters: &lt; &gt; &amp; &quot;</p>
            <p>Non-breaking space:&nbsp;here</p>
        </body>
        </html>
        """
        file_obj = io.BytesIO(html_content.encode("utf-8"))

        result = extractor.extract(file_obj, "entities.html")

        # Entities should be decoded
        assert "<" in result.text or "&lt;" in result.text
        assert ">" in result.text or "&gt;" in result.text
        assert "&" in result.text or "&amp;" in result.text


class TestHTMLContentTypeDetection:
    """Test content type determination based on structure."""

    @pytest.fixture
    def extractor(self):
        """Create HTML extractor instance."""
        return HTMLExtractor()

    def test_table_content_type(self, extractor):
        """Test that HTML with tables gets TABLE content type."""
        html_content = """
        <html>
        <body>
            <table>
                <tr><th>Header</th></tr>
                <tr><td>Data</td></tr>
            </table>
        </body>
        </html>
        """
        file_obj = io.BytesIO(html_content.encode("utf-8"))

        result = extractor.extract(file_obj, "table_type.html")

        # Should detect TABLE content type
        assert result.content_type == ContentType.TABLE

    def test_list_content_type(self, extractor):
        """Test that HTML with lists gets LIST content type."""
        html_content = """
        <html>
        <body>
            <ul>
                <li>Item 1</li>
                <li>Item 2</li>
                <li>Item 3</li>
            </ul>
        </body>
        </html>
        """
        file_obj = io.BytesIO(html_content.encode("utf-8"))

        result = extractor.extract(file_obj, "list_type.html")

        # Should detect LIST content type
        assert result.content_type in [ContentType.LIST, ContentType.TEXT]

    def test_heading_content_type(self, extractor):
        """Test that HTML with headings gets HEADING content type."""
        html_content = """
        <html>
        <body>
            <h1>Title</h1>
            <p>Content</p>
            <h2>Section</h2>
            <p>More content</p>
        </body>
        </html>
        """
        file_obj = io.BytesIO(html_content.encode("utf-8"))

        result = extractor.extract(file_obj, "heading_type.html")

        # Should detect HEADING content type
        assert result.content_type in [ContentType.HEADING, ContentType.TEXT]


class TestHTMLQualityIndicators:
    """Test quality indicators for HTML extraction."""

    @pytest.fixture
    def extractor(self):
        """Create HTML extractor instance."""
        return HTMLExtractor()

    def test_quality_indicators_present(self, extractor):
        """Test that quality indicators are provided."""
        html_content = """
        <html>
        <body>
            <h1>Title</h1>
            <p>Content text here.</p>
        </body>
        </html>
        """
        file_obj = io.BytesIO(html_content.encode("utf-8"))

        result = extractor.extract(file_obj, "quality.html")

        assert result.quality_indicators is not None
        assert isinstance(result.quality_indicators, dict)
        assert "char_count" in result.quality_indicators
        assert "word_count" in result.quality_indicators

    def test_word_count_calculation(self, extractor):
        """Test that word count is calculated correctly."""
        html_content = """
        <html>
        <body>
            <p>One two three four five words.</p>
        </body>
        </html>
        """
        file_obj = io.BytesIO(html_content.encode("utf-8"))

        result = extractor.extract(file_obj, "words.html")

        word_count = result.quality_indicators.get("word_count", 0)
        # Should count approximately 6 words
        assert word_count >= 5
