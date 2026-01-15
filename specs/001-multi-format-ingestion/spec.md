# Feature Specification: Multi-Format Document Ingestion API

**Feature Branch**: `001-multi-format-ingestion`
**Created**: 2026-01-15
**Status**: Draft
**Input**: User description: "I want to look into the ingest api and i want u to design it to take html, markdown, pdf, word, plain text, and images. and embedd them to ask at them and chunk them in the best way. ultrathink"

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Upload and Query PDF Documents (Priority: P1)

A data analyst has a collection of Arabic PDF research reports and wants to ask questions about them using natural language queries. They need to upload PDFs and immediately start querying the content without manual text extraction.

**Why this priority**: PDFs are the most common document format for professional and academic content. Supporting PDF ingestion enables the core use case for 80% of potential users and delivers immediate value. The existing codebase already has PDF handling infrastructure (PDFCleaner, PDFAwareChunker), making this the fastest path to MVP.

**Independent Test**: Can be fully tested by uploading a multi-page Arabic PDF, asking domain-specific questions, and verifying accurate answers with source attribution. Delivers standalone value even before other formats are supported.

**Acceptance Scenarios**:

1. **Given** a user has a 20-page Arabic PDF research report, **When** they upload the PDF via the API, **Then** the system extracts all text, chunks it intelligently (respecting sections and tables), creates embeddings, and confirms successful ingestion with chunk count
2. **Given** a PDF document has been ingested, **When** the user asks a question related to content on page 15, **Then** the system retrieves relevant chunks and returns an accurate answer with page number attribution
3. **Given** a PDF contains both Arabic and English text mixed together, **When** the document is ingested, **Then** the system preserves both languages and can answer questions in either language
4. **Given** a PDF has tables with numerical data, **When** the document is ingested, **Then** tables are preserved as intact chunks and can be accurately retrieved for data-related queries

---

### User Story 2 - Process HTML Web Content (Priority: P2)

A content curator regularly saves web articles as HTML files and wants to build a searchable knowledge base from these articles, preserving important formatting and structure.

**Why this priority**: HTML is the native format for web content, and many users want to archive and search web articles, blog posts, and documentation. Supporting HTML enables use cases like personal knowledge management and web scraping pipelines.

**Independent Test**: Can be fully tested by uploading an HTML file with headings, paragraphs, lists, and links, then verifying that the text content is extracted cleanly without HTML tags polluting the results.

**Acceptance Scenarios**:

1. **Given** an HTML file with article content including headings, paragraphs, and lists, **When** the file is uploaded, **Then** text content is extracted (removing HTML tags and scripts) while preserving semantic structure through chunking boundaries
2. **Given** an HTML page with Arabic content and right-to-left formatting, **When** the file is ingested, **Then** text direction markers are removed but content is preserved correctly
3. **Given** an HTML file with embedded JavaScript and CSS, **When** the file is processed, **Then** only the meaningful text content is extracted and code blocks are excluded
4. **Given** an HTML document with complex nested tables, **When** the file is ingested, **Then** table data is extracted in a linearized format that preserves row-column relationships

---

### User Story 3 - Import Markdown Documentation (Priority: P3)

A technical writer maintains documentation in Markdown format and wants to make it searchable through the RAG system for an AI-powered documentation assistant.

**Why this priority**: Markdown is the standard for technical documentation, README files, and developer resources. Supporting Markdown enables technical teams to integrate their existing documentation directly without conversion.

**Independent Test**: Can be fully tested by uploading a Markdown file with headers, code blocks, and bullet lists, then querying for specific sections and verifying that structure is preserved in responses.

**Acceptance Scenarios**:

1. **Given** a Markdown file with hierarchical headers (H1-H6), **When** the file is uploaded, **Then** headers define section boundaries for intelligent chunking and are preserved in metadata
2. **Given** Markdown content with code blocks (fenced with \`\`\`), **When** the file is ingested, **Then** code blocks are extracted as separate content type and can be retrieved distinctly from regular text
3. **Given** a Markdown file with bullet lists and numbered lists, **When** the file is processed, **Then** list structure is preserved and lists are treated as cohesive units during chunking
4. **Given** a Markdown document with inline links and images, **When** the file is ingested, **Then** link text is extracted but URLs are preserved in metadata for reference

---

### User Story 4 - Upload Microsoft Word Documents (Priority: P3)

A business analyst has reports and proposals in Word format (.docx) and wants to make them searchable without converting to PDF or other formats first.

**Why this priority**: Word documents are ubiquitous in business environments but often overlooked by technical systems. Supporting Word enables enterprise adoption and non-technical user onboarding without requiring format conversion.

**Independent Test**: Can be fully tested by uploading a .docx file with multiple sections, styles, and embedded tables, then verifying content is extracted correctly with formatting indicators preserved in metadata.

**Acceptance Scenarios**:

1. **Given** a Word document (.docx) with styled headings and body text, **When** the file is uploaded, **Then** text is extracted with heading structure detected for section-aware chunking
2. **Given** a Word document with embedded tables and charts, **When** the file is ingested, **Then** table content is extracted (charts are skipped with a warning) and tables are preserved as cohesive chunks
3. **Given** a Word document with track changes and comments, **When** the file is processed, **Then** only the accepted text is extracted and metadata indicates if tracked changes were present
4. **Given** a legacy .doc file (older Word format), **When** the file is uploaded, **Then** the system either converts and processes it or returns a clear error message indicating format not supported

---

### User Story 5 - Ingest Plain Text Files (Priority: P1)

A researcher has a collection of plain text files containing notes, transcripts, and raw data that need to be searchable through the RAG system without any format conversion.

**Why this priority**: Plain text is the most universal and simplest format, requiring no parsing or extraction overhead. It's commonly used for notes, logs, transcripts, and data exports. Supporting TXT ensures the system can handle the most fundamental document type and serves as a baseline for all other formats. This is essential for MVP completeness.

**Independent Test**: Can be fully tested by uploading a plain text file with Arabic and English content, querying specific facts, and verifying accurate retrieval without any encoding or formatting issues.

**Acceptance Scenarios**:

1. **Given** a plain text file with UTF-8 encoded Arabic content, **When** the file is uploaded, **Then** the system ingests the text directly without any preprocessing and creates appropriately sized chunks
2. **Given** a large text file (>5MB) with continuous prose, **When** the file is uploaded, **Then** the system applies sentence-aware chunking to maintain semantic coherence across chunk boundaries
3. **Given** a text file with mixed encodings (UTF-8, Windows-1256), **When** the file is uploaded, **Then** the system automatically detects and converts the encoding to UTF-8 for consistent storage
4. **Given** a plain text file with structured content (numbered sections, bullet points using ASCII characters), **When** the file is ingested, **Then** the system preserves the structure through intelligent chunking that respects line breaks and formatting patterns

---

### User Story 6 - Extract Text and Descriptions from Images via Vision LLM (Priority: P2)

A legal team has scanned documents and photographs of handwritten notes that need to be digitized and made searchable through the RAG system. They also have charts and diagrams that need meaningful descriptions for retrieval.

**Why this priority**: Many valuable documents exist only as images - scanned papers, photographs of whiteboards, screenshots, charts, and digitized archives. Using a Vision Language Model (vLLM) provides superior text extraction compared to traditional OCR, especially for Arabic text, and can generate semantic descriptions for non-text visual content. This is particularly important for Arabic documents where physical archives are common.

**Independent Test**: Can be fully tested by uploading an image containing both printed and handwritten Arabic text, verifying that vLLM extracts the text accurately, and confirming the extracted text is searchable. Additionally, test with charts/diagrams to verify meaningful descriptions are generated.

**Acceptance Scenarios**:

1. **Given** a scanned image of a printed Arabic document (JPEG, PNG, TIFF), **When** the file is uploaded, **Then** the system uses the vision LLM to extract text, ingests the extracted text with metadata indicating vLLM source, and reports extraction quality
2. **Given** an image with mixed Arabic and English text in multiple columns, **When** the file is uploaded, **Then** the vLLM detects the layout, preserves reading order (right-to-left for Arabic, left-to-right for English), and extracts text maintaining column boundaries
3. **Given** a low-quality image (blurry, skewed, poor lighting), **When** the file is uploaded, **Then** the system processes through vLLM which handles visual noise gracefully and reports quality warnings if extraction is uncertain
4. **Given** a multi-page image file (TIFF, PDF with scanned pages), **When** the file is uploaded, **Then** the system processes each page separately through vLLM, extracts text from all pages, and preserves page boundaries in metadata for attribution
5. **Given** an image file that contains no text but has visual content (photo, diagram, chart), **When** the file is uploaded, **Then** the vLLM generates a semantic description of the visual content that can be embedded and searched

---

### Edge Cases

- **What happens when a file has no extractable text** (e.g., image-only PDF, empty document)?
  - For text-based formats: System returns validation error indicating zero text extracted
  - For images: System uses vLLM to generate a semantic description of the visual content instead, making it searchable
- **How does system handle very large files** (e.g., 100MB PDF, 50MB Word document)?
  - System enforces file size limits (e.g., 25MB max) and returns clear error if exceeded
- **What happens when file format detection fails** (e.g., corrupted file, wrong extension)?
  - System attempts automatic format detection by content inspection; if both extension and content detection fail, returns format error with guidance
- **How does system handle files with mixed languages** (Arabic, English, French)?
  - System treats all languages equally during chunking and embedding; metadata indicates detected languages. For images, vLLM handles multi-language text extraction natively without explicit language configuration 
- **How does system handle password-protected or encrypted files**?
  - System returns error indicating file is encrypted and cannot be processed; user must provide decrypted version
- **What happens when the same file is uploaded multiple times**?
  - System treats each upload as separate ingestion unless deduplication is explicitly enabled (default: allow duplicates with warning in response)
- **How does system handle files with non-UTF-8 encoding**?
  - System attempts automatic encoding detection and conversion to UTF-8; if detection fails, defaults to UTF-8 with error markers for invalid sequences
- **What happens when vLLM extraction quality is uncertain** (e.g., heavily degraded or handwritten text)?
  - vLLM provides best-effort extraction with quality indicators in metadata; system ingests the content but flags uncertainty, allowing users to review and improve source images if needed
- **How does system handle images with extremely high resolution** (e.g., 50MB TIFF scans)?
  - System enforces file size limit (25MB) and suggests image compression or downsampling; for processing, images are automatically downsampled to optimal OCR resolution (300 DPI) while preserving quality
- **What happens when an image has text in unsupported languages or scripts**?
  - vLLM attempts extraction for any language/script; multi-lingual models handle diverse text natively. For less common scripts, extraction accuracy may vary and metadata indicates detected content
- **How does system handle mixed content** (image contains both text and non-text elements like charts, diagrams)?
  - vLLM processes the entire image holistically, extracting text where present and generating semantic descriptions of visual elements (charts, diagrams, photos), enabling comprehensive search across all content types 
## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: System MUST accept file uploads in the following formats: PDF (.pdf), HTML (.html, .htm), Markdown (.md, .markdown), Microsoft Word (.docx), Plain Text (.txt), and Image files (.jpg, .jpeg, .png, .tiff, .tif, .bmp, .webp)
- **FR-002**: System MUST automatically detect file format from both file extension and content inspection (magic number/MIME type detection) when extension is ambiguous or missing
- **FR-003**: System MUST extract plain text content from each supported format while removing format-specific artifacts (HTML tags, PDF headers/footers, Word formatting codes); for images, use the existing vLLM integration to extract text and/or generate semantic descriptions
- **FR-004**: System MUST preserve document structure in metadata (sections, headings, page numbers, content type) to enable structure-aware chunking and retrieval
- **FR-005**: System MUST apply format-specific chunking strategies: sentence-aware for plain text/HTML/Markdown, structure-aware for PDF (respecting sections/tables) and Word documents (respecting heading hierarchy), and content-aware for vLLM-extracted image text (chunking based on logical segments identified by the vision model)
- **FR-006**: System MUST generate embeddings for all extracted text chunks using the existing BGE-M3 embedding model (1024 dimensions) configured in the codebase
- **FR-007**: System MUST store chunks and embeddings in Qdrant vector database with metadata including: original filename, file format, chunk index, content type, and format-specific metadata (e.g., page number for PDF, heading level for Markdown/Word, element type for HTML, extraction type for images: text vs description)
- **FR-008**: System MUST validate file size before processing, rejecting files larger than 25MB with clear error message indicating size limit
- **FR-009**: System MUST validate file integrity and format correctness, returning specific error messages for corrupted files, malformed markup, or unreadable formats
- **FR-010**: System MUST return ingestion summary including: total documents processed, total chunks created, format breakdown, and processing time
- **FR-011**: System MUST support batch upload of multiple files in a single API request, processing them sequentially or in parallel (default: sequential to prevent memory issues)
- **FR-012**: System MUST handle encoding detection and conversion automatically, supporting UTF-8, UTF-16, ISO-8859-1, and Windows-1256 (Arabic) encodings with fallback to UTF-8
- **FR-013**: System MUST preserve bidirectional text (Arabic RTL, English LTR) correctly during extraction without introducing formatting markers in the stored content
- **FR-014**: Users MUST be able to specify optional metadata (custom tags, source attribution, creation date) per file upload that is stored alongside chunk metadata
- **FR-015**: System MUST provide format-specific extraction options via API parameters (e.g., `preserve_tables=true` for PDF, `extract_code_blocks=true` for Markdown, `include_styles=false` for Word, `image_mode='text'|'description'|'auto'` for images to control vLLM extraction behavior)
- **FR-016**: System MUST log all ingestion operations with details including: file hash, processing time, chunk count, and any warnings or errors for debugging and audit trails
- **FR-017**: For image files, system MUST use the existing vLLM integration to process images, extracting text (for document images) or generating semantic descriptions (for photos, charts, diagrams) based on automatic content detection or user-specified mode
- **FR-018**: System MUST leverage vLLM's native vision capabilities to handle image quality issues (blur, skew, noise) without requiring separate preprocessing pipelines
- **FR-019**: System MUST include image extraction metadata indicating: extraction type (text/description/mixed), content detected (document/chart/photo/diagram), and processing model used
- **FR-020**: For plain text files, system MUST detect encoding automatically from common formats (UTF-8, UTF-16, Windows-1256, ISO-8859-1) and convert to UTF-8 for consistent storage and retrieval
- **FR-021**: System MUST detect and handle multi-page image formats (multi-page TIFF, scanned PDFs) by processing each page separately through vLLM and preserving page boundaries in metadata
- **FR-022**: For images where vLLM indicates low extraction quality or uncertainty, system MUST include quality warnings in the ingestion response and metadata

### Key Entities *(include if feature involves data)*

- **DocumentUpload**: Represents a file upload request containing the file binary, filename, format (optional), and custom metadata; tracks upload timestamp and user identification (if available)
- **ExtractedDocument**: Represents processed document content after format-specific extraction, containing cleaned text, detected structure metadata (sections, tables, lists), and original source reference
- **TextChunk**: Represents a segmented piece of document text, containing the chunk content (plain text), chunk index/position, parent document reference, content type classification (table, list, heading, text), and chunking strategy applied
- **ChunkEmbedding**: Represents vector representation of a text chunk, containing 1024-dimensional BGE-M3 embedding vector, pointer to source chunk, and generation timestamp
- **IngestionJob**: Represents the processing workflow for one or more uploaded files, tracking processing status (pending, processing, completed, failed), file count, chunk count, start/end time, and error logs
- **FormatMetadata**: Format-specific metadata extracted during processing; for PDF: page numbers, section headers, table boundaries; for HTML: heading hierarchy, link references, DOM element types; for Markdown: code block language, list types, heading levels; for Word: style information, document properties, heading hierarchy; for Images: extraction type (text/description), content classification (document/chart/photo/diagram), vLLM model used; for Plain Text: detected encoding, line ending style, structure indicators (numbered sections, bullet points)
- **VLLMExtractionResult**: Represents content extracted from an image via vision LLM, containing extracted text and/or semantic description, content type classification, extraction mode used (text/description/auto), and quality indicators
- **ImageMetadata**: Represents image-specific information including original resolution, color depth, format, file size, detected content type (document/chart/photo/diagram), and extraction approach used

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Users can upload a 10-page Arabic PDF and receive successful ingestion confirmation within 15 seconds
- **SC-002**: System correctly extracts text from all 6 supported format categories (PDF, HTML, Markdown, Word, Plain Text, Images) with >98% accuracy for digital formats and >85% accuracy for OCR from printed images (measured by manual review of sample documents)
- **SC-003**: Queries against ingested multi-format documents return relevant answers with source attribution in <2 seconds for 95% of queries
- **SC-004**: System handles batches of 10 mixed-format files (total <50MB) without errors or timeouts
- **SC-005**: Structure-aware chunking improves retrieval accuracy by 8-12% compared to fixed-size chunking for PDF and HTML documents (measured through evaluation test suite)
- **SC-006**: 90% of uploaded files are processed successfully on first attempt; files that fail return actionable error messages that enable users to fix issues
- **SC-007**: System throughput supports at least 100 document uploads per hour under normal load conditions
- **SC-008**: Format detection correctly identifies file type in >99% of cases even when file extension is wrong or missing
- **SC-009**: Zero data loss during ingestion process - all extractable text content from source files is preserved in vector database
- **SC-010**: Ingestion API has <1% error rate in production over 30-day rolling window
- **SC-011**: vLLM image processing for standard-quality scanned documents completes within 10 seconds per image with accurate text extraction (leveraging existing vLLM infrastructure)
- **SC-012**: Plain text files with common encodings (UTF-8, Windows-1256) are detected and ingested correctly 100% of the time
- **SC-013**: For images without text (photos, charts, diagrams), vLLM generates useful semantic descriptions that enable relevant search results in >90% of test queries
- **SC-014**: Mixed-language images (Arabic/English) are processed correctly with both languages accurately extracted in >95% of test cases
