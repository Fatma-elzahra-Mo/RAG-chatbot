"""
Unit tests for image extractor using vision-capable LLM.

Tests text extraction mode (document images), description mode (charts/photos),
auto mode (automatic detection), multi-page TIFF, and quality indicators.

Following TDD approach - these tests should FAIL until implementation is complete.
"""

import io
from unittest.mock import Mock, patch, MagicMock

import pytest
from PIL import Image
from langchain_core.messages import AIMessage

from src.models.schemas import ExtractionResult, ContentType, ImageExtractionMode
from src.preprocessing.extractors.image import ImageExtractor
from src.models.vllm_model import VLLMConnectionError


class TestImageExtractorBasics:
    """Test basic image extractor functionality."""

    @pytest.fixture
    def mock_vllm(self):
        """Create mock VLLMLLMWrapper."""
        mock = Mock()
        mock.invoke = Mock(return_value=AIMessage(content="Extracted text from image"))
        return mock

    @pytest.fixture
    def extractor(self, mock_vllm):
        """Create image extractor instance with mocked vLLM."""
        with patch("src.preprocessing.extractors.image.VLLMLLMWrapper", return_value=mock_vllm):
            return ImageExtractor(verify_connection=False)

    def test_extractor_supports_image_format(self, extractor):
        """Test that extractor declares support for image format."""
        assert extractor.supports_format("image")

    def test_extractor_does_not_support_other_formats(self, extractor):
        """Test that extractor rejects non-image formats."""
        assert not extractor.supports_format("pdf")
        assert not extractor.supports_format("text")
        assert not extractor.supports_format("html")

    def test_extractor_initialization_with_custom_params(self):
        """Test extractor initialization with custom parameters."""
        with patch("src.preprocessing.extractors.image.VLLMLLMWrapper") as mock_class:
            extractor = ImageExtractor(
                base_url="http://custom:8000/v1",
                model_name="llava-1.5-13b-hf",
                default_mode=ImageExtractionMode.TEXT,
                verify_connection=False,
            )

            assert extractor.base_url == "http://custom:8000/v1"
            assert extractor.model_name == "llava-1.5-13b-hf"
            assert extractor.default_mode == ImageExtractionMode.TEXT

    def test_extractor_handles_vllm_connection_error(self):
        """Test that extractor handles vLLM connection errors gracefully."""
        with patch(
            "src.preprocessing.extractors.image.VLLMLLMWrapper",
            side_effect=VLLMConnectionError("Server not available"),
        ):
            extractor = ImageExtractor(verify_connection=False)
            assert extractor.llm is None


class TestTextExtractionMode:
    """Test text extraction mode for document images (OCR-like)."""

    @pytest.fixture
    def mock_vllm_text_response(self):
        """Create mock vLLM with text extraction response."""
        mock = Mock()
        mock.invoke = Mock(
            return_value=AIMessage(
                content="This is extracted text from a scanned document.\n\n"
                "Section 1: Introduction\n"
                "This document contains important information.\n\n"
                "Section 2: Details\n"
                "More detailed content here."
            )
        )
        return mock

    @pytest.fixture
    def extractor(self, mock_vllm_text_response):
        """Create image extractor with mocked text extraction."""
        with patch(
            "src.preprocessing.extractors.image.VLLMLLMWrapper",
            return_value=mock_vllm_text_response,
        ):
            return ImageExtractor(
                default_mode=ImageExtractionMode.TEXT, verify_connection=False
            )

    @pytest.fixture
    def sample_document_image(self):
        """Create a sample document image (white background with black text simulation)."""
        # Create a simple white image
        img = Image.new("RGB", (800, 600), color="white")
        buffer = io.BytesIO()
        img.save(buffer, format="PNG")
        buffer.seek(0)
        return buffer

    def test_extract_text_from_document_image(self, extractor, sample_document_image):
        """Test text extraction from document image."""
        result = extractor.extract(
            sample_document_image, "document.png", mode=ImageExtractionMode.TEXT
        )

        assert isinstance(result, ExtractionResult)
        assert result.content_type == ContentType.IMAGE_TEXT
        assert len(result.text) > 0
        assert "extracted text" in result.text.lower()

    def test_text_mode_metadata_includes_model_info(
        self, extractor, sample_document_image
    ):
        """Test that metadata includes vLLM model information."""
        result = extractor.extract(
            sample_document_image, "doc.png", mode=ImageExtractionMode.TEXT
        )

        assert "vllm_model_used" in result.metadata
        assert "extraction_mode" in result.metadata
        assert result.metadata["extraction_mode"] == ImageExtractionMode.TEXT.value

    def test_text_mode_includes_image_dimensions(
        self, extractor, sample_document_image
    ):
        """Test that metadata includes image dimensions."""
        result = extractor.extract(
            sample_document_image, "doc.png", mode=ImageExtractionMode.TEXT
        )

        assert "original_dimensions" in result.metadata
        assert "width" in result.metadata["original_dimensions"]
        assert "height" in result.metadata["original_dimensions"]
        assert result.metadata["original_dimensions"]["width"] == 800
        assert result.metadata["original_dimensions"]["height"] == 600

    def test_text_mode_quality_indicators(self, extractor, sample_document_image):
        """Test quality indicators for text extraction."""
        result = extractor.extract(
            sample_document_image, "doc.png", mode=ImageExtractionMode.TEXT
        )

        assert result.quality_indicators is not None
        assert "text_length" in result.quality_indicators
        assert "word_count" in result.quality_indicators
        assert "confidence_score" in result.quality_indicators
        assert "image_area_pixels" in result.quality_indicators

    def test_text_mode_with_arabic_content(self, extractor):
        """Test text extraction from Arabic document image."""
        # Mock Arabic text response
        with patch.object(
            extractor.llm,
            "invoke",
            return_value=AIMessage(
                content="مرحبا بك في النظام\n\nالفقرة الأولى: معلومات مهمة\n"
                "هذا نص تجريبي باللغة العربية من صورة ممسوحة ضوئيا."
            ),
        ):
            img = Image.new("RGB", (800, 600), color="white")
            buffer = io.BytesIO()
            img.save(buffer, format="PNG")
            buffer.seek(0)

            result = extractor.extract(
                buffer, "arabic_doc.png", mode=ImageExtractionMode.TEXT
            )

            assert "مرحبا" in result.text
            assert "العربية" in result.text
            assert result.content_type == ContentType.IMAGE_TEXT

    def test_text_mode_warns_on_short_extraction(self, extractor, sample_document_image):
        """Test warning when extracted text is very short."""
        # Mock short response
        with patch.object(
            extractor.llm, "invoke", return_value=AIMessage(content="Short")
        ):
            result = extractor.extract(
                sample_document_image, "short.png", mode=ImageExtractionMode.TEXT
            )

            # Should have warning about short extraction
            assert len(result.warnings) > 0
            assert any("short" in w.lower() for w in result.warnings)


class TestDescriptionMode:
    """Test description mode for charts, photos, and diagrams."""

    @pytest.fixture
    def mock_vllm_description_response(self):
        """Create mock vLLM with description response."""
        mock = Mock()
        mock.invoke = Mock(
            return_value=AIMessage(
                content="This is a bar chart showing quarterly sales performance. "
                "The chart displays four bars representing Q1 through Q4, with values "
                "ranging from $50K to $120K. Q4 shows the highest sales at $120K, "
                "while Q2 had the lowest at $50K. The trend indicates strong growth "
                "in the second half of the year."
            )
        )
        return mock

    @pytest.fixture
    def extractor(self, mock_vllm_description_response):
        """Create image extractor with mocked description extraction."""
        with patch(
            "src.preprocessing.extractors.image.VLLMLLMWrapper",
            return_value=mock_vllm_description_response,
        ):
            return ImageExtractor(
                default_mode=ImageExtractionMode.DESCRIPTION, verify_connection=False
            )

    @pytest.fixture
    def sample_chart_image(self):
        """Create a sample chart image (colorful bars simulation)."""
        img = Image.new("RGB", (1024, 768), color="white")
        buffer = io.BytesIO()
        img.save(buffer, format="PNG")
        buffer.seek(0)
        return buffer

    def test_extract_description_from_chart(self, extractor, sample_chart_image):
        """Test description generation from chart image."""
        result = extractor.extract(
            sample_chart_image, "chart.png", mode=ImageExtractionMode.DESCRIPTION
        )

        assert isinstance(result, ExtractionResult)
        assert result.content_type == ContentType.IMAGE_DESCRIPTION
        assert len(result.text) > 0
        assert "chart" in result.text.lower() or "bar" in result.text.lower()

    def test_description_mode_metadata(self, extractor, sample_chart_image):
        """Test metadata for description mode."""
        result = extractor.extract(
            sample_chart_image, "diagram.png", mode=ImageExtractionMode.DESCRIPTION
        )

        assert result.metadata["extraction_mode"] == ImageExtractionMode.DESCRIPTION.value
        assert "image_format" in result.metadata
        assert "file_hash" in result.metadata

    def test_description_mode_with_photo(self, extractor):
        """Test description generation from photo."""
        # Mock photo description
        with patch.object(
            extractor.llm,
            "invoke",
            return_value=AIMessage(
                content="This photo shows a modern office workspace with natural lighting. "
                "The image features a desk with a laptop, monitor, and keyboard. "
                "In the background, there are bookshelves and plants. "
                "The overall aesthetic is minimalist and professional."
            ),
        ):
            img = Image.new("RGB", (1920, 1080), color="lightblue")
            buffer = io.BytesIO()
            img.save(buffer, format="JPEG")
            buffer.seek(0)

            result = extractor.extract(
                buffer, "office.jpg", mode=ImageExtractionMode.DESCRIPTION
            )

            assert "office" in result.text.lower() or "workspace" in result.text.lower()
            assert result.content_type == ContentType.IMAGE_DESCRIPTION

    def test_description_mode_quality_indicators(self, extractor, sample_chart_image):
        """Test quality indicators for description mode."""
        result = extractor.extract(
            sample_chart_image, "chart.png", mode=ImageExtractionMode.DESCRIPTION
        )

        assert result.quality_indicators is not None
        assert result.quality_indicators["extraction_mode"] == ImageExtractionMode.DESCRIPTION.value
        assert "confidence_score" in result.quality_indicators


class TestAutoDetectionMode:
    """Test automatic content type detection mode."""

    @pytest.fixture
    def mock_vllm_auto_detect(self):
        """Create mock vLLM for auto-detection."""
        mock = Mock()

        def side_effect_invoke(messages):
            prompt = messages[0].content[0]["text"]
            if "determine its primary content type" in prompt.lower():
                # Auto-detection prompt
                return AIMessage(content="TEXT_DOCUMENT")
            else:
                # Actual extraction
                return AIMessage(content="Extracted content from detected mode")

        mock.invoke = Mock(side_effect=side_effect_invoke)
        return mock

    @pytest.fixture
    def extractor(self, mock_vllm_auto_detect):
        """Create image extractor with auto-detection."""
        with patch(
            "src.preprocessing.extractors.image.VLLMLLMWrapper",
            return_value=mock_vllm_auto_detect,
        ):
            return ImageExtractor(
                default_mode=ImageExtractionMode.AUTO, verify_connection=False
            )

    def test_auto_detect_text_document(self, extractor):
        """Test auto-detection of text document image."""
        img = Image.new("RGB", (800, 600), color="white")
        buffer = io.BytesIO()
        img.save(buffer, format="PNG")
        buffer.seek(0)

        result = extractor.extract(buffer, "scanned_doc.png", mode=ImageExtractionMode.AUTO)

        assert "auto_detected_mode" in result.metadata
        # Should detect TEXT mode
        assert result.metadata["auto_detected_mode"] in [
            ImageExtractionMode.TEXT.value,
            "TEXT",
        ]

    def test_auto_detect_visual_content(self, extractor):
        """Test auto-detection of visual content (chart/photo)."""
        # Mock visual content detection
        def visual_detect_side_effect(messages):
            prompt = messages[0].content[0]["text"]
            if "determine its primary content type" in prompt.lower():
                return AIMessage(content="VISUAL_CONTENT")
            else:
                return AIMessage(content="Description of visual content")

        with patch.object(extractor.llm, "invoke", side_effect=visual_detect_side_effect):
            img = Image.new("RGB", (1024, 768), color="blue")
            buffer = io.BytesIO()
            img.save(buffer, format="PNG")
            buffer.seek(0)

            result = extractor.extract(
                buffer, "chart.png", mode=ImageExtractionMode.AUTO
            )

            assert result.metadata["auto_detected_mode"] in [
                ImageExtractionMode.DESCRIPTION.value,
                "DESCRIPTION",
            ]
            assert result.content_type == ContentType.IMAGE_DESCRIPTION

    def test_auto_detect_fallback_on_unclear_response(self, extractor):
        """Test fallback to DESCRIPTION when auto-detection is unclear."""
        # Mock unclear response
        def unclear_detect_side_effect(messages):
            prompt = messages[0].content[0]["text"]
            if "determine its primary content type" in prompt.lower():
                return AIMessage(content="UNCLEAR_RESPONSE")
            else:
                return AIMessage(content="Fallback description content")

        with patch.object(extractor.llm, "invoke", side_effect=unclear_detect_side_effect):
            img = Image.new("RGB", (800, 600), color="white")
            buffer = io.BytesIO()
            img.save(buffer, format="PNG")
            buffer.seek(0)

            result = extractor.extract(
                buffer, "unclear.png", mode=ImageExtractionMode.AUTO
            )

            # Should default to DESCRIPTION and have warning
            assert len(result.warnings) > 0
            assert any("auto-detection" in w.lower() for w in result.warnings)

    def test_auto_detect_handles_exceptions(self, extractor):
        """Test that auto-detection handles exceptions gracefully."""
        # Mock exception during detection
        def exception_side_effect(messages):
            prompt = messages[0].content[0]["text"]
            if "determine its primary content type" in prompt.lower():
                raise Exception("Detection failed")
            else:
                return AIMessage(content="Fallback content")

        with patch.object(extractor.llm, "invoke", side_effect=exception_side_effect):
            img = Image.new("RGB", (800, 600), color="white")
            buffer = io.BytesIO()
            img.save(buffer, format="PNG")
            buffer.seek(0)

            result = extractor.extract(
                buffer, "error.png", mode=ImageExtractionMode.AUTO
            )

            # Should fall back to DESCRIPTION mode
            assert result.content_type in [
                ContentType.IMAGE_DESCRIPTION,
                ContentType.IMAGE_TEXT,
            ]
            # Should have warning about detection failure
            assert len(result.warnings) > 0


class TestMultiPageTIFF:
    """Test multi-page TIFF image processing."""

    @pytest.fixture
    def mock_vllm_multipage(self):
        """Create mock vLLM for multi-page extraction."""
        mock = Mock()
        call_count = [0]

        def multipage_side_effect(messages):
            call_count[0] += 1
            return AIMessage(content=f"Page {call_count[0]} content extracted here.")

        mock.invoke = Mock(side_effect=multipage_side_effect)
        return mock

    @pytest.fixture
    def extractor(self, mock_vllm_multipage):
        """Create image extractor for TIFF processing."""
        with patch(
            "src.preprocessing.extractors.image.VLLMLLMWrapper",
            return_value=mock_vllm_multipage,
        ):
            return ImageExtractor(
                default_mode=ImageExtractionMode.TEXT, verify_connection=False
            )

    @pytest.fixture
    def multi_page_tiff(self):
        """Create a multi-page TIFF image."""
        # Create 3-page TIFF
        images = [
            Image.new("RGB", (800, 600), color="white"),
            Image.new("RGB", (800, 600), color="lightgray"),
            Image.new("RGB", (800, 600), color="gray"),
        ]

        buffer = io.BytesIO()
        images[0].save(
            buffer,
            format="TIFF",
            save_all=True,
            append_images=images[1:],
        )
        buffer.seek(0)
        return buffer

    def test_extract_multipage_tiff(self, extractor, multi_page_tiff):
        """Test extraction from multi-page TIFF."""
        result = extractor.extract(
            multi_page_tiff, "document.tiff", mode=ImageExtractionMode.TEXT
        )

        assert isinstance(result, ExtractionResult)
        assert result.metadata.get("is_multipage") is True
        assert result.metadata.get("num_pages_total") == 3
        assert result.metadata.get("num_pages_processed") == 3

    def test_multipage_tiff_combines_pages(self, extractor, multi_page_tiff):
        """Test that multi-page TIFF combines all page content."""
        result = extractor.extract(
            multi_page_tiff, "document.tiff", mode=ImageExtractionMode.TEXT
        )

        # Should contain page break markers
        assert "---PAGE_BREAK---" in result.text
        # Should have content from multiple pages
        assert len(result.text.split("---PAGE_BREAK---")) == 3

    def test_multipage_tiff_page_limit(self, extractor):
        """Test that max_pages option limits page processing."""
        # Create 5-page TIFF
        images = [Image.new("RGB", (800, 600), color="white") for _ in range(5)]
        buffer = io.BytesIO()
        images[0].save(buffer, format="TIFF", save_all=True, append_images=images[1:])
        buffer.seek(0)

        result = extractor.extract(
            buffer, "long.tiff", mode=ImageExtractionMode.TEXT, max_pages=3
        )

        assert result.metadata["num_pages_total"] == 5
        assert result.metadata["num_pages_processed"] == 3
        # Should have warning about page limit
        assert len(result.warnings) > 0
        assert any("processing only first 3" in w.lower() for w in result.warnings)

    def test_multipage_tiff_quality_indicators(self, extractor, multi_page_tiff):
        """Test quality indicators for multi-page TIFF."""
        result = extractor.extract(
            multi_page_tiff, "document.tiff", mode=ImageExtractionMode.TEXT
        )

        assert result.quality_indicators is not None
        assert "total_pages" in result.quality_indicators
        assert "pages_processed" in result.quality_indicators
        assert "pages_extracted" in result.quality_indicators
        assert "extraction_success_rate" in result.quality_indicators
        assert result.quality_indicators["extraction_success_rate"] == 1.0

    def test_multipage_tiff_page_metadata(self, extractor, multi_page_tiff):
        """Test that page-level metadata is tracked."""
        result = extractor.extract(
            multi_page_tiff, "document.tiff", mode=ImageExtractionMode.TEXT
        )

        assert "pages_data" in result.metadata
        assert len(result.metadata["pages_data"]) == 3

        # Each page should have metadata
        for page_data in result.metadata["pages_data"]:
            assert "page_number" in page_data
            assert "text_length" in page_data
            assert "content_type" in page_data

    def test_multipage_tiff_handles_page_errors(self, extractor):
        """Test handling of errors on individual pages."""
        # Mock error on page 2
        call_count = [0]

        def error_on_page_2(messages):
            call_count[0] += 1
            if call_count[0] == 2:
                raise Exception("Page 2 extraction failed")
            return AIMessage(content=f"Page {call_count[0]} content")

        with patch.object(extractor.llm, "invoke", side_effect=error_on_page_2):
            images = [Image.new("RGB", (800, 600), color="white") for _ in range(3)]
            buffer = io.BytesIO()
            images[0].save(
                buffer, format="TIFF", save_all=True, append_images=images[1:]
            )
            buffer.seek(0)

            result = extractor.extract(
                buffer, "error.tiff", mode=ImageExtractionMode.TEXT
            )

            # Should have warning about page 2 failure
            assert len(result.warnings) > 0
            # Should still extract other pages
            assert len(result.text) > 0


class TestQualityIndicators:
    """Test extraction quality indicators and confidence scores."""

    @pytest.fixture
    def mock_vllm(self):
        """Create mock vLLM."""
        mock = Mock()
        mock.invoke = Mock(
            return_value=AIMessage(
                content="Detailed extracted text content with good length "
                "and comprehensive information from the image."
            )
        )
        return mock

    @pytest.fixture
    def extractor(self, mock_vllm):
        """Create image extractor."""
        with patch(
            "src.preprocessing.extractors.image.VLLMLLMWrapper", return_value=mock_vllm
        ):
            return ImageExtractor(verify_connection=False)

    def test_quality_indicators_include_text_metrics(self, extractor):
        """Test that quality indicators include text-based metrics."""
        img = Image.new("RGB", (800, 600), color="white")
        buffer = io.BytesIO()
        img.save(buffer, format="PNG")
        buffer.seek(0)

        result = extractor.extract(buffer, "test.png", mode=ImageExtractionMode.TEXT)

        assert "text_length" in result.quality_indicators
        assert "word_count" in result.quality_indicators
        assert result.quality_indicators["text_length"] > 0
        assert result.quality_indicators["word_count"] > 0

    def test_quality_indicators_include_image_metrics(self, extractor):
        """Test that quality indicators include image-based metrics."""
        img = Image.new("RGB", (1024, 768), color="white")
        buffer = io.BytesIO()
        img.save(buffer, format="PNG")
        buffer.seek(0)

        result = extractor.extract(buffer, "test.png", mode=ImageExtractionMode.TEXT)

        assert "image_width" in result.quality_indicators
        assert "image_height" in result.quality_indicators
        assert "image_area_pixels" in result.quality_indicators
        assert "aspect_ratio" in result.quality_indicators
        assert result.quality_indicators["image_width"] == 1024
        assert result.quality_indicators["image_height"] == 768

    def test_confidence_score_calculation(self, extractor):
        """Test that confidence score is calculated."""
        img = Image.new("RGB", (800, 600), color="white")
        buffer = io.BytesIO()
        img.save(buffer, format="PNG")
        buffer.seek(0)

        result = extractor.extract(buffer, "test.png", mode=ImageExtractionMode.TEXT)

        assert "confidence_score" in result.quality_indicators
        assert 0 <= result.quality_indicators["confidence_score"] <= 1.0

    def test_low_confidence_warning(self, extractor):
        """Test warning when confidence score is low."""
        # Mock very short extraction (low confidence)
        with patch.object(
            extractor.llm, "invoke", return_value=AIMessage(content="X")
        ):
            img = Image.new("RGB", (800, 600), color="white")
            buffer = io.BytesIO()
            img.save(buffer, format="PNG")
            buffer.seek(0)

            result = extractor.extract(
                buffer, "low.png", mode=ImageExtractionMode.TEXT
            )

            # Should have low confidence warning
            assert len(result.warnings) > 0
            assert any("confidence" in w.lower() or "short" in w.lower() for w in result.warnings)


class TestImageFormats:
    """Test support for various image formats."""

    @pytest.fixture
    def mock_vllm(self):
        """Create mock vLLM."""
        mock = Mock()
        mock.invoke = Mock(return_value=AIMessage(content="Extracted content"))
        return mock

    @pytest.fixture
    def extractor(self, mock_vllm):
        """Create image extractor."""
        with patch(
            "src.preprocessing.extractors.image.VLLMLLMWrapper", return_value=mock_vllm
        ):
            return ImageExtractor(verify_connection=False)

    def test_extract_from_png(self, extractor):
        """Test extraction from PNG image."""
        img = Image.new("RGB", (800, 600), color="white")
        buffer = io.BytesIO()
        img.save(buffer, format="PNG")
        buffer.seek(0)

        result = extractor.extract(buffer, "test.png", mode=ImageExtractionMode.TEXT)

        assert result.metadata["image_format"] == "PNG"
        assert len(result.text) > 0

    def test_extract_from_jpeg(self, extractor):
        """Test extraction from JPEG image."""
        img = Image.new("RGB", (800, 600), color="white")
        buffer = io.BytesIO()
        img.save(buffer, format="JPEG")
        buffer.seek(0)

        result = extractor.extract(buffer, "test.jpg", mode=ImageExtractionMode.TEXT)

        assert result.metadata["image_format"] == "JPEG"

    def test_extract_from_webp(self, extractor):
        """Test extraction from WebP image."""
        img = Image.new("RGB", (800, 600), color="white")
        buffer = io.BytesIO()
        img.save(buffer, format="WEBP")
        buffer.seek(0)

        result = extractor.extract(buffer, "test.webp", mode=ImageExtractionMode.TEXT)

        assert result.metadata["image_format"] == "WEBP"

    def test_extract_from_bmp(self, extractor):
        """Test extraction from BMP image."""
        img = Image.new("RGB", (800, 600), color="white")
        buffer = io.BytesIO()
        img.save(buffer, format="BMP")
        buffer.seek(0)

        result = extractor.extract(buffer, "test.bmp", mode=ImageExtractionMode.TEXT)

        assert result.metadata["image_format"] == "BMP"


class TestErrorHandling:
    """Test error handling and edge cases."""

    @pytest.fixture
    def mock_vllm(self):
        """Create mock vLLM."""
        mock = Mock()
        mock.invoke = Mock(return_value=AIMessage(content="Valid content"))
        return mock

    @pytest.fixture
    def extractor(self, mock_vllm):
        """Create image extractor."""
        with patch(
            "src.preprocessing.extractors.image.VLLMLLMWrapper", return_value=mock_vllm
        ):
            return ImageExtractor(verify_connection=False)

    def test_vllm_not_available(self):
        """Test handling when vLLM server is not available."""
        with patch(
            "src.preprocessing.extractors.image.VLLMLLMWrapper",
            side_effect=VLLMConnectionError("Server not available"),
        ):
            extractor = ImageExtractor(verify_connection=False)

            img = Image.new("RGB", (800, 600), color="white")
            buffer = io.BytesIO()
            img.save(buffer, format="PNG")
            buffer.seek(0)

            result = extractor.extract(
                buffer, "test.png", mode=ImageExtractionMode.TEXT
            )

            # Should return empty result with warning
            assert result.text == ""
            assert len(result.warnings) > 0
            assert any("vllm" in w.lower() or "not available" in w.lower() for w in result.warnings)

    def test_corrupted_image_file(self, extractor):
        """Test handling of corrupted image file."""
        corrupted_data = b"This is not a valid image file"
        buffer = io.BytesIO(corrupted_data)

        result = extractor.extract(buffer, "corrupt.png", mode=ImageExtractionMode.TEXT)

        # Should handle gracefully
        assert result.text == ""
        assert len(result.warnings) > 0
        assert any("loading failed" in w.lower() or "failed" in w.lower() for w in result.warnings)

    def test_empty_image_file(self, extractor):
        """Test handling of empty image file."""
        buffer = io.BytesIO(b"")

        result = extractor.extract(buffer, "empty.png", mode=ImageExtractionMode.TEXT)

        assert result.text == ""
        assert len(result.warnings) > 0

    def test_vllm_extraction_error(self, extractor):
        """Test handling of vLLM extraction errors."""
        # Mock vLLM error
        with patch.object(
            extractor.llm,
            "invoke",
            side_effect=VLLMConnectionError("Request failed"),
        ):
            img = Image.new("RGB", (800, 600), color="white")
            buffer = io.BytesIO()
            img.save(buffer, format="PNG")
            buffer.seek(0)

            result = extractor.extract(
                buffer, "error.png", mode=ImageExtractionMode.TEXT
            )

            assert result.text == ""
            assert len(result.warnings) > 0
            assert any("vllm" in w.lower() or "error" in w.lower() for w in result.warnings)

    def test_extraction_generic_exception(self, extractor):
        """Test handling of generic exceptions during extraction."""
        # Mock generic error
        with patch.object(
            extractor.llm, "invoke", side_effect=Exception("Unexpected error")
        ):
            img = Image.new("RGB", (800, 600), color="white")
            buffer = io.BytesIO()
            img.save(buffer, format="PNG")
            buffer.seek(0)

            result = extractor.extract(
                buffer, "error.png", mode=ImageExtractionMode.TEXT
            )

            assert result.text == ""
            assert len(result.warnings) > 0
            assert any("extraction failed" in w.lower() for w in result.warnings)


class TestMetadataExtraction:
    """Test metadata extraction from images."""

    @pytest.fixture
    def mock_vllm(self):
        """Create mock vLLM."""
        mock = Mock()
        mock.invoke = Mock(return_value=AIMessage(content="Extracted content"))
        return mock

    @pytest.fixture
    def extractor(self, mock_vllm):
        """Create image extractor."""
        with patch(
            "src.preprocessing.extractors.image.VLLMLLMWrapper", return_value=mock_vllm
        ):
            return ImageExtractor(verify_connection=False)

    def test_metadata_includes_file_hash(self, extractor):
        """Test that metadata includes file hash."""
        img = Image.new("RGB", (800, 600), color="white")
        buffer = io.BytesIO()
        img.save(buffer, format="PNG")
        buffer.seek(0)

        result = extractor.extract(buffer, "test.png", mode=ImageExtractionMode.TEXT)

        assert "file_hash" in result.metadata
        assert len(result.metadata["file_hash"]) == 64  # SHA256 hex

    def test_metadata_includes_file_size(self, extractor):
        """Test that metadata includes file size."""
        img = Image.new("RGB", (800, 600), color="white")
        buffer = io.BytesIO()
        img.save(buffer, format="PNG")
        buffer.seek(0)

        result = extractor.extract(buffer, "test.png", mode=ImageExtractionMode.TEXT)

        assert "file_size_bytes" in result.metadata
        assert result.metadata["file_size_bytes"] > 0

    def test_metadata_includes_image_mode(self, extractor):
        """Test that metadata includes PIL image mode (RGB, RGBA, etc.)."""
        img = Image.new("RGBA", (800, 600), color=(255, 255, 255, 255))
        buffer = io.BytesIO()
        img.save(buffer, format="PNG")
        buffer.seek(0)

        result = extractor.extract(buffer, "rgba.png", mode=ImageExtractionMode.TEXT)

        assert "image_mode" in result.metadata
        assert result.metadata["image_mode"] in ["RGBA", "RGB"]
