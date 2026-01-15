"""
File format detection using MIME type analysis and extension fallback.

Uses python-magic for accurate MIME type detection with filename extension
as fallback for edge cases.
"""

from pathlib import Path
from typing import Optional

from src.models.schemas import FileFormat
from src.preprocessing.extractors.base import BaseExtractor

# MIME type to FileFormat mapping
MIME_TO_FORMAT = {
    # PDF
    "application/pdf": FileFormat.PDF,
    # HTML
    "text/html": FileFormat.HTML,
    "application/xhtml+xml": FileFormat.HTML,
    # Markdown
    "text/markdown": FileFormat.MARKDOWN,
    "text/x-markdown": FileFormat.MARKDOWN,
    # Word
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document": FileFormat.DOCX,
    "application/msword": FileFormat.DOCX,
    # Plain text
    "text/plain": FileFormat.TEXT,
    # Images
    "image/png": FileFormat.IMAGE,
    "image/jpeg": FileFormat.IMAGE,
    "image/jpg": FileFormat.IMAGE,
    "image/tiff": FileFormat.IMAGE,
    "image/bmp": FileFormat.IMAGE,
    "image/gif": FileFormat.IMAGE,
    "image/webp": FileFormat.IMAGE,
    "image/svg+xml": FileFormat.IMAGE,
    # JSON
    "application/json": FileFormat.JSON,
    "application/ld+json": FileFormat.JSON,
    "text/json": FileFormat.JSON,
    # CSV
    "text/csv": FileFormat.CSV,
    "application/csv": FileFormat.CSV,
}

# Extension to FileFormat mapping (fallback)
EXTENSION_TO_FORMAT = {
    ".pdf": FileFormat.PDF,
    ".html": FileFormat.HTML,
    ".htm": FileFormat.HTML,
    ".xhtml": FileFormat.HTML,
    ".md": FileFormat.MARKDOWN,
    ".markdown": FileFormat.MARKDOWN,
    ".mdown": FileFormat.MARKDOWN,
    ".mkd": FileFormat.MARKDOWN,
    ".docx": FileFormat.DOCX,
    ".txt": FileFormat.TEXT,
    ".text": FileFormat.TEXT,
    ".png": FileFormat.IMAGE,
    ".jpg": FileFormat.IMAGE,
    ".jpeg": FileFormat.IMAGE,
    ".tiff": FileFormat.IMAGE,
    ".tif": FileFormat.IMAGE,
    ".bmp": FileFormat.IMAGE,
    ".gif": FileFormat.IMAGE,
    ".webp": FileFormat.IMAGE,
    ".svg": FileFormat.IMAGE,
    ".json": FileFormat.JSON,
    ".jsonl": FileFormat.JSON,
    ".ndjson": FileFormat.JSON,
    ".csv": FileFormat.CSV,
    ".tsv": FileFormat.CSV,
}


def detect_format(content: bytes, filename: str) -> FileFormat:
    """
    Detect file format using MIME type detection with extension fallback.

    Uses python-magic to analyze file magic numbers for accurate format detection.
    Falls back to filename extension if MIME detection fails or returns ambiguous results.

    Args:
        content: File content as bytes (first 2048 bytes sufficient for detection)
        filename: Original filename with extension

    Returns:
        Detected FileFormat enum value, or FileFormat.UNKNOWN if detection fails

    Examples:
        >>> detect_format(b'%PDF-1.4...', 'document.pdf')
        FileFormat.PDF
        >>> detect_format(b'<html>...', 'page.html')
        FileFormat.HTML
    """
    # Step 1: Try MIME type detection via python-magic
    detected_format = _detect_by_mime(content)
    if detected_format != FileFormat.UNKNOWN:
        return detected_format

    # Step 2: Fall back to extension-based detection
    detected_format = _detect_by_extension(filename)
    if detected_format != FileFormat.UNKNOWN:
        return detected_format

    # Step 3: Unknown format
    return FileFormat.UNKNOWN


def _detect_by_mime(content: bytes) -> FileFormat:
    """
    Detect format using MIME type analysis via python-magic.

    Args:
        content: File content bytes (first 2048 bytes sufficient)

    Returns:
        Detected FileFormat or FileFormat.UNKNOWN
    """
    try:
        import magic

        # Detect MIME type from file magic numbers
        # Only need first 2048 bytes for accurate detection
        sample = content[:2048] if len(content) > 2048 else content
        mime_type = magic.from_buffer(sample, mime=True)

        # Map MIME type to FileFormat
        return MIME_TO_FORMAT.get(mime_type, FileFormat.UNKNOWN)

    except ImportError:
        # python-magic not installed, skip MIME detection
        return FileFormat.UNKNOWN
    except Exception:
        # Any error in MIME detection, fall back to extension
        return FileFormat.UNKNOWN


def _detect_by_extension(filename: str) -> FileFormat:
    """
    Detect format based on file extension.

    Args:
        filename: Filename with extension

    Returns:
        Detected FileFormat or FileFormat.UNKNOWN
    """
    ext = Path(filename).suffix.lower()
    return EXTENSION_TO_FORMAT.get(ext, FileFormat.UNKNOWN)


def get_mime_type(content: bytes) -> Optional[str]:
    """
    Get MIME type string for file content.

    Utility function for debugging and logging purposes.

    Args:
        content: File content bytes

    Returns:
        MIME type string or None if detection fails
    """
    try:
        import magic

        sample = content[:2048] if len(content) > 2048 else content
        return magic.from_buffer(sample, mime=True)
    except Exception:
        return None


# Extractor registry - maps FileFormat to extractor class
_EXTRACTOR_REGISTRY: dict[FileFormat, type[BaseExtractor]] = {}


def register_extractor(file_format: FileFormat, extractor_class: type[BaseExtractor]) -> None:
    """
    Register an extractor for a specific file format.

    Args:
        file_format: FileFormat enum value to register
        extractor_class: Extractor class that implements BaseExtractor

    Example:
        >>> from src.preprocessing.extractors.pdf import PDFExtractor
        >>> register_extractor(FileFormat.PDF, PDFExtractor)
    """
    _EXTRACTOR_REGISTRY[file_format] = extractor_class


def get_extractor(file_format: FileFormat) -> Optional[BaseExtractor]:
    """
    Get an extractor instance for the given file format.

    Args:
        file_format: FileFormat enum value

    Returns:
        Extractor instance if registered, None otherwise

    Example:
        >>> extractor = get_extractor(FileFormat.PDF)
        >>> if extractor:
        ...     result = extractor.extract(file_content, "document.pdf")
    """
    extractor_class = _EXTRACTOR_REGISTRY.get(file_format)
    if extractor_class:
        return extractor_class()
    return None


# Auto-register extractors on module import
def _auto_register_extractors() -> None:
    """Auto-register all available extractors."""
    try:
        from src.preprocessing.extractors.pdf import PDFExtractor
        register_extractor(FileFormat.PDF, PDFExtractor)
    except ImportError:
        pass  # PDF extractor not available

    try:
        from src.preprocessing.extractors.text import TextExtractor
        register_extractor(FileFormat.TEXT, TextExtractor)
    except ImportError:
        pass  # Text extractor not available

    try:
        from src.preprocessing.extractors.html import HTMLExtractor
        register_extractor(FileFormat.HTML, HTMLExtractor)
    except ImportError:
        pass  # HTML extractor not available

    try:
        from src.preprocessing.extractors.markdown import MarkdownExtractor
        register_extractor(FileFormat.MARKDOWN, MarkdownExtractor)
    except ImportError:
        pass  # Markdown extractor not available

    try:
        from src.preprocessing.extractors.image import ImageExtractor
        register_extractor(FileFormat.IMAGE, ImageExtractor)
    except ImportError:
        pass  # Image extractor not available

    try:
        from src.preprocessing.extractors.docx import WordExtractor
        register_extractor(FileFormat.DOCX, WordExtractor)
    except ImportError:
        pass  # Word extractor not available


# Register extractors on module import
_auto_register_extractors()
