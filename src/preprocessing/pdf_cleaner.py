"""
PDF-specific text cleaning and preprocessing for Arabic documents.

Handles common PDF artifacts like page numbers, headers/footers, OCR noise,
and formatting issues that degrade retrieval quality.
"""

import re
from typing import Optional


class PDFCleaner:
    """
    Clean and preprocess text extracted from PDF documents.

    Removes common PDF artifacts that interfere with chunking and retrieval:
    - Page numbers (header/footer patterns)
    - Repeated headers and footers
    - Multiple consecutive spaces/newlines
    - OCR artifacts and formatting noise
    - Common Arabic encoding issues

    This preprocessing significantly improves chunking quality and
    retrieval accuracy for PDF documents.
    """

    # Common page number patterns (Arabic and English numerals)
    PAGE_NUMBER_PATTERNS = [
        r"^\s*\d+\s*$",  # Standalone numbers: "1", "  42  "
        r"^\s*[٠-٩]+\s*$",  # Arabic numerals standalone: "١", "  ٤٢  "
        r"^صفحة\s+\d+",  # "صفحة 1", "صفحة 42"
        r"^Page\s+\d+",  # "Page 1", "Page 42"
        r"\d+\s*/\s*\d+$",  # "1/10", "42 / 100"
        r"[٠-٩]+\s*/\s*[٠-٩]+$",  # Arabic numerals: "١/١٠"
    ]

    # Common header/footer patterns
    HEADER_FOOTER_PATTERNS = [
        r"^[\-_=]{3,}$",  # Horizontal lines: "---", "___", "==="
        r"^\s*\|\s*\|\s*$",  # Table borders
        r"^©.*$",  # Copyright notices
        r"^\s*www\.",  # URLs at start of line
        r"^\s*http[s]?://",  # Full URLs
    ]

    # OCR and formatting artifacts
    ARTIFACT_PATTERNS = [
        r"\s{3,}",  # Multiple consecutive spaces (3+)
        r"\n{4,}",  # Multiple consecutive newlines (4+)
        r"[\u200B-\u200D\uFEFF]",  # Zero-width spaces and invisible chars
        r"[\x00-\x08\x0B-\x0C\x0E-\x1F]",  # Control characters
    ]

    # Arabic encoding normalization
    ARABIC_NORMALIZATIONS = [
        (r"[إأٱآا]", "ا"),  # Normalize alef variations to simple alef
        (r"[ىي]", "ي"),  # Normalize yaa variations
        (r"[ةه]", "ه"),  # Normalize taa marbuta and haa
        (r"[ؤئ]", "ء"),  # Normalize hamza variations
    ]

    def __init__(
        self,
        remove_page_numbers: bool = True,
        remove_headers_footers: bool = True,
        clean_artifacts: bool = True,
        normalize_arabic: bool = False,  # Conservative default
        min_line_length: int = 10,
    ):
        """
        Initialize PDF cleaner with configuration options.

        Args:
            remove_page_numbers: Remove detected page numbers
            remove_headers_footers: Remove repeated headers/footers
            clean_artifacts: Remove OCR artifacts and extra whitespace
            normalize_arabic: Apply Arabic text normalization (may affect retrieval)
            min_line_length: Minimum line length to keep (discard shorter)
        """
        self.remove_page_numbers = remove_page_numbers
        self.remove_headers_footers = remove_headers_footers
        self.clean_artifacts = clean_artifacts
        self.normalize_arabic = normalize_arabic
        self.min_line_length = min_line_length

        # Compile regex patterns for efficiency
        self._page_patterns = [re.compile(p, re.MULTILINE) for p in self.PAGE_NUMBER_PATTERNS]
        self._header_footer_patterns = [
            re.compile(p, re.MULTILINE) for p in self.HEADER_FOOTER_PATTERNS
        ]
        self._artifact_patterns = [re.compile(p) for p in self.ARTIFACT_PATTERNS]

    def clean(self, text: str, metadata: Optional[dict] = None) -> tuple[str, dict]:
        """
        Clean PDF text and extract structural metadata.

        Pipeline:
        1. Extract page boundaries (if present)
        2. Remove page numbers
        3. Detect and remove repeated headers/footers
        4. Clean OCR artifacts
        5. Normalize Arabic (optional)
        6. Extract structural metadata

        Args:
            text: Raw text extracted from PDF
            metadata: Optional existing metadata to enhance

        Returns:
            Tuple of (cleaned_text, enhanced_metadata)

        Example:
            >>> cleaner = PDFCleaner()
            >>> text = "Page 1\\n\\nمرحبا\\n\\nPage 2\\n\\nكيف حالك"
            >>> cleaned, meta = cleaner.clean(text)
            >>> "Page" not in cleaned
            True
        """
        metadata = metadata or {}

        # Track original text stats
        metadata["original_length"] = len(text)

        # Split into lines for line-by-line processing
        lines = text.split("\n")

        # Step 1: Detect page boundaries (page numbers often indicate page breaks)
        page_info = self._extract_page_info(lines)
        if page_info:
            metadata["num_pages_detected"] = page_info["num_pages"]

        # Step 2: Remove page numbers
        if self.remove_page_numbers:
            lines = self._remove_page_numbers(lines)

        # Step 3: Detect and remove repeated headers/footers
        if self.remove_headers_footers:
            lines = self._remove_repeated_headers_footers(lines)

        # Rejoin lines
        text = "\n".join(lines)

        # Step 4: Remove header/footer patterns
        if self.remove_headers_footers:
            for pattern in self._header_footer_patterns:
                text = pattern.sub("", text)

        # Step 5: Clean OCR artifacts
        if self.clean_artifacts:
            text = self._clean_artifacts(text)

        # Step 6: Normalize Arabic (optional - may affect embeddings)
        if self.normalize_arabic:
            text = self._normalize_arabic_encoding(text)

        # Step 7: Remove very short lines (likely artifacts)
        lines = [
            line.strip() for line in text.split("\n") if len(line.strip()) >= self.min_line_length
        ]
        text = "\n".join(lines)

        # Final cleanup
        text = text.strip()

        # Add cleaning metadata
        metadata["cleaned_length"] = len(text)
        metadata["reduction_ratio"] = (
            1 - metadata["cleaned_length"] / metadata["original_length"]
            if metadata["original_length"] > 0
            else 0
        )

        return text, metadata

    def _extract_page_info(self, lines: list[str]) -> dict:
        """Extract page boundary information from text."""
        page_numbers = []

        for i, line in enumerate(lines):
            for pattern in self._page_patterns:
                if pattern.match(line.strip()):
                    # Try to extract actual page number
                    digits = re.findall(r"\d+|[٠-٩]+", line)
                    if digits:
                        page_numbers.append((i, digits[0]))
                    break

        if not page_numbers:
            return {}

        return {"num_pages": len(page_numbers), "page_boundaries": page_numbers}

    def _remove_page_numbers(self, lines: list[str]) -> list[str]:
        """Remove lines that are identified as page numbers."""
        cleaned_lines = []

        for line in lines:
            is_page_number = False
            stripped = line.strip()

            # Check against all page number patterns
            for pattern in self._page_patterns:
                if pattern.match(stripped):
                    is_page_number = True
                    break

            if not is_page_number:
                cleaned_lines.append(line)

        return cleaned_lines

    def _remove_repeated_headers_footers(
        self, lines: list[str], repetition_threshold: int = 3
    ) -> list[str]:
        """
        Remove lines that repeat frequently (likely headers/footers).

        Args:
            lines: List of text lines
            repetition_threshold: Minimum repetitions to consider as header/footer

        Returns:
            Lines with repeated headers/footers removed
        """
        # Count line occurrences (ignoring empty lines)
        line_counts = {}
        for line in lines:
            stripped = line.strip()
            if len(stripped) >= self.min_line_length:  # Don't count very short lines
                line_counts[stripped] = line_counts.get(stripped, 0) + 1

        # Identify repeated lines (headers/footers)
        repeated_lines = {
            line for line, count in line_counts.items() if count >= repetition_threshold
        }

        # Remove repeated lines
        cleaned_lines = []
        for line in lines:
            stripped = line.strip()
            if stripped not in repeated_lines:
                cleaned_lines.append(line)

        return cleaned_lines

    def _clean_artifacts(self, text: str) -> str:
        """Remove OCR artifacts and excessive whitespace."""
        for pattern in self._artifact_patterns:
            text = pattern.sub(" ", text)

        # Normalize newlines (max 3 consecutive)
        text = re.sub(r"\n{4,}", "\n\n\n", text)

        # Normalize spaces (max 2 consecutive)
        text = re.sub(r" {3,}", "  ", text)

        return text

    def _normalize_arabic_encoding(self, text: str) -> str:
        """
        Normalize Arabic character variations.

        Note: This is conservative and only normalizes common encoding issues.
        For retrieval, excessive normalization may harm embedding quality.
        """
        for pattern, replacement in self.ARABIC_NORMALIZATIONS:
            text = re.sub(pattern, replacement, text)

        return text

    def detect_structure(self, text: str) -> dict[str, any]:
        """
        Detect document structure elements (headers, tables, lists).

        Returns metadata about document structure that can guide chunking.

        Args:
            text: Cleaned text to analyze

        Returns:
            Dictionary with structure information:
            - has_tables: bool
            - has_lists: bool
            - section_count: int
            - header_positions: List[int]

        Example:
            >>> cleaner = PDFCleaner()
            >>> structure = cleaner.detect_structure("# العنوان\\n\\nالمحتوى")
            >>> structure["has_headers"]
            True
        """
        structure = {
            "has_tables": False,
            "has_lists": False,
            "has_headers": False,
            "section_count": 0,
            "header_positions": [],
        }

        lines = text.split("\n")

        # Detect tables (common patterns: "|", "---", tab-separated values)
        table_indicators = [r"\|.*\|", r"[-─]{3,}", r"\t.*\t"]
        for pattern in table_indicators:
            if re.search(pattern, text):
                structure["has_tables"] = True
                break

        # Detect lists (Arabic and English markers)
        list_patterns = [
            r"^\s*[-•*]",  # Bullet points
            r"^\s*\d+[.)]\s",  # Numbered lists: "1. ", "1) "
            r"^\s*[٠-٩]+[.)]\s",  # Arabic numbered lists
            r"^\s*[أ-ي][.)]\s",  # Arabic letter lists
        ]
        for line in lines:
            for pattern in list_patterns:
                if re.match(pattern, line):
                    structure["has_lists"] = True
                    break
            if structure["has_lists"]:
                break

        # Detect headers (lines that are short, end without punctuation, possibly bold/caps)
        # Heuristic: line < 80 chars, doesn't end with sentence delimiter, next line is empty
        for i, line in enumerate(lines[:-1]):
            stripped = line.strip()
            if (
                10 < len(stripped) < 80
                and stripped[-1] not in ".؟!،"
                and (i + 1 < len(lines) and not lines[i + 1].strip())
            ):
                structure["has_headers"] = True
                structure["header_positions"].append(i)
                structure["section_count"] += 1

        return structure
