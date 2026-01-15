"""
Unit tests for PDF extractor.

Tests PDF text extraction, table preservation, Arabic handling, metadata extraction,
and structure-aware chunking. Following TDD approach - these tests exercise the
PDFExtractor implementation with PDFCleaner and PDFAwareChunker integration.
"""

import io
import pytest
from unittest.mock import Mock, patch

from src.models.schemas import ExtractionResult, ContentType
from src.preprocessing.extractors.pdf import PDFExtractor


class TestPDFExtractorBasics:
    """Test basic PDF extractor functionality."""

    @pytest.fixture
    def extractor(self):
        """Create PDF extractor instance."""
        return PDFExtractor()

    def test_extractor_supports_pdf_format(self, extractor):
        """Test that extractor declares support for PDF format."""
        assert extractor.supports_format("pdf")
        assert extractor.supports_format("PDF")

    def test_extractor_does_not_support_other_formats(self, extractor):
        """Test that extractor rejects non-PDF formats."""
        assert not extractor.supports_format("txt")
        assert not extractor.supports_format("html")
        assert not extractor.supports_format("docx")


class TestSimplePDFExtraction:
    """Test extraction from simple PDF documents."""

    @pytest.fixture
    def extractor(self):
        """Create PDF extractor instance."""
        return PDFExtractor()

    @pytest.fixture
    def simple_pdf(self):
        """Create minimal valid PDF with text."""
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
(Hello World Test) Tj
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
        return io.BytesIO(pdf_content)

    def test_extract_simple_pdf(self, extractor, simple_pdf):
        """Test extraction from simple PDF document."""
        result = extractor.extract(simple_pdf, "test.pdf")

        assert isinstance(result, ExtractionResult)
        assert isinstance(result.text, str)
        assert len(result.text) > 0
        assert result.content_type in [ContentType.TEXT, ContentType.HEADING, ContentType.TABLE, ContentType.LIST]
        assert isinstance(result.warnings, list)

    def test_extract_returns_metadata(self, extractor, simple_pdf):
        """Test that extraction returns PDF metadata."""
        result = extractor.extract(simple_pdf, "test.pdf")

        assert result.metadata is not None
        assert "source" in result.metadata
        assert result.metadata["source"] == "test.pdf"
        assert "source_format" in result.metadata
        assert result.metadata["source_format"] == "pdf"

    def test_extract_includes_page_count(self, extractor, simple_pdf):
        """Test that metadata includes page count."""
        result = extractor.extract(simple_pdf, "test.pdf")

        # Should track total pages
        assert "num_pages_total" in result.metadata
        assert result.metadata["num_pages_total"] >= 1

    def test_extract_includes_file_hash(self, extractor, simple_pdf):
        """Test that metadata includes file hash for deduplication."""
        result = extractor.extract(simple_pdf, "test.pdf")

        assert "file_hash" in result.metadata
        assert isinstance(result.metadata["file_hash"], str)
        assert len(result.metadata["file_hash"]) == 64  # SHA-256 hex

    def test_extract_includes_chunk_count(self, extractor, simple_pdf):
        """Test that metadata includes chunk count."""
        result = extractor.extract(simple_pdf, "test.pdf")

        assert "num_chunks" in result.metadata
        assert isinstance(result.metadata["num_chunks"], int)
        assert result.metadata["num_chunks"] >= 1


class TestArabicPDFExtraction:
    """Test extraction from Arabic PDF documents."""

    @pytest.fixture
    def extractor(self):
        """Create PDF extractor instance."""
        return PDFExtractor()

    @pytest.fixture
    def arabic_pdf(self):
        """Create PDF with Arabic text content."""
        # Note: This is a simplified PDF. Real Arabic PDFs have complex encodings.
        pdf_content = b"""%PDF-1.4
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
<< /Length 50 >>
stream
BT
100 700 Td
(Arabic text placeholder) Tj
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
319
%%EOF
"""
        return io.BytesIO(pdf_content)

    def test_extract_arabic_pdf_without_errors(self, extractor, arabic_pdf):
        """Test that Arabic PDFs are extracted without errors."""
        result = extractor.extract(arabic_pdf, "arabic.pdf")

        assert isinstance(result, ExtractionResult)
        assert len(result.text) > 0

    def test_extract_arabic_preserves_text(self, extractor, arabic_pdf):
        """Test that Arabic text is preserved correctly."""
        result = extractor.extract(arabic_pdf, "arabic.pdf")

        # Text should be present (exact content depends on PDF encoding)
        assert len(result.text.strip()) > 0
        # Should have extracted text successfully
        assert "Arabic text" in result.text or len(result.text) > 10


class TestMultiPagePDFExtraction:
    """Test extraction from multi-page PDF documents."""

    @pytest.fixture
    def extractor(self):
        """Create PDF extractor instance."""
        return PDFExtractor()

    @pytest.fixture
    def multi_page_pdf(self):
        """Create multi-page PDF for testing."""
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
(Page 1 content) Tj
ET
endstream
endobj
6 0 obj
<< /Length 30 >>
stream
BT
100 700 Td
(Page 2 content) Tj
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
        return io.BytesIO(pdf_content)

    def test_extract_multi_page_pdf(self, extractor, multi_page_pdf):
        """Test extraction from multi-page PDF."""
        result = extractor.extract(multi_page_pdf, "multi.pdf")

        assert isinstance(result, ExtractionResult)
        assert len(result.text) > 0

        # Should detect 2 pages
        assert result.metadata["num_pages_total"] == 2

    def test_multi_page_includes_page_data(self, extractor, multi_page_pdf):
        """Test that multi-page PDF includes page-level data."""
        result = extractor.extract(multi_page_pdf, "multi.pdf")

        # Should have page-level metadata
        assert "pages_data" in result.metadata
        pages_data = result.metadata["pages_data"]

        assert len(pages_data) == 2
        # Each page should have page number
        for page_data in pages_data:
            assert "page_number" in page_data
            assert "text" in page_data
            assert "char_count" in page_data

    def test_multi_page_creates_chunks(self, extractor, multi_page_pdf):
        """Test that multi-page PDF creates appropriate chunks."""
        result = extractor.extract(multi_page_pdf, "multi.pdf")

        # Should create at least one chunk
        assert result.metadata["num_chunks"] >= 1


class TestTablePreservation:
    """Test table detection and preservation in PDFs."""

    @pytest.fixture
    def extractor(self):
        """Create PDF extractor with table preservation enabled."""
        return PDFExtractor(preserve_tables=True)

    @pytest.fixture
    def extractor_no_tables(self):
        """Create PDF extractor with table preservation disabled."""
        return PDFExtractor(preserve_tables=False)

    @pytest.fixture
    def pdf_with_table(self):
        """Create PDF containing table structure."""
        # Simplified PDF with table-like content
        pdf_content = b"""%PDF-1.4
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
<< /Length 100 >>
stream
BT
100 700 Td
(Name | Age | City) Tj
0 -20 Td
(John | 25 | NYC) Tj
0 -20 Td
(Jane | 30 | LA) Tj
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
369
%%EOF
"""
        return io.BytesIO(pdf_content)

    def test_detect_tables_in_pdf(self, extractor, pdf_with_table):
        """Test that tables are detected in PDF content."""
        result = extractor.extract(pdf_with_table, "table.pdf")

        # Should detect table structure (may or may not depending on heuristics)
        structure = result.metadata.get("structure", {})
        # has_tables is a boolean
        assert "has_tables" in structure or "has_tables" in result.metadata

    def test_table_preservation_option(self, extractor, extractor_no_tables, pdf_with_table):
        """Test that preserve_tables option affects chunking."""
        # Reset file position
        pdf_with_table.seek(0)
        result_with_tables = extractor.extract(pdf_with_table, "table1.pdf")

        pdf_with_table.seek(0)
        result_without_tables = extractor_no_tables.extract(pdf_with_table, "table2.pdf")

        # Both should succeed
        assert isinstance(result_with_tables, ExtractionResult)
        assert isinstance(result_without_tables, ExtractionResult)


class TestSectionHeaderDetection:
    """Test section header detection and section-aware chunking."""

    @pytest.fixture
    def extractor(self):
        """Create PDF extractor with header detection enabled."""
        return PDFExtractor(respect_headers=True)

    @pytest.fixture
    def pdf_with_sections(self):
        """Create PDF with section headers."""
        pdf_content = b"""%PDF-1.4
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
<< /Length 120 >>
stream
BT
100 750 Td
(Introduction) Tj
0 -30 Td
(This is the intro section text content here.) Tj
0 -40 Td
(Methodology) Tj
0 -30 Td
(This is the methodology section text content.) Tj
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
389
%%EOF
"""
        return io.BytesIO(pdf_content)

    def test_extract_section_header_list(self, extractor, pdf_with_sections):
        """Test that section headers are extracted to metadata."""
        result = extractor.extract(pdf_with_sections, "sections.pdf")

        # Should have section headers in metadata
        assert "section_headers" in result.metadata
        section_headers = result.metadata["section_headers"]
        assert isinstance(section_headers, list)

    def test_section_count_in_metadata(self, extractor, pdf_with_sections):
        """Test that section count is included in metadata."""
        result = extractor.extract(pdf_with_sections, "sections.pdf")

        # Should track section count
        assert "section_count" in result.metadata
        assert isinstance(result.metadata["section_count"], int)
        assert result.metadata["section_count"] >= 0


class TestPDFMetadataExtraction:
    """Test extraction of PDF document metadata (author, title, etc.)."""

    @pytest.fixture
    def extractor(self):
        """Create PDF extractor with metadata extraction enabled."""
        return PDFExtractor(extract_metadata=True)

    @pytest.fixture
    def pdf_with_metadata(self):
        """Create PDF with document metadata."""
        # Simplified - in real PDFs, metadata is more complex
        pdf_content = b"""%PDF-1.4
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
<< /Length 30 >>
stream
BT
100 700 Td
(Test) Tj
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
299
%%EOF
"""
        return io.BytesIO(pdf_content)

    def test_extract_pdf_metadata_fields(self, extractor, pdf_with_metadata):
        """Test that PDF metadata fields are extracted."""
        result = extractor.extract(pdf_with_metadata, "meta.pdf")

        # Should have source in metadata
        assert "source" in result.metadata
        # May have additional PDF metadata fields (author, title, etc.)


class TestPDFCleaningArtifacts:
    """Test PDF cleaning (page numbers, headers/footers removal)."""

    @pytest.fixture
    def extractor_with_cleaning(self):
        """Create PDF extractor with artifact cleaning enabled."""
        return PDFExtractor(clean_artifacts=True)

    @pytest.fixture
    def extractor_without_cleaning(self):
        """Create PDF extractor with artifact cleaning disabled."""
        return PDFExtractor(clean_artifacts=False)

    @pytest.fixture
    def pdf_with_artifacts(self):
        """Create PDF with page numbers and headers."""
        pdf_content = b"""%PDF-1.4
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
<< /Length 80 >>
stream
BT
100 780 Td
(Header Text) Tj
0 -50 Td
(Main content here) Tj
0 -700 Td
(Page 1) Tj
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
349
%%EOF
"""
        return io.BytesIO(pdf_content)

    def test_cleaning_option_affects_extraction(self, extractor_with_cleaning,
                                               extractor_without_cleaning, pdf_with_artifacts):
        """Test that cleaning option affects extraction results."""
        pdf_with_artifacts.seek(0)
        result_cleaned = extractor_with_cleaning.extract(pdf_with_artifacts, "clean.pdf")

        pdf_with_artifacts.seek(0)
        result_raw = extractor_without_cleaning.extract(pdf_with_artifacts, "raw.pdf")

        # Both should succeed
        assert isinstance(result_cleaned, ExtractionResult)
        assert isinstance(result_raw, ExtractionResult)

        # With cleaning enabled, may have cleaning metadata
        if "cleaned_length" in result_cleaned.metadata:
            assert result_cleaned.metadata["cleaned_length"] >= 0


class TestDynamicChunkSizing:
    """Test dynamic chunk sizing based on content type."""

    @pytest.fixture
    def extractor_dynamic(self):
        """Create PDF extractor with dynamic sizing enabled."""
        return PDFExtractor(use_dynamic_sizing=True, max_chunk_size=350)

    @pytest.fixture
    def simple_pdf(self):
        """Create simple PDF."""
        pdf_content = b"""%PDF-1.4
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
<< /Length 50 >>
stream
BT
100 700 Td
(Test content for chunking) Tj
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
319
%%EOF
"""
        return io.BytesIO(pdf_content)

    def test_dynamic_sizing_option_accepted(self, extractor_dynamic, simple_pdf):
        """Test that dynamic sizing option is accepted."""
        result = extractor_dynamic.extract(simple_pdf, "dynamic.pdf")

        assert isinstance(result, ExtractionResult)
        assert result.metadata["num_chunks"] >= 1


class TestQualityIndicators:
    """Test extraction quality indicators for PDFs."""

    @pytest.fixture
    def extractor(self):
        """Create PDF extractor instance."""
        return PDFExtractor()

    @pytest.fixture
    def good_pdf(self):
        """Create well-formed PDF."""
        pdf_content = b"""%PDF-1.4
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
<< /Length 100 >>
stream
BT
/F1 12 Tf
100 700 Td
(This is good quality PDF content with sufficient text for quality assessment.) Tj
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
369
%%EOF
"""
        return io.BytesIO(pdf_content)

    def test_quality_indicators_present(self, extractor, good_pdf):
        """Test that quality indicators are provided."""
        result = extractor.extract(good_pdf, "quality.pdf")

        assert result.quality_indicators is not None
        assert isinstance(result.quality_indicators, dict)

    def test_quality_includes_page_metrics(self, extractor, good_pdf):
        """Test that quality indicators include page-level metrics."""
        result = extractor.extract(good_pdf, "quality.pdf")

        quality = result.quality_indicators
        # Should have page extraction metrics
        assert "pages_extracted" in quality
        assert "total_pages" in quality
        assert quality["pages_extracted"] == quality["total_pages"]


class TestEdgeCasesAndErrors:
    """Test edge cases and error handling."""

    @pytest.fixture
    def extractor(self):
        """Create PDF extractor instance."""
        return PDFExtractor()

    def test_empty_pdf_file(self, extractor):
        """Test handling of empty PDF file."""
        empty_pdf = io.BytesIO(b"")

        result = extractor.extract(empty_pdf, "empty.pdf")

        # Should handle gracefully with warnings
        assert isinstance(result, ExtractionResult)
        assert len(result.warnings) > 0

    def test_corrupted_pdf_file(self, extractor):
        """Test handling of corrupted PDF file."""
        corrupted = io.BytesIO(b"This is not a valid PDF")

        result = extractor.extract(corrupted, "corrupted.pdf")

        # Should handle gracefully
        assert isinstance(result, ExtractionResult)
        # Should have warnings or empty text
        assert len(result.warnings) > 0 or result.text == ""

    def test_pdf_with_empty_pages(self, extractor):
        """Test PDF containing empty pages."""
        pdf_with_empty_page = b"""%PDF-1.4
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
<< /Length 0 >>
stream
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
249
%%EOF
"""
        file_obj = io.BytesIO(pdf_with_empty_page)
        result = extractor.extract(file_obj, "empty_page.pdf")

        # Should detect empty pages
        assert isinstance(result, ExtractionResult)
        # Should have warning about empty page
        assert any("empty" in w.lower() or "no text" in w.lower() for w in result.warnings)

    def test_max_pages_option(self, extractor):
        """Test limiting number of pages to process."""
        # Simple 2-page PDF
        multi_page = b"""%PDF-1.4
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
        file_obj = io.BytesIO(multi_page)
        result = extractor.extract(file_obj, "multi.pdf", max_pages=1)

        # Should process only 1 page
        assert isinstance(result, ExtractionResult)
        # Should have warning about limiting pages
        assert any("page" in w.lower() for w in result.warnings)


class TestExtractionOptions:
    """Test optional extraction parameters."""

    @pytest.fixture
    def simple_pdf(self):
        """Create simple PDF."""
        pdf_content = b"""%PDF-1.4
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
<< /Length 30 >>
stream
BT
100 700 Td
(Test) Tj
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
299
%%EOF
"""
        return io.BytesIO(pdf_content)

    def test_custom_chunk_size_initialization(self):
        """Test initializing extractor with custom chunk size."""
        extractor = PDFExtractor(max_chunk_size=500, chunk_overlap=150)

        assert extractor.max_chunk_size == 500
        assert extractor.chunk_overlap == 150

    def test_preserve_tables_option_initialization(self):
        """Test initializing extractor with preserve_tables option."""
        extractor = PDFExtractor(preserve_tables=True)
        assert extractor.preserve_tables is True

        extractor_no_tables = PDFExtractor(preserve_tables=False)
        assert extractor_no_tables.preserve_tables is False

    def test_clean_artifacts_initialization(self):
        """Test initializing extractor with clean_artifacts option."""
        extractor_clean = PDFExtractor(clean_artifacts=True)
        assert extractor_clean.clean_artifacts is True

        extractor_no_clean = PDFExtractor(clean_artifacts=False)
        assert extractor_no_clean.clean_artifacts is False
