# Data Model: Multi-Format Document Ingestion

**Date**: 2026-01-15
**Feature**: 001-multi-format-ingestion

## Entities

### 1. FileFormat (Enum)

Supported file format categories.

```python
class FileFormat(str, Enum):
    PDF = "pdf"
    HTML = "html"
    MARKDOWN = "markdown"
    DOCX = "docx"
    TEXT = "text"
    IMAGE = "image"
    UNKNOWN = "unknown"
```

### 2. ImageExtractionMode (Enum)

Mode for vLLM image processing.

```python
class ImageExtractionMode(str, Enum):
    TEXT = "text"           # Extract text only
    DESCRIPTION = "description"  # Generate semantic description
    AUTO = "auto"           # Auto-detect based on content
```

### 3. ContentType (Enum)

Classification of extracted content chunks.

```python
class ContentType(str, Enum):
    TEXT = "text"           # Regular paragraph text
    HEADING = "heading"     # Section headers
    TABLE = "table"         # Tabular data
    CODE = "code"           # Code blocks
    LIST = "list"           # Bullet/numbered lists
    IMAGE_TEXT = "image_text"       # Text extracted from image
    IMAGE_DESCRIPTION = "image_description"  # Description of visual content
```

### 4. ExtractionResult

Result from format-specific extraction.

| Field | Type | Description |
|-------|------|-------------|
| text | str | Extracted plain text content |
| content_type | ContentType | Classification of content |
| metadata | dict | Format-specific metadata |
| quality_indicators | Optional[dict] | Extraction quality metrics |
| warnings | List[str] | Any warnings during extraction |

```python
class ExtractionResult(BaseModel):
    text: str
    content_type: ContentType = ContentType.TEXT
    metadata: Dict[str, Any] = Field(default_factory=dict)
    quality_indicators: Optional[Dict[str, Any]] = None
    warnings: List[str] = Field(default_factory=list)
```

### 5. FileUploadRequest

Request model for file upload endpoint.

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| file | UploadFile | Yes | The uploaded file |
| custom_metadata | Optional[str] | No | JSON string of custom metadata |
| image_mode | ImageExtractionMode | No | Mode for image processing (default: auto) |
| preserve_tables | bool | No | Preserve table structure (default: true) |
| extract_code_blocks | bool | No | Extract code blocks separately (default: true) |

### 6. FileIngestResponse

Response model for file ingestion.

| Field | Type | Description |
|-------|------|-------------|
| message | str | Status message |
| filename | str | Original filename |
| file_format | FileFormat | Detected file format |
| file_size_bytes | int | Size of uploaded file |
| documents_created | int | Number of logical documents |
| chunks_created | int | Number of chunks stored |
| processing_time_ms | int | Processing duration |
| metadata | dict | Extraction metadata |
| warnings | List[str] | Any warnings during processing |

```python
class FileIngestResponse(BaseModel):
    message: str
    filename: str
    file_format: FileFormat
    file_size_bytes: int
    documents_created: int
    chunks_created: int
    processing_time_ms: int
    metadata: Dict[str, Any] = Field(default_factory=dict)
    warnings: List[str] = Field(default_factory=list)
```

### 7. BatchFileIngestRequest

Request for batch file upload.

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| files | List[UploadFile] | Yes | List of files to upload (max 10) |
| shared_metadata | Optional[str] | No | JSON metadata applied to all files |

### 8. BatchFileIngestResponse

Response for batch file ingestion.

| Field | Type | Description |
|-------|------|-------------|
| message | str | Overall status |
| total_files | int | Number of files processed |
| successful | int | Successfully ingested count |
| failed | int | Failed count |
| results | List[FileIngestResponse] | Per-file results |
| total_chunks | int | Total chunks created |
| total_processing_time_ms | int | Total processing time |

### 9. FormatMetadata

Format-specific metadata stored with chunks.

#### PDF Metadata
```python
{
    "source_format": "pdf",
    "page_number": int,
    "section_header": Optional[str],
    "is_table": bool,
    "table_index": Optional[int],
    "num_pages_total": int
}
```

#### HTML Metadata
```python
{
    "source_format": "html",
    "heading_level": Optional[int],  # 1-6 for h1-h6
    "heading_text": Optional[str],
    "element_type": str,  # p, table, ul, ol, etc.
    "link_urls": List[str]  # Extracted from anchor tags
}
```

#### Markdown Metadata
```python
{
    "source_format": "markdown",
    "heading_level": Optional[int],
    "heading_text": Optional[str],
    "is_code_block": bool,
    "code_language": Optional[str],
    "list_type": Optional[str]  # "bullet" or "numbered"
}
```

#### Word Metadata
```python
{
    "source_format": "docx",
    "style_name": str,  # "Heading 1", "Normal", etc.
    "is_table": bool,
    "table_index": Optional[int],
    "has_track_changes": bool
}
```

#### Plain Text Metadata
```python
{
    "source_format": "text",
    "detected_encoding": str,
    "line_ending_style": str,  # "LF", "CRLF", "CR"
    "has_structure": bool  # Detected numbered sections, bullets
}
```

#### Image Metadata
```python
{
    "source_format": "image",
    "image_type": str,  # "jpeg", "png", "tiff", etc.
    "extraction_mode": str,  # "text", "description", "auto"
    "content_detected": str,  # "document", "chart", "photo", "diagram"
    "original_dimensions": {"width": int, "height": int},
    "vllm_model_used": str
}
```

## Relationships

```text
FileUploadRequest
    └── 1:N → ExtractionResult (one per logical document/section)
               └── 1:N → TextChunk (after chunking)
                          └── 1:1 → ChunkEmbedding (BGE-M3 vector)
                                     └── Stored in Qdrant
```

## Validation Rules

### File Upload Validation
- Maximum file size: 25MB
- Maximum batch size: 10 files
- Maximum total batch size: 50MB
- Allowed formats: PDF, HTML, Markdown, DOCX, TXT, JPG, JPEG, PNG, TIFF, TIF, BMP, WEBP

### Content Validation
- Minimum text extracted: 10 characters (configurable)
- Maximum chunk size: 512 tokens (existing chunker default)
- Encoding: Must be convertible to UTF-8

## State Transitions

### File Processing States
```text
UPLOADED → VALIDATING → DETECTING_FORMAT → EXTRACTING → CHUNKING → EMBEDDING → STORED
     │          │              │               │           │          │
     └──────────┴──────────────┴───────────────┴───────────┴──────────┴── FAILED
```

### Error States
- VALIDATION_FAILED: File too large, unsupported format
- EXTRACTION_FAILED: Corrupted file, parsing error
- CHUNKING_FAILED: No text extracted
- EMBEDDING_FAILED: vLLM/embedding service unavailable
- STORAGE_FAILED: Qdrant connection error

## Database Schema (Qdrant)

Chunks are stored in the existing Qdrant collection with extended metadata:

```python
# Qdrant point structure
{
    "id": "uuid",
    "vector": [float] * 1024,  # BGE-M3 embedding
    "payload": {
        # Standard fields
        "content": str,
        "chunk_index": int,
        "total_chunks": int,

        # File ingestion fields (NEW)
        "source_filename": str,
        "source_format": str,  # FileFormat value
        "content_type": str,   # ContentType value
        "ingestion_timestamp": str,  # ISO format
        "file_hash": str,      # SHA256 for deduplication

        # Format-specific metadata
        "format_metadata": dict,  # FormatMetadata based on format
    }
}
```
