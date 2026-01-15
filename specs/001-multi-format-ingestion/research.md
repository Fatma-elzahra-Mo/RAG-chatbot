# Research: Multi-Format Document Ingestion

**Date**: 2026-01-15
**Feature**: 001-multi-format-ingestion

## 1. PDF Extraction Library

**Decision**: Use existing `PDFCleaner` + `PDFAwareChunker` with PyMuPDF (fitz) backend

**Rationale**:
- Already implemented and optimized for Arabic text in the codebase
- PDFCleaner handles page numbers, headers/footers, OCR artifacts
- PDFAwareChunker respects sections, tables, and document structure
- Benchmark: 74.78% retrieval accuracy with structure-aware chunking

**Alternatives Considered**:
| Library | Pros | Cons | Decision |
|---------|------|------|----------|
| pdfplumber | Table extraction, layout analysis | Slower, more complex | Not needed - existing works |
| pypdf2 | Simple API | Poor Arabic support | Rejected |
| PyMuPDF (fitz) | Fast, good Arabic | Already in use | **Selected** |

## 2. HTML Extraction Library

**Decision**: BeautifulSoup4 with html5lib parser

**Rationale**:
- Industry standard, excellent documentation
- html5lib handles malformed HTML gracefully (important for saved web pages)
- Can selectively extract text from semantic elements
- Pairs well with existing sentence-aware chunker

**Alternatives Considered**:
| Library | Pros | Cons | Decision |
|---------|------|------|----------|
| BeautifulSoup4 | Flexible, handles malformed HTML | Slower than lxml | **Selected** for robustness |
| lxml | Fast parsing | Strict, fails on malformed HTML | Rejected |
| html2text | Markdown output | Less control over extraction | Rejected |
| trafilatura | Article extraction | Too opinionated for general use | Rejected |

**Implementation Notes**:
- Strip `<script>`, `<style>`, `<nav>`, `<footer>` tags
- Preserve `<h1>`-`<h6>` hierarchy for section metadata
- Extract table data row-by-row for linearization
- Handle RTL text direction markers gracefully

## 3. Markdown Extraction Library

**Decision**: markdown-it-py with custom renderer

**Rationale**:
- Fast, CommonMark compliant
- Extensible token stream allows preserving structure metadata
- Can identify code blocks, headers, lists for content typing
- Python native (unlike marked.js)

**Alternatives Considered**:
| Library | Pros | Cons | Decision |
|---------|------|------|----------|
| markdown-it-py | Fast, extensible, CommonMark | Needs custom renderer | **Selected** |
| mistune | Very fast | Less extensible | Considered |
| python-markdown | Standard | Slower, extension complexity | Rejected |
| commonmark.py | Spec compliant | Less maintained | Rejected |

**Implementation Notes**:
- Extract code block language for metadata (```python → language: python)
- Use headers as section boundaries for chunking
- Preserve list structure as cohesive units
- Extract link URLs to metadata (keep link text in content)

## 4. Word Document Extraction Library

**Decision**: python-docx

**Rationale**:
- Official Microsoft format support (.docx only)
- Extracts paragraphs with style information
- Handles tables natively
- Well-maintained, widely used

**Alternatives Considered**:
| Library | Pros | Cons | Decision |
|---------|------|------|----------|
| python-docx | Native .docx, styles | .docx only, no .doc | **Selected** |
| docx2txt | Simple text extraction | No structure | Rejected |
| LibreOffice CLI | Supports .doc | External dependency | Fallback for .doc |
| mammoth | Clean output | Less structure preservation | Considered |

**Implementation Notes**:
- Map Word styles (Heading 1, Heading 2) to section boundaries
- Extract tables as structured content
- Skip charts/images with warning in metadata
- For .doc files: return error with guidance to convert or save as .docx

## 5. Plain Text Handling

**Decision**: chardet for encoding detection + standard Python io

**Rationale**:
- chardet is the standard for encoding detection
- Handles Windows-1256 (Arabic Windows encoding) reliably
- Minimal dependencies, fast processing

**Alternatives Considered**:
| Library | Pros | Cons | Decision |
|---------|------|------|----------|
| chardet | Accurate, widely used | Can be slow on large files | **Selected** |
| charset-normalizer | Faster | Less accurate for Arabic | Fallback |
| cchardet | C-based, very fast | Compilation issues | Rejected |

**Implementation Notes**:
- Detect encoding with chardet (sample first 10KB for speed)
- Convert to UTF-8 with error handling (replace invalid chars)
- Detect line endings (CRLF/LF/CR) for metadata
- Apply existing ArabicSentenceChunker for chunking

## 6. Image Processing with vLLM

**Decision**: Use existing VLLMLLMWrapper with vision-capable model

**Rationale**:
- vLLM infrastructure already exists in codebase
- Vision LLMs provide superior text extraction vs traditional OCR for Arabic
- Can generate semantic descriptions for non-text content (charts, diagrams)
- Single model handles both text extraction and description generation

**Implementation Approach**:
```text
1. Detect image content type (document/chart/photo)
2. Choose appropriate prompt:
   - Document: "Extract all text from this image exactly as written..."
   - Chart: "Describe this chart including all data points, labels..."
   - Photo: "Describe this image in detail for search indexing..."
3. Process through vLLM
4. Parse and chunk extracted text/description
5. Store with metadata indicating extraction type
```

**vLLM Model Requirements**:
- Must support vision inputs (LLaVA, GPT-4V compatible, Qwen-VL, etc.)
- Arabic language support for bilingual documents
- Configurable via settings.py (existing pattern)

**Alternatives Considered**:
| Approach | Pros | Cons | Decision |
|----------|------|------|----------|
| vLLM Vision | Semantic understanding, Arabic support | Requires vision model | **Selected** |
| Tesseract OCR | Open source, many languages | Poor Arabic, no semantics | Rejected |
| Google Vision API | Excellent accuracy | External API, cost | Rejected |
| AWS Textract | Good for documents | External API, cost | Rejected |
| EasyOCR | Good Arabic support | Less accurate than vLLM | Fallback option |

## 7. File Format Detection

**Decision**: python-magic + extension fallback

**Rationale**:
- python-magic uses libmagic for accurate MIME type detection
- Combined with extension checking provides >99% accuracy
- Can detect misnamed files (e.g., .txt file that's actually HTML)

**Implementation Strategy**:
```python
def detect_format(file_bytes: bytes, filename: str) -> FileFormat:
    # 1. Try magic number detection
    mime = magic.from_buffer(file_bytes[:2048], mime=True)

    # 2. Map MIME to format
    if mime in MIME_MAP:
        return MIME_MAP[mime]

    # 3. Fall back to extension
    ext = Path(filename).suffix.lower()
    if ext in EXTENSION_MAP:
        return EXTENSION_MAP[ext]

    # 4. Return unknown for manual handling
    return FileFormat.UNKNOWN
```

## 8. File Upload Handling

**Decision**: FastAPI UploadFile with streaming

**Rationale**:
- Built into FastAPI, handles multipart/form-data
- Streaming support for large files (doesn't load entire file in memory)
- Automatic temporary file cleanup
- Validates file size before processing

**API Design**:
```python
@router.post("/ingest/file")
async def ingest_file(
    file: UploadFile,
    custom_metadata: Optional[str] = Form(None),  # JSON string
    image_mode: Optional[str] = Form("auto"),  # text|description|auto
) -> FileIngestResponse
```

## 9. Chunking Strategy per Format

| Format | Chunking Strategy | Rationale |
|--------|-------------------|-----------|
| PDF | PDFAwareChunker (existing) | Respects sections, tables, columns |
| HTML | ArabicSentenceChunker after extraction | Semantic tags stripped, pure text |
| Markdown | Header-based splitting → sentence chunking | Headers define logical sections |
| Word | Style-based splitting → sentence chunking | Heading styles define sections |
| Plain Text | ArabicSentenceChunker | Simple sentence boundaries |
| Images | Single chunk per extraction | vLLM output is already coherent |

## 10. Error Handling Strategy

| Error Type | Response | User Guidance |
|------------|----------|---------------|
| File too large (>25MB) | 413 Payload Too Large | Compress or split file |
| Unsupported format | 415 Unsupported Media Type | List supported formats |
| Corrupted file | 422 Unprocessable Entity | Re-export from source |
| No text extracted | 422 with warning | Verify file has text content |
| Encoding detection failure | Process with UTF-8 fallback | Check original encoding |
| vLLM unavailable | 503 Service Unavailable | Retry or check vLLM server |

## Summary of Technology Stack

| Component | Technology | Status |
|-----------|------------|--------|
| PDF Extraction | PyMuPDF + PDFCleaner | Existing |
| HTML Extraction | BeautifulSoup4 + html5lib | New dependency |
| Markdown Extraction | markdown-it-py | New dependency |
| Word Extraction | python-docx | New dependency |
| Plain Text | chardet + Python io | New dependency |
| Image Processing | VLLMLLMWrapper (vision) | Existing (needs vision model) |
| Format Detection | python-magic | New dependency |
| File Upload | FastAPI UploadFile | Existing |
| Chunking | ArabicSentenceChunker, PDFAwareChunker | Existing |
| Embeddings | BGE-M3 | Existing |
| Storage | Qdrant | Existing |

## New Dependencies to Add

```toml
# pyproject.toml additions
beautifulsoup4 = "^4.12"
html5lib = "^1.1"
markdown-it-py = "^3.0"
python-docx = "^1.1"
chardet = "^5.2"
python-magic = "^0.4"
Pillow = "^10.0"  # For image handling
```
