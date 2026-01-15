"""
Format-specific document extractors.

Provides base interface and implementations for extracting text and metadata
from various file formats (PDF, HTML, Markdown, Word, plain text, images).
"""

from src.preprocessing.extractors.base import BaseExtractor

# Import extractors with optional dependencies
_extractors = ["BaseExtractor"]

try:
    from src.preprocessing.extractors.pdf import PDFExtractor
    _extractors.append("PDFExtractor")
except ImportError:
    pass

try:
    from src.preprocessing.extractors.text import TextExtractor
    _extractors.append("TextExtractor")
except ImportError:
    pass

try:
    from src.preprocessing.extractors.html import HTMLExtractor
    _extractors.append("HTMLExtractor")
except ImportError:
    pass

try:
    from src.preprocessing.extractors.markdown import MarkdownExtractor
    _extractors.append("MarkdownExtractor")
except ImportError:
    pass

try:
    from src.preprocessing.extractors.image import ImageExtractor
    _extractors.append("ImageExtractor")
except ImportError:
    pass

try:
    from src.preprocessing.extractors.docx import WordExtractor
    _extractors.append("WordExtractor")
except ImportError:
    pass

__all__ = _extractors
