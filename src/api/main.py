"""
Main FastAPI application for Arabic RAG Chatbot.

Provides RESTful API endpoints for:
- Chat queries with conversation memory
- Document ingestion
- Health checks
"""

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from loguru import logger

from src.api.routes import chat, documents, health
from src.config.settings import settings


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan events."""
    logger.info("Starting Arabic RAG Chatbot API")
    logger.info(f"Environment: {settings.environment}")
    logger.info(f"Qdrant URL: {settings.qdrant_url}")
    yield
    logger.info("Shutting down Arabic RAG Chatbot API")


# Create FastAPI app
app = FastAPI(
    title="Arabic RAG Chatbot API",
    description="Production-ready Arabic RAG chatbot with conversation memory",
    version="1.0.0",
    lifespan=lifespan,
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(chat.router)
app.include_router(documents.router)
app.include_router(health.router)


@app.get("/")
async def root():
    """Root endpoint."""
    return {
        "message": "Arabic RAG Chatbot API",
        "version": "1.0.0",
        "docs": "/docs",
        "health": "/health",
    }
