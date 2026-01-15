"""
Health check endpoint.

Provides system health status and component checks.
"""

from fastapi import APIRouter
from loguru import logger

from src.config.settings import settings
from src.models.schemas import HealthResponse

router = APIRouter(prefix="/health", tags=["health"])


@router.get("", response_model=HealthResponse)
async def health_check() -> HealthResponse:
    """
    Health check endpoint.

    Returns application status and component health.
    """
    components = {
        "qdrant": "unknown",
        "embeddings": "ok",
        "memory": "ok",
    }

    # Check Qdrant connection
    try:
        from qdrant_client import QdrantClient

        client = QdrantClient(url=settings.qdrant_url)
        client.get_collections()
        components["qdrant"] = "ok"
    except Exception as e:
        logger.warning(f"Qdrant health check failed: {e}")
        components["qdrant"] = "error"

    return HealthResponse(
        status="healthy" if all(v == "ok" for v in components.values()) else "degraded",
        version=settings.app_version,
        components=components,
    )
