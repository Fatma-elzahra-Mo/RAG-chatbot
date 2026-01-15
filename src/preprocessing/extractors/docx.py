"""
Word (.docx) extractor using python-docx.

Extracts text from Word documents with heading style detection, table preservation,
and track changes handling. Rejects legacy .doc format with clear guidance.
"""

import hashlib
import io
from typing import Any, BinaryIO

from docx import Document
from docx.oxml.text.paragraph import CT_P
from docx.oxml.table import CT_Tbl
from docx.table import Table
from docx.text.paragraph import Paragraph
from loguru import logger

from src.models.schemas import ContentType, ExtractionResult
from src.preprocessing.extractors.base import BaseExtractor


class WordExtractor(BaseExtractor):
    """
    Extract text and metadata from Word (.docx) documents.

    Features:
    - Heading style detection (Heading 1, Heading 2, etc.)
    - Table extraction as cohesive chunks
    - Track changes detection (extracts accepted text only)
    - Rejects legacy .doc format with clear error
    - Comprehensive metadata (style names, table indices, track changes flags)
    """

    def __init__(
        self,
        preserve_tables: bool = True,
        extract_headings: bool = True,
        handle_track_changes: bool = True,
    ):
        """
        Initialize Word extractor.

        Args:
            preserve_tables: Keep tables as cohesive chunks (default: True)
            extract_headings: Detect and track heading styles (default: True)
            handle_track_changes: Process track changes (accept only) (default: True)
        """
        self.preserve_tables = preserve_tables
        self.extract_headings = extract_headings
        self.handle_track_changes = handle_track_changes

    def extract(
        self, file_content: BinaryIO, filename: str, **options: Any
    ) -> ExtractionResult:
        """
        Extract text and metadata from Word (.docx) file.

        Pipeline:
        1. Validate file format (reject .doc)
        2. Load document using python-docx
        3. Detect heading styles and structure
        4. Extract tables as cohesive chunks
        5. Handle track changes (extract accepted text only)
        6. Compile comprehensive metadata

        Args:
            file_content: Binary Word file stream
            filename: Original filename
            **options: Additional options:
                - preserve_tables: bool (override instance setting)
                - extract_headings: bool (override instance setting)

        Returns:
            ExtractionResult with:
                - text: Extracted text with structure preserved
                - content_type: Primary content type (TEXT, HEADING, or TABLE)
                - metadata: Comprehensive Word metadata including:
                    - has_headings: bool
                    - has_tables: bool
                    - has_track_changes: bool
                    - heading_count: int
                    - table_count: int
                    - headings: list of heading info
                    - tables: list of table info
                - quality_indicators: Quality metrics
                - warnings: Any issues encountered

        Raises:
            ValueError: If file is legacy .doc format or corrupted
        """
        warnings = []

        # Calculate file hash
        file_content.seek(0)
        file_bytes = file_content.read()
        file_hash = hashlib.sha256(file_bytes).hexdigest()
        file_content.seek(0)

        metadata = {
            "source": filename,
            "source_format": "docx",
            "file_hash": file_hash,
            "file_size_bytes": len(file_bytes),
        }

        # Check for legacy .doc format (OLE/CFB header)
        if len(file_bytes) >= 8 and file_bytes[:8] == b"\xd0\xcf\x11\xe0\xa1\xb1\x1a\xe1":
            error_msg = (
                "Legacy .doc format is not supported. "
                "Please convert to .docx format using Microsoft Word "
                "(File > Save As > Word Document (.docx)) or online converters."
            )
            warnings.append(error_msg)
            logger.warning(f"Rejected legacy .doc file: {filename}")
            return ExtractionResult(
                text="",
                content_type=ContentType.TEXT,
                metadata=metadata,
                warnings=warnings,
            )

        try:
            # Load Word document
            doc = Document(io.BytesIO(file_bytes))

            # Track document structure
            headings_list = []
            tables_list = []
            paragraphs_list = []
            has_track_changes = False

            # Extract content while preserving structure
            text_parts = []
            table_index = 0

            # Iterate through document body elements (paragraphs and tables)
            for element in doc.element.body:
                if isinstance(element, CT_P):
                    # Paragraph element
                    para = Paragraph(element, doc)
                    para_text = para.text.strip()

                    # Check for track changes in paragraph
                    if self.handle_track_changes:
                        if self._has_track_changes(para):
                            has_track_changes = True
                        # Extract only accepted text (skip deletions)
                        para_text = self._get_accepted_text(para)

                    if not para_text:
                        continue

                    # Detect heading style
                    style_name = para.style.name if para.style else "Normal"

                    # Also check raw style value from XML (for minimal Word files without styles.xml)
                    raw_style_val = None
                    if para._element.pPr is not None:
                        pStyle_elem = para._element.pPr.find(".//{http://schemas.openxmlformats.org/wordprocessingml/2006/main}pStyle")
                        if pStyle_elem is not None:
                            raw_style_val = pStyle_elem.get("{http://schemas.openxmlformats.org/wordprocessingml/2006/main}val")

                    # Use raw style value if available, otherwise use detected style name
                    effective_style = raw_style_val if raw_style_val else style_name

                    if self.extract_headings and "heading" in effective_style.lower():
                        # Extract heading level (e.g., "Heading 1" or "Heading1" -> 1)
                        try:
                            # Handle both "Heading 1" and "Heading1" formats
                            heading_part = effective_style.lower().replace("heading", "").strip()
                            level = int(heading_part) if heading_part else 1
                        except ValueError:
                            level = 1

                        headings_list.append({
                            "text": para_text,
                            "level": level,
                            "style_name": effective_style,
                        })

                        # Add heading with marker
                        text_parts.append(f"\n# {para_text}\n")
                    else:
                        # Regular paragraph
                        paragraphs_list.append({
                            "text": para_text,
                            "style_name": style_name,
                        })
                        text_parts.append(para_text)

                elif isinstance(element, CT_Tbl):
                    # Table element
                    table = Table(element, doc)
                    table_text = self._extract_table_text(table)

                    if table_text.strip():
                        tables_list.append({
                            "table_index": table_index,
                            "row_count": len(table.rows),
                            "col_count": len(table.columns) if table.rows else 0,
                            "text": table_text,
                        })

                        if self.preserve_tables:
                            # Add table as cohesive chunk with markers
                            text_parts.append(f"\n[TABLE {table_index}]\n{table_text}\n[/TABLE]\n")
                        else:
                            text_parts.append(table_text)

                        table_index += 1

            # Combine all text
            full_text = "\n".join(text_parts)

            # Update metadata
            metadata.update({
                "has_headings": len(headings_list) > 0,
                "heading_count": len(headings_list),
                "headings": headings_list,
                "has_tables": len(tables_list) > 0,
                "table_count": len(tables_list),
                "tables": tables_list,
                "paragraph_count": len(paragraphs_list),
                "has_track_changes": has_track_changes,
            })

            # Determine content type
            content_type = self._determine_content_type(metadata)

            # Calculate quality indicators
            quality_indicators = {
                "text_length": len(full_text),
                "heading_count": len(headings_list),
                "table_count": len(tables_list),
                "paragraph_count": len(paragraphs_list),
                "char_count": len(full_text),
                "has_track_changes": has_track_changes,
            }

            # Warnings
            if has_track_changes:
                warnings.append(
                    "Document contains track changes. Only accepted text is extracted."
                )

            if len(full_text.strip()) == 0:
                warnings.append("No extractable text found in Word document.")

            logger.info(
                f"Extracted Word document: {filename} "
                f"({len(headings_list)} headings, {len(tables_list)} tables, "
                f"{len(paragraphs_list)} paragraphs)"
            )

            return ExtractionResult(
                text=full_text,
                content_type=content_type,
                metadata=metadata,
                quality_indicators=quality_indicators,
                warnings=warnings,
            )

        except Exception as e:
            error_msg = f"Word extraction failed: {str(e)}"
            logger.error(f"{error_msg} for file: {filename}")
            warnings.append(error_msg)

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
            True if format is 'docx', False otherwise
        """
        return file_format.lower() == "docx"

    def _extract_table_text(self, table: Table) -> str:
        """
        Extract text from table in a structured format.

        Args:
            table: python-docx Table object

        Returns:
            Formatted table text with rows separated by newlines
        """
        table_lines = []

        for row in table.rows:
            cells = [cell.text.strip() for cell in row.cells]
            # Join cells with tab separator for structure
            row_text = "\t".join(cells)
            if row_text.strip():
                table_lines.append(row_text)

        return "\n".join(table_lines)

    def _has_track_changes(self, paragraph: Paragraph) -> bool:
        """
        Check if paragraph contains track changes (insertions/deletions).

        Args:
            paragraph: python-docx Paragraph object

        Returns:
            True if track changes are present
        """
        # Check for deletion (w:del) or insertion (w:ins) elements
        has_del = len(paragraph._element.findall(".//{http://schemas.openxmlformats.org/wordprocessingml/2006/main}del")) > 0
        has_ins = len(paragraph._element.findall(".//{http://schemas.openxmlformats.org/wordprocessingml/2006/main}ins")) > 0

        return has_del or has_ins

    def _get_accepted_text(self, paragraph: Paragraph) -> str:
        """
        Extract only accepted text from paragraph (skip deletions).

        Args:
            paragraph: python-docx Paragraph object

        Returns:
            Text with deletions removed and insertions included
        """
        # python-docx's paragraph.text already excludes deleted text
        # and includes inserted text, so we can use it directly
        return paragraph.text.strip()

    def _determine_content_type(self, metadata: dict) -> ContentType:
        """
        Determine primary content type based on document structure.

        Args:
            metadata: Document metadata

        Returns:
            Primary content type
        """
        has_tables = metadata.get("has_tables", False)
        has_headings = metadata.get("has_headings", False)
        table_count = metadata.get("table_count", 0)
        heading_count = metadata.get("heading_count", 0)
        paragraph_count = metadata.get("paragraph_count", 0)

        # Prioritize based on dominant structure
        if has_tables and table_count > paragraph_count / 2:
            return ContentType.TABLE

        if has_headings and heading_count > 0:
            return ContentType.HEADING

        return ContentType.TEXT
