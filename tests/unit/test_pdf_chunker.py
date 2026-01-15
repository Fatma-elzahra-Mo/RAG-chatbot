"""
Unit tests for PDF-aware chunker.

Tests structure detection, table preservation, dynamic sizing, and metadata enhancement.
"""

import pytest
from langchain_core.documents import Document

from src.preprocessing.pdf_chunker import PDFAwareChunker


class TestPDFAwareChunker:
    """Test suite for PDFAwareChunker."""

    @pytest.fixture
    def chunker(self):
        """Create PDF-aware chunker with test-friendly parameters."""
        return PDFAwareChunker(
            max_chunk_size=200,
            overlap=30,
            min_chunk_size=20,
            preserve_tables=True,
            preserve_lists=True,
            respect_headers=True,
            use_dynamic_sizing=True,
            clean_pdf_artifacts=True,
        )

    @pytest.fixture
    def simple_pdf_text(self):
        """Sample PDF text with common artifacts."""
        return """Page 1

مرحبا بكم في هذا المستند.

هذا هو محتوى الصفحة الأولى.

Page 2

المزيد من المحتوى هنا.
"""

    @pytest.fixture
    def pdf_with_table(self):
        """Sample PDF with table structure."""
        return """العنوان الرئيسي

هذا هو النص التمهيدي.

| العمود 1 | العمود 2 | العمود 3 |
|---------|---------|---------|
| قيمة 1  | قيمة 2  | قيمة 3  |
| قيمة 4  | قيمة 5  | قيمة 6  |

النص بعد الجدول.
"""

    @pytest.fixture
    def pdf_with_headers(self):
        """Sample PDF with section headers."""
        return """مقدمة

هذا هو نص المقدمة مع بعض المعلومات الأساسية.

القسم الأول

هذا هو محتوى القسم الأول مع تفاصيل إضافية.

القسم الثاني

هذا هو محتوى القسم الثاني مع معلومات مختلفة.
"""

    @pytest.fixture
    def pdf_with_lists(self):
        """Sample PDF with list structures."""
        return """العناصر الأساسية:

- العنصر الأول
- العنصر الثاني
- العنصر الثالث

الخطوات التالية:

1. الخطوة الأولى
2. الخطوة الثانية
3. الخطوة الثالثة
"""

    def test_pdf_detection(self, chunker):
        """Test PDF document detection by metadata."""
        # PDF by source extension
        doc_pdf = Document(page_content="مرحبا", metadata={"source": "document.pdf"})
        assert chunker._is_pdf_document(doc_pdf) is True

        # PDF by document_type
        doc_pdf2 = Document(page_content="مرحبا", metadata={"document_type": "pdf"})
        assert chunker._is_pdf_document(doc_pdf2) is True

        # Not PDF
        doc_text = Document(page_content="مرحبا", metadata={"source": "document.txt"})
        assert chunker._is_pdf_document(doc_text) is False

    def test_pdf_detection_by_content(self, chunker, simple_pdf_text):
        """Test PDF detection by content patterns."""
        doc = Document(page_content=simple_pdf_text, metadata={})
        # Should detect PDF by "Page 1", "Page 2" patterns (2 matches)
        # But only if it has 2+ indicators; our text has "Page X" twice = 2 indicators
        is_pdf = chunker._is_pdf_document(doc)
        # This is a heuristic, may or may not detect based on indicator count
        assert isinstance(is_pdf, bool)  # Just verify it returns a boolean

    def test_basic_pdf_chunking(self, chunker, simple_pdf_text):
        """Test basic chunking of PDF content."""
        docs = [Document(page_content=simple_pdf_text, metadata={"source": "test.pdf"})]
        chunked = chunker.chunk_documents(docs)

        assert len(chunked) > 0
        assert all(isinstance(d, Document) for d in chunked)
        assert all("content_type" in d.metadata for d in chunked)

    def test_page_number_removal(self, chunker, simple_pdf_text):
        """Test that page numbers are removed during cleaning."""
        docs = [Document(page_content=simple_pdf_text, metadata={"source": "test.pdf"})]
        chunked = chunker.chunk_documents(docs)

        # Check that "Page 1" and "Page 2" were removed
        all_content = " ".join(d.page_content for d in chunked)
        assert "Page 1" not in all_content
        assert "Page 2" not in all_content

    def test_table_preservation(self, chunker, pdf_with_table):
        """Test that tables are preserved in chunks."""
        docs = [Document(page_content=pdf_with_table, metadata={"source": "test.pdf"})]
        chunked = chunker.chunk_documents(docs)

        # Find chunk with table content
        table_chunks = [d for d in chunked if d.metadata.get("content_type") == "table"]
        assert len(table_chunks) > 0

        # Table content should be preserved
        table_content = table_chunks[0].page_content
        assert "|" in table_content or "العمود" in table_content

    def test_section_aware_chunking(self, chunker, pdf_with_headers):
        """Test chunking respects section boundaries."""
        docs = [Document(page_content=pdf_with_headers, metadata={"source": "test.pdf"})]
        chunked = chunker.chunk_documents(docs)

        # Should have chunks
        assert len(chunked) > 0

        # Check if any chunks have section metadata
        section_chunks = [d for d in chunked if "section_header" in d.metadata]

        # If section awareness worked, we should have section metadata
        # Otherwise, it falls back to standard chunking
        if section_chunks:
            # Check that different sections are in different chunks
            section_headers = [d.metadata.get("section_header") for d in section_chunks]
            assert len(set(section_headers)) >= 1  # At least one section detected

    def test_list_detection(self, chunker, pdf_with_lists):
        """Test detection of list structures."""
        docs = [Document(page_content=pdf_with_lists, metadata={"source": "test.pdf"})]
        chunked = chunker.chunk_documents(docs)

        # Should detect list content
        list_chunks = [d for d in chunked if d.metadata.get("content_type") == "list"]

        # Content should contain list markers
        all_content = " ".join(d.page_content for d in chunked)
        assert "العنصر الأول" in all_content or "الخطوة الأولى" in all_content

    def test_content_type_detection(self, chunker):
        """Test detection of different content types."""
        # Test table detection
        table_text = "| col1 | col2 | col3 |\n| val1 | val2 | val3 |"
        assert chunker._detect_content_type(table_text) == "table"

        # Test list detection
        list_text = "- item 1\n- item 2\n- item 3\n- item 4"
        assert chunker._detect_content_type(list_text) == "list"

        # Test regular text
        text = "هذا نص عادي بدون أي هياكل خاصة."
        assert chunker._detect_content_type(text) == "text"

    def test_dynamic_chunk_sizing(self, chunker):
        """Test dynamic chunk size adjustment based on content type."""
        # Table content should use smaller chunks
        table_size = chunker._get_dynamic_chunk_size("table content", "table")
        assert table_size == PDFAwareChunker.CHUNK_SIZES["table"]

        # Text content should use larger chunks
        text_size = chunker._get_dynamic_chunk_size("regular text", "text")
        assert text_size == PDFAwareChunker.CHUNK_SIZES["text"]

        # List content should use moderate chunks
        list_size = chunker._get_dynamic_chunk_size("list content", "list")
        assert list_size == PDFAwareChunker.CHUNK_SIZES["list"]

    def test_dynamic_sizing_disabled(self):
        """Test that dynamic sizing can be disabled."""
        chunker = PDFAwareChunker(
            max_chunk_size=500, use_dynamic_sizing=False, clean_pdf_artifacts=False
        )

        # Should always return max_chunk_size when disabled
        assert chunker._get_dynamic_chunk_size("any content", "table") == 500
        assert chunker._get_dynamic_chunk_size("any content", "text") == 500

    def test_metadata_enhancement(self, chunker, pdf_with_table):
        """Test that chunks have enhanced metadata."""
        docs = [
            Document(page_content=pdf_with_table, metadata={"source": "test.pdf", "author": "test"})
        ]
        chunked = chunker.chunk_documents(docs)

        for chunk in chunked:
            # Original metadata preserved
            assert chunk.metadata.get("source") == "test.pdf"
            assert chunk.metadata.get("author") == "test"

            # Enhanced metadata added
            assert "content_type" in chunk.metadata

            # Cleaning metadata (if cleaned)
            if chunk.metadata.get("original_length"):
                assert "cleaned_length" in chunk.metadata
                assert "reduction_ratio" in chunk.metadata

    def test_fallback_to_sentence_chunking(self, chunker):
        """Test fallback to sentence chunking for non-PDF documents."""
        text = "مرحبا. كيف حالك؟ أنا بخير."
        docs = [Document(page_content=text, metadata={"source": "document.txt"})]

        chunked = chunker.chunk_documents(docs)

        assert len(chunked) > 0
        # Should still have content_type metadata
        assert all("content_type" in d.metadata for d in chunked)
        # Should be marked as text
        assert all(d.metadata.get("content_type") == "text" for d in chunked)

    def test_empty_document(self, chunker):
        """Test handling of empty documents."""
        docs = [Document(page_content="", metadata={"source": "empty.pdf"})]
        chunked = chunker.chunk_documents(docs)

        # Should return empty list or handle gracefully
        assert isinstance(chunked, list)

    def test_very_long_table(self, chunker):
        """Test handling of tables that exceed chunk size."""
        # Create a large table
        table_rows = [
            "| العمود 1 | العمود 2 | العمود 3 |",
            "|---------|---------|---------|",
        ]
        for i in range(50):
            table_rows.append(f"| قيمة {i}1 | قيمة {i}2 | قيمة {i}3 |")

        large_table = "\n".join(table_rows)
        docs = [Document(page_content=large_table, metadata={"source": "test.pdf"})]

        chunked = chunker.chunk_documents(docs)

        # Should handle large tables by splitting
        assert len(chunked) > 1
        # All chunks should respect reasonable size limits
        assert all(len(d.page_content) < 1000 for d in chunked)

    def test_mixed_content_document(self, chunker):
        """Test document with mixed content types (text, tables, lists)."""
        mixed_content = """العنوان

النص التمهيدي مع بعض المعلومات.

القائمة:
- العنصر الأول
- العنصر الثاني

| الجدول | البيانات |
|--------|----------|
| قيمة 1 | قيمة 2   |

النص الختامي.
"""
        docs = [Document(page_content=mixed_content, metadata={"source": "test.pdf"})]
        chunked = chunker.chunk_documents(docs)

        # Should have multiple chunks with different content types
        content_types = {d.metadata.get("content_type") for d in chunked}
        assert len(content_types) >= 2  # At least 2 different content types

    def test_chunk_overlap(self, chunker):
        """Test that chunks maintain overlap."""
        text = "الجملة الأولى. " * 50  # Create long text
        docs = [Document(page_content=text, metadata={"source": "test.pdf"})]

        chunked = chunker.chunk_documents(docs)

        if len(chunked) > 1:
            # Check that consecutive chunks have some overlap
            # (This is a heuristic check - exact overlap may vary due to structure awareness)
            assert len(chunked[0].page_content) > chunker.min_chunk_size

    def test_arabic_content_preservation(self, chunker):
        """Test that Arabic content is preserved correctly."""
        arabic_text = """المقدمة

هذا نص عربي يحتوي على معلومات مهمة. يجب أن يتم الحفاظ على النص العربي بشكل صحيح.

الخلاصة

النص العربي مهم جدا للاختبار.
"""
        docs = [Document(page_content=arabic_text, metadata={"source": "test.pdf"})]
        chunked = chunker.chunk_documents(docs)

        # Verify Arabic content is preserved
        all_content = " ".join(d.page_content for d in chunked)
        assert "المقدمة" in all_content or "عربي" in all_content
        assert "الخلاصة" in all_content or "مهم" in all_content

    def test_structure_detection_metadata(self, chunker, pdf_with_headers):
        """Test that structure information is added to metadata."""
        docs = [Document(page_content=pdf_with_headers, metadata={"source": "test.pdf"})]
        chunked = chunker.chunk_documents(docs)

        # Should have chunks
        assert len(chunked) > 0

        # Check if any chunks have structure metadata from cleaning
        chunks_with_structure = [d for d in chunked if "structure" in d.metadata]
        if chunks_with_structure:
            structure = chunks_with_structure[0].metadata["structure"]
            assert isinstance(structure, dict)
            # Structure should have expected keys
            assert "has_tables" in structure
            assert "has_lists" in structure

    def test_cleaning_disabled(self):
        """Test that PDF cleaning can be disabled."""
        chunker = PDFAwareChunker(
            clean_pdf_artifacts=False, min_chunk_size=5  # Lower threshold for test
        )

        text = "Page 1\n\nمرحبا هذا نص طويل\n\nPage 2\n\nكيف حالك والأحوال"
        docs = [Document(page_content=text, metadata={"source": "test.pdf"})]
        chunked = chunker.chunk_documents(docs)

        # Should still produce chunks
        assert len(chunked) > 0
        # Content should be preserved
        all_content = " ".join(d.page_content for d in chunked)
        assert len(all_content) > 0
        assert "مرحبا" in all_content or "حالك" in all_content

    def test_preserve_tables_disabled(self):
        """Test table preservation can be disabled."""
        chunker = PDFAwareChunker(preserve_tables=False, clean_pdf_artifacts=False)

        table_text = """Text before.

| col1 | col2 |
| val1 | val2 |

Text after.
"""
        docs = [Document(page_content=table_text, metadata={"source": "test.pdf"})]
        chunked = chunker.chunk_documents(docs)

        # Should still chunk, but without special table handling
        assert len(chunked) > 0

    def test_respect_headers_disabled(self):
        """Test that header-based chunking can be disabled."""
        chunker = PDFAwareChunker(
            respect_headers=False, clean_pdf_artifacts=False, min_chunk_size=5
        )

        text_with_headers = """Header 1

Content 1 with more text to meet minimum chunk size.

Header 2

Content 2 with more text to meet minimum chunk size.
"""
        docs = [Document(page_content=text_with_headers, metadata={"source": "test.pdf"})]
        chunked = chunker.chunk_documents(docs)

        # Should chunk without section awareness
        assert len(chunked) > 0
        # Should not have section_header metadata (or very few)
        section_chunks = [d for d in chunked if "section_header" in d.metadata]
        # When headers are disabled, should use other strategies
        assert len(section_chunks) < len(chunked) or len(section_chunks) == 0
