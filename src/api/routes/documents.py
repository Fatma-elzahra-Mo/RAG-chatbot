"""
Document management endpoints.

Provides endpoints for:
- Ingesting documents into the vector store
- Batch file ingestion
- Supported file formats
"""

from typing import List, Optional

from fastapi import APIRouter, File, Form, HTTPException, UploadFile, status
from loguru import logger

from src.core.pipeline import RAGPipeline
from src.models.schemas import (
    BatchFileIngestResponse,
    DocumentIngestRequest,
    DocumentIngestResponse,
    FileFormat,
    FileIngestResponse,
    ImageExtractionMode,
)

router = APIRouter(prefix="/documents", tags=["documents"])


def get_pipeline() -> RAGPipeline:
    """Get pipeline instance."""
    from src.api.routes.chat import get_pipeline

    return get_pipeline()


@router.post("/ingest", response_model=DocumentIngestResponse, status_code=status.HTTP_201_CREATED)
async def ingest_documents(request: DocumentIngestRequest) -> DocumentIngestResponse:
    """
    Ingest documents into the vector store.

    - **texts**: List of document texts to ingest
    - **metadatas**: Optional metadata for each document
    """
    try:
        logger.info(f"Ingesting {len(request.texts)} documents")

        pipeline = get_pipeline()

        # Calculate chunks (approximate)
        from src.preprocessing.chunker import ArabicSentenceChunker

        chunker = ArabicSentenceChunker()
        total_chunks = sum(len(chunker.chunk(text)) for text in request.texts)

        # Ingest
        pipeline.ingest_documents(
            texts=request.texts,
            metadatas=request.metadatas,
        )

        return DocumentIngestResponse(
            message="Documents ingested successfully",
            documents_ingested=len(request.texts),
            chunks_created=total_chunks,
        )

    except Exception as e:
        logger.error(f"Document ingest error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error ingesting documents: {str(e)}",
        )


@router.post("/ingest/file", response_model=FileIngestResponse)
async def ingest_file(
    file: UploadFile = File(...),
    custom_metadata: Optional[str] = Form(None),
    image_mode: ImageExtractionMode = Form(ImageExtractionMode.AUTO),
    preserve_tables: bool = Form(True),
    extract_code_blocks: bool = Form(True),
) -> FileIngestResponse:
    """
    Ingest a single file and extract content for RAG.

    Supports: PDF, HTML, Markdown, Word, Plain Text, Images
    """
    import json
    import time

    try:
        start_time = time.time()

        # Validate file
        if not file.filename:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="No filename provided",
            )

        # Detect file format
        file_extension = file.filename.lower().split(".")[-1]

        # Map extension to FileFormat
        format_mapping = {
            "pdf": FileFormat.PDF,
            "html": FileFormat.HTML,
            "htm": FileFormat.HTML,
            "md": FileFormat.MARKDOWN,
            "markdown": FileFormat.MARKDOWN,
            "docx": FileFormat.DOCX,
            "txt": FileFormat.TEXT,
            "jpg": FileFormat.IMAGE,
            "jpeg": FileFormat.IMAGE,
            "png": FileFormat.IMAGE,
            "tiff": FileFormat.IMAGE,
            "tif": FileFormat.IMAGE,
        }

        detected_format = format_mapping.get(file_extension, FileFormat.UNKNOWN)

        if detected_format == FileFormat.UNKNOWN:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Unsupported file format: .{file_extension}",
            )

        # Parse custom metadata if provided
        parsed_metadata = {}
        if custom_metadata:
            try:
                parsed_metadata = json.loads(custom_metadata)
            except json.JSONDecodeError:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Invalid JSON in custom_metadata field",
                )

        # Read file content
        file_content = await file.read()
        file_size = len(file_content)

        # Validate file size (max 25MB)
        max_size = 25 * 1024 * 1024  # 25MB
        if file_size > max_size:
            raise HTTPException(
                status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                detail=f"File size ({file_size} bytes) exceeds maximum allowed size (25MB)",
            )

        logger.info(f"Ingesting file: {file.filename} ({file_size} bytes, format: {detected_format})")

        # Get pipeline
        pipeline = get_pipeline()

        # Create file-like object from bytes
        import io
        file_obj = io.BytesIO(file_content)

        # Ingest file through pipeline
        result = pipeline.ingest_file(
            file_content=file_obj,
            filename=file.filename,
            file_format=file_extension,
            custom_metadata=parsed_metadata,
            preserve_tables=preserve_tables,
        )

        logger.info(
            f"File ingestion complete: {file.filename} - "
            f"{result.chunks_created} chunks created in {result.processing_time_ms}ms"
        )

        return result

    except ValueError as e:
        logger.error(f"File ingestion validation error: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )
    except Exception as e:
        logger.error(f"File ingestion error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error ingesting file: {str(e)}",
        )


@router.post("/ingest/batch", response_model=BatchFileIngestResponse)
async def ingest_batch(
    files: List[UploadFile] = File(...),
    shared_metadata: Optional[str] = Form(None),
) -> BatchFileIngestResponse:
    """
    Ingest multiple files in a single request.

    Max 10 files, max 50MB total size.
    """
    # TODO: Implementation in Phase 9
    raise NotImplementedError("Batch ingestion not yet implemented")


@router.get("/formats")
async def get_supported_formats():
    """Get list of supported file formats and their extensions."""
    return {
        "formats": [
            {
                "format": FileFormat.PDF,
                "extensions": [".pdf"],
                "mime_types": ["application/pdf"],
                "description": "Adobe PDF documents",
            },
            {
                "format": FileFormat.HTML,
                "extensions": [".html", ".htm"],
                "mime_types": ["text/html"],
                "description": "HTML web pages",
            },
            {
                "format": FileFormat.MARKDOWN,
                "extensions": [".md", ".markdown"],
                "mime_types": ["text/markdown"],
                "description": "Markdown documentation",
            },
            {
                "format": FileFormat.DOCX,
                "extensions": [".docx"],
                "mime_types": [
                    "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
                ],
                "description": "Microsoft Word documents",
            },
            {
                "format": FileFormat.TEXT,
                "extensions": [".txt"],
                "mime_types": ["text/plain"],
                "description": "Plain text files",
            },
            {
                "format": FileFormat.IMAGE,
                "extensions": [".jpg", ".jpeg", ".png", ".tiff", ".tif", ".bmp", ".webp"],
                "mime_types": [
                    "image/jpeg",
                    "image/png",
                    "image/tiff",
                    "image/bmp",
                    "image/webp",
                ],
                "description": "Images (processed with vLLM)",
            },
        ]
    }
