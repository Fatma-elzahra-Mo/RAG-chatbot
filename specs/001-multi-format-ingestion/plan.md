# Implementation Plan: Multi-Format Document Ingestion API

**Branch**: `001-multi-format-ingestion` | **Date**: 2026-01-15 | **Spec**: [spec.md](./spec.md)
**Input**: Feature specification from `/specs/001-multi-format-ingestion/spec.md`

## Summary

Multi-format document ingestion API supporting 6 format categories: PDF, HTML, Markdown, Word (.docx), Plain Text (.txt), and Images (with vLLM-based text extraction and description generation). The system will leverage the existing vLLM integration for image processing instead of traditional OCR, providing superior text extraction for Arabic and enabling semantic descriptions for non-text visual content.

## Technical Context

**Language/Version**: Python 3.11
**Primary Dependencies**: FastAPI, LangChain, python-docx, beautifulsoup4, markdown-it-py, Pillow, python-magic
**Storage**: Qdrant vector database (existing), file system for temporary uploads
**Testing**: pytest with fixtures in tests/unit/, tests/integration/
**Target Platform**: Linux server (Docker-based deployment)
**Project Type**: Single project (API backend)
**Performance Goals**: 15s for 10-page PDF, 10s for image processing, 100 docs/hour throughput
**Constraints**: <25MB file size limit, UTF-8 conversion for all text, memory-efficient streaming for large files
**Scale/Scope**: Batch uploads of 10 files, concurrent API requests supported

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

Constitution file is a template (not configured for this project). Proceeding with codebase conventions from CLAUDE.md:
- ✅ Uses existing infrastructure (vLLM, Qdrant, BGE-M3 embeddings)
- ✅ Follows existing code patterns (FastAPI routes, Pydantic schemas)
- ✅ Type hints required on all functions
- ✅ Test coverage target >80%
- ✅ No changes to model configurations (BGE-M3, ARA-Reranker-V1)

## Project Structure

### Documentation (this feature)

```text
specs/001-multi-format-ingestion/
├── plan.md              # This file
├── research.md          # Phase 0 output - technology decisions
├── data-model.md        # Phase 1 output - entity definitions
├── quickstart.md        # Phase 1 output - usage guide
├── contracts/           # Phase 1 output - OpenAPI specs
│   └── ingest-api.yaml
└── tasks.md             # Phase 2 output (via /speckit.tasks)
```

### Source Code (repository root)

```text
src/
├── api/
│   └── routes/
│       └── documents.py      # MODIFY: Add file upload endpoint
├── preprocessing/
│   ├── chunker.py            # EXISTING: ArabicSentenceChunker
│   ├── pdf_chunker.py        # EXISTING: PDFAwareChunker
│   ├── pdf_cleaner.py        # EXISTING: PDFCleaner
│   ├── extractors/           # NEW: Format-specific extractors
│   │   ├── __init__.py
│   │   ├── base.py           # Base extractor interface
│   │   ├── pdf.py            # PDF extraction (wraps existing)
│   │   ├── html.py           # HTML extraction
│   │   ├── markdown.py       # Markdown extraction
│   │   ├── docx.py           # Word document extraction
│   │   ├── text.py           # Plain text extraction
│   │   └── image.py          # vLLM-based image extraction
│   └── format_detector.py    # NEW: Auto-detect file format
├── models/
│   ├── schemas.py            # MODIFY: Add file upload schemas
│   └── vllm_model.py         # EXISTING: vLLM wrapper
└── core/
    └── pipeline.py           # MODIFY: Add file ingestion method

tests/
├── unit/
│   ├── test_extractors/      # NEW: Extractor unit tests
│   │   ├── test_html.py
│   │   ├── test_markdown.py
│   │   ├── test_docx.py
│   │   ├── test_text.py
│   │   └── test_image.py
│   └── test_format_detector.py
└── integration/
    └── test_file_ingestion.py  # NEW: End-to-end file upload tests
```

**Structure Decision**: Single project structure following existing patterns. New extractors module under `preprocessing/` to align with existing chunker and cleaner patterns. Modular design allows adding new formats easily.

## Complexity Tracking

No constitution violations requiring justification.

| Aspect | Decision | Rationale |
|--------|----------|-----------|
| vLLM for images | Use existing vLLM integration | Leverages existing infrastructure, superior Arabic support vs traditional OCR |
| Extractor pattern | Strategy pattern with base class | Enables easy addition of new formats, testable in isolation |
| File upload | FastAPI File + UploadFile | Standard approach, handles streaming for large files |
