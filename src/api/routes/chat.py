"""
Chat endpoints for querying the RAG chatbot.

Provides endpoints for:
- Querying the chatbot with optional conversation memory
- Clearing conversation history for a session
"""

from fastapi import APIRouter, HTTPException, status
from loguru import logger

from src.core.pipeline import RAGPipeline
from src.models.schemas import ChatRequest, ChatResponse

router = APIRouter(prefix="/chat", tags=["chat"])

# Initialize pipeline (singleton)
_pipeline: RAGPipeline | None = None


def get_pipeline() -> RAGPipeline:
    """Get or create RAG pipeline instance."""
    global _pipeline
    if _pipeline is None:
        _pipeline = RAGPipeline()
    return _pipeline


@router.post("/query", response_model=ChatResponse, status_code=status.HTTP_200_OK)
async def chat_query(request: ChatRequest) -> ChatResponse:
    """
    Query the chatbot with optional conversation memory.

    - **query**: User question in Arabic or English
    - **session_id**: Optional session for multi-turn conversation
    - **use_rag**: Whether to use RAG retrieval (default: true)
    """
    try:
        logger.info(f"Chat query: {request.query[:50]}... | Session: {request.session_id}")

        pipeline = get_pipeline()
        result = pipeline.query(
            query=request.query,
            session_id=request.session_id,
            use_rag=request.use_rag,
        )

        return ChatResponse(**result)

    except Exception as e:
        logger.error(f"Chat query error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error processing query: {str(e)}",
        )


@router.delete("/session/{session_id}", status_code=status.HTTP_200_OK)
async def clear_session(session_id: str):
    """
    Clear conversation history for a session.

    - **session_id**: Session ID to clear
    """
    try:
        logger.info(f"Clearing session: {session_id}")

        pipeline = get_pipeline()
        if pipeline.use_memory:
            pipeline.memory.clear_session(session_id)

        return {"message": "Session cleared successfully", "session_id": session_id}

    except Exception as e:
        logger.error(f"Clear session error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error clearing session: {str(e)}",
        )
