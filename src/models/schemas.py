"""
Pydantic schemas for API request/response validation.

Provides type-safe models for all API endpoints with validation,
examples, and comprehensive documentation.
"""

from enum import Enum
from typing import Any, Dict, List, Optional

from fastapi import UploadFile
from pydantic import BaseModel, Field


class FileFormat(str, Enum):
    """Supported file formats for document ingestion."""

    PDF = "pdf"
    HTML = "html"
    MARKDOWN = "markdown"
    DOCX = "docx"
    TEXT = "text"
    IMAGE = "image"
    JSON = "json"
    CSV = "csv"
    UNKNOWN = "unknown"


class ImageExtractionMode(str, Enum):
    """Image extraction modes for OCR and vision models."""

    TEXT = "text"
    DESCRIPTION = "description"
    AUTO = "auto"


class ContentType(str, Enum):
    """Content type classification for document chunks."""

    TEXT = "text"
    HEADING = "heading"
    TABLE = "table"
    CODE = "code"
    LIST = "list"
    IMAGE_TEXT = "image_text"
    IMAGE_DESCRIPTION = "image_description"


class ExtractionResult(BaseModel):
    """Result from format-specific extraction."""

    text: str = Field(..., description="Extracted plain text content")
    content_type: ContentType = Field(
        default=ContentType.TEXT, description="Classification of content"
    )
    metadata: Dict[str, Any] = Field(
        default_factory=dict, description="Format-specific metadata"
    )
    quality_indicators: Optional[Dict[str, Any]] = Field(
        None, description="Extraction quality metrics"
    )
    warnings: List[str] = Field(
        default_factory=list, description="Any warnings during extraction"
    )


class FileUploadRequest(BaseModel):
    """Request model for file upload endpoint."""

    file: UploadFile = Field(..., description="The uploaded file")
    custom_metadata: Optional[str] = Field(
        None, description="JSON string of custom metadata to apply to all chunks"
    )
    image_mode: ImageExtractionMode = Field(
        default=ImageExtractionMode.AUTO,
        description="Mode for image processing: text, description, or auto-detect",
    )
    preserve_tables: bool = Field(
        default=True, description="Whether to preserve table structure during extraction"
    )
    extract_code_blocks: bool = Field(
        default=True,
        description="Whether to extract code blocks separately with language detection",
    )


class ChatRequest(BaseModel):
    """Chat query request."""

    query: str = Field(..., min_length=1, description="User question in Arabic or English")
    session_id: Optional[str] = Field(None, description="Session ID for conversation memory")
    use_rag: bool = Field(True, description="Whether to use RAG retrieval")

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "query": "ما هي عاصمة مصر؟",
                    "session_id": "user123_session1",
                    "use_rag": True,
                }
            ]
        }
    }


class Source(BaseModel):
    """Source document information."""

    content: str = Field(..., description="Document content excerpt")
    metadata: Dict = Field(default_factory=dict, description="Document metadata")


class ChatResponse(BaseModel):
    """Chat query response."""

    response: str = Field(..., description="AI-generated answer")
    sources: List[Source] = Field(default_factory=list, description="Source documents used")
    query_type: str = Field(..., description="Type of query: greeting, simple, rag, calculator")
    session_id: Optional[str] = Field(None, description="Session ID if provided")

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "response": "عاصمة مصر هي القاهرة.",
                    "sources": [{"content": "القاهرة هي...", "metadata": {}}],
                    "query_type": "rag",
                    "session_id": "user123_session1",
                }
            ]
        }
    }


class DocumentIngestRequest(BaseModel):
    """Document ingestion request."""

    texts: List[str] = Field(..., min_length=1, description="Documents to ingest")
    metadatas: Optional[List[Dict]] = Field(None, description="Metadata for each document")


class DocumentIngestResponse(BaseModel):
    """Document ingestion response."""

    message: str
    documents_ingested: int
    chunks_created: int


class FileIngestResponse(BaseModel):
    """Response model for single file ingestion.

    Provides detailed information about the ingestion process including
    file metadata, processing metrics, and any warnings encountered.
    """

    message: str = Field(..., description="Status message describing the ingestion result")
    filename: str = Field(..., description="Original filename of the uploaded file")
    file_format: FileFormat = Field(..., description="Detected file format (pdf, html, text, etc.)")
    file_size_bytes: int = Field(..., description="Size of the uploaded file in bytes")
    documents_created: int = Field(..., description="Number of documents created from the file")
    chunks_created: int = Field(..., description="Number of chunks created after processing")
    processing_time_ms: int = Field(..., description="Total processing time in milliseconds")
    metadata: Dict[str, Any] = Field(
        default_factory=dict,
        description="Additional metadata extracted from the file"
    )
    warnings: List[str] = Field(
        default_factory=list,
        description="List of non-fatal warnings encountered during processing"
    )

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "message": "File ingested successfully",
                    "filename": "document.pdf",
                    "file_format": "pdf",
                    "file_size_bytes": 524288,
                    "documents_created": 1,
                    "chunks_created": 15,
                    "processing_time_ms": 1234,
                    "metadata": {
                        "num_pages": 10,
                        "author": "John Doe",
                        "created_date": "2025-01-15"
                    },
                    "warnings": [
                        "Page 5 contains low-quality scanned text",
                        "Some formatting may be lost in tables"
                    ]
                }
            ]
        }
    }


class BatchFileUploadRequest(BaseModel):
    """Batch file upload request."""

    files: List[UploadFile] = Field(..., description="List of files to upload")
    shared_metadata: Optional[str] = Field(None, description="JSON metadata applied to all files")


class FileIngestResult(BaseModel):
    """Result for a single file in batch ingestion."""

    filename: str = Field(..., description="Name of the file")
    status: str = Field(..., description="Status: success or error")
    chunks_created: int = Field(0, description="Number of chunks created")
    error: Optional[str] = Field(None, description="Error message if failed")


class BatchFileIngestResponse(BaseModel):
    """Batch file ingestion response."""

    message: str = Field(..., description="Overall status message")
    total_files: int = Field(..., description="Total number of files processed")
    successful: int = Field(..., description="Number of successful ingestions")
    failed: int = Field(..., description="Number of failed ingestions")
    results: List[FileIngestResponse] = Field(..., description="Detailed results per file")
    total_chunks: int = Field(..., description="Total chunks created across all files")
    total_processing_time_ms: int = Field(..., description="Total processing time in milliseconds")


class SessionClearRequest(BaseModel):
    """Session clear request."""

    session_id: str = Field(..., description="Session ID to clear")


class SessionClearResponse(BaseModel):
    """Session clear response."""

    message: str
    session_id: str


class HealthResponse(BaseModel):
    """Health check response."""

    status: str
    version: str
    components: Dict[str, str]
