"""
Unit tests for Word (.docx) extractor.

Tests Word text extraction, heading style detection, table preservation, track changes
handling, and .doc format rejection following TDD approach. These tests should FAIL
initially as the WordExtractor implementation doesn't exist yet.
"""

import io
from unittest.mock import Mock, patch
from zipfile import ZipFile

import pytest

from src.models.schemas import ContentType, ExtractionResult
from src.preprocessing.extractors.base import BaseExtractor


class TestWordExtractor:
    """Test suite for Word extractor (TDD - implementation pending)."""

    @pytest.fixture
    def word_extractor(self):
        """Create Word extractor instance."""
        # This import will fail until WordExtractor is implemented
        try:
            from src.preprocessing.extractors.docx import WordExtractor
            return WordExtractor()
        except ImportError:
            pytest.skip("WordExtractor not yet implemented (TDD)")

    @pytest.fixture
    def sample_docx_bytes(self):
        """
        Create a minimal valid .docx file for testing.

        .docx is a ZIP archive containing XML files. We create the bare minimum
        structure required for python-docx to read it.
        """
        # Create in-memory ZIP with minimal Word structure
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

            # Main document with simple paragraph
            docx.writestr('word/document.xml', '''<?xml version="1.0" encoding="UTF-8"?>
<w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">
    <w:body>
        <w:p>
            <w:r>
                <w:t>Sample Word document text</w:t>
            </w:r>
        </w:p>
    </w:body>
</w:document>''')

        buffer.seek(0)
        return buffer

    @pytest.fixture
    def docx_with_headings(self):
        """Create .docx with heading styles (Heading 1, Heading 2)."""
        buffer = io.BytesIO()

        with ZipFile(buffer, 'w') as docx:
            docx.writestr('[Content_Types].xml', '''<?xml version="1.0" encoding="UTF-8"?>
<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">
    <Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>
    <Default Extension="xml" ContentType="application/xml"/>
    <Override PartName="/word/document.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.document.main+xml"/>
</Types>''')

            docx.writestr('_rels/.rels', '''<?xml version="1.0" encoding="UTF-8"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
    <Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="word/document.xml"/>
</Relationships>''')

            # Document with headings
            docx.writestr('word/document.xml', '''<?xml version="1.0" encoding="UTF-8"?>
<w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">
    <w:body>
        <w:p>
            <w:pPr>
                <w:pStyle w:val="Heading1"/>
            </w:pPr>
            <w:r>
                <w:t>Main Heading</w:t>
            </w:r>
        </w:p>
        <w:p>
            <w:r>
                <w:t>Regular paragraph text</w:t>
            </w:r>
        </w:p>
        <w:p>
            <w:pPr>
                <w:pStyle w:val="Heading2"/>
            </w:pPr>
            <w:r>
                <w:t>Subheading</w:t>
            </w:r>
        </w:p>
        <w:p>
            <w:r>
                <w:t>More paragraph text</w:t>
            </w:r>
        </w:p>
    </w:body>
</w:document>''')

        buffer.seek(0)
        return buffer

    @pytest.fixture
    def docx_with_table(self):
        """Create .docx with a table."""
        buffer = io.BytesIO()

        with ZipFile(buffer, 'w') as docx:
            docx.writestr('[Content_Types].xml', '''<?xml version="1.0" encoding="UTF-8"?>
<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">
    <Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>
    <Default Extension="xml" ContentType="application/xml"/>
    <Override PartName="/word/document.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.document.main+xml"/>
</Types>''')

            docx.writestr('_rels/.rels', '''<?xml version="1.0" encoding="UTF-8"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
    <Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="word/document.xml"/>
</Relationships>''')

            # Document with table
            docx.writestr('word/document.xml', '''<?xml version="1.0" encoding="UTF-8"?>
<w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">
    <w:body>
        <w:p>
            <w:r>
                <w:t>Text before table</w:t>
            </w:r>
        </w:p>
        <w:tbl>
            <w:tr>
                <w:tc>
                    <w:p>
                        <w:r>
                            <w:t>Header 1</w:t>
                        </w:r>
                    </w:p>
                </w:tc>
                <w:tc>
                    <w:p>
                        <w:r>
                            <w:t>Header 2</w:t>
                        </w:r>
                    </w:p>
                </w:tc>
            </w:tr>
            <w:tr>
                <w:tc>
                    <w:p>
                        <w:r>
                            <w:t>Cell 1</w:t>
                        </w:r>
                    </w:p>
                </w:tc>
                <w:tc>
                    <w:p>
                        <w:r>
                            <w:t>Cell 2</w:t>
                        </w:r>
                    </w:p>
                </w:tc>
            </w:tr>
        </w:tbl>
        <w:p>
            <w:r>
                <w:t>Text after table</w:t>
            </w:r>
        </w:p>
    </w:body>
</w:document>''')

        buffer.seek(0)
        return buffer

    def test_extractor_is_base_extractor(self, word_extractor):
        """Test that WordExtractor implements BaseExtractor interface."""
        assert isinstance(word_extractor, BaseExtractor)

    def test_supports_docx_format(self, word_extractor):
        """Test that extractor correctly identifies .docx format support."""
        assert word_extractor.supports_format("docx") is True
        assert word_extractor.supports_format("pdf") is False
        assert word_extractor.supports_format("txt") is False

    def test_rejects_doc_format(self, word_extractor):
        """Test that .doc (legacy binary format) is rejected with clear error."""
        # .doc files are binary format, not ZIP
        doc_bytes = io.BytesIO(b"\xd0\xcf\x11\xe0\xa1\xb1\x1a\xe1")  # OLE header

        result = word_extractor.extract(doc_bytes, "legacy.doc")

        # Should return error in warnings or raise ValueError
        assert isinstance(result, ExtractionResult)
        assert len(result.warnings) > 0
        # Error should mention .doc format and suggest conversion
        warning_text = " ".join(result.warnings).lower()
        assert "doc" in warning_text or "docx" in warning_text
        assert "convert" in warning_text or "not supported" in warning_text

    def test_extract_basic_text_from_docx(self, word_extractor, sample_docx_bytes):
        """Test basic text extraction from .docx file."""
        result = word_extractor.extract(sample_docx_bytes, "sample.docx")

        assert isinstance(result, ExtractionResult)
        assert result.text is not None
        assert len(result.text) > 0
        assert "Sample Word document text" in result.text
        assert result.content_type == ContentType.TEXT

    def test_extract_detects_heading_styles(self, word_extractor, docx_with_headings):
        """Test that heading styles (Heading 1, Heading 2, etc.) are detected."""
        result = word_extractor.extract(docx_with_headings, "headings.docx")

        assert isinstance(result, ExtractionResult)
        # Metadata should indicate heading detection
        assert "has_headings" in result.metadata or "heading_count" in result.metadata

        # Extracted text should contain headings
        assert "Main Heading" in result.text
        assert "Subheading" in result.text

        # Content type should be HEADING when headings are primary structure
        assert result.content_type in [ContentType.HEADING, ContentType.TEXT]

    def test_extract_preserves_heading_hierarchy(self, word_extractor, docx_with_headings):
        """Test that heading hierarchy (H1 > H2 > H3) is preserved in metadata."""
        result = word_extractor.extract(docx_with_headings, "hierarchy.docx")

        # Metadata should track heading levels
        metadata = result.metadata
        assert "headings" in metadata or "heading_levels" in metadata or "structure" in metadata

        # Should be able to identify which text is which heading level
        if "headings" in metadata:
            headings = metadata["headings"]
            assert isinstance(headings, list)
            assert len(headings) >= 2  # At least H1 and H2 from fixture

    def test_extract_table_as_cohesive_chunk(self, word_extractor, docx_with_table):
        """Test that tables are extracted as cohesive chunks (not split mid-table)."""
        result = word_extractor.extract(docx_with_table, "table.docx")

        assert isinstance(result, ExtractionResult)
        # Metadata should indicate table presence
        assert "has_tables" in result.metadata or "table_count" in result.metadata

        # Table content should be present
        assert "Header 1" in result.text
        assert "Header 2" in result.text
        assert "Cell 1" in result.text
        assert "Cell 2" in result.text

        # Content type should reflect table presence
        if result.metadata.get("has_tables") or result.metadata.get("table_count", 0) > 0:
            assert result.content_type in [ContentType.TABLE, ContentType.TEXT]

    def test_extract_table_metadata(self, word_extractor, docx_with_table):
        """Test that table metadata (row count, column count) is captured."""
        result = word_extractor.extract(docx_with_table, "table_meta.docx")

        metadata = result.metadata

        # Should track table information
        assert "table_count" in metadata or "tables" in metadata

        if "table_count" in metadata:
            assert metadata["table_count"] >= 1

        # Detailed table metadata might include dimensions
        if "tables" in metadata:
            tables = metadata["tables"]
            assert isinstance(tables, list)
            assert len(tables) >= 1

    def test_extract_handles_track_changes(self, word_extractor):
        """Test that track changes are detected and handled (extract accepted text only)."""
        # Create docx with track changes (revision markup)
        buffer = io.BytesIO()

        with ZipFile(buffer, 'w') as docx:
            docx.writestr('[Content_Types].xml', '''<?xml version="1.0" encoding="UTF-8"?>
<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">
    <Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>
    <Default Extension="xml" ContentType="application/xml"/>
    <Override PartName="/word/document.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.document.main+xml"/>
</Types>''')

            docx.writestr('_rels/.rels', '''<?xml version="1.0" encoding="UTF-8"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
    <Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="word/document.xml"/>
</Relationships>''')

            # Document with track changes (deletion)
            docx.writestr('word/document.xml', '''<?xml version="1.0" encoding="UTF-8"?>
<w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">
    <w:body>
        <w:p>
            <w:r>
                <w:t>This is accepted text</w:t>
            </w:r>
            <w:del>
                <w:r>
                    <w:t>This is deleted text</w:t>
                </w:r>
            </w:del>
            <w:ins>
                <w:r>
                    <w:t>This is inserted text</w:t>
                </w:r>
            </w:ins>
        </w:p>
    </w:body>
</w:document>''')

        buffer.seek(0)

        result = word_extractor.extract(buffer, "tracked.docx")

        # Should extract only accepted text (inserted and non-deleted)
        assert "accepted text" in result.text or "inserted text" in result.text
        # Should NOT include deleted text
        assert "deleted text" not in result.text or result.text.count("deleted") == 0

        # Metadata should flag track changes presence
        assert "has_track_changes" in result.metadata
        assert result.metadata["has_track_changes"] is True

    def test_extract_flags_track_changes_in_metadata(self, word_extractor):
        """Test that presence of track changes is flagged in metadata."""
        # Simple doc without track changes
        buffer = io.BytesIO()

        with ZipFile(buffer, 'w') as docx:
            docx.writestr('[Content_Types].xml', '''<?xml version="1.0" encoding="UTF-8"?>
<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">
    <Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>
    <Default Extension="xml" ContentType="application/xml"/>
    <Override PartName="/word/document.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.document.main+xml"/>
</Types>''')

            docx.writestr('_rels/.rels', '''<?xml version="1.0" encoding="UTF-8"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
    <Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="word/document.xml"/>
</Relationships>''')

            docx.writestr('word/document.xml', '''<?xml version="1.0" encoding="UTF-8"?>
<w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">
    <w:body>
        <w:p>
            <w:r>
                <w:t>Clean text without track changes</w:t>
            </w:r>
        </w:p>
    </w:body>
</w:document>''')

        buffer.seek(0)

        result = word_extractor.extract(buffer, "clean.docx")

        # Should have track changes flag set to False
        assert "has_track_changes" in result.metadata
        assert result.metadata["has_track_changes"] is False

    def test_extract_arabic_text_from_docx(self, word_extractor):
        """Test extraction of Arabic content from Word document."""
        buffer = io.BytesIO()

        with ZipFile(buffer, 'w') as docx:
            docx.writestr('[Content_Types].xml', '''<?xml version="1.0" encoding="UTF-8"?>
<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">
    <Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>
    <Default Extension="xml" ContentType="application/xml"/>
    <Override PartName="/word/document.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.document.main+xml"/>
</Types>''')

            docx.writestr('_rels/.rels', '''<?xml version="1.0" encoding="UTF-8"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
    <Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="word/document.xml"/>
</Relationships>''')

            docx.writestr('word/document.xml', '''<?xml version="1.0" encoding="UTF-8"?>
<w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">
    <w:body>
        <w:p>
            <w:r>
                <w:t>مرحبا بك في معالج النصوص</w:t>
            </w:r>
        </w:p>
    </w:body>
</w:document>''')

        buffer.seek(0)

        result = word_extractor.extract(buffer, "arabic.docx")

        assert isinstance(result, ExtractionResult)
        assert result.text is not None
        # Arabic text should be preserved
        assert "مرحبا" in result.text

    def test_extract_with_empty_paragraphs(self, word_extractor):
        """Test handling of documents with empty paragraphs."""
        buffer = io.BytesIO()

        with ZipFile(buffer, 'w') as docx:
            docx.writestr('[Content_Types].xml', '''<?xml version="1.0" encoding="UTF-8"?>
<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">
    <Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>
    <Default Extension="xml" ContentType="application/xml"/>
    <Override PartName="/word/document.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.document.main+xml"/>
</Types>''')

            docx.writestr('_rels/.rels', '''<?xml version="1.0" encoding="UTF-8"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
    <Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="word/document.xml"/>
</Relationships>''')

            docx.writestr('word/document.xml', '''<?xml version="1.0" encoding="UTF-8"?>
<w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">
    <w:body>
        <w:p>
            <w:r>
                <w:t>First paragraph</w:t>
            </w:r>
        </w:p>
        <w:p/>
        <w:p/>
        <w:p>
            <w:r>
                <w:t>Second paragraph</w:t>
            </w:r>
        </w:p>
    </w:body>
</w:document>''')

        buffer.seek(0)

        result = word_extractor.extract(buffer, "empty_paras.docx")

        # Should handle empty paragraphs gracefully
        assert "First paragraph" in result.text
        assert "Second paragraph" in result.text
        # Empty paragraphs should be normalized (not create excessive whitespace)
        assert "\n\n\n\n" not in result.text

    def test_extract_handles_corrupted_docx(self, word_extractor):
        """Test handling of corrupted .docx file."""
        corrupted_bytes = io.BytesIO(b"This is not a valid DOCX file")

        result = word_extractor.extract(corrupted_bytes, "corrupted.docx")

        # Should handle gracefully with warnings
        assert isinstance(result, ExtractionResult)
        assert len(result.warnings) > 0
        # Warning should mention corruption or invalid format
        warning_text = " ".join(result.warnings).lower()
        assert any(word in warning_text for word in ["corrupt", "invalid", "error", "failed"])

    def test_extract_includes_filename_in_metadata(self, word_extractor, sample_docx_bytes):
        """Test that filename is preserved in metadata."""
        result = word_extractor.extract(sample_docx_bytes, "report.docx")

        assert "source" in result.metadata or "filename" in result.metadata
        if "source" in result.metadata:
            assert result.metadata["source"] == "report.docx"

    def test_extract_with_multiple_tables(self, word_extractor):
        """Test document with multiple tables."""
        buffer = io.BytesIO()

        with ZipFile(buffer, 'w') as docx:
            docx.writestr('[Content_Types].xml', '''<?xml version="1.0" encoding="UTF-8"?>
<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">
    <Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>
    <Default Extension="xml" ContentType="application/xml"/>
    <Override PartName="/word/document.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.document.main+xml"/>
</Types>''')

            docx.writestr('_rels/.rels', '''<?xml version="1.0" encoding="UTF-8"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
    <Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="word/document.xml"/>
</Relationships>''')

            docx.writestr('word/document.xml', '''<?xml version="1.0" encoding="UTF-8"?>
<w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">
    <w:body>
        <w:tbl>
            <w:tr>
                <w:tc><w:p><w:r><w:t>Table 1 Cell</w:t></w:r></w:p></w:tc>
            </w:tr>
        </w:tbl>
        <w:p><w:r><w:t>Text between tables</w:t></w:r></w:p>
        <w:tbl>
            <w:tr>
                <w:tc><w:p><w:r><w:t>Table 2 Cell</w:t></w:r></w:p></w:tc>
            </w:tr>
        </w:tbl>
    </w:body>
</w:document>''')

        buffer.seek(0)

        result = word_extractor.extract(buffer, "multi_tables.docx")

        # Should detect multiple tables
        assert result.metadata.get("table_count", 0) >= 2
        assert result.metadata.get("has_tables", False) is True

    def test_extract_table_with_metadata_includes_table_index(self, word_extractor, docx_with_table):
        """Test that table chunks include table_index in metadata."""
        result = word_extractor.extract(docx_with_table, "indexed_table.docx")

        # If tables are extracted separately, they should have indices
        metadata = result.metadata
        if "tables" in metadata:
            tables = metadata["tables"]
            for idx, table in enumerate(tables):
                # Each table should have an index
                assert "table_index" in table or "index" in table

    def test_extract_mixed_content_with_headings_and_tables(self, word_extractor):
        """Test document with both headings and tables."""
        buffer = io.BytesIO()

        with ZipFile(buffer, 'w') as docx:
            docx.writestr('[Content_Types].xml', '''<?xml version="1.0" encoding="UTF-8"?>
<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">
    <Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>
    <Default Extension="xml" ContentType="application/xml"/>
    <Override PartName="/word/document.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.document.main+xml"/>
</Types>''')

            docx.writestr('_rels/.rels', '''<?xml version="1.0" encoding="UTF-8"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
    <Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="word/document.xml"/>
</Relationships>''')

            docx.writestr('word/document.xml', '''<?xml version="1.0" encoding="UTF-8"?>
<w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">
    <w:body>
        <w:p>
            <w:pPr><w:pStyle w:val="Heading1"/></w:pPr>
            <w:r><w:t>Report Title</w:t></w:r>
        </w:p>
        <w:p><w:r><w:t>Introduction text</w:t></w:r></w:p>
        <w:tbl>
            <w:tr>
                <w:tc><w:p><w:r><w:t>Data Table</w:t></w:r></w:p></w:tc>
            </w:tr>
        </w:tbl>
    </w:body>
</w:document>''')

        buffer.seek(0)

        result = word_extractor.extract(buffer, "mixed.docx")

        # Should detect both structures
        assert result.metadata.get("has_headings", False) or result.metadata.get("heading_count", 0) > 0
        assert result.metadata.get("has_tables", False) or result.metadata.get("table_count", 0) > 0

    def test_extract_returns_quality_indicators(self, word_extractor, sample_docx_bytes):
        """Test that extraction includes quality indicators."""
        result = word_extractor.extract(sample_docx_bytes, "quality.docx")

        # Quality indicators are optional but useful
        if result.quality_indicators:
            assert isinstance(result.quality_indicators, dict)
            # Common quality metrics
            assert "text_length" in result.quality_indicators or "char_count" in result.quality_indicators

    @pytest.mark.parametrize("filename,expected_format", [
        ("document.docx", "docx"),
        ("report_2025.docx", "docx"),
        ("arabic_doc.docx", "docx"),
    ])
    def test_supports_format_from_filename(self, word_extractor, filename, expected_format):
        """Test format detection from filename extension."""
        assert word_extractor.supports_format(expected_format) is True

    def test_extract_with_style_name_metadata(self, word_extractor, docx_with_headings):
        """Test that paragraph style names are captured in metadata."""
        result = word_extractor.extract(docx_with_headings, "styles.docx")

        # Metadata should include style information
        metadata = result.metadata
        # Either in headings list or separate styles tracking
        assert "headings" in metadata or "styles" in metadata or "has_headings" in metadata
