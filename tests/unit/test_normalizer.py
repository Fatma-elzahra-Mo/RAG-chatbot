"""
Unit tests for Arabic text normalizer.
"""

import pytest

from src.preprocessing.normalizer import ArabicNormalizer


class TestArabicNormalizer:
    """Test suite for ArabicNormalizer."""

    @pytest.fixture
    def normalizer(self):
        """Create normalizer instance with all features enabled."""
        return ArabicNormalizer()

    def test_alef_normalization(self, normalizer):
        """Test normalization of Alef variants to standard Alef."""
        # Note: elongation normalization also applies, reducing repeated characters
        assert normalizer.normalize("أإآا") == "اا"

    def test_alef_variants_individually(self):
        """Test each Alef variant is normalized correctly."""
        normalizer = ArabicNormalizer(normalize_elongation=False)
        assert normalizer.normalize("أ") == "ا"
        assert normalizer.normalize("إ") == "ا"
        assert normalizer.normalize("آ") == "ا"

    def test_yaa_normalization(self, normalizer):
        """Test normalization of Yaa variants."""
        assert normalizer.normalize("ى") == "ي"

    def test_diacritic_removal(self, normalizer):
        """Test removal of Arabic diacritical marks."""
        assert normalizer.normalize("مُحَمَّد") == "محمد"

    def test_tatweel_removal(self, normalizer):
        """Test removal of tatweel (kashida) character."""
        assert normalizer.normalize("مــــرحبا") == "مرحبا"

    def test_elongation_normalization(self, normalizer):
        """Test reduction of character elongation."""
        assert normalizer.normalize("شكرااااااا") == "شكراا"

    def test_persian_chars(self, normalizer):
        """Test conversion of Persian characters to Arabic equivalents."""
        assert normalizer.normalize("گچپ") == "كجب"

    def test_empty_string(self, normalizer):
        """Test handling of empty string."""
        assert normalizer.normalize("") == ""

    def test_combined_normalization(self, normalizer):
        """Test multiple normalization steps together."""
        text = "مُحَمَّدأگ"
        expected = "محمداك"
        assert normalizer.normalize(text) == expected

    def test_selective_normalization(self):
        """Test normalizer with selective features."""
        normalizer = ArabicNormalizer(
            remove_diacritics=False, normalize_alef=True, normalize_yaa=False
        )
        assert normalizer.normalize("أُ") == "اُ"

    def test_whitespace_stripping(self, normalizer):
        """Test that leading/trailing whitespace is stripped."""
        assert normalizer.normalize("  مرحبا  ") == "مرحبا"
