"""
Image extractor using vision-capable LLM for text extraction and description.

Uses VLLMLLMWrapper with vision-capable models to extract text from document images
or generate searchable descriptions for charts/photos/diagrams. Supports multi-page
TIFF processing and auto-detection of image content type.
"""

import base64
import hashlib
import io
from typing import Any, BinaryIO

from langchain_core.messages import HumanMessage
from loguru import logger
from PIL import Image

from src.config.settings import settings
from src.models.schemas import ContentType, ExtractionResult, ImageExtractionMode
from src.models.vllm_model import VLLMConnectionError, VLLMLLMWrapper
from src.preprocessing.extractors.base import BaseExtractor


class ImageExtractor(BaseExtractor):
    """
    Extract text or descriptions from images using vision-capable LLM.

    Features:
    - Text extraction from document images (OCR-like)
    - Description generation for charts, photos, diagrams
    - Auto-detection of image content type
    - Multi-page TIFF support
    - Quality indicators and confidence warnings

    Supports image formats: PNG, JPEG, TIFF, BMP, GIF, WebP
    """

    # Prompts for different extraction modes
    TEXT_EXTRACTION_PROMPT = """Extract ALL text visible in this document image.

Instructions:
- Preserve the original layout and reading order as much as possible
- Include all text: headings, body text, captions, labels, footnotes
- Maintain paragraph structure and line breaks where appropriate
- For tables, preserve the tabular format
- For Arabic text, maintain right-to-left reading order
- If the image is rotated, extract as if properly oriented
- If text is unclear or blurry, make your best attempt but indicate uncertainty with [?]

Output the extracted text ONLY, without any preamble or commentary."""

    DESCRIPTION_PROMPT = """Describe this image in detail for searchability and information retrieval.

Instructions:
- Identify the type of visual content (chart, diagram, photo, infographic, etc.)
- Describe key visual elements, data points, and relationships
- Extract any visible text labels, titles, or legends
- Explain what information or insight the image conveys
- For charts/graphs: describe trends, comparisons, or patterns
- For diagrams: explain the structure, components, and connections
- For photos: describe the subject, context, and relevant details
- Use clear, searchable language
- Support both Arabic and English content

Provide a comprehensive description that would help someone understand the image without seeing it."""

    AUTO_DETECTION_PROMPT = """Analyze this image and determine its primary content type.

Respond with EXACTLY ONE of these categories:
- TEXT_DOCUMENT: Image contains primarily readable text (scanned document, screenshot of text, etc.)
- VISUAL_CONTENT: Image contains primarily visual elements (chart, diagram, photo, infographic, etc.)

Consider:
- If >60% of image area contains readable text in paragraphs/sentences, it's TEXT_DOCUMENT
- If the image has charts, diagrams, illustrations, photos as primary content, it's VISUAL_CONTENT
- For mixed content, prioritize based on information value

Respond with just the category name, nothing else."""

    def __init__(
        self,
        base_url: str | None = None,
        model_name: str | None = None,
        default_mode: ImageExtractionMode = ImageExtractionMode.AUTO,
        verify_connection: bool = False,  # Don't verify by default for image extraction
    ):
        """
        Initialize image extractor with vision-capable LLM.

        Args:
            base_url: vLLM server URL (defaults to settings.vllm_base_url)
            model_name: Vision-capable model name (defaults to settings.vllm_model)
            default_mode: Default extraction mode (AUTO, TEXT, or DESCRIPTION)
            verify_connection: Whether to verify vLLM connection on init
                             (set to False by default to avoid startup delays)

        Note:
            For vision tasks, ensure you're using a vision-capable model like:
            - llava-1.5-7b-hf
            - llava-1.5-13b-hf
            - bakLlava-v1-hf
            - claude-3-opus (via OpenRouter)
            - gpt-4-vision-preview (via OpenAI API)
        """
        self.default_mode = default_mode
        self.base_url = base_url or settings.vllm_base_url
        self.model_name = model_name or settings.vllm_model

        # Initialize LLM wrapper (delay connection verification)
        try:
            self.llm = VLLMLLMWrapper(
                base_url=self.base_url,
                model_name=self.model_name,
                verify_connection=verify_connection,
            )
        except VLLMConnectionError as e:
            logger.warning(f"Failed to connect to vLLM server: {e}")
            logger.warning("Image extraction will fail until vLLM server is available")
            self.llm = None

    def extract(self, file_content: BinaryIO, filename: str, **options: Any) -> ExtractionResult:
        """
        Extract text or description from image using vision LLM.

        Pipeline:
        1. Load image and extract dimensions
        2. Determine extraction mode (auto-detect if needed)
        3. Convert image to base64 for LLM input
        4. For multi-page TIFF: process each page
        5. Send to vision LLM with appropriate prompt
        6. Parse response and compile metadata
        7. Generate quality indicators

        Args:
            file_content: Binary image file stream
            filename: Original filename
            **options: Additional options:
                - mode: ImageExtractionMode override (AUTO, TEXT, DESCRIPTION)
                - max_pages: int - Limit number of pages for TIFF (default: 10)
                - confidence_threshold: float - Minimum confidence for auto-detection (0-1)

        Returns:
            ExtractionResult with:
                - text: Extracted text or description
                - content_type: IMAGE_TEXT or IMAGE_DESCRIPTION
                - metadata: Image metadata (dimensions, format, mode, model, etc.)
                - quality_indicators: Confidence scores and metrics
                - warnings: Issues encountered (low confidence, connection errors, etc.)

        Raises:
            ValueError: If image cannot be loaded or is corrupted
            VLLMConnectionError: If vLLM server is not available
        """
        if self.llm is None:
            return ExtractionResult(
                text="",
                content_type=ContentType.IMAGE_TEXT,
                metadata={"source": filename, "source_format": "image"},
                warnings=["vLLM server not available. Cannot extract from images."],
            )

        warnings = []
        mode = options.get("mode", self.default_mode)
        max_pages = options.get("max_pages", 10)

        # Calculate file hash
        file_content.seek(0)
        image_bytes = file_content.read()
        file_hash = hashlib.sha256(image_bytes).hexdigest()
        file_content.seek(0)

        metadata = {
            "source": filename,
            "source_format": "image",
            "file_hash": file_hash,
            "file_size_bytes": len(image_bytes),
            "vllm_model_used": self.model_name,
        }

        try:
            # Load image with PIL
            image = Image.open(io.BytesIO(image_bytes))

            # Extract image metadata
            metadata.update(
                {
                    "image_format": image.format,
                    "original_dimensions": {"width": image.width, "height": image.height},
                    "image_mode": image.mode,  # RGB, RGBA, L, etc.
                }
            )

            # Check if multi-page TIFF
            is_multipage = hasattr(image, "n_frames") and image.n_frames > 1

            if is_multipage:
                return self._extract_multipage_tiff(
                    image, filename, metadata, warnings, mode, max_pages
                )
            else:
                return self._extract_single_image(image, filename, metadata, warnings, mode)

        except Exception as e:
            error_msg = f"Image loading failed: {str(e)}"
            logger.error(error_msg)
            warnings.append(error_msg)

            return ExtractionResult(
                text="",
                content_type=ContentType.IMAGE_TEXT,
                metadata=metadata,
                warnings=warnings,
            )

    def _extract_single_image(
        self,
        image: Image.Image,
        filename: str,
        metadata: dict,
        warnings: list,
        mode: ImageExtractionMode,
    ) -> ExtractionResult:
        """
        Extract content from a single image.

        Args:
            image: PIL Image object
            filename: Original filename
            metadata: Metadata dictionary to update
            warnings: Warnings list to append to
            mode: Extraction mode (AUTO, TEXT, DESCRIPTION)

        Returns:
            ExtractionResult with extracted content
        """
        # Auto-detect content type if needed
        if mode == ImageExtractionMode.AUTO:
            detected_mode = self._auto_detect_content_type(image, warnings)
            mode = detected_mode
            metadata["auto_detected_mode"] = detected_mode.value

        metadata["extraction_mode"] = mode.value

        # Convert image to base64
        image_base64 = self._image_to_base64(image)

        # Choose prompt based on mode
        if mode == ImageExtractionMode.TEXT:
            prompt = self.TEXT_EXTRACTION_PROMPT
            content_type = ContentType.IMAGE_TEXT
        else:  # DESCRIPTION
            prompt = self.DESCRIPTION_PROMPT
            content_type = ContentType.IMAGE_DESCRIPTION

        # Extract content using vision LLM
        try:
            extracted_text = self._call_vision_llm(image_base64, prompt)

            # Calculate quality indicators
            quality_indicators = self._calculate_quality_indicators(extracted_text, image, mode)

            # Check for quality issues
            if quality_indicators.get("text_length", 0) < 20:
                warnings.append(
                    "Very short extraction result. Image may be low quality, "
                    "empty, or model may have failed to extract content."
                )

            if quality_indicators.get("confidence_score", 1.0) < 0.5:
                warnings.append(
                    f"Low confidence extraction (score: {quality_indicators['confidence_score']:.2f}). "
                    "Results may be unreliable."
                )

            return ExtractionResult(
                text=extracted_text,
                content_type=content_type,
                metadata=metadata,
                quality_indicators=quality_indicators,
                warnings=warnings,
            )

        except VLLMConnectionError as e:
            error_msg = f"vLLM connection error: {str(e)}"
            logger.error(error_msg)
            warnings.append(error_msg)

            return ExtractionResult(
                text="",
                content_type=content_type,
                metadata=metadata,
                warnings=warnings,
            )
        except Exception as e:
            error_msg = f"Image extraction failed: {str(e)}"
            logger.error(error_msg)
            warnings.append(error_msg)

            return ExtractionResult(
                text="",
                content_type=content_type,
                metadata=metadata,
                warnings=warnings,
            )

    def _extract_multipage_tiff(
        self,
        image: Image.Image,
        filename: str,
        metadata: dict,
        warnings: list,
        mode: ImageExtractionMode,
        max_pages: int,
    ) -> ExtractionResult:
        """
        Extract content from multi-page TIFF image.

        Processes each page separately and combines results.

        Args:
            image: PIL Image object (TIFF with multiple frames)
            filename: Original filename
            metadata: Metadata dictionary to update
            warnings: Warnings list to append to
            mode: Extraction mode
            max_pages: Maximum number of pages to process

        Returns:
            ExtractionResult with combined content from all pages
        """
        num_pages = image.n_frames
        metadata["num_pages_total"] = num_pages
        metadata["is_multipage"] = True

        # Limit pages if needed
        pages_to_process = min(num_pages, max_pages)
        if num_pages > max_pages:
            warnings.append(f"TIFF has {num_pages} pages, processing only first {max_pages}")
        metadata["num_pages_processed"] = pages_to_process

        # Extract from each page
        page_results = []
        pages_data = []

        for page_num in range(pages_to_process):
            try:
                # Seek to page
                image.seek(page_num)

                # Extract from this page
                page_result = self._extract_single_image(
                    image, f"{filename}_page_{page_num+1}", {}, [], mode
                )

                page_results.append(page_result.text)
                pages_data.append(
                    {
                        "page_number": page_num + 1,
                        "text_length": len(page_result.text),
                        "content_type": page_result.content_type.value,
                        "warnings": page_result.warnings,
                    }
                )

            except Exception as e:
                warnings.append(f"Failed to extract page {page_num + 1}: {str(e)}")
                pages_data.append(
                    {
                        "page_number": page_num + 1,
                        "error": str(e),
                    }
                )

        # Store page-level data
        metadata["pages_data"] = pages_data
        metadata["extraction_mode"] = mode.value

        # Aggregate page-level warnings into overall warnings
        for page_data in pages_data:
            if "warnings" in page_data and page_data["warnings"]:
                for page_warning in page_data["warnings"]:
                    warnings.append(f"Page {page_data['page_number']}: {page_warning}")

        # Combine all page results
        combined_text = "\n\n---PAGE_BREAK---\n\n".join(result for result in page_results if result)

        # Determine content type based on mode
        if mode == ImageExtractionMode.TEXT:
            content_type = ContentType.IMAGE_TEXT
        else:
            content_type = ContentType.IMAGE_DESCRIPTION

        # Calculate overall quality indicators
        quality_indicators = {
            "total_pages": num_pages,
            "pages_processed": pages_to_process,
            "pages_extracted": len([p for p in pages_data if "error" not in p]),
            "total_text_length": len(combined_text),
            "avg_text_per_page": len(combined_text) / pages_to_process
            if pages_to_process > 0
            else 0,
            "extraction_success_rate": (
                len([p for p in pages_data if "error" not in p]) / pages_to_process
                if pages_to_process > 0
                else 0
            ),
        }

        return ExtractionResult(
            text=combined_text,
            content_type=content_type,
            metadata=metadata,
            quality_indicators=quality_indicators,
            warnings=warnings,
        )

    def _auto_detect_content_type(self, image: Image.Image, warnings: list) -> ImageExtractionMode:
        """
        Auto-detect whether image contains primarily text or visual content.

        Uses vision LLM to classify the image content type.

        Args:
            image: PIL Image object
            warnings: Warnings list to append detection issues

        Returns:
            Detected ImageExtractionMode (TEXT or DESCRIPTION)
        """
        try:
            image_base64 = self._image_to_base64(image)
            response = self._call_vision_llm(image_base64, self.AUTO_DETECTION_PROMPT)

            # Parse response
            response_clean = response.strip().upper()

            if "TEXT_DOCUMENT" in response_clean:
                return ImageExtractionMode.TEXT
            elif "VISUAL_CONTENT" in response_clean:
                return ImageExtractionMode.DESCRIPTION
            else:
                # Default to description if unclear
                warnings.append(
                    f"Auto-detection unclear (got: {response[:50]}). Defaulting to DESCRIPTION mode."
                )
                return ImageExtractionMode.DESCRIPTION

        except Exception as e:
            logger.warning(f"Auto-detection failed: {e}. Defaulting to DESCRIPTION mode.")
            warnings.append(f"Auto-detection failed: {str(e)}. Using DESCRIPTION mode.")
            return ImageExtractionMode.DESCRIPTION

    def _image_to_base64(self, image: Image.Image) -> str:
        """
        Convert PIL Image to base64 string for LLM input.

        Args:
            image: PIL Image object

        Returns:
            Base64-encoded image string
        """
        # Convert image to RGB if needed (for consistent encoding)
        if image.mode not in ("RGB", "L"):
            image = image.convert("RGB")

        # Save to bytes buffer
        buffer = io.BytesIO()
        image.save(buffer, format="PNG")
        buffer.seek(0)

        # Encode to base64
        image_base64 = base64.b64encode(buffer.read()).decode("utf-8")
        return image_base64

    def _call_vision_llm(self, image_base64: str, prompt: str) -> str:
        """
        Call vision-capable LLM with image and prompt.

        Args:
            image_base64: Base64-encoded image
            prompt: Text prompt for the model

        Returns:
            Model response text

        Raises:
            VLLMConnectionError: If LLM request fails
        """
        # Create message with image content
        # Note: Format may vary by model - this follows OpenAI/vLLM convention
        message = HumanMessage(
            content=[
                {"type": "text", "text": prompt},
                {
                    "type": "image_url",
                    "image_url": {"url": f"data:image/png;base64,{image_base64}"},
                },
            ]
        )

        # Call LLM
        response = self.llm.invoke([message])
        return response.content

    def _calculate_quality_indicators(
        self, extracted_text: str, image: Image.Image, mode: ImageExtractionMode
    ) -> dict[str, Any]:
        """
        Calculate quality indicators for extracted content.

        Args:
            extracted_text: Extracted text content
            image: Original PIL Image
            mode: Extraction mode used

        Returns:
            Quality indicators dictionary
        """
        # Basic text metrics
        text_length = len(extracted_text)
        word_count = len(extracted_text.split())

        # Image metrics
        image_area = image.width * image.height
        aspect_ratio = image.width / image.height if image.height > 0 else 1.0

        # Estimate confidence based on text length and image size
        # More text from larger images = higher confidence
        expected_chars_per_pixel = 0.01 if mode == ImageExtractionMode.TEXT else 0.005
        expected_chars = image_area * expected_chars_per_pixel

        if expected_chars > 0:
            confidence = min(1.0, text_length / expected_chars)
        else:
            confidence = 0.5  # Default medium confidence

        # Adjust confidence based on content characteristics
        if text_length < 20:
            confidence *= 0.5  # Very short text = low confidence
        elif word_count < 5:
            confidence *= 0.7  # Few words = reduced confidence

        return {
            "text_length": text_length,
            "word_count": word_count,
            "image_width": image.width,
            "image_height": image.height,
            "image_area_pixels": image_area,
            "aspect_ratio": aspect_ratio,
            "extraction_mode": mode.value,
            "confidence_score": confidence,
            "model_used": self.model_name,
        }

    def supports_format(self, file_format: str) -> bool:
        """
        Check if this extractor supports the given format.

        Args:
            file_format: File format identifier

        Returns:
            True if format is 'image', False otherwise
        """
        return file_format.lower() == "image"
