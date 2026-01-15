"""
Plain text extractor with encoding detection.

Handles plain text files with automatic encoding detection using chardet,
supporting various encodings including UTF-8, UTF-16, Windows-1256, and ISO-8859-1.
"""

import hashlib
import re
from typing import BinaryIO, Any

import chardet

from src.models.schemas import ExtractionResult, ContentType
from src.preprocessing.extractors.base import BaseExtractor


class TextExtractor(BaseExtractor):
    """Extractor for plain text files with encoding detection."""

    # Common encodings for Arabic and multilingual text
    SUPPORTED_ENCODINGS = {
        "utf-8",
        "utf-16",
        "utf-16-le",
        "utf-16-be",
        "windows-1256",
        "iso-8859-1",
        "ascii",
    }

    def extract(
        self, file_content: BinaryIO, filename: str, **options: Any
    ) -> ExtractionResult:
        """
        Extract text from plain text file with encoding detection.

        Args:
            file_content: Binary file content stream
            filename: Original filename for context
            **options: Optional parameters:
                - fallback_encoding: Encoding to use if detection fails (default: 'utf-8')
                - detect_structure: Whether to analyze document structure (default: True)
                - encoding_hint: Optional encoding hint to use instead of auto-detection
                - max_size_mb: Maximum file size in MB (default: 25)

        Returns:
            ExtractionResult with text, metadata, and warnings
        """
        warnings = []
        fallback_encoding = options.get("fallback_encoding", "utf-8")
        detect_structure = options.get("detect_structure", True)
        encoding_hint = options.get("encoding_hint", None)
        max_size_mb = options.get("max_size_mb", 25)

        # Read raw bytes
        raw_content = file_content.read()
        file_size_bytes = len(raw_content)
        file_size_mb = file_size_bytes / (1024 * 1024)

        # Check file size limit
        if file_size_mb > max_size_mb:
            raise ValueError(
                f"File size ({file_size_mb:.2f} MB) exceeds maximum allowed size ({max_size_mb} MB)"
            )

        # Check for empty file
        if file_size_bytes == 0:
            warnings.append("File is empty")
            return ExtractionResult(
                text="",
                content_type=ContentType.TEXT,
                metadata={
                    "source_format": "text",
                    "file_size_bytes": 0,
                    "file_hash": hashlib.sha256(b"").hexdigest(),
                },
                warnings=warnings,
            )

        # Calculate file hash (SHA256) for deduplication
        file_hash = hashlib.sha256(raw_content).hexdigest()

        # Detect encoding (or use hint if provided)
        encoding_hint_used = False
        if encoding_hint:
            detected_encoding = encoding_hint
            confidence = 1.0
            encoding_hint_used = True
        else:
            detected_encoding, confidence = self._detect_encoding(raw_content)

        if confidence < 0.7 and not encoding_hint:
            warnings.append(
                f"Low confidence encoding detection ({confidence:.2f}). "
                f"Detected: {detected_encoding}"
            )

        # Decode text with fallback mechanism
        text, actual_encoding, decode_warnings = self._decode_with_fallback(
            raw_content, detected_encoding, fallback_encoding
        )
        warnings.extend(decode_warnings)

        # Check if encoding conversion was needed
        encoding_converted = actual_encoding.lower() != "utf-8" and "replacement" not in actual_encoding.lower()
        if encoding_converted and not encoding_hint_used:
            warnings.append(f"Converted from {actual_encoding} to UTF-8")

        # Detect line ending style
        line_ending = self._detect_line_ending(raw_content)
        if line_ending == "mixed":
            warnings.append("File contains mixed line ending styles (LF, CRLF, CR)")

        # Check for binary content
        null_bytes = raw_content.count(b"\x00")
        if null_bytes > 0:
            warnings.append(f"File contains {null_bytes} null bytes, may be binary or non-text content")

        # Check for whitespace-only content
        if text.strip() == "":
            warnings.append("File contains only whitespace")

        # Build metadata
        # For detected_encoding field, use actual_encoding if different (for backward compatibility with tests)
        final_detected = actual_encoding if actual_encoding != detected_encoding else detected_encoding
        metadata = {
            "source_format": "text",
            "detected_encoding": final_detected,  # Use actual encoding for compatibility
            "encoding_confidence": confidence,
            "actual_encoding": actual_encoding,
            "encoding_converted": encoding_converted,
            "line_ending_style": line_ending,
            "file_hash": file_hash,
            "file_size_bytes": file_size_bytes,
            "file_size_mb": file_size_mb,
            "line_count": text.count("\n") if text else 0,
            "char_count": len(text),
        }

        if encoding_hint_used:
            metadata["encoding_hint_used"] = True

        # Detect structure if requested
        if detect_structure:
            structure_info = self._detect_structure(text)
            metadata.update(structure_info)
        else:
            metadata["structure_detection_enabled"] = False

        # Determine content type based on structure
        content_type = ContentType.TEXT
        if detect_structure and (
            metadata.get("has_numbered_sections") or metadata.get("has_bullet_points")
        ):
            content_type = ContentType.LIST

        # Calculate quality indicators
        quality_indicators = self._calculate_quality_indicators(
            text, raw_content, actual_encoding, warnings
        )

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
            True if format is 'text' or 'txt', False otherwise
        """
        return file_format.lower() in ("text", "txt")

    def _detect_encoding(self, raw_content: bytes) -> tuple[str, float]:
        """
        Detect encoding of raw bytes using chardet.

        Args:
            raw_content: Raw byte content

        Returns:
            Tuple of (encoding_name, confidence_score)
        """
        # Use chardet to detect encoding
        result = chardet.detect(raw_content)

        encoding = result.get("encoding", "utf-8")
        confidence = result.get("confidence", 0.0)

        # Normalize encoding name
        if encoding:
            encoding = encoding.lower()

        # Default to UTF-8 if detection fails
        if not encoding or encoding == "none":
            encoding = "utf-8"
            confidence = 0.0

        return encoding, confidence

    def _decode_with_fallback(
        self, raw_content: bytes, primary_encoding: str, fallback_encoding: str
    ) -> tuple[str, str, list[str]]:
        """
        Decode bytes to text with fallback mechanism.

        Args:
            raw_content: Raw byte content
            primary_encoding: Primary encoding to try
            fallback_encoding: Fallback encoding if primary fails

        Returns:
            Tuple of (decoded_text, actual_encoding_used, warnings)
        """
        warnings = []

        # Try primary encoding
        try:
            text = raw_content.decode(primary_encoding)
            return text, primary_encoding, warnings
        except (UnicodeDecodeError, LookupError) as e:
            warnings.append(
                f"Failed to decode with {primary_encoding}. "
                f"Trying common Arabic encodings..."
            )

        # Try common Arabic encodings if primary failed
        arabic_encodings = ["windows-1256", "iso-8859-6", "utf-8"]
        for encoding in arabic_encodings:
            try:
                text = raw_content.decode(encoding)
                # Check if decoded text looks reasonable (has Arabic chars)
                arabic_char_count = sum(1 for c in text if '\u0600' <= c <= '\u06FF')
                if arabic_char_count > len(text) * 0.1:  # At least 10% Arabic
                    warnings.append(f"Successfully decoded with {encoding} (Arabic encoding fallback)")
                    return text, encoding, warnings
            except (UnicodeDecodeError, LookupError):
                continue

        # Try fallback encoding with error handling
        try:
            text = raw_content.decode(fallback_encoding, errors="replace")
            warnings.append(f"Used fallback encoding: {fallback_encoding}")
            # Check if we had to replace characters
            if '\ufffd' in text:
                warnings.append("Decoding errors occurred - some characters were replaced")
            return text, fallback_encoding, warnings
        except (UnicodeDecodeError, LookupError) as e:
            # Last resort: UTF-8 with replacement
            warnings.append(
                f"Fallback encoding {fallback_encoding} failed: {str(e)}. "
                "Using UTF-8 with character replacement"
            )
            text = raw_content.decode("utf-8", errors="replace")
            if '\ufffd' in text:
                warnings.append("Decoding errors occurred - some characters were replaced")
            return text, "utf-8 (with replacement)", warnings

    def _detect_line_ending(self, raw_content: bytes) -> str:
        """
        Detect line ending style (windows, unix, mac, or mixed).

        Args:
            raw_content: Raw byte content

        Returns:
            Line ending style: 'windows', 'unix', 'mac', or 'mixed'
        """
        crlf_count = raw_content.count(b"\r\n")
        lf_count = raw_content.count(b"\n") - crlf_count  # LF without CR
        cr_count = raw_content.count(b"\r") - crlf_count  # CR without LF

        # Determine dominant line ending
        total = crlf_count + lf_count + cr_count

        if total == 0:
            return "none"

        # If one style dominates (>80%), return it
        if crlf_count > 0.8 * total:
            return "windows"
        if lf_count > 0.8 * total:
            return "unix"
        if cr_count > 0.8 * total:
            return "mac"

        # If multiple styles present
        non_zero_count = sum(1 for count in [crlf_count, lf_count, cr_count] if count > 0)
        if non_zero_count > 1:
            return "mixed"

        # Single style but less than 80% (shouldn't happen, but fallback)
        if crlf_count > 0:
            return "windows"
        if lf_count > 0:
            return "unix"
        if cr_count > 0:
            return "mac"

        return "unknown"

    def _detect_structure(self, text: str) -> dict[str, Any]:
        """
        Detect document structure indicators.

        Args:
            text: Decoded text content

        Returns:
            Dictionary with structure indicators
        """
        # Check for numbered sections (e.g., "1.", "1.1", "١.", "١.١")
        numbered_pattern = r"^\s*(?:\d+\.|\d+\.\d+|[٠-٩]+\.|[٠-٩]+\.[٠-٩]+)\s+"
        has_numbered = bool(re.search(numbered_pattern, text, re.MULTILINE))

        # Check for bullet points (•, -, *, ●, ○, ◦)
        bullet_pattern = r"^\s*[•\-*●○◦]\s+"
        has_bullets = bool(re.search(bullet_pattern, text, re.MULTILINE))

        # Check for section headers (all caps lines, or lines with # markdown)
        header_pattern = r"^(?:[A-Z\s]{10,}|#{1,6}\s+.+)$"
        has_headers = bool(re.search(header_pattern, text, re.MULTILINE))

        # Check for indentation structure
        indent_pattern = r"^[ \t]{2,}"
        has_indentation = bool(re.search(indent_pattern, text, re.MULTILINE))

        # Count structural elements
        num_numbered_items = len(re.findall(numbered_pattern, text, re.MULTILINE))
        num_bullet_items = len(re.findall(bullet_pattern, text, re.MULTILINE))
        num_headers = len(re.findall(header_pattern, text, re.MULTILINE))

        return {
            "has_structure": has_numbered or has_bullets or has_headers,
            "has_numbered_sections": has_numbered,
            "has_bullet_points": has_bullets,
            "has_headers": has_headers,
            "has_indentation": has_indentation,
            "num_numbered_items": num_numbered_items,
            "num_bullet_items": num_bullet_items,
            "num_headers": num_headers,
        }

    def _calculate_quality_indicators(
        self, text: str, raw_content: bytes, actual_encoding: str, warnings: list[str]
    ) -> dict[str, Any]:
        """
        Calculate quality indicators for the extraction.

        Args:
            text: Decoded text content
            raw_content: Original byte content
            actual_encoding: Encoding used for decoding
            warnings: List of warnings generated during extraction

        Returns:
            Dictionary with quality metrics
        """
        # Determine extraction quality based on encoding and warnings
        quality = "high"

        # Check for replacement characters (indicating decoding errors)
        replacement_char_count = text.count('\ufffd')

        # Check for encoding issues
        if "replacement" in actual_encoding.lower() or replacement_char_count > 0:
            quality = "low"
        elif actual_encoding.lower() not in ("utf-8", "ascii"):
            quality = "medium"

        # Check for corruption indicators
        null_bytes = raw_content.count(b"\x00")
        if null_bytes > 0:  # Any null bytes in text file is suspicious
            quality = "low"

        # Check for decoding warnings
        decode_error_warnings = [w for w in warnings if "decode" in w.lower() or "encoding" in w.lower() or "replacement" in w.lower()]
        if len(decode_error_warnings) > 2:
            quality = "low"

        return {
            "extraction_quality": quality,
            "text_length": len(text),
            "byte_length": len(raw_content),
            "encoding_used": actual_encoding,
            "has_decoding_errors": "replacement" in actual_encoding.lower() or replacement_char_count > 0,
            "null_byte_count": null_bytes,
            "replacement_char_count": replacement_char_count,
        }
