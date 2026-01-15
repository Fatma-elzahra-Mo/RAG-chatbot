"""
Configuration management for Arabic RAG Chatbot.

Uses pydantic-settings for environment-based configuration with validation.
"""

from typing import Optional

from pydantic import Field, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """
    Application settings with validation and environment variable support.

    All settings can be overridden via environment variables.
    Example: OPENAI_API_KEY="sk-..." python main.py
    """

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",  # Ignore extra fields in .env
    )

    # Application config
    app_name: str = "Arabic RAG Chatbot"
    environment: str = Field("development", pattern="^(development|staging|production)$")

    # LLM config
    llm_provider: str = Field(
        "openrouter", pattern="^(openai|gemini|openrouter|huggingface|local)$"
    )
    openai_api_key: Optional[SecretStr] = None
    openai_model: str = "gpt-4-turbo-preview"
    openai_temperature: float = 0.7

    # Gemini config
    gemini_api_key: Optional[SecretStr] = None
    gemini_model: str = "gemini-3-flash-preview"
    gemini_temperature: float = 0.7

    # OpenRouter config
    openrouter_api_key: Optional[SecretStr] = None
    openrouter_model: str = "google/gemini-2.5-flash"  # or anthropic/claude-3.5-sonnet
    openrouter_temperature: float = 0.7
    openrouter_base_url: str = "https://openrouter.ai/api/v1"

    # vLLM / Local model config
    vllm_base_url: str = "http://localhost:8000/v1"
    vllm_model: str = "meta-llama/Llama-2-7b-chat-hf"
    vllm_temperature: float = 0.7
    vllm_max_tokens: int = 512

    # Embeddings configuration
    embeddings_provider: str = Field("gemini", pattern="^(gemini|local)$")
    embeddings_model: str = "BAAI/bge-m3"  # For local provider
    embeddings_dimension: int = 768  # Gemini text-embedding-004 = 768
    embeddings_device: str = "cpu"

    # Reranker (ARA-Reranker-V1)
    reranker_model: str = "Omartificial-Intelligence-Space/ARA-Reranker-V1"
    reranker_top_n: int = 5

    # Qdrant (1ms p99 latency)
    qdrant_url: str = "http://localhost:6333"
    qdrant_collection: str = "arabic_documents"

    # Retrieval (sentence-aware chunking: 74.78% vs 69.41% fixed-size)
    retrieval_top_k: int = 15
    chunk_size: int = 350  # Arabic text is denser
    chunk_overlap: int = 100  # Better context preservation

    # PDF-specific processing
    pdf_chunk_size: int = 350  # Base chunk size for PDF content
    pdf_preserve_tables: bool = True  # Keep tables intact when possible
    pdf_preserve_lists: bool = True  # Maintain list structure
    pdf_respect_headers: bool = True  # Use headers as chunk boundaries
    pdf_use_dynamic_sizing: bool = True  # Adjust chunk size by content type
    pdf_remove_headers: bool = True  # Remove repeated headers/footers
    pdf_remove_page_numbers: bool = True  # Clean page number artifacts
    pdf_clean_artifacts: bool = True  # Remove OCR noise and formatting issues

    # Memory
    max_conversation_history: int = 10
    conversation_ttl_hours: int = 24

    # Redis
    redis_url: str = "redis://localhost:6379/0"
    cache_enabled: bool = True

    # Logging
    log_level: str = "INFO"

    # API configuration
    api_host: str = "0.0.0.0"
    api_port: int = 8000
    api_workers: int = 4
    cors_origins: list[str] = ["*"]
    app_version: str = "1.0.0"


# Singleton instance
settings = Settings()
