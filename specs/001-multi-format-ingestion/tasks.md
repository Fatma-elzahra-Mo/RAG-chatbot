# Tasks: Multi-Format Document Ingestion API

**Input**: Design documents from `/specs/001-multi-format-ingestion/`
**Prerequisites**: plan.md (required), spec.md (required), research.md, data-model.md, contracts/ingest-api.yaml

**Tests**: Tests are included as the codebase has >80% test coverage target (per CLAUDE.md).

**Organization**: Tasks are grouped by user story to enable independent implementation and testing of each story.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (e.g., US1, US5, US2, US6, US3, US4)
- Include exact file paths in descriptions

## Path Conventions

- **Single project**: `src/`, `tests/` at repository root (per plan.md)

---

## Phase 1: Setup (Shared Infrastructure) ✅ COMPLETE

**Purpose**: Project initialization and dependency setup

- [X] T001 Add new dependencies to pyproject.toml: beautifulsoup4, html5lib, markdown-it-py, python-docx, chardet, python-magic, Pillow
- [X] T002 [P] Create src/preprocessing/extractors/ directory structure with __init__.py
- [X] T003 [P] Create tests/unit/test_extractors/ directory structure

---

## Phase 2: Foundational (Blocking Prerequisites) ✅ COMPLETE

**Purpose**: Core infrastructure that MUST be complete before ANY user story can be implemented

**⚠️ CRITICAL**: No user story work can begin until this phase is complete

- [X] T004 Create FileFormat, ImageExtractionMode, ContentType enums in src/models/schemas.py
- [X] T005 Create ExtractionResult Pydantic model in src/models/schemas.py
- [X] T006 [P] Create FileUploadRequest schema in src/models/schemas.py (with file, custom_metadata, image_mode, preserve_tables, extract_code_blocks fields)
- [X] T007 [P] Create FileIngestResponse schema in src/models/schemas.py (with message, filename, file_format, file_size_bytes, documents_created, chunks_created, processing_time_ms, metadata, warnings)
- [X] T008 [P] Create BatchFileUploadRequest and BatchFileIngestResponse schemas in src/models/schemas.py
- [X] T009 Create base extractor interface (BaseExtractor abstract class) in src/preprocessing/extractors/base.py with extract() method signature
- [X] T010 Implement format detector in src/preprocessing/format_detector.py using python-magic for MIME detection with extension fallback
- [X] T011 [P] Write unit tests for format detector in tests/unit/test_format_detector.py
- [X] T012 Create file upload endpoint skeleton POST /documents/ingest/file in src/api/routes/documents.py
- [X] T013 [P] Create batch upload endpoint skeleton POST /documents/ingest/batch in src/api/routes/documents.py
- [X] T014 [P] Create GET /documents/formats endpoint in src/api/routes/documents.py

**Checkpoint**: ✅ Foundation ready - user story implementation can now begin

---

## Phase 3: User Story 1 - Upload and Query PDF Documents (Priority: P1) 🎯 MVP ✅ COMPLETE

**Goal**: Users can upload PDF documents and query their content with source attribution

**Independent Test**: Upload a multi-page Arabic PDF, ask domain-specific questions, verify accurate answers with page numbers

### Tests for User Story 1

> **NOTE: Write these tests FIRST, ensure they FAIL before implementation**

- [X] T015 [P] [US1] Unit test for PDF extractor in tests/unit/test_extractors/test_pdf.py (test text extraction, table preservation, Arabic handling)
- [X] T016 [P] [US1] Integration test for PDF upload endpoint in tests/integration/test_file_ingestion.py::test_pdf_upload

### Implementation for User Story 1

- [X] T017 [US1] Create PDF extractor in src/preprocessing/extractors/pdf.py wrapping existing PDFCleaner and PDFAwareChunker
- [X] T018 [US1] Integrate PDF extractor with format detector in src/preprocessing/format_detector.py
- [X] T019 [US1] Implement file ingestion method in src/core/pipeline.py::ingest_file() for PDF format
- [X] T020 [US1] Wire up /documents/ingest/file endpoint for PDF in src/api/routes/documents.py
- [X] T021 [US1] Add PDF-specific metadata (page_number, section_header, num_pages_total) to chunk payload

**Checkpoint**: ✅ PDF upload and query working independently

---

## Phase 4: User Story 5 - Ingest Plain Text Files (Priority: P1) 🎯 MVP ✅ COMPLETE

**Goal**: Users can upload plain text files with automatic encoding detection

**Independent Test**: Upload a plain text file with Arabic and English content, verify accurate retrieval without encoding issues

### Tests for User Story 5

> **NOTE: Write these tests FIRST, ensure they FAIL before implementation**

- [X] T022 [P] [US5] Unit test for text extractor in tests/unit/test_extractors/test_text.py (test UTF-8, Windows-1256, encoding detection)
- [X] T023 [P] [US5] Integration test for text upload in tests/integration/test_file_ingestion.py::test_text_upload

### Implementation for User Story 5

- [X] T024 [US5] Create text extractor in src/preprocessing/extractors/text.py with chardet encoding detection
- [X] T025 [US5] Integrate text extractor with format detector
- [X] T026 [US5] Extend src/core/pipeline.py::ingest_file() to handle plain text format
- [X] T027 [US5] Add text-specific metadata (detected_encoding, line_ending_style, has_structure) to chunk payload

**Checkpoint**: ✅ Plain text upload working independently alongside PDF

---

## Phase 5: User Story 2 - Process HTML Web Content (Priority: P2) ✅ COMPLETE

**Goal**: Users can upload HTML files with clean text extraction (no tags, scripts, styles)

**Independent Test**: Upload an HTML file with headings, paragraphs, lists, verify clean text extraction

### Tests for User Story 2

> **NOTE: Write these tests FIRST, ensure they FAIL before implementation**

- [X] T028 [P] [US2] Unit test for HTML extractor in tests/unit/test_extractors/test_html.py (test tag stripping, RTL handling, table linearization)
- [X] T029 [P] [US2] Integration test for HTML upload in tests/integration/test_file_ingestion.py::test_html_upload

### Implementation for User Story 2

- [X] T030 [US2] Create HTML extractor in src/preprocessing/extractors/html.py using BeautifulSoup4 + html5lib
- [X] T031 [US2] Implement script/style/nav/footer stripping in HTML extractor
- [X] T032 [US2] Implement table linearization (row-by-row) in HTML extractor
- [X] T033 [US2] Integrate HTML extractor with format detector
- [X] T034 [US2] Extend src/core/pipeline.py::ingest_file() to handle HTML format
- [X] T035 [US2] Add HTML-specific metadata (heading_level, heading_text, element_type, link_urls) to chunk payload

**Checkpoint**: ✅ HTML upload working independently alongside PDF and Plain Text

---

## Phase 6: User Story 6 - Extract Text and Descriptions from Images via Vision LLM (Priority: P2) ✅ COMPLETE

**Goal**: Users can upload images and get vLLM-based text extraction or semantic descriptions

**Independent Test**: Upload an image with Arabic text, verify vLLM extracts text accurately; upload a chart, verify meaningful description is generated

### Tests for User Story 6

> **NOTE: Write these tests FIRST, ensure they FAIL before implementation**

- [X] T036 [P] [US6] Unit test for image extractor in tests/unit/test_extractors/test_image.py (test text mode, description mode, auto mode)
- [X] T037 [P] [US6] Integration test for image upload in tests/integration/test_file_ingestion.py::test_image_upload

### Implementation for User Story 6

- [X] T038 [US6] Create image extractor in src/preprocessing/extractors/image.py using existing VLLMLLMWrapper
- [X] T039 [US6] Implement text extraction prompt for document images in image extractor
- [X] T040 [US6] Implement description generation prompt for charts/photos/diagrams in image extractor
- [X] T041 [US6] Implement auto-detection logic to choose text vs description mode based on image content
- [X] T042 [US6] Handle multi-page TIFF processing (page-by-page extraction)
- [X] T043 [US6] Integrate image extractor with format detector
- [X] T044 [US6] Extend src/core/pipeline.py::ingest_file() to handle image formats
- [X] T045 [US6] Add image-specific metadata (image_type, extraction_mode, content_detected, original_dimensions, vllm_model_used) to chunk payload
- [X] T046 [US6] Add quality indicators and warnings for low-confidence extractions

**Checkpoint**: ✅ Image upload working independently alongside PDF, Plain Text, and HTML

---

## Phase 7: User Story 3 - Import Markdown Documentation (Priority: P3) ✅ COMPLETE

**Goal**: Users can upload Markdown files with header-based chunking and code block preservation

**Independent Test**: Upload a Markdown file with headers, code blocks, and lists, verify structure-aware chunking

### Tests for User Story 3

> **NOTE: Write these tests FIRST, ensure they FAIL before implementation**

- [X] T047 [P] [US3] Unit test for Markdown extractor in tests/unit/test_extractors/test_markdown.py (test header extraction, code block handling, list preservation)
- [X] T048 [P] [US3] Integration test for Markdown upload in tests/integration/test_file_ingestion.py::test_markdown_upload

### Implementation for User Story 3

- [X] T049 [US3] Create Markdown extractor in src/preprocessing/extractors/markdown.py using markdown-it-py
- [X] T050 [US3] Implement header-based section splitting in Markdown extractor
- [X] T051 [US3] Implement code block extraction with language detection in Markdown extractor
- [X] T052 [US3] Implement list structure preservation in Markdown extractor
- [X] T053 [US3] Integrate Markdown extractor with format detector
- [X] T054 [US3] Extend src/core/pipeline.py::ingest_file() to handle Markdown format
- [X] T055 [US3] Add Markdown-specific metadata (heading_level, heading_text, is_code_block, code_language, list_type) to chunk payload

**Checkpoint**: ✅ Markdown upload working independently alongside all previous formats

---

## Phase 8: User Story 4 - Upload Microsoft Word Documents (Priority: P3) ✅ COMPLETE

**Goal**: Users can upload .docx files with style-based chunking and table extraction

**Independent Test**: Upload a Word document with styled headings and tables, verify structure-aware extraction

### Tests for User Story 4

> **NOTE: Write these tests FIRST, ensure they FAIL before implementation**

- [X] T056 [P] [US4] Unit test for Word extractor in tests/unit/test_extractors/test_docx.py (test style detection, table extraction, track changes handling)
- [X] T057 [P] [US4] Integration test for Word upload in tests/integration/test_file_ingestion.py::test_docx_upload

### Implementation for User Story 4

- [X] T058 [US4] Create Word extractor in src/preprocessing/extractors/docx.py using python-docx
- [X] T059 [US4] Implement heading style detection (Heading 1, Heading 2, etc.) in Word extractor
- [X] T060 [US4] Implement table extraction as cohesive chunks in Word extractor
- [X] T061 [US4] Implement track changes detection (extract accepted text only, flag in metadata)
- [X] T062 [US4] Handle .doc format gracefully (return clear error with guidance to convert)
- [X] T063 [US4] Integrate Word extractor with format detector
- [X] T064 [US4] Extend src/core/pipeline.py::ingest_file() to handle Word format
- [X] T065 [US4] Add Word-specific metadata (style_name, is_table, table_index, has_track_changes) to chunk payload

**Checkpoint**: ✅ Word upload working independently alongside all previous formats

---

## Phase 9: Batch Upload & Polish

**Purpose**: Multi-file batch processing and cross-cutting improvements

- [ ] T066 Implement batch upload logic in /documents/ingest/batch endpoint (sequential processing, aggregated response)
- [ ] T067 Add shared_metadata handling to batch uploads
- [ ] T068 [P] Add file size validation (25MB single file, 50MB batch total) with clear error messages
- [ ] T069 [P] Add file count validation (max 10 files per batch)
- [ ] T070 Implement deduplication detection via file hash (SHA256) with warning in response
- [ ] T071 [P] Add ingestion logging with file hash, processing time, chunk count, warnings
- [ ] T072 Run quickstart.md validation - test all curl examples
- [ ] T073 [P] Add API documentation/OpenAPI updates in src/api/main.py

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies - can start immediately
- **Foundational (Phase 2)**: Depends on Setup completion - BLOCKS all user stories
- **User Stories (Phase 3-8)**: All depend on Foundational phase completion
  - P1 stories (US1 PDF, US5 Plain Text) should be prioritized for MVP
  - P2 stories (US2 HTML, US6 Images) can follow
  - P3 stories (US3 Markdown, US4 Word) can be deferred
- **Batch & Polish (Phase 9)**: Depends on at least US1 (PDF) being complete

### User Story Dependencies

- **User Story 1 (PDF) - P1**: Can start after Foundational - No dependencies on other stories
- **User Story 5 (Plain Text) - P1**: Can start after Foundational - No dependencies on other stories
- **User Story 2 (HTML) - P2**: Can start after Foundational - No dependencies on other stories
- **User Story 6 (Images) - P2**: Can start after Foundational - Depends on existing vLLM integration being functional
- **User Story 3 (Markdown) - P3**: Can start after Foundational - No dependencies on other stories
- **User Story 4 (Word) - P3**: Can start after Foundational - No dependencies on other stories

### Within Each User Story

- Tests MUST be written and FAIL before implementation
- Extractor before integration
- Integration before endpoint wiring
- Endpoint before metadata enrichment
- Story complete before moving to next priority

### Parallel Opportunities

- T002, T003 can run in parallel (directory creation)
- T006, T007, T008 can run in parallel (schema definitions)
- T011, T012, T013, T014 can run in parallel (different files)
- All tests for a user story marked [P] can run in parallel
- Different user stories can be worked on in parallel by different team members once Phase 2 completes

---

## Implementation Strategy

### MVP First (P1 Stories: US1 + US5)

1. Complete Phase 1: Setup
2. Complete Phase 2: Foundational (CRITICAL - blocks all stories)
3. Complete Phase 3: User Story 1 (PDF)
4. Complete Phase 4: User Story 5 (Plain Text)
5. **STOP and VALIDATE**: Test PDF and Plain Text uploads independently
6. Deploy/demo if ready

### Incremental Delivery

1. Complete Setup + Foundational → Foundation ready
2. Add User Story 1 (PDF) → Test independently → Deploy/Demo (MVP!)
3. Add User Story 5 (Plain Text) → Test independently → Deploy/Demo
4. Add User Story 2 (HTML) → Test independently → Deploy/Demo
5. Add User Story 6 (Images) → Test independently → Deploy/Demo
6. Add User Story 3 (Markdown) → Test independently → Deploy/Demo
7. Add User Story 4 (Word) → Test independently → Deploy/Demo
8. Each story adds value without breaking previous stories

---

## Notes

- [P] tasks = different files, no dependencies
- [Story] label maps task to specific user story for traceability
- Each user story should be independently completable and testable
- Verify tests fail before implementing
- Commit after each task or logical group
- Stop at any checkpoint to validate story independently
- Existing infrastructure to leverage: PDFCleaner, PDFAwareChunker, VLLMLLMWrapper, ArabicSentenceChunker, BGE-M3 embeddings
