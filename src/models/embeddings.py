"""
Embeddings providers for Arabic RAG chatbot.

Supports Google Gemini embeddings (online) and local sentence-transformers.
"""

from typing import List, Optional

from langchain_core.embeddings import Embeddings

from src.config.settings import settings


class GeminiEmbeddings(Embeddings):
    """
    Google Gemini embeddings using text-embedding-004 model.

    Features:
    - 768-dimensional vectors
    - Multilingual support including Arabic
    - Free tier: 1500 requests/minute

    Example:
        >>> embeddings = GeminiEmbeddings()
        >>> vectors = embeddings.embed_documents(["مرحبا", "Hello"])
        >>> print(len(vectors[0]))  # 768
    """

    def __init__(
        self,
        model_name: str = "text-embedding-004",
        api_key: Optional[str] = None,
    ):
        """
        Initialize Gemini embeddings.

        Args:
            model_name: Gemini embedding model (text-embedding-004)
            api_key: Google API key (defaults to settings.gemini_api_key)
        """
        from google import genai

        api_key = api_key or (
            settings.gemini_api_key.get_secret_value()
            if settings.gemini_api_key
            else None
        )

        if not api_key:
            raise ValueError(
                "Gemini API key required. Set GEMINI_API_KEY in .env"
            )

        self.model_name = model_name
        self.client = genai.Client(api_key=api_key)

    def embed_documents(self, texts: List[str]) -> List[List[float]]:
        """
        Embed a list of documents.

        Args:
            texts: List of texts to embed

        Returns:
            List of embedding vectors
        """
        embeddings = []
        # Process in batches of 100 (API limit)
        batch_size = 100
        for i in range(0, len(texts), batch_size):
            batch = texts[i:i + batch_size]
            # Embed each text individually for type safety
            for text in batch:
                result = self.client.models.embed_content(
                    model=self.model_name,
                    contents=text,
                )
                if result.embeddings and result.embeddings[0].values:
                    embeddings.append(list(result.embeddings[0].values))
        return embeddings

    def embed_query(self, text: str) -> List[float]:
        """
        Embed a single query.

        Args:
            text: Query text to embed

        Returns:
            Embedding vector
        """
        result = self.client.models.embed_content(
            model=self.model_name,
            contents=text,
        )
        if result.embeddings and result.embeddings[0].values:
            return list(result.embeddings[0].values)
        return []


def create_embeddings(provider: str = "gemini") -> Embeddings:
    """
    Factory function to create embeddings instance.

    Args:
        provider: Embeddings provider ("gemini" or "local")

    Returns:
        Embeddings instance
    """
    if provider == "gemini":
        return GeminiEmbeddings()
    elif provider == "local":
        from langchain_huggingface import HuggingFaceEmbeddings
        return HuggingFaceEmbeddings(
            model_name=settings.embeddings_model,
            model_kwargs={"device": settings.embeddings_device},
        )
    else:
        raise ValueError(f"Unsupported embeddings provider: {provider}")
