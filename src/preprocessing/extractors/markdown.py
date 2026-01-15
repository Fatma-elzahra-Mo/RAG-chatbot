"""
Markdown extractor using markdown-it-py parser.

Extracts text, headers, code blocks, lists, and comprehensive metadata from
Markdown documents with structure-aware parsing and semantic chunking support.
"""

import hashlib
import re
from collections import Counter
from typing import Any, BinaryIO

from markdown_it import MarkdownIt

from src.models.schemas import ContentType, ExtractionResult
from src.preprocessing.extractors.base import BaseExtractor


class MarkdownExtractor(BaseExtractor):
    """
    Extract text and metadata from Markdown documents with structure-aware parsing.

    Features:
    - Header-based section detection and splitting
    - Code block extraction with language detection
    - List structure preservation (ordered and unordered)
    - Table detection
    - Link and image reference tracking
    - Comprehensive metadata extraction
    - Support for Arabic and mixed-language content
    """

    def __init__(self, preserve_structure: bool = True, detect_tables: bool = True):
        """
        Initialize Markdown extractor.

        Args:
            preserve_structure: Preserve markdown structure (headers, lists, code blocks)
            detect_tables: Detect and track table structures
        """
        self.preserve_structure = preserve_structure
        self.detect_tables = detect_tables

        # Initialize markdown-it parser with full features
        # Use "commonmark" preset to avoid linkify dependency
        self.md_parser = MarkdownIt("commonmark", {"typographer": True}).enable([
            "table",
            "strikethrough",
        ])

    def extract(
        self, file_content: BinaryIO, filename: str, **options: Any
    ) -> ExtractionResult:
        """
        Extract text and metadata from Markdown file.

        Pipeline:
        1. Read and decode raw content
        2. Parse markdown structure using markdown-it-py
        3. Extract headers, code blocks, lists, tables
        4. Build comprehensive metadata
        5. Detect content type based on structure
        6. Return ExtractionResult with text, metadata, and quality indicators

        Args:
            file_content: Binary file content stream
            filename: Original filename for context
            **options: Optional parameters (unused currently)

        Returns:
            ExtractionResult with extracted text, metadata, and warnings
        """
        warnings = []

        # Read and decode content
        raw_content = file_content.read()
        file_hash = hashlib.sha256(raw_content).hexdigest()

        # Decode as UTF-8 (markdown is always UTF-8)
        try:
            text = raw_content.decode("utf-8")
        except UnicodeDecodeError:
            warnings.append("File is not valid UTF-8, attempting fallback decoding")
            text = raw_content.decode("utf-8", errors="replace")

        # Handle empty file
        if not text or text.strip() == "":
            warnings.append("File is empty or contains only whitespace")
            return ExtractionResult(
                text="",
                content_type=ContentType.TEXT,
                metadata={
                    "source_format": "markdown",
                    "file_hash": file_hash,
                    "file_size_bytes": len(raw_content),
                },
                warnings=warnings,
            )

        # Parse markdown structure
        tokens = self.md_parser.parse(text)

        # Extract structure metadata (using tokens directly)
        metadata = self._build_metadata(text, tokens, raw_content, file_hash)

        # Detect content type
        content_type = self._detect_content_type(metadata)

        # Build quality indicators
        quality_indicators = self._build_quality_indicators(metadata, warnings)

        return ExtractionResult(
            text=text,
            content_type=content_type,
            metadata=metadata,
            quality_indicators=quality_indicators,
            warnings=warnings,
        )

    def supports_format(self, file_format: str) -> bool:
        """
        Check if this extractor supports the given format.

        Args:
            file_format: File format identifier

        Returns:
            True if format is 'markdown' or 'md', False otherwise
        """
        return file_format.lower() in ["markdown", "md"]

    def _build_metadata(
        self, text: str, tokens: list, raw_content: bytes, file_hash: str
    ) -> dict[str, Any]:
        """
        Build comprehensive metadata from parsed markdown tokens.

        Args:
            text: Decoded text content
            tokens: Parsed markdown tokens
            raw_content: Raw bytes
            file_hash: SHA256 hash of file

        Returns:
            Dictionary with comprehensive metadata
        """
        metadata = {
            "source_format": "markdown",
            "file_hash": file_hash,
            "file_size_bytes": len(raw_content),
            "line_count": text.count("\n") + 1,
            "char_count": len(text),
        }

        # Extract headers from tokens
        header_info = self._extract_header_info_from_tokens(tokens)
        metadata.update(header_info)

        # Extract code blocks from tokens
        code_info = self._extract_code_block_info_from_tokens(tokens)
        metadata.update(code_info)

        # Extract lists from tokens
        list_info = self._extract_list_info_from_tokens(tokens)
        metadata.update(list_info)

        # Extract tables from tokens
        if self.detect_tables:
            table_info = self._extract_table_info_from_tokens(tokens)
            metadata.update(table_info)

        # Extract links and images from tokens
        link_info = self._extract_link_info_from_tokens(tokens)
        metadata.update(link_info)

        # Count sections (top-level headers)
        if metadata.get("num_h1_headers", 0) > 0 or metadata.get("num_h2_headers", 0) > 0:
            metadata["num_sections"] = (
                metadata.get("num_h1_headers", 0) + metadata.get("num_h2_headers", 0)
            )

        return metadata

    def _extract_header_info_from_tokens(self, tokens: list) -> dict[str, Any]:
        """Extract header information from token stream."""
        header_levels = []
        level_counts = {"h1": 0, "h2": 0, "h3": 0, "h4": 0, "h5": 0, "h6": 0}
        
        for token in tokens:
            if token.type == "heading_open":
                level = int(token.tag[1])
                header_levels.append(level)
                level_counts[f"h{level}"] += 1
        
        if not header_levels:
            return {
                "has_headers": False,
                "num_h1_headers": 0,
                "num_h2_headers": 0,
                "num_h3_headers": 0,
                "num_h4_headers": 0,
                "num_h5_headers": 0,
                "num_h6_headers": 0,
            }
        
        return {
            "has_headers": True,
            "num_h1_headers": level_counts["h1"],
            "num_h2_headers": level_counts["h2"],
            "num_h3_headers": level_counts["h3"],
            "num_h4_headers": level_counts["h4"],
            "num_h5_headers": level_counts["h5"],
            "num_h6_headers": level_counts["h6"],
            "min_header_level": min(header_levels),
            "max_header_level": max(header_levels),
        }

    def _extract_code_block_info_from_tokens(self, tokens: list) -> dict[str, Any]:
        """Extract code block information from token stream."""
        code_blocks = []
        languages = []
        has_inline_code = False

        for token in tokens:
            if token.type == "fence":
                code_blocks.append(token)
                if token.info:
                    lang = token.info.strip().split()[0]
                    if lang:
                        languages.append(lang.lower())
            elif token.type == "code_inline":
                has_inline_code = True
            # Check children for inline code
            if token.children:
                for child in token.children:
                    if child.type == "code_inline":
                        has_inline_code = True

        if not code_blocks:
            return {
                "has_code_blocks": False,
                "num_code_blocks": 0,
                "code_languages": [],
                "has_inline_code": has_inline_code,
            }

        return {
            "has_code_blocks": True,
            "num_code_blocks": len(code_blocks),
            "code_languages": list(set(languages)),
            "has_inline_code": has_inline_code,
        }

    def _extract_list_info_from_tokens(self, tokens: list) -> dict[str, Any]:
        """Extract list information from token stream."""
        ordered_lists = 0
        unordered_lists = 0
        has_nested = False
        list_stack = []
        
        for token in tokens:
            if token.type == "ordered_list_open":
                ordered_lists += 1
                if list_stack:
                    has_nested = True
                list_stack.append("ol")
            elif token.type == "bullet_list_open":
                unordered_lists += 1
                if list_stack:
                    has_nested = True
                list_stack.append("ul")
            elif token.type in ("ordered_list_close", "bullet_list_close"):
                if list_stack:
                    list_stack.pop()
        
        if ordered_lists == 0 and unordered_lists == 0:
            return {
                "has_lists": False,
                "num_ordered_lists": 0,
                "num_unordered_lists": 0,
                "has_nested_lists": False,
            }
        
        return {
            "has_lists": True,
            "num_ordered_lists": ordered_lists,
            "num_unordered_lists": unordered_lists,
            "has_nested_lists": has_nested,
        }

    def _extract_table_info_from_tokens(self, tokens: list) -> dict[str, Any]:
        """Extract table information from token stream."""
        tables = 0
        
        for token in tokens:
            if token.type == "table_open":
                tables += 1
        
        return {
            "has_tables": tables > 0,
            "num_tables": tables,
        }

    def _extract_link_info_from_tokens(self, tokens: list) -> dict[str, Any]:
        """Extract link and image information from token stream."""
        links = 0
        images = 0

        for token in tokens:
            if token.type == "link_open":
                links += 1
            elif token.type == "image":
                images += 1
            # Also check children (for inline tokens)
            if token.children:
                for child in token.children:
                    if child.type == "link_open":
                        links += 1
                    elif child.type == "image":
                        images += 1

        return {
            "has_links": links > 0,
            "num_links": links,
            "has_images": images > 0,
            "num_images": images,
        }
    def _detect_content_type(self, metadata: dict[str, Any]) -> ContentType:
        """
        Detect content type based on structural metadata.

        Prioritizes:
        1. CODE - if document is primarily code blocks
        2. HEADING - if document has clear header structure
        3. LIST - if document is primarily lists
        4. TABLE - if document has tables
        5. TEXT - default fallback

        Args:
            metadata: Extracted metadata

        Returns:
            Detected ContentType
        """
        # Check for code-heavy documents
        if metadata.get("has_code_blocks") and metadata.get("num_code_blocks", 0) >= 1:
            return ContentType.CODE

        # Check for header-structured documents
        if metadata.get("has_headers") and metadata.get("num_sections", 0) >= 2:
            return ContentType.HEADING

        # Check for list-heavy documents
        if metadata.get("has_lists") and (
            metadata.get("num_ordered_lists", 0) + metadata.get("num_unordered_lists", 0) >= 1
        ):
            return ContentType.LIST

        # Check for tables
        if metadata.get("has_tables"):
            return ContentType.TABLE

        # Default to text
        return ContentType.TEXT

    def _build_quality_indicators(
        self, metadata: dict[str, Any], warnings: list[str]
    ) -> dict[str, Any]:
        """
        Build quality indicators for the extraction.

        Args:
            metadata: Extracted metadata
            warnings: List of warnings

        Returns:
            Dictionary with quality indicators
        """
        # Determine extraction quality
        if len(warnings) == 0:
            quality = "high"
        elif len(warnings) <= 2:
            quality = "medium"
        else:
            quality = "low"

        return {
            "extraction_quality": quality,
            "has_structure": (
                metadata.get("has_headers", False)
                or metadata.get("has_lists", False)
                or metadata.get("has_code_blocks", False)
                or metadata.get("has_tables", False)
            ),
            "warning_count": len(warnings),
        }
