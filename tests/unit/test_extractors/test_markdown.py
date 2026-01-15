"""
Unit tests for Markdown extractor.

Tests header extraction, code block handling, list preservation, and metadata extraction
for Markdown documents using markdown-it-py. Follows TDD approach.
"""

import io

import pytest

from src.models.schemas import ContentType, ExtractionResult, FileFormat
from src.preprocessing.extractors.markdown import MarkdownExtractor


class TestMarkdownExtractorBasics:
    """Test basic Markdown extraction functionality."""

    @pytest.fixture
    def extractor(self):
        """Create markdown extractor instance."""
        return MarkdownExtractor()

    def test_extractor_supports_markdown_format(self, extractor):
        """Test that extractor declares support for markdown format."""
        assert extractor.supports_format("markdown")
        assert extractor.supports_format("md")

    def test_extractor_does_not_support_other_formats(self, extractor):
        """Test that extractor rejects non-markdown formats."""
        assert not extractor.supports_format("pdf")
        assert not extractor.supports_format("html")
        assert not extractor.supports_format("text")


class TestMarkdownHeaderExtraction:
    """Test extraction of headers and header-based section splitting."""

    @pytest.fixture
    def extractor(self):
        """Create markdown extractor instance."""
        return MarkdownExtractor()

    def test_extract_simple_markdown_with_headers(self, extractor):
        """Test extraction of markdown with simple headers."""
        content = """# Main Title

This is the introduction paragraph.

## Section 1

Content for section 1.

## Section 2

Content for section 2.
"""
        file_obj = io.BytesIO(content.encode("utf-8"))
        result = extractor.extract(file_obj, "test.md")

        assert isinstance(result, ExtractionResult)
        assert "Main Title" in result.text
        assert "Section 1" in result.text
        assert "Section 2" in result.text
        assert result.content_type == ContentType.HEADING
        assert len(result.warnings) == 0

    def test_extract_h1_header_metadata(self, extractor):
        """Test that H1 headers are detected and included in metadata."""
        content = "# Top Level Header\n\nSome content here.\n"
        file_obj = io.BytesIO(content.encode("utf-8"))

        result = extractor.extract(file_obj, "header.md")

        # Should detect H1 header
        assert result.metadata.get("has_headers") is True
        assert result.metadata.get("num_h1_headers") >= 1

    def test_extract_multiple_header_levels(self, extractor):
        """Test extraction with multiple header levels (H1-H6)."""
        content = """# H1 Header
## H2 Header
### H3 Header
#### H4 Header
##### H5 Header
###### H6 Header

Content under all headers.
"""
        file_obj = io.BytesIO(content.encode("utf-8"))
        result = extractor.extract(file_obj, "levels.md")

        # Should detect all header levels
        assert result.metadata.get("has_headers") is True
        assert result.metadata.get("max_header_level") == 6
        assert result.metadata.get("min_header_level") == 1

    def test_header_based_section_splitting(self, extractor):
        """Test that content is split into sections based on headers."""
        content = """# Document Title

Introduction paragraph.

## Section A

Section A content with multiple lines.
More content here.

## Section B

Section B content.
"""
        file_obj = io.BytesIO(content.encode("utf-8"))
        result = extractor.extract(file_obj, "sections.md")

        # Should identify sections
        assert result.metadata.get("num_sections") >= 2

    def test_arabic_headers_extraction(self, extractor):
        """Test extraction of Arabic markdown headers."""
        content = """# العنوان الرئيسي

مقدمة بالعربية.

## القسم الأول

محتوى القسم الأول.

## القسم الثاني

محتوى القسم الثاني.
"""
        file_obj = io.BytesIO(content.encode("utf-8"))
        result = extractor.extract(file_obj, "arabic.md")

        assert "العنوان الرئيسي" in result.text
        assert "القسم الأول" in result.text
        assert result.metadata.get("has_headers") is True


class TestMarkdownCodeBlockHandling:
    """Test extraction of code blocks with language detection."""

    @pytest.fixture
    def extractor(self):
        """Create markdown extractor instance."""
        return MarkdownExtractor()

    def test_extract_code_block_with_language(self, extractor):
        """Test extraction of fenced code block with language specification."""
        content = """# Code Example

Here's some Python code:

```python
def hello_world():
    print("Hello, World!")
    return 42
```

End of document.
"""
        file_obj = io.BytesIO(content.encode("utf-8"))
        result = extractor.extract(file_obj, "code.md")

        # Should detect code blocks
        assert result.metadata.get("has_code_blocks") is True
        assert result.metadata.get("num_code_blocks") >= 1
        assert "python" in result.metadata.get("code_languages", [])

    def test_extract_multiple_code_blocks(self, extractor):
        """Test extraction of multiple code blocks with different languages."""
        content = """# Multi-Language Examples

Python example:
```python
x = 1 + 1
```

JavaScript example:
```javascript
const x = 1 + 1;
```

Bash example:
```bash
echo "Hello"
```
"""
        file_obj = io.BytesIO(content.encode("utf-8"))
        result = extractor.extract(file_obj, "multi_code.md")

        # Should detect all code blocks
        assert result.metadata.get("num_code_blocks") == 3
        code_languages = result.metadata.get("code_languages", [])
        assert "python" in code_languages
        assert "javascript" in code_languages
        assert "bash" in code_languages

    def test_extract_code_block_without_language(self, extractor):
        """Test extraction of code block without language specification."""
        content = """# Generic Code

```
Generic code block
No language specified
```
"""
        file_obj = io.BytesIO(content.encode("utf-8"))
        result = extractor.extract(file_obj, "no_lang.md")

        # Should still detect code block
        assert result.metadata.get("has_code_blocks") is True
        assert result.metadata.get("num_code_blocks") == 1

    def test_code_block_content_type(self, extractor):
        """Test that documents with code blocks get CODE content type."""
        content = """```python
print("test")
```"""
        file_obj = io.BytesIO(content.encode("utf-8"))
        result = extractor.extract(file_obj, "only_code.md")

        assert result.content_type == ContentType.CODE

    def test_inline_code_detection(self, extractor):
        """Test detection of inline code snippets."""
        content = "Use the `print()` function and `return` statement.\n"
        file_obj = io.BytesIO(content.encode("utf-8"))
        result = extractor.extract(file_obj, "inline.md")

        # Should detect inline code
        assert result.metadata.get("has_inline_code") is True


class TestMarkdownListPreservation:
    """Test preservation of list structures."""

    @pytest.fixture
    def extractor(self):
        """Create markdown extractor instance."""
        return MarkdownExtractor()

    def test_extract_unordered_list(self, extractor):
        """Test extraction of unordered (bullet) list."""
        content = """# Shopping List

- Apples
- Bananas
- Oranges
"""
        file_obj = io.BytesIO(content.encode("utf-8"))
        result = extractor.extract(file_obj, "bullets.md")

        # Should preserve list structure
        assert "Apples" in result.text
        assert "Bananas" in result.text
        assert result.metadata.get("has_lists") is True
        assert result.metadata.get("num_unordered_lists") >= 1

    def test_extract_ordered_list(self, extractor):
        """Test extraction of ordered (numbered) list."""
        content = """# Steps

1. First step
2. Second step
3. Third step
"""
        file_obj = io.BytesIO(content.encode("utf-8"))
        result = extractor.extract(file_obj, "numbered.md")

        # Should preserve numbered list
        assert result.metadata.get("has_lists") is True
        assert result.metadata.get("num_ordered_lists") >= 1

    def test_extract_nested_lists(self, extractor):
        """Test extraction of nested lists."""
        content = """# Nested List

- Item 1
  - Nested 1a
  - Nested 1b
- Item 2
  - Nested 2a
"""
        file_obj = io.BytesIO(content.encode("utf-8"))
        result = extractor.extract(file_obj, "nested.md")

        # Should detect nested structure
        assert result.metadata.get("has_lists") is True
        assert result.metadata.get("has_nested_lists") is True

    def test_extract_mixed_lists(self, extractor):
        """Test extraction of mixed ordered and unordered lists."""
        content = """# Mixed Lists

1. First ordered item
2. Second ordered item

- First bullet
- Second bullet
"""
        file_obj = io.BytesIO(content.encode("utf-8"))
        result = extractor.extract(file_obj, "mixed_lists.md")

        # Should detect both types
        assert result.metadata.get("num_ordered_lists") >= 1
        assert result.metadata.get("num_unordered_lists") >= 1

    def test_list_content_type(self, extractor):
        """Test that documents with lists get LIST content type."""
        content = """- Item 1
- Item 2
- Item 3
"""
        file_obj = io.BytesIO(content.encode("utf-8"))
        result = extractor.extract(file_obj, "only_list.md")

        assert result.content_type == ContentType.LIST


class TestMarkdownMetadataExtraction:
    """Test extraction of comprehensive metadata from Markdown."""

    @pytest.fixture
    def extractor(self):
        """Create markdown extractor instance."""
        return MarkdownExtractor()

    def test_metadata_includes_source_format(self, extractor):
        """Test that metadata includes source format indicator."""
        content = "# Test\n\nContent here.\n"
        file_obj = io.BytesIO(content.encode("utf-8"))
        result = extractor.extract(file_obj, "meta.md")

        assert result.metadata.get("source_format") == "markdown"

    def test_metadata_includes_file_hash(self, extractor):
        """Test that metadata includes file hash for deduplication."""
        content = "# Unique Content\n\nSome text.\n"
        file_obj = io.BytesIO(content.encode("utf-8"))
        result = extractor.extract(file_obj, "hash.md")

        assert "file_hash" in result.metadata
        assert len(result.metadata["file_hash"]) == 64  # SHA256

    def test_metadata_includes_line_count(self, extractor):
        """Test that metadata includes line count."""
        content = "Line 1\nLine 2\nLine 3\n"
        file_obj = io.BytesIO(content.encode("utf-8"))
        result = extractor.extract(file_obj, "lines.md")

        assert "line_count" in result.metadata
        assert result.metadata["line_count"] >= 3

    def test_metadata_includes_char_count(self, extractor):
        """Test that metadata includes character count."""
        content = "Hello World"
        file_obj = io.BytesIO(content.encode("utf-8"))
        result = extractor.extract(file_obj, "chars.md")

        assert "char_count" in result.metadata
        assert result.metadata["char_count"] == len(content)

    def test_metadata_includes_heading_levels(self, extractor):
        """Test that metadata includes heading level information."""
        content = """# H1
## H2
### H3
"""
        file_obj = io.BytesIO(content.encode("utf-8"))
        result = extractor.extract(file_obj, "headings.md")

        assert "num_h1_headers" in result.metadata
        assert "num_h2_headers" in result.metadata
        assert "num_h3_headers" in result.metadata


class TestMarkdownSpecificMetadata:
    """Test Markdown-specific metadata for chunk payload (T055)."""

    @pytest.fixture
    def extractor(self):
        """Create markdown extractor instance."""
        return MarkdownExtractor()

    def test_heading_level_metadata(self, extractor):
        """Test extraction of heading_level metadata for chunks."""
        content = """## Section Header

Content under this header.
"""
        file_obj = io.BytesIO(content.encode("utf-8"))
        result = extractor.extract(file_obj, "heading_meta.md")

        # Should track heading levels
        assert "max_header_level" in result.metadata
        assert result.metadata["max_header_level"] == 2

    def test_heading_text_metadata(self, extractor):
        """Test extraction of heading_text metadata."""
        content = """# Important Section

Section content.
"""
        file_obj = io.BytesIO(content.encode("utf-8"))
        result = extractor.extract(file_obj, "heading_text.md")

        # Should capture heading text
        assert result.metadata.get("has_headers") is True

    def test_is_code_block_metadata(self, extractor):
        """Test extraction of is_code_block flag."""
        content = """```python
print("code")
```"""
        file_obj = io.BytesIO(content.encode("utf-8"))
        result = extractor.extract(file_obj, "code_flag.md")

        assert result.metadata.get("has_code_blocks") is True

    def test_code_language_metadata(self, extractor):
        """Test extraction of code_language metadata."""
        content = """```javascript
console.log("test");
```"""
        file_obj = io.BytesIO(content.encode("utf-8"))
        result = extractor.extract(file_obj, "code_lang.md")

        assert "code_languages" in result.metadata
        assert "javascript" in result.metadata["code_languages"]

    def test_list_type_metadata(self, extractor):
        """Test extraction of list_type metadata (ordered/unordered)."""
        content = """1. First
2. Second
"""
        file_obj = io.BytesIO(content.encode("utf-8"))
        result = extractor.extract(file_obj, "list_type.md")

        assert result.metadata.get("has_lists") is True
        assert result.metadata.get("num_ordered_lists") >= 1


class TestMarkdownEdgeCases:
    """Test edge cases and error handling for Markdown extraction."""

    @pytest.fixture
    def extractor(self):
        """Create markdown extractor instance."""
        return MarkdownExtractor()

    def test_empty_markdown_file(self, extractor):
        """Test extraction from empty file."""
        file_obj = io.BytesIO(b"")
        result = extractor.extract(file_obj, "empty.md")

        assert result.text == ""
        assert result.content_type == ContentType.TEXT
        assert any("empty" in w.lower() for w in result.warnings)

    def test_only_whitespace(self, extractor):
        """Test file containing only whitespace."""
        content = "   \n\n\t\t  \n   "
        file_obj = io.BytesIO(content.encode("utf-8"))
        result = extractor.extract(file_obj, "whitespace.md")

        assert len(result.warnings) > 0

    def test_malformed_markdown(self, extractor):
        """Test handling of malformed markdown syntax."""
        content = """# Header without closing

## Broken [link](

```python
Unclosed code block
"""
        file_obj = io.BytesIO(content.encode("utf-8"))
        result = extractor.extract(file_obj, "malformed.md")

        # Should extract what's possible
        assert "Header without closing" in result.text
        # May have warnings about malformed content
        assert isinstance(result.warnings, list)

    def test_markdown_with_html_tags(self, extractor):
        """Test markdown containing inline HTML tags."""
        content = """# Title

<div>HTML content</div>

Regular markdown paragraph.
"""
        file_obj = io.BytesIO(content.encode("utf-8"))
        result = extractor.extract(file_obj, "html_mixed.md")

        # Should handle HTML gracefully
        assert "Title" in result.text
        assert "Regular markdown" in result.text

    def test_markdown_with_tables(self, extractor):
        """Test markdown containing tables."""
        content = """# Data Table

| Column 1 | Column 2 | Column 3 |
|----------|----------|----------|
| Value 1  | Value 2  | Value 3  |
| Value 4  | Value 5  | Value 6  |
"""
        file_obj = io.BytesIO(content.encode("utf-8"))
        result = extractor.extract(file_obj, "table.md")

        # Should detect tables
        assert result.metadata.get("has_tables") is True
        assert result.metadata.get("num_tables") >= 1

    def test_markdown_with_links(self, extractor):
        """Test markdown with links."""
        content = "Check [this link](https://example.com) for more info.\n"
        file_obj = io.BytesIO(content.encode("utf-8"))
        result = extractor.extract(file_obj, "links.md")

        # Should preserve link text
        assert "this link" in result.text
        # May track links in metadata
        assert result.metadata.get("has_links") is True

    def test_markdown_with_images(self, extractor):
        """Test markdown with image references."""
        content = "![Alt text](image.png)\n\nCaption below.\n"
        file_obj = io.BytesIO(content.encode("utf-8"))
        result = extractor.extract(file_obj, "images.md")

        # Should detect images
        assert result.metadata.get("has_images") is True

    def test_large_markdown_file(self, extractor):
        """Test extraction from large markdown file."""
        # Create ~2MB markdown content
        section = """## Section Header

This is a paragraph with some content. """ * 50 + "\n\n"
        large_content = section * 500  # ~2MB

        file_obj = io.BytesIO(large_content.encode("utf-8"))
        result = extractor.extract(file_obj, "large.md")

        assert len(result.text) > 1_000_000
        assert result.metadata.get("file_size_bytes") > 1_000_000


class TestMarkdownComplexDocuments:
    """Test extraction from complex real-world markdown documents."""

    @pytest.fixture
    def extractor(self):
        """Create markdown extractor instance."""
        return MarkdownExtractor()

    def test_readme_style_document(self, extractor):
        """Test extraction from README-style markdown."""
        content = """# Project Name

## Description

This is a comprehensive project description.

## Features

- Feature 1
- Feature 2
- Feature 3

## Installation

```bash
pip install package-name
```

## Usage

```python
from package import module
module.run()
```

## License

MIT License
"""
        file_obj = io.BytesIO(content.encode("utf-8"))
        result = extractor.extract(file_obj, "README.md")

        assert result.metadata.get("has_headers") is True
        assert result.metadata.get("has_lists") is True
        assert result.metadata.get("has_code_blocks") is True
        assert "bash" in result.metadata.get("code_languages", [])
        assert "python" in result.metadata.get("code_languages", [])

    def test_documentation_style_document(self, extractor):
        """Test extraction from documentation markdown."""
        content = """# API Documentation

## Overview

The API provides the following endpoints:

### Authentication

Use Bearer token:

```
Authorization: Bearer <token>
```

### Endpoints

#### GET /users

Returns list of users.

**Parameters:**
- `limit`: Maximum number of results
- `offset`: Pagination offset

**Response:**
```json
{
  "users": [...],
  "total": 100
}
```
"""
        file_obj = io.BytesIO(content.encode("utf-8"))
        result = extractor.extract(file_obj, "docs.md")

        # Should handle complex nested structure
        assert result.metadata.get("max_header_level") >= 4
        assert result.metadata.get("has_code_blocks") is True
        assert result.metadata.get("has_lists") is True

    def test_arabic_markdown_document(self, extractor):
        """Test extraction from Arabic markdown documentation."""
        content = """# توثيق المشروع

## نظرة عامة

هذا مشروع لمعالجة النصوص العربية.

## المميزات

- دعم كامل للغة العربية
- معالجة متقدمة للنصوص
- تكامل مع الأنظمة الحديثة

## مثال على الاستخدام

```python
from arabic_processor import process
result = process("نص عربي")
```

## الترخيص

رخصة MIT
"""
        file_obj = io.BytesIO(content.encode("utf-8"))
        result = extractor.extract(file_obj, "arabic_docs.md")

        assert "توثيق المشروع" in result.text
        assert "المميزات" in result.text
        assert result.metadata.get("has_headers") is True
        assert result.metadata.get("has_lists") is True
        assert result.metadata.get("has_code_blocks") is True
        assert "python" in result.metadata.get("code_languages", [])
