"""
HTML extractor using BeautifulSoup4 with html5lib parser.

Handles HTML documents with comprehensive processing:
- Strips script, style, navigation, and footer elements
- Preserves heading hierarchy and structure
- Linearizes tables row-by-row for readability
- Extracts link URLs to metadata
- Preserves RTL text markers for Arabic content
"""

import hashlib
import re
from typing import Any, BinaryIO

from bs4 import BeautifulSoup, NavigableString, Tag
from loguru import logger

from src.models.schemas import ContentType, ExtractionResult
from src.preprocessing.extractors.base import BaseExtractor


class HTMLExtractor(BaseExtractor):
    """
    Extract text and metadata from HTML documents with structure preservation.

    Features:
    - Removes script, style, nav, footer, and other non-content elements
    - Preserves heading hierarchy (h1-h6)
    - Linearizes tables into row-by-row text format
    - Extracts link URLs for metadata
    - Preserves RTL markers and direction attributes
    - Detects document structure (headings, lists, tables)
    """

    # Tags to strip entirely (non-content)
    STRIP_TAGS = {
        "script", "style", "noscript", "iframe",
        "nav", "footer", "header", "aside",
        "form", "button", "input", "textarea", "select",
        "svg", "canvas", "video", "audio",
        "meta", "link", "base"
    }

    # Heading tags (for hierarchy tracking)
    HEADING_TAGS = {"h1", "h2", "h3", "h4", "h5", "h6"}

    # List item tags
    LIST_TAGS = {"ul", "ol", "dl", "li", "dt", "dd"}

    def __init__(
        self,
        strip_comments: bool = True,
        preserve_links: bool = True,
        linearize_tables: bool = True,
        extract_headings: bool = True,
        preserve_rtl_markers: bool = True,
    ):
        """
        Initialize HTML extractor.

        Args:
            strip_comments: Remove HTML comments (default: True)
            preserve_links: Extract link URLs to metadata (default: True)
            linearize_tables: Convert tables to row-by-row text (default: True)
            extract_headings: Track heading hierarchy (default: True)
            preserve_rtl_markers: Preserve RTL direction markers (default: True)
        """
        self.strip_comments = strip_comments
        self.preserve_links = preserve_links
        self.linearize_tables = linearize_tables
        self.extract_headings = extract_headings
        self.preserve_rtl_markers = preserve_rtl_markers

    def extract(
        self, file_content: BinaryIO, filename: str, **options: Any
    ) -> ExtractionResult:
        """
        Extract text and metadata from HTML file.

        Pipeline:
        1. Parse HTML with BeautifulSoup4 + html5lib
        2. Strip non-content tags (script, style, nav, footer)
        3. Extract heading hierarchy
        4. Linearize tables into readable text
        5. Extract link URLs
        6. Preserve RTL text markers
        7. Compile metadata and structure info

        Args:
            file_content: Binary HTML file stream
            filename: Original filename
            **options: Additional options:
                - encoding: str (default 'utf-8') - HTML encoding
                - detect_encoding: bool (default True) - Auto-detect encoding

        Returns:
            ExtractionResult with:
                - text: Extracted and structured text content
                - content_type: Primary content type detected
                - metadata: HTML metadata and structure info
                - warnings: Any issues encountered during extraction
        """
        warnings = []
        encoding = options.get("encoding", "utf-8")
        detect_encoding = options.get("detect_encoding", True)

        # Read HTML content
        html_bytes = file_content.read()

        # Calculate file hash for deduplication
        file_hash = hashlib.sha256(html_bytes).hexdigest()

        # Detect encoding if requested
        actual_encoding = encoding
        if detect_encoding:
            actual_encoding = self._detect_encoding(html_bytes, encoding)
            if actual_encoding != encoding:
                warnings.append(
                    f"Auto-detected encoding: {actual_encoding} (overriding {encoding})"
                )

        # Decode HTML
        try:
            html_text = html_bytes.decode(actual_encoding, errors="replace")
        except (UnicodeDecodeError, LookupError) as e:
            warnings.append(
                f"Encoding {actual_encoding} failed: {str(e)}. Using UTF-8 with replacement."
            )
            html_text = html_bytes.decode("utf-8", errors="replace")
            actual_encoding = "utf-8 (with replacement)"

        # Parse HTML with BeautifulSoup4 + html5lib (most lenient parser)
        try:
            soup = BeautifulSoup(html_text, "html5lib")
        except Exception as e:
            warnings.append(f"html5lib parser failed: {str(e)}. Falling back to lxml.")
            try:
                soup = BeautifulSoup(html_text, "lxml")
            except Exception as e2:
                warnings.append(f"lxml parser failed: {str(e2)}. Using html.parser.")
                soup = BeautifulSoup(html_text, "html.parser")

        # Extract basic HTML metadata
        metadata = {
            "source": filename,
            "source_format": "html",
            "file_hash": file_hash,
            "file_size_bytes": len(html_bytes),
            "encoding": actual_encoding,
        }

        # Extract document metadata from meta tags
        self._extract_html_metadata(soup, metadata)

        # Detect RTL content
        is_rtl = self._detect_rtl_content(soup)
        metadata["is_rtl"] = is_rtl

        # Strip non-content elements
        self._strip_non_content_tags(soup)

        # Extract headings with hierarchy
        headings_info = []
        if self.extract_headings:
            headings_info = self._extract_headings(soup)
            metadata["headings"] = headings_info
            metadata["heading_count"] = len(headings_info)

        # Extract link URLs
        links = []
        if self.preserve_links:
            links = self._extract_links(soup)
            metadata["links"] = links
            metadata["link_count"] = len(links)

        # Linearize tables (note: this modifies soup by removing table tags)
        table_count = 0
        if self.linearize_tables:
            table_count = self._linearize_tables(soup)
            metadata["table_count"] = table_count
            metadata["has_tables"] = table_count > 0

        # Extract text content with structure preservation
        extracted_text = self._extract_text_with_structure(soup)

        # Remove excessive whitespace
        extracted_text = self._clean_whitespace(extracted_text)

        # Check for empty extraction
        if not extracted_text or len(extracted_text.strip()) == 0:
            warnings.append("No text content extracted from HTML (file may be empty or contain only media)")

        # Detect document structure (pass table_count since tables were linearized)
        structure = self._detect_structure(soup, extracted_text, table_count)
        metadata["structure"] = structure

        # Determine content type
        content_type = self._determine_content_type(structure)

        # Calculate quality indicators
        quality_indicators = {
            "text_length": len(extracted_text),
            "char_count": len(extracted_text),
            "word_count": len(extracted_text.split()),
            "heading_count": len(headings_info),
            "link_count": len(links),
            "table_count": table_count,
            "has_structure": structure.get("has_structure", False),
        }

        logger.info(
            f"Extracted HTML: {filename} - "
            f"{quality_indicators['char_count']} chars, "
            f"{quality_indicators['heading_count']} headings, "
            f"{quality_indicators['table_count']} tables"
        )

        return ExtractionResult(
            text=extracted_text,
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
            True if format is 'html' or 'htm', False otherwise
        """
        return file_format.lower() in ("html", "htm")

    def _detect_encoding(self, html_bytes: bytes, fallback: str = "utf-8") -> str:
        """
        Detect HTML encoding from meta tags or BOM.

        Args:
            html_bytes: Raw HTML bytes
            fallback: Fallback encoding if detection fails

        Returns:
            Detected encoding name
        """
        # Check for BOM (Byte Order Mark)
        if html_bytes.startswith(b"\xef\xbb\xbf"):
            return "utf-8"
        if html_bytes.startswith(b"\xff\xfe"):
            return "utf-16-le"
        if html_bytes.startswith(b"\xfe\xff"):
            return "utf-16-be"

        # Try to extract charset from meta tags (sample first 2048 bytes)
        sample = html_bytes[:2048].lower()

        # Look for <meta charset="...">
        charset_match = re.search(rb'charset\s*=\s*["\']?([a-z0-9\-_]+)', sample)
        if charset_match:
            charset = charset_match.group(1).decode("ascii", errors="ignore")
            return charset

        # Default fallback
        return fallback

    def _extract_html_metadata(self, soup: BeautifulSoup, metadata: dict) -> None:
        """
        Extract metadata from HTML meta tags.

        Args:
            soup: BeautifulSoup parsed HTML
            metadata: Dictionary to populate with metadata
        """
        # Title
        title_tag = soup.find("title")
        if title_tag:
            metadata["title"] = title_tag.get_text(strip=True)

        # Meta tags
        meta_tags = soup.find_all("meta")
        for meta in meta_tags:
            name = meta.get("name", "").lower()
            content = meta.get("content", "")

            if name == "description":
                metadata["description"] = content
            elif name == "author":
                metadata["author"] = content
            elif name == "keywords":
                metadata["keywords"] = content
            elif name == "language":
                metadata["language"] = content

        # Open Graph metadata
        og_title = soup.find("meta", property="og:title")
        if og_title:
            metadata["og_title"] = og_title.get("content", "")

    def _detect_rtl_content(self, soup: BeautifulSoup) -> bool:
        """
        Detect if HTML contains RTL (right-to-left) content.

        Args:
            soup: BeautifulSoup parsed HTML

        Returns:
            True if RTL content detected
        """
        # Check html or body dir attribute
        html_tag = soup.find("html")
        if html_tag and html_tag.get("dir", "").lower() == "rtl":
            return True

        body_tag = soup.find("body")
        if body_tag and body_tag.get("dir", "").lower() == "rtl":
            return True

        # Check for Arabic script characters in text
        text_sample = soup.get_text()[:1000]
        arabic_chars = len(re.findall(r"[\u0600-\u06FF\u0750-\u077F]", text_sample))
        return arabic_chars > 50  # Threshold for RTL detection

    def _strip_non_content_tags(self, soup: BeautifulSoup) -> None:
        """
        Remove non-content tags from HTML.

        Args:
            soup: BeautifulSoup parsed HTML (modified in-place)
        """
        # Remove all tags in STRIP_TAGS
        for tag_name in self.STRIP_TAGS:
            for tag in soup.find_all(tag_name):
                tag.decompose()

        # Remove HTML comments if requested
        if self.strip_comments:
            for comment in soup.find_all(string=lambda text: isinstance(text, type(soup))):
                if hasattr(comment, "parent") and comment.parent.name == "[document]":
                    continue
                if str(comment).strip().startswith("<!--"):
                    comment.extract()

    def _extract_headings(self, soup: BeautifulSoup) -> list[dict]:
        """
        Extract headings with hierarchy information.

        Args:
            soup: BeautifulSoup parsed HTML

        Returns:
            List of heading dictionaries with level and text
        """
        headings = []
        for tag_name in self.HEADING_TAGS:
            for heading in soup.find_all(tag_name):
                text = heading.get_text(strip=True)
                if text:  # Skip empty headings
                    level = int(tag_name[1])  # Extract number from h1, h2, etc.
                    headings.append({
                        "level": level,
                        "text": text,
                        "tag": tag_name,
                    })

        return headings

    def _extract_links(self, soup: BeautifulSoup) -> list[dict]:
        """
        Extract all link URLs from HTML.

        Args:
            soup: BeautifulSoup parsed HTML

        Returns:
            List of link dictionaries with URL and text
        """
        links = []
        for link in soup.find_all("a", href=True):
            url = link.get("href", "")
            text = link.get_text(strip=True)
            if url:  # Skip empty URLs
                links.append({
                    "url": url,
                    "text": text,
                })

        return links

    def _linearize_tables(self, soup: BeautifulSoup) -> int:
        """
        Convert HTML tables to row-by-row text format.

        Replaces table elements with linearized text in-place.

        Args:
            soup: BeautifulSoup parsed HTML (modified in-place)

        Returns:
            Number of tables linearized
        """
        tables = soup.find_all("table")
        table_count = 0

        for table in tables:
            linearized_text = self._table_to_text(table)
            if linearized_text:
                # Replace table with linearized text
                table.replace_with(NavigableString(f"\n[TABLE]\n{linearized_text}\n[/TABLE]\n"))
                table_count += 1

        return table_count

    def _table_to_text(self, table: Tag) -> str:
        """
        Convert a single HTML table to row-by-row text.

        Args:
            table: BeautifulSoup table tag

        Returns:
            Linearized table text
        """
        rows = []

        # Process table rows
        for row in table.find_all("tr"):
            cells = []

            # Extract header cells
            for th in row.find_all("th"):
                cell_text = th.get_text(strip=True)
                if cell_text:
                    cells.append(f"[HEADER: {cell_text}]")

            # Extract data cells
            for td in row.find_all("td"):
                cell_text = td.get_text(strip=True)
                if cell_text:
                    cells.append(cell_text)

            # Join cells in row
            if cells:
                row_text = " | ".join(cells)
                rows.append(row_text)

        return "\n".join(rows)

    def _extract_text_with_structure(self, soup: BeautifulSoup) -> str:
        """
        Extract text while preserving document structure.

        Uses space separator to avoid breaking inline elements,
        then cleans whitespace to preserve document structure.

        Args:
            soup: BeautifulSoup parsed HTML

        Returns:
            Structured text content
        """
        # Get text from body if available, otherwise entire document
        # Use space separator to avoid breaking inline elements
        body = soup.find("body")
        if body:
            return body.get_text(separator=" ", strip=False)
        else:
            return soup.get_text(separator=" ", strip=False)

    def _clean_whitespace(self, text: str) -> str:
        """
        Clean excessive whitespace while preserving structure.

        Args:
            text: Raw extracted text

        Returns:
            Cleaned text
        """
        # Collapse multiple spaces into single space
        text = re.sub(r" {2,}", " ", text)

        # Remove multiple consecutive blank lines (keep max 2)
        text = re.sub(r"\n{3,}", "\n\n", text)

        # Remove trailing/leading whitespace from each line
        lines = [line.strip() for line in text.split("\n")]
        text = "\n".join(lines)

        # Remove leading/trailing whitespace from entire text
        text = text.strip()

        return text

    def _detect_structure(self, soup: BeautifulSoup, text: str, table_count: int = 0) -> dict:
        """
        Detect document structure indicators.

        Args:
            soup: BeautifulSoup parsed HTML
            text: Extracted text
            table_count: Number of tables (if already linearized and removed from soup)

        Returns:
            Dictionary with structure indicators
        """
        # Count structural elements
        num_headings = len(soup.find_all(list(self.HEADING_TAGS)))
        num_lists = len(soup.find_all(["ul", "ol"]))
        # Use provided table_count if tables were linearized, otherwise count from soup
        num_tables = table_count if table_count > 0 else len(soup.find_all("table"))
        num_paragraphs = len(soup.find_all("p"))

        # Detect list items in text
        bullet_pattern = r"^\s*[•\-*●○◦]\s+"
        num_bullets = len(re.findall(bullet_pattern, text, re.MULTILINE))

        numbered_pattern = r"^\s*(?:\d+\.|\d+\.\d+|[٠-٩]+\.|[٠-٩]+\.[٠-٩]+)\s+"
        num_numbered = len(re.findall(numbered_pattern, text, re.MULTILINE))

        has_structure = (num_headings > 0 or num_lists > 0 or num_tables > 0)

        return {
            "has_structure": has_structure,
            "has_headings": num_headings > 0,
            "has_lists": num_lists > 0,
            "has_tables": num_tables > 0,
            "num_headings": num_headings,
            "num_lists": num_lists,
            "num_tables": num_tables,
            "num_paragraphs": num_paragraphs,
            "num_bullet_items": num_bullets,
            "num_numbered_items": num_numbered,
        }

    def _determine_content_type(self, structure: dict) -> ContentType:
        """
        Determine primary content type based on structure.

        Args:
            structure: Structure information

        Returns:
            Primary ContentType enum value
        """
        # Prioritize based on structure
        if structure.get("has_tables", False):
            return ContentType.TABLE

        if structure.get("has_lists", False):
            return ContentType.LIST

        if structure.get("has_headings", False):
            return ContentType.HEADING

        return ContentType.TEXT