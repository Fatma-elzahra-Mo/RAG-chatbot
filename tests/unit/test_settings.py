"""
Unit tests for configuration settings.
"""

import pytest
from pydantic import ValidationError

from src.config.settings import Settings


class TestSettings:
    """Test suite for Settings."""

    def test_default_settings(self):
        """Test that default settings are valid."""
        settings = Settings()
        assert settings.app_name == "Arabic RAG Chatbot"
        assert settings.environment == "development"
        assert settings.embeddings_model == "BAAI/bge-m3"
        assert settings.embeddings_dimension == 1024
        assert settings.chunk_size == 512

    def test_environment_validation(self):
        """Test environment field validation."""
        # Valid environments
        for env in ["development", "staging", "production"]:
            settings = Settings(environment=env)
            assert settings.environment == env

        # Invalid environment should raise ValidationError
        with pytest.raises(ValidationError):
            Settings(environment="invalid")

    def test_llm_provider_validation(self):
        """Test LLM provider field validation."""
        # Valid providers
        for provider in ["openai", "huggingface", "local"]:
            settings = Settings(llm_provider=provider)
            assert settings.llm_provider == provider

        # Invalid provider should raise ValidationError
        with pytest.raises(ValidationError):
            Settings(llm_provider="invalid")

    def test_embeddings_config(self):
        """Test embeddings configuration."""
        settings = Settings()
        assert settings.embeddings_model == "BAAI/bge-m3"
        assert settings.embeddings_dimension == 1024
        assert settings.embeddings_device in ["cpu", "cuda", "mps"]

    def test_qdrant_config(self):
        """Test Qdrant configuration."""
        settings = Settings()
        assert settings.qdrant_url.startswith("http://")
        assert settings.qdrant_collection == "arabic_documents"

    def test_retrieval_config(self):
        """Test retrieval configuration."""
        settings = Settings()
        assert settings.retrieval_top_k == 10
        assert settings.chunk_size == 512
        assert settings.chunk_overlap == 50

    def test_memory_config(self):
        """Test memory configuration."""
        settings = Settings()
        assert settings.max_conversation_history == 10
        assert settings.conversation_ttl_hours == 24

    def test_custom_settings(self):
        """Test custom settings override."""
        settings = Settings(
            app_name="Custom App",
            chunk_size=256,
            retrieval_top_k=5,
        )
        assert settings.app_name == "Custom App"
        assert settings.chunk_size == 256
        assert settings.retrieval_top_k == 5

    def test_secret_str(self):
        """Test SecretStr handling for sensitive data."""
        settings = Settings(openai_api_key="sk-test123")
        assert settings.openai_api_key is not None
        # SecretStr doesn't expose value in repr
        assert "sk-test123" not in repr(settings.openai_api_key)
