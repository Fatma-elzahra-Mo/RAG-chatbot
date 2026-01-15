"""
Arabic text normalization for consistent embeddings.

Following 2025 best practices for Arabic NLP preprocessing.
"""

import re
from typing import Protocol


class TextNormalizer(Protocol):
    """Protocol for text normalization implementations."""

    def normalize(self, text: str) -> str:
        """Normalize text."""
        ...


class ArabicNormalizer:
    """
    Arabic text normalizer for consistent embeddings.

    Handles:
    - Alef variants (أ إ آ ا → ا)
    - Yaa variants (ى → ي)
    - Diacritic removal
    - Tatweel removal
    - Persian character normalization
    - Elongation normalization

    This normalization is critical for consistent embeddings and
    improves retrieval accuracy in Arabic RAG systems.
    """

    # Unicode patterns for Arabic text normalization
    DIACRITICS_PATTERN = re.compile(r"[\u0617-\u061A\u064B-\u0652]")
    TATWEEL_PATTERN = re.compile(r"\u0640")
    ELONGATION_PATTERN = re.compile(r"(.)\1{2,}")
    ALEF_VARIANTS = re.compile("[إأآا]")
    YAA_VARIANTS = re.compile("ى")

    # Persian to Arabic character mapping
    PERSIAN_CHARS = {"گ": "ك", "چ": "ج", "پ": "ب", "ژ": "ز"}

    def __init__(
        self,
        remove_diacritics: bool = True,
        normalize_alef: bool = True,
        normalize_yaa: bool = True,
        remove_tatweel: bool = True,
        normalize_persian: bool = True,
        normalize_elongation: bool = True,
    ):
        """
        Initialize Arabic normalizer.

        Args:
            remove_diacritics: Remove Arabic diacritical marks (harakat)
            normalize_alef: Normalize all Alef variants to ا
            normalize_yaa: Normalize ى to ي
            remove_tatweel: Remove tatweel/kashida character (ـ)
            normalize_persian: Convert Persian characters to Arabic equivalents
            normalize_elongation: Reduce character elongation (شكراااا → شكراا)
        """
        self.remove_diacritics = remove_diacritics
        self.normalize_alef = normalize_alef
        self.normalize_yaa = normalize_yaa
        self.remove_tatweel = remove_tatweel
        self.normalize_persian = normalize_persian
        self.normalize_elongation = normalize_elongation

    def normalize(self, text: str) -> str:
        """
        Apply all normalization steps to text.

        Args:
            text: Input Arabic text

        Returns:
            Normalized text

        Example:
            >>> normalizer = ArabicNormalizer()
            >>> normalizer.normalize("أإآا")
            'ااااا'
            >>> normalizer.normalize("مُحَمَّد")
            'محمد'
        """
        if not text:
            return text

        # Normalize Alef variants to standard Alef
        if self.normalize_alef:
            text = self.ALEF_VARIANTS.sub("ا", text)

        # Normalize Yaa variants
        if self.normalize_yaa:
            text = self.YAA_VARIANTS.sub("ي", text)

        # Remove diacritical marks
        if self.remove_diacritics:
            text = self.DIACRITICS_PATTERN.sub("", text)

        # Remove tatweel (kashida) character
        if self.remove_tatweel:
            text = self.TATWEEL_PATTERN.sub("", text)

        # Convert Persian characters to Arabic equivalents
        if self.normalize_persian:
            for persian, arabic in self.PERSIAN_CHARS.items():
                text = text.replace(persian, arabic)

        # Normalize elongation (reduce repeated characters)
        if self.normalize_elongation:
            text = self.ELONGATION_PATTERN.sub(r"\1\1", text)

        return text.strip()
