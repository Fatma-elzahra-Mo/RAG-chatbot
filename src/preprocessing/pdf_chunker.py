"""
PDF-aware intelligent chunking for Arabic documents.

Extends sentence-aware chunking with PDF-specific structure detection:
- Respects section boundaries (headers)
- Keeps tables intact
- Preserves list hierarchy
- Dynamically adjusts chunk size based on content type
"""

import re

from langchain_core.documents import Document

from src.preprocessing.chunker import ArabicSentenceChunker
from src.preprocessing.pdf_cleaner import PDFCleaner


class PDFAwareChunker(ArabicSentenceChunker):
    """
    Intelligent chunker optimized for PDF documents.

    Extends ArabicSentenceChunker with PDF-specific features:
    - Detects and respects document structure (headers, tables, lists)
    - Dynamically adjusts chunk size based on content type
    - Preserves semantic boundaries from PDF structure
    - Extracts enhanced metadata (page numbers, sections, content type)

    This approach improves retrieval quality by maintaining document
    structure and keeping related content together.
    """

    # Content type chunk size mappings (in characters)
    CHUNK_SIZES = {
        "table": 250,  # Tables are dense, use smaller chunks
        "list": 300,  # Lists are structured, moderate size
        "header": 150,  # Headers are short, small chunks
        "text": 400,  # Regular text can use larger chunks
        "default": 350,  # Fallback size
    }

    def __init__(
        self,
        max_chunk_size: int = 350,
        overlap: int = 100,
        min_chunk_size: int = 50,
        preserve_tables: bool = True,
        preserve_lists: bool = True,
        respect_headers: bool = True,
        use_dynamic_sizing: bool = True,
        clean_pdf_artifacts: bool = True,
    ):
        """
        Initialize PDF-aware chunker.

        Args:
            max_chunk_size: Maximum characters per chunk (default for text)
            overlap: Number of characters to overlap between chunks
            min_chunk_size: Minimum characters per chunk
            preserve_tables: Keep tables intact in single chunks when possible
            preserve_lists: Maintain list structure across chunks
            respect_headers: Treat headers as chunk boundaries
            use_dynamic_sizing: Adjust chunk size based on content type
            clean_pdf_artifacts: Apply PDF cleaning before chunking
        """
        super().__init__(max_chunk_size, overlap, min_chunk_size)

        self.preserve_tables = preserve_tables
        self.preserve_lists = preserve_lists
        self.respect_headers = respect_headers
        self.use_dynamic_sizing = use_dynamic_sizing
        self.clean_pdf_artifacts = clean_pdf_artifacts

        # Initialize PDF cleaner
        self.cleaner = PDFCleaner(
            remove_page_numbers=True,
            remove_headers_footers=True,
            clean_artifacts=True,
            normalize_arabic=False,  # Keep original for embeddings
        )

    def chunk_documents(self, documents: list[Document]) -> list[Document]:
        """
        Chunk PDF documents with structure awareness.

        Enhanced pipeline:
        1. Detect PDF content (by metadata or content analysis)
        2. Clean PDF artifacts
        3. Detect document structure
        4. Apply structure-aware chunking
        5. Add enhanced metadata

        Args:
            documents: List of documents to chunk

        Returns:
            List of chunked documents with enhanced metadata

        Example:
            >>> chunker = PDFAwareChunker()
            >>> docs = [Document(page_content="PDF text...", metadata={"source": "doc.pdf"})]
            >>> chunked = chunker.chunk_documents(docs)
            >>> "content_type" in chunked[0].metadata
            True
        """
        chunked_docs = []

        for doc in documents:
            # Check if this is a PDF document
            is_pdf = self._is_pdf_document(doc)

            if is_pdf and self.clean_pdf_artifacts:
                # Clean PDF artifacts
                cleaned_text, enhanced_metadata = self.cleaner.clean(
                    doc.page_content, doc.metadata.copy()
                )

                # Detect document structure
                structure = self.cleaner.detect_structure(cleaned_text)
                enhanced_metadata["structure"] = structure

                # Create cleaned document
                doc = Document(page_content=cleaned_text, metadata=enhanced_metadata)

            # Apply structure-aware chunking
            if is_pdf:
                chunks = self._chunk_with_structure(doc)
            else:
                # Fall back to standard sentence-aware chunking
                chunks = super().chunk(doc.page_content)
                chunks = [
                    Document(
                        page_content=chunk,
                        metadata={
                            **doc.metadata,
                            "chunk_index": i,
                            "total_chunks": len(chunks),
                            "content_type": "text",
                        },
                    )
                    for i, chunk in enumerate(chunks)
                ]

            chunked_docs.extend(chunks)

        return chunked_docs

    def _is_pdf_document(self, doc: Document) -> bool:
        """
        Detect if document is from a PDF source.

        Checks metadata and content patterns to determine PDF origin.

        Args:
            doc: Document to check

        Returns:
            True if document appears to be from PDF
        """
        # Check metadata for PDF indicators
        source = doc.metadata.get("source", "").lower()
        doc_type = doc.metadata.get("document_type", "").lower()

        if source.endswith(".pdf") or doc_type == "pdf":
            return True

        # Check content for PDF-like patterns
        content = doc.page_content
        pdf_indicators = [
            r"Page\s+\d+",  # Page numbers
            r"صفحة\s+\d+",  # Arabic page numbers
            r"\|.*\|.*\|",  # Table markers
            r"[\n\r]{3,}",  # Multiple consecutive newlines (common in PDFs)
        ]

        indicator_count = sum(1 for pattern in pdf_indicators if re.search(pattern, content))

        # If 2+ indicators present, likely a PDF
        return indicator_count >= 2

    def _chunk_with_structure(self, doc: Document) -> list[Document]:
        """
        Chunk document with structure awareness.

        Respects document structure elements:
        - Headers as chunk boundaries
        - Tables kept intact
        - Lists preserved
        - Dynamic chunk sizing

        Args:
            doc: Document with detected structure metadata

        Returns:
            List of chunked documents with content type metadata
        """
        structure = doc.metadata.get("structure", {})

        # If document has headers, chunk by sections
        if self.respect_headers and structure.get("has_headers", False):
            return self._chunk_by_sections(doc)

        # If document has tables, extract and chunk them separately
        if self.preserve_tables and structure.get("has_tables", False):
            return self._chunk_with_tables(doc)

        # Fall back to enhanced sentence-aware chunking
        return self._chunk_with_dynamic_sizing(doc)

    def _chunk_by_sections(self, doc: Document) -> list[Document]:
        """
        Chunk document by detected sections (headers).

        Each section becomes a separate chunking unit, preventing
        chunks from crossing section boundaries.

        Args:
            doc: Document with header positions in metadata

        Returns:
            List of chunked documents, one per section
        """
        text = doc.page_content
        lines = text.split("\n")
        structure = doc.metadata.get("structure", {})
        header_positions = structure.get("header_positions", [])

        if not header_positions:
            # No headers detected, fall back to standard chunking
            return self._chunk_with_dynamic_sizing(doc)

        # Split into sections
        sections = []
        current_section = []
        current_header = None

        for i, line in enumerate(lines):
            if i in header_positions:
                # Save previous section
                if current_section:
                    sections.append(
                        {
                            "header": current_header,
                            "content": "\n".join(current_section),
                            "start_line": header_positions[len(sections) - 1] if sections else 0,
                        }
                    )
                # Start new section
                current_header = line.strip()
                current_section = []
            else:
                current_section.append(line)

        # Add final section
        if current_section:
            sections.append(
                {
                    "header": current_header,
                    "content": "\n".join(current_section),
                    "start_line": header_positions[-1] if header_positions else 0,
                }
            )

        # Chunk each section separately
        chunked_docs = []
        for section_idx, section in enumerate(sections):
            section_content = section["content"]

            # Determine chunk size for this section
            chunk_size = self._get_dynamic_chunk_size(section_content, "text")

            # Create temporary chunker for this section
            section_chunker = ArabicSentenceChunker(
                max_chunk_size=chunk_size, overlap=self.overlap, min_chunk_size=self.min_chunk_size
            )

            chunks = section_chunker.chunk(section_content)

            for chunk in chunks:
                chunked_doc = Document(
                    page_content=chunk,
                    metadata={
                        **doc.metadata,
                        "chunk_index": len(chunked_docs),
                        "section_index": section_idx,
                        "section_header": section["header"],
                        "content_type": "text",
                        "chunking_strategy": "section_aware",
                    },
                )
                chunked_docs.append(chunked_doc)

        return chunked_docs

    def _chunk_with_tables(self, doc: Document) -> list[Document]:
        """
        Chunk document with table extraction and preservation.

        Tables are detected and kept intact in separate chunks when possible.
        Non-table content is chunked normally.

        Args:
            doc: Document with tables

        Returns:
            List of chunked documents with table/text separation
        """
        text = doc.page_content

        # Detect table regions (simple heuristic: lines with multiple "|" or tabs)
        lines = text.split("\n")
        table_regions = []
        current_table = []
        in_table = False

        for i, line in enumerate(lines):
            is_table_line = (
                line.count("|") >= 2 or line.count("\t") >= 2 or re.match(r"^[-─]{3,}", line)
            )

            if is_table_line:
                current_table.append(line)
                in_table = True
            else:
                if in_table and current_table:
                    # End of table
                    table_regions.append(
                        {
                            "type": "table",
                            "content": "\n".join(current_table),
                            "start_line": i - len(current_table),
                            "end_line": i,
                        }
                    )
                    current_table = []
                    in_table = False

        # Add final table if exists
        if current_table:
            table_regions.append(
                {
                    "type": "table",
                    "content": "\n".join(current_table),
                    "start_line": len(lines) - len(current_table),
                    "end_line": len(lines),
                }
            )

        # If no tables found, fall back to standard chunking
        if not table_regions:
            return self._chunk_with_dynamic_sizing(doc)

        # Extract non-table text and chunk separately
        chunked_docs = []
        last_end = 0

        for table in table_regions:
            # Chunk text before this table
            if table["start_line"] > last_end:
                text_before = "\n".join(lines[last_end : table["start_line"]])
                if text_before.strip():
                    text_chunks = self._chunk_text_segment(text_before, "text", doc.metadata)
                    chunked_docs.extend(text_chunks)

            # Add table as single chunk (or split if too large)
            table_content = table["content"]
            if len(table_content) <= self.CHUNK_SIZES["table"] * 2:
                # Keep table intact
                chunked_doc = Document(
                    page_content=table_content,
                    metadata={
                        **doc.metadata,
                        "chunk_index": len(chunked_docs),
                        "content_type": "table",
                        "chunking_strategy": "table_preserved",
                    },
                )
                chunked_docs.append(chunked_doc)
            else:
                # Table too large, split by rows
                table_chunks = self._chunk_text_segment(
                    table_content, "table", doc.metadata, use_sentences=False
                )
                chunked_docs.extend(table_chunks)

            last_end = table["end_line"]

        # Chunk remaining text after last table
        if last_end < len(lines):
            text_after = "\n".join(lines[last_end:])
            if text_after.strip():
                text_chunks = self._chunk_text_segment(text_after, "text", doc.metadata)
                chunked_docs.extend(text_chunks)

        return chunked_docs

    def _chunk_with_dynamic_sizing(self, doc: Document) -> list[Document]:
        """
        Chunk with dynamic size adjustment based on content type.

        Analyzes content to determine optimal chunk size.

        Args:
            doc: Document to chunk

        Returns:
            List of chunked documents
        """
        text = doc.page_content
        content_type = self._detect_content_type(text)
        chunk_size = self._get_dynamic_chunk_size(text, content_type)

        # Create temporary chunker with dynamic size
        dynamic_chunker = ArabicSentenceChunker(
            max_chunk_size=chunk_size, overlap=self.overlap, min_chunk_size=self.min_chunk_size
        )

        chunks = dynamic_chunker.chunk(text)

        return [
            Document(
                page_content=chunk,
                metadata={
                    **doc.metadata,
                    "chunk_index": i,
                    "total_chunks": len(chunks),
                    "content_type": content_type,
                    "chunk_size_used": chunk_size,
                },
            )
            for i, chunk in enumerate(chunks)
        ]

    def _chunk_text_segment(
        self,
        text: str,
        content_type: str,
        base_metadata: dict,
        use_sentences: bool = True,
    ) -> list[Document]:
        """
        Chunk a text segment with specified content type.

        Args:
            text: Text to chunk
            content_type: Type of content (table, text, list)
            base_metadata: Base metadata to include
            use_sentences: Whether to use sentence-aware splitting

        Returns:
            List of chunked documents
        """
        chunk_size = self._get_dynamic_chunk_size(text, content_type)

        if use_sentences:
            chunker = ArabicSentenceChunker(
                max_chunk_size=chunk_size, overlap=self.overlap, min_chunk_size=self.min_chunk_size
            )
            chunks = chunker.chunk(text)
        else:
            # Split by lines for non-sentence content (tables)
            lines = text.split("\n")
            chunks = []
            current_chunk = []
            current_size = 0

            for line in lines:
                if current_size + len(line) > chunk_size and current_chunk:
                    chunks.append("\n".join(current_chunk))
                    # Keep overlap
                    if self.overlap > 0 and len(current_chunk) > 1:
                        current_chunk = current_chunk[-1:]
                        current_size = len(current_chunk[0])
                    else:
                        current_chunk = []
                        current_size = 0

                current_chunk.append(line)
                current_size += len(line)

            if current_chunk:
                chunks.append("\n".join(current_chunk))

        return [
            Document(
                page_content=chunk,
                metadata={
                    **base_metadata,
                    "content_type": content_type,
                    "chunk_size_used": chunk_size,
                },
            )
            for chunk in chunks
        ]

    def _detect_content_type(self, text: str) -> str:
        """
        Detect the type of content in text segment.

        Args:
            text: Text to analyze

        Returns:
            Content type: "table", "list", "text"
        """
        # Check for table indicators
        if text.count("|") >= 4 or text.count("\t") >= 4:
            return "table"

        # Check for list indicators
        list_patterns = [r"^\s*[-•*]", r"^\s*\d+[.)]\s", r"^\s*[٠-٩]+[.)]\s"]
        lines = text.split("\n")
        list_line_count = sum(1 for line in lines if any(re.match(p, line) for p in list_patterns))

        if list_line_count / len(lines) > 0.3:  # 30% of lines are list items
            return "list"

        return "text"

    def _get_dynamic_chunk_size(self, text: str, content_type: str) -> int:
        """
        Get optimal chunk size based on content type.

        Args:
            text: Text content
            content_type: Detected content type

        Returns:
            Optimal chunk size in characters
        """
        if not self.use_dynamic_sizing:
            return self.max_chunk_size

        # Use predefined sizes for content types
        return self.CHUNK_SIZES.get(content_type, self.CHUNK_SIZES["default"])
