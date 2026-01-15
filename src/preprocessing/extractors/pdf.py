"""
PDF extractor using pypdf and existing PDFCleaner/PDFAwareChunker.

Wraps existing PDF processing infrastructure to conform to BaseExtractor interface.
Integrates PDFCleaner for artifact removal and PDFAwareChunker for structure-aware
intelligent chunking with table preservation.
"""

import hashlib
import io
from typing import Any, BinaryIO

from langchain_core.documents import Document
from loguru import logger
from pypdf import PdfReader

from src.models.schemas import ContentType, ExtractionResult
from src.preprocessing.extractors.base import BaseExtractor
from src.preprocessing.pdf_chunker import PDFAwareChunker
from src.preprocessing.pdf_cleaner import PDFCleaner


class PDFExtractor(BaseExtractor):
    """
    Extract text and metadata from PDF documents with structure-aware chunking.

    Uses pypdf for text extraction and integrates with:
    - PDFCleaner: Removes headers, footers, page numbers, and artifacts
    - PDFAwareChunker: Performs structure-aware chunking with table preservation

    Features:
    - Extracts page numbers and section headers
    - Preserves tables as intact chunks when possible
    - Respects document structure (sections, lists, tables)
    - Handles corrupted PDFs and empty pages gracefully
    - Provides comprehensive quality indicators
    """

    def __init__(
        self,
        clean_artifacts: bool = True,
        extract_metadata: bool = True,
        preserve_tables: bool = True,
        respect_headers: bool = True,
        use_dynamic_sizing: bool = True,
        max_chunk_size: int = 350,
        chunk_overlap: int = 100,
    ):
        """
        Initialize PDF extractor.

        Args:
            clean_artifacts: Apply PDF cleaning (page numbers, headers/footers, etc.)
            extract_metadata: Extract PDF metadata (author, title, creation date, etc.)
            preserve_tables: Keep tables intact in single chunks when possible
            respect_headers: Treat section headers as chunk boundaries
            use_dynamic_sizing: Adjust chunk size based on content type
            max_chunk_size: Maximum characters per chunk (default: 350)
            chunk_overlap: Number of characters to overlap between chunks (default: 100)
        """
        self.clean_artifacts = clean_artifacts
        self.extract_metadata = extract_metadata
        self.preserve_tables = preserve_tables
        self.respect_headers = respect_headers
        self.use_dynamic_sizing = use_dynamic_sizing
        self.max_chunk_size = max_chunk_size
        self.chunk_overlap = chunk_overlap

        # Initialize PDF cleaner
        if self.clean_artifacts:
            self.cleaner = PDFCleaner(
                remove_page_numbers=True,
                remove_headers_footers=True,
                clean_artifacts=True,
                normalize_arabic=False,  # Keep original for embeddings
            )

        # Initialize PDF-aware chunker
        self.chunker = PDFAwareChunker(
            max_chunk_size=max_chunk_size,
            overlap=chunk_overlap,
            preserve_tables=preserve_tables,
            respect_headers=respect_headers,
            use_dynamic_sizing=use_dynamic_sizing,
            clean_pdf_artifacts=False,  # We handle cleaning separately
        )

    def extract(
        self, file_content: BinaryIO, filename: str, **options: Any
    ) -> ExtractionResult:
        """
        Extract text and metadata from PDF file with structure-aware chunking.

        Pipeline:
        1. Extract raw text from PDF using pypdf
        2. Clean PDF artifacts (if enabled) using PDFCleaner
        3. Detect document structure (tables, headers, lists)
        4. Extract page numbers and section headers
        5. Perform structure-aware chunking using PDFAwareChunker
        6. Compile metadata and quality indicators

        Args:
            file_content: Binary PDF file stream
            filename: Original filename
            **options: Additional options:
                - preserve_tables: bool (default True) - Override instance setting
                - extract_images: bool (default False, not implemented yet)
                - max_pages: int (default None) - Limit number of pages to process

        Returns:
            ExtractionResult with:
                - text: Combined chunked text with structure markers
                - content_type: Primary content type detected
                - metadata: Comprehensive PDF metadata and extraction stats
                - quality_indicators: Quality metrics for extracted content
                - warnings: Any issues encountered during extraction

        Raises:
            ValueError: If PDF is corrupted or cannot be read
            IOError: If file operations fail
        """
        warnings = []
        max_pages = options.get("max_pages", None)

        # Calculate file hash for deduplication
        file_content.seek(0)
        pdf_bytes = file_content.read()
        file_hash = hashlib.sha256(pdf_bytes).hexdigest()
        file_content.seek(0)  # Reset for pypdf

        metadata = {
            "source": filename,
            "source_format": "pdf",
            "file_hash": file_hash,
            "file_size_bytes": len(pdf_bytes),
        }

        try:
            # Read PDF using pypdf
            reader = PdfReader(io.BytesIO(pdf_bytes))

            # Extract PDF metadata
            if self.extract_metadata and reader.metadata:
                pdf_meta = reader.metadata
                metadata.update({
                    "author": pdf_meta.get("/Author", ""),
                    "title": pdf_meta.get("/Title", ""),
                    "subject": pdf_meta.get("/Subject", ""),
                    "creator": pdf_meta.get("/Creator", ""),
                    "producer": pdf_meta.get("/Producer", ""),
                    "creation_date": str(pdf_meta.get("/CreationDate", "")),
                })

            # Get total pages
            num_pages = len(reader.pages)
            metadata["num_pages_total"] = num_pages

            # Limit pages if requested
            pages_to_process = reader.pages
            if max_pages and num_pages > max_pages:
                warnings.append(
                    f"PDF has {num_pages} pages, processing only first {max_pages}"
                )
                pages_to_process = reader.pages[:max_pages]
                num_pages = max_pages

            # Extract text from all pages with page-level tracking
            full_text_parts = []
            pages_data = []

            for page_num, page in enumerate(pages_to_process, start=1):
                try:
                    page_text = page.extract_text()
                    if page_text.strip():
                        full_text_parts.append(page_text)
                        pages_data.append({
                            "page_number": page_num,
                            "text": page_text,
                            "char_count": len(page_text),
                        })
                    else:
                        warnings.append(f"Page {page_num} appears to be empty or contains only images")
                except Exception as e:
                    warnings.append(f"Failed to extract text from page {page_num}: {str(e)}")

            # Store page-level data in metadata
            metadata["pages_data"] = pages_data

            # Combine all page text
            full_text = "\n\n".join(full_text_parts)

            logger.info(f"Extracted {len(pages_data)}/{num_pages} pages from PDF: {filename}")

            if not full_text.strip():
                warnings.append("No text content extracted from PDF (may be scanned images)")
                return ExtractionResult(
                    text="",
                    content_type=ContentType.TEXT,
                    metadata=metadata,
                    warnings=warnings,
                )

            # Apply PDF cleaning if enabled
            cleaned_text = full_text
            structure = {}
            if self.clean_artifacts and self.cleaner:
                cleaned_text, cleaning_metadata = self.cleaner.clean(full_text, metadata.copy())
                metadata.update(cleaning_metadata)

                # Detect structure
                structure = self.cleaner.detect_structure(cleaned_text)
                metadata["structure"] = structure

                # Track cleaning effectiveness
                if "reduction_ratio" in cleaning_metadata:
                    if cleaning_metadata["reduction_ratio"] > 0.3:
                        warnings.append(
                            f"Significant text reduction during cleaning "
                            f"({cleaning_metadata['reduction_ratio']:.1%}). "
                            "Some content may have been headers/footers."
                        )
            else:
                # Even without cleaning, detect structure
                if self.cleaner:
                    structure = self.cleaner.detect_structure(full_text)
                    metadata["structure"] = structure

            # Extract section headers
            section_headers = self._extract_section_headers(cleaned_text, structure)
            metadata["section_headers"] = section_headers
            metadata["section_count"] = len(section_headers)

            # Determine content type based on structure
            content_type = self._determine_content_type(structure, structure.get("has_tables", False))

            # Calculate quality indicators (without chunking - pipeline handles that)
            quality_indicators = self._calculate_quality_indicators_simple(
                pages_data, num_pages, cleaned_text, full_text, structure
            )

            # Check for quality issues
            if quality_indicators.get("avg_chars_per_page", 0) < 100:
                warnings.append(
                    "Low character count per page. PDF may contain scanned images "
                    "or be poorly formatted."
                )

            empty_page_ratio = quality_indicators.get("empty_page_ratio", 0)
            if empty_page_ratio > 0.2:
                empty_count = quality_indicators.get("empty_page_count", 0)
                warnings.append(
                    f"{empty_count} of {num_pages} pages appear to be empty or "
                    "have minimal text."
                )

            return ExtractionResult(
                text=cleaned_text,
                content_type=content_type,
                metadata=metadata,
                quality_indicators=quality_indicators,
                warnings=warnings,
            )

        except Exception as e:
            # Handle extraction failures gracefully
            error_msg = f"PDF extraction failed: {str(e)}"
            logger.error(error_msg)
            warnings.append(error_msg)

            # Return empty result with error info
            return ExtractionResult(
                text="",
                content_type=ContentType.TEXT,
                metadata=metadata,
                warnings=warnings,
            )

    def supports_format(self, file_format: str) -> bool:
        """
        Check if this extractor supports the given format.

        Args:
            file_format: File format identifier

        Returns:
            True if format is 'pdf', False otherwise
        """
        return file_format.lower() == "pdf"

    def _extract_section_headers(self, text: str, structure: dict) -> list[str]:
        """
        Extract section headers from text based on structure detection.

        Args:
            text: Cleaned text
            structure: Structure information from PDFCleaner

        Returns:
            List of detected section headers
        """
        section_headers = []

        # Check if structure has header positions
        header_positions = structure.get("header_positions", [])
        if header_positions:
            lines = text.split("\n")
            for pos in header_positions:
                if 0 <= pos < len(lines):
                    section_headers.append(lines[pos].strip())

        return section_headers

    def _determine_content_type(self, structure: dict, has_tables: bool) -> ContentType:
        """
        Determine primary content type based on structure.

        Args:
            structure: Structure information
            has_tables: Whether document has tables

        Returns:
            Primary content type
        """
        if has_tables:
            return ContentType.TABLE
        elif structure.get("has_headers", False):
            return ContentType.HEADING
        else:
            return ContentType.TEXT

    def _calculate_quality_indicators(
        self,
        pages_data: list[dict],
        num_pages: int,
        cleaned_text: str,
        original_text: str,
        structure: dict,
        chunked_docs: list[Document],
    ) -> dict:
        """
        Calculate quality indicators for extraction.

        Args:
            pages_data: Page-level data
            num_pages: Total number of pages
            cleaned_text: Cleaned text
            original_text: Original text
            structure: Structure information
            chunked_docs: Chunked documents

        Returns:
            Quality indicators dictionary
        """
        empty_pages = num_pages - len(pages_data)

        quality_indicators = {
            "text_length": len(cleaned_text),
            "pages_extracted": len(pages_data),
            "pages_total": num_pages,
            "extraction_success_rate": len(pages_data) / num_pages if num_pages > 0 else 0,
            "avg_chars_per_page": sum(p["char_count"] for p in pages_data) / len(pages_data) if pages_data else 0,
            "empty_page_count": empty_pages,
            "empty_page_ratio": empty_pages / num_pages if num_pages > 0 else 0,
            "num_chunks": len(chunked_docs),
            "avg_chunk_size": len(cleaned_text) / len(chunked_docs) if chunked_docs else 0,
            "has_tables": structure.get("has_tables", False),
            "has_headers": structure.get("has_headers", False),
            "has_lists": structure.get("has_lists", False),
        }

        # Calculate text reduction ratio from cleaning
        if original_text:
            reduction = 1 - (len(cleaned_text) / len(original_text))
            quality_indicators["cleaning_reduction_ratio"] = reduction

        return quality_indicators

    def _extract_section_headers(self, text: str, structure: dict) -> list[str]:
        """
        Extract section headers from cleaned text.

        Args:
            text: Cleaned text content
            structure: Structure metadata from PDFCleaner

        Returns:
            List of detected section headers
        """
        headers = []
        header_positions = structure.get("header_positions", [])

        if not header_positions:
            return headers

        lines = text.split("\n")

        for pos in header_positions:
            if pos < len(lines):
                header_text = lines[pos].strip()
                # Filter out very short or empty headers
                if header_text and len(header_text) > 3:
                    headers.append(header_text)

        return headers

    def _determine_content_type(self, structure: dict, has_tables: bool) -> ContentType:
        """
        Determine primary content type based on document structure.

        Args:
            structure: Document structure metadata
            has_tables: Whether document contains tables

        Returns:
            Primary ContentType enum value
        """
        # Prioritize based on structure
        if has_tables and structure.get("has_tables", False):
            return ContentType.TABLE

        if structure.get("has_lists", False):
            return ContentType.LIST

        if structure.get("has_headers", False):
            return ContentType.HEADING

        return ContentType.TEXT

    def _calculate_quality_indicators_simple(
        self,
        pages_data: list[dict],
        num_pages: int,
        cleaned_text: str,
        original_text: str,
        structure: dict,
    ) -> dict[str, Any]:
        """
        Calculate extraction quality indicators (without chunking metrics).

        Args:
            pages_data: List of page-level data dictionaries
            num_pages: Total number of pages in PDF
            cleaned_text: Cleaned text content
            original_text: Original extracted text before cleaning
            structure: Document structure metadata

        Returns:
            Dictionary with quality metrics including:
                - Page extraction statistics
                - Text length and character counts
                - Structure analysis results
        """
        # Calculate page-level statistics
        empty_pages = num_pages - len(pages_data)
        total_chars = sum(p["char_count"] for p in pages_data) if pages_data else 0

        return {
            "total_pages": num_pages,
            "pages_extracted": len(pages_data),
            "empty_page_count": empty_pages,
            "empty_page_ratio": empty_pages / num_pages if num_pages > 0 else 0,
            "extraction_success_rate": len(pages_data) / num_pages if num_pages > 0 else 0,
            "avg_chars_per_page": total_chars / len(pages_data) if pages_data else 0,
            "total_chars_original": len(original_text),
            "total_chars_cleaned": len(cleaned_text),
            "cleaning_reduction_ratio": (
                (len(original_text) - len(cleaned_text)) / len(original_text)
                if len(original_text) > 0 else 0
            ),
            "has_structure": structure.get("has_headers", False) or structure.get("has_tables", False) or structure.get("has_lists", False),
            "structure_elements": {
                "tables": structure.get("has_tables", False),
                "lists": structure.get("has_lists", False),
                "headers": structure.get("has_headers", False),
            },
            "structure_counts": {
                "num_headers": structure.get("section_count", 0),
                "num_bullet_items": 0,  # Would need additional detection
                "num_numbered_items": 0,  # Would need additional detection
            },
        }
