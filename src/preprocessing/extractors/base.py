"""
Base extractor interface for format-specific document extraction.

Provides abstract base class that all format extractors must implement
to ensure consistent API across different file formats.
"""

from abc import ABC, abstractmethod
from typing import BinaryIO, Any

from src.models.schemas import ExtractionResult


class BaseExtractor(ABC):
    """Base class for format-specific extractors."""

    @abstractmethod
    def extract(
        self, file_content: BinaryIO, filename: str, **options: Any
    ) -> ExtractionResult:
        """
        Extract text and metadata from a file.

        Args:
            file_content: Binary file content stream
            filename: Original filename for context
            **options: Format-specific extraction options

        Returns:
            ExtractionResult with text, metadata, and warnings
        """
        pass

    @abstractmethod
    def supports_format(self, file_format: str) -> bool:
        """
        Check if this extractor supports the given format.

        Args:
            file_format: File format identifier (e.g., 'pdf', 'txt', 'html')

        Returns:
            True if this extractor can handle the format, False otherwise
        """
        pass
