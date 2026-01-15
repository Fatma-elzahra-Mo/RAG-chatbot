# Quickstart: Multi-Format Document Ingestion

## Overview

The Multi-Format Document Ingestion API allows you to upload and search documents in various formats:
- **PDF** - Research papers, reports, books
- **HTML** - Web pages, saved articles
- **Markdown** - Documentation, README files
- **Word (.docx)** - Business documents, proposals
- **Plain Text (.txt)** - Notes, transcripts
- **Images** - Scanned documents, charts, photos (processed with vLLM)

## Prerequisites

1. **Running API Server**
   ```bash
   uvicorn src.api.main:app --reload
   ```

2. **Running Qdrant** (for vector storage)
   ```bash
   docker-compose up -d qdrant
   ```

3. **Running vLLM** (for image processing) - Optional
   ```bash
   python -m vllm.entrypoints.openai.api_server \
     --model llava-hf/llava-1.5-7b-hf \
     --port 8000
   ```

## Quick Examples

### Upload a PDF Document

```bash
curl -X POST "http://localhost:8000/documents/ingest/file" \
  -H "accept: application/json" \
  -F "file=@research_paper.pdf"
```

**Response:**
```json
{
  "message": "File ingested successfully",
  "filename": "research_paper.pdf",
  "file_format": "pdf",
  "file_size_bytes": 2048576,
  "documents_created": 1,
  "chunks_created": 45,
  "processing_time_ms": 3200,
  "metadata": {
    "num_pages": 12,
    "detected_language": "ar"
  },
  "warnings": []
}
```

### Upload an Image with Text

```bash
curl -X POST "http://localhost:8000/documents/ingest/file" \
  -H "accept: application/json" \
  -F "file=@scanned_document.jpg" \
  -F "image_mode=text"
```

### Upload an Image for Description

```bash
curl -X POST "http://localhost:8000/documents/ingest/file" \
  -H "accept: application/json" \
  -F "file=@data_chart.png" \
  -F "image_mode=description"
```

### Batch Upload Multiple Files

```bash
curl -X POST "http://localhost:8000/documents/ingest/batch" \
  -H "accept: application/json" \
  -F "files=@doc1.pdf" \
  -F "files=@doc2.html" \
  -F "files=@doc3.md" \
  -F "shared_metadata={\"project\": \"research-2025\"}"
```

### Upload with Custom Metadata

```bash
curl -X POST "http://localhost:8000/documents/ingest/file" \
  -H "accept: application/json" \
  -F "file=@report.docx" \
  -F "custom_metadata={\"author\": \"Ahmed\", \"department\": \"Engineering\"}"
```

## Python SDK Example

```python
import httpx

async def ingest_file(filepath: str, metadata: dict = None):
    async with httpx.AsyncClient() as client:
        with open(filepath, "rb") as f:
            files = {"file": (filepath.split("/")[-1], f)}
            data = {}
            if metadata:
                data["custom_metadata"] = json.dumps(metadata)

            response = await client.post(
                "http://localhost:8000/documents/ingest/file",
                files=files,
                data=data,
            )
            return response.json()

# Usage
result = await ingest_file("research.pdf", {"source": "arxiv"})
print(f"Created {result['chunks_created']} chunks")
```

## Query Ingested Documents

After ingestion, query documents using the chat endpoint:

```bash
curl -X POST "http://localhost:8000/chat" \
  -H "Content-Type: application/json" \
  -d '{
    "query": "ما هي النتائج الرئيسية في التقرير؟",
    "session_id": "user123",
    "use_rag": true
  }'
```

## Supported Formats Reference

| Format | Extensions | Max Size | Notes |
|--------|------------|----------|-------|
| PDF | .pdf | 25MB | Structure-aware chunking |
| HTML | .html, .htm | 25MB | Scripts/styles removed |
| Markdown | .md, .markdown | 25MB | Code blocks preserved |
| Word | .docx | 25MB | .doc not supported |
| Text | .txt | 25MB | Encoding auto-detected |
| Images | .jpg, .png, .tiff, etc. | 25MB | vLLM text extraction |

## Image Processing Modes

| Mode | Use Case | Example |
|------|----------|---------|
| `text` | Scanned documents, screenshots with text | Scanned Arabic PDF page |
| `description` | Charts, diagrams, photos | Data visualization, product photo |
| `auto` (default) | Let vLLM decide | Any image |

## Error Handling

| HTTP Code | Meaning | Solution |
|-----------|---------|----------|
| 413 | File too large | Compress or split file |
| 415 | Unsupported format | Convert to supported format |
| 422 | Processing failed | Check file isn't corrupted |
| 503 | Service unavailable | Check vLLM/Qdrant status |

## Best Practices

1. **Use batch upload** for multiple related files
2. **Add metadata** for better organization and filtering
3. **Use `image_mode=text`** for document scans to get faster, more accurate extraction
4. **Use `image_mode=description`** for charts/diagrams to get semantic understanding
5. **Keep files under 10MB** for optimal processing speed
6. **Use PDF** when possible - best structure preservation
