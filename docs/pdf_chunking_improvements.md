# PDF Chunking Improvements

## Overview

Enhanced the Arabic RAG chatbot with comprehensive PDF-aware chunking capabilities that significantly improve document processing quality for PDF uploads.

## What Was Implemented

### 1. PDF Cleaner Module (`src/preprocessing/pdf_cleaner.py`)

A robust PDF text cleaning system that removes common artifacts:

**Features:**
- **Page Number Removal**: Detects and removes page numbers in multiple formats
  - English: "Page 1", "Page 42"
  - Arabic: "صفحة ١", "صفحة ٤٢"
  - Standalone numbers: "1", "42"
  - Fraction format: "1/10", "5/20"
  - Arabic numerals: "١", "٤٢"

- **Header/Footer Detection**: Identifies and removes repeated headers/footers
  - Detects lines that appear 3+ times
  - Removes horizontal lines (---, ===)
  - Removes copyright notices
  - Removes URLs and website addresses

- **OCR Artifact Cleaning**:
  - Removes excessive whitespace (3+ spaces, 4+ newlines)
  - Removes zero-width characters and invisible Unicode
  - Removes control characters
  - Normalizes line breaks and spacing

- **Structure Detection**:
  - Detects tables (pipe-separated, tab-separated, markdown)
  - Detects lists (bullet points, numbered, Arabic)
  - Detects section headers
  - Returns structural metadata for intelligent chunking

- **Metadata Extraction**:
  - Original and cleaned text length
  - Reduction ratio (how much was cleaned)
  - Number of pages detected
  - Document structure information

**Configuration Options:**
```python
PDFCleaner(
    remove_page_numbers=True,      # Remove page number patterns
    remove_headers_footers=True,   # Remove repeated headers/footers
    clean_artifacts=True,          # Clean OCR noise
    normalize_arabic=False,        # Conservative Arabic normalization
    min_line_length=10             # Minimum line length to keep
)
```

### 2. PDF-Aware Chunker (`src/preprocessing/pdf_chunker.py`)

Extends the existing `ArabicSentenceChunker` with PDF-specific intelligence:

**Features:**
- **Structure-Aware Chunking**:
  - **Section Chunking**: Respects document headers as natural boundaries
  - **Table Preservation**: Keeps tables intact when possible, splits intelligently if too large
  - **List Handling**: Maintains list structure and hierarchy
  - **Page Boundaries**: Tracks page numbers in metadata

- **Dynamic Chunk Sizing**:
  - Tables: 250 tokens (dense content)
  - Lists: 300 tokens (structured content)
  - Headers: 150 tokens (short content)
  - Text: 400 tokens (narrative content)
  - Adjusts automatically based on content type

- **Enhanced Metadata**:
  - `content_type`: "table", "list", "text", "header"
  - `section_header`: Name of the section (if detected)
  - `section_index`: Which section this chunk belongs to
  - `chunking_strategy`: "section_aware", "table_preserved", etc.
  - `chunk_size_used`: Actual chunk size used for this content

- **Auto-Detection**: Automatically detects PDF documents by:
  - File extension (.pdf in metadata)
  - `document_type` metadata field
  - Content patterns (page numbers, tables, multiple newlines)

**Configuration Options:**
```python
PDFAwareChunker(
    max_chunk_size=350,           # Base chunk size
    overlap=100,                  # Overlap between chunks
    preserve_tables=True,         # Keep tables intact
    preserve_lists=True,          # Maintain list structure
    respect_headers=True,         # Use headers as boundaries
    use_dynamic_sizing=True,      # Adjust size by content type
    clean_pdf_artifacts=True      # Apply PDF cleaning
)
```

### 3. Pipeline Integration (`src/core/pipeline.py`)

Updated the RAG pipeline to support PDF chunking:

**New Features:**
- `document_type` parameter in `ingest_documents()`:
  - `"pdf"`: Uses PDF-aware chunker
  - `"text"`: Uses standard sentence-aware chunker
  - `None`: Auto-detects based on metadata and content

- **Auto-Detection Logic**:
  - Checks metadata for `.pdf` extension
  - Checks `document_type` field
  - Analyzes content for PDF patterns
  - Falls back to text chunking if uncertain

- **Backward Compatible**: Existing code continues to work without changes

**Usage Example:**
```python
# Explicit PDF mode
pipeline.ingest_documents(
    texts=[pdf_text],
    metadatas=[{"source": "document.pdf"}],
    document_type="pdf"
)

# Auto-detection (recommended)
pipeline.ingest_documents(
    texts=[pdf_text],
    metadatas=[{"source": "document.pdf"}]
)

# Standard text mode (unchanged)
pipeline.ingest_documents(
    texts=[plain_text],
    metadatas=[{"source": "document.txt"}]
)
```

### 4. Configuration Settings (`src/config/settings.py`)

Added PDF-specific settings with sensible defaults:

```python
# PDF-specific processing
pdf_chunk_size: int = 350                  # Base chunk size for PDF content
pdf_preserve_tables: bool = True           # Keep tables intact when possible
pdf_preserve_lists: bool = True            # Maintain list structure
pdf_respect_headers: bool = True           # Use headers as chunk boundaries
pdf_use_dynamic_sizing: bool = True        # Adjust chunk size by content type
pdf_remove_headers: bool = True            # Remove repeated headers/footers
pdf_remove_page_numbers: bool = True       # Clean page number artifacts
pdf_clean_artifacts: bool = True           # Remove OCR noise and formatting issues
```

All settings are configurable via environment variables.

### 5. Comprehensive Testing

**Test Coverage:**
- `test_pdf_cleaner.py`: 34 tests, 100% coverage
  - Page number removal (all formats)
  - Header/footer detection and removal
  - Artifact cleaning
  - Structure detection
  - Metadata extraction
  - Edge cases (empty, whitespace-only)

- `test_pdf_chunker.py`: 21 tests, 79% coverage
  - PDF detection
  - Structure-aware chunking
  - Table preservation
  - Section boundaries
  - Dynamic sizing
  - Metadata enhancement
  - Fallback behavior
  - Feature toggles

**Backward Compatibility:**
- All 10 existing `test_chunker.py` tests pass
- Standard text chunking unchanged
- No breaking changes to API

## Quality Improvements for PDF Documents

### Before (Standard Chunking)
- Page numbers mixed with content
- Chunks break across table rows
- Headers repeated in every chunk
- Fixed 350-character chunks regardless of content
- No awareness of document structure

### After (PDF-Aware Chunking)
- Page numbers removed during preprocessing
- Tables kept intact (or split intelligently)
- Headers used as natural boundaries
- Dynamic chunk sizes (250-400 chars) based on content
- Metadata tracks content type and structure

### Expected Impact
- **Better Retrieval Accuracy**: Content-aware chunking keeps related information together
- **Cleaner Context**: Removed artifacts mean less noise in retrieval
- **Improved Embeddings**: Semantic units (tables, sections) embedded as complete units
- **Richer Metadata**: Content type information helps with result ranking

## Performance Considerations

- **Preprocessing Overhead**: PDF cleaning adds ~50-100ms per document (acceptable for ingestion)
- **Memory Usage**: Comparable to standard chunking (no significant increase)
- **Query Time**: Zero impact (preprocessing happens at ingestion time)
- **Storage**: Slight increase due to enhanced metadata (negligible)

## Usage Recommendations

### For Best Results:
1. **Use Auto-Detection**: Let the system detect PDF documents automatically
2. **Enable All Features**: Default settings are optimized for Arabic PDFs
3. **Review First Document**: Check chunking quality on a sample document
4. **Adjust if Needed**: Fine-tune settings based on your PDF characteristics

### For Specific Use Cases:
- **Academic Papers**: Enable header-based chunking (default)
- **Data-Heavy Documents**: Enable table preservation (default)
- **Scanned PDFs**: Enable artifact cleaning (default)
- **Clean PDFs**: Can disable cleaning for slight speed improvement

### For Existing Deployments:
- No migration needed - system auto-detects document types
- Existing text documents continue using standard chunking
- Gradually re-ingest PDF documents to benefit from improvements

## Code Quality

- **Type Hints**: All functions fully typed
- **Docstrings**: Comprehensive documentation with examples
- **Tests**: 65 total tests (55 new, 10 existing)
- **Coverage**: 100% for new cleaner, 79% for new chunker
- **Code Style**: Black formatted (line-length 100)
- **Linting**: Ruff clean (no violations)

## Files Modified

**New Files:**
- `src/preprocessing/pdf_cleaner.py` (338 lines)
- `src/preprocessing/pdf_chunker.py` (541 lines)
- `tests/unit/test_pdf_cleaner.py` (503 lines)
- `tests/unit/test_pdf_chunker.py` (387 lines)

**Modified Files:**
- `src/config/settings.py` (+8 lines)
- `src/core/pipeline.py` (+44 lines)

**Total Added:** ~1,800 lines of production code and tests

## Future Enhancements (Optional)

Potential improvements for future iterations:

1. **Multi-Column Layout Detection**: Better handling of two/three-column PDFs
2. **Image Region Detection**: Skip or handle embedded images
3. **Footnote Handling**: Special processing for footnotes and references
4. **Citation Extraction**: Extract and preserve citation metadata
5. **Performance Optimization**: Parallel processing for large PDFs
6. **Custom Rules**: Allow users to define custom cleaning patterns

## Conclusion

The PDF chunking improvements provide a significant quality boost for PDF document processing while maintaining full backward compatibility. The system is production-ready, well-tested, and follows all project conventions and code quality standards.
