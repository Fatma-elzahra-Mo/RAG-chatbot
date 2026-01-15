"""
Qdrant vector store interface for Arabic RAG.

Qdrant provides 1ms p99 latency for vector search.
"""

from typing import List

from langchain_core.documents import Document
from loguru import logger
from qdrant_client import QdrantClient
from qdrant_client.models import Distance, PointStruct, VectorParams


class QdrantStore:
    """
    Qdrant vector store interface.

    Performance:
    - 1ms p99 latency
    - Efficient cosine similarity search
    - Persistent storage with HNSW indexing

    Qdrant excels at:
    - Fast vector search at scale
    - Metadata filtering
    - Real-time updates
    """

    def __init__(
        self,
        url: str = "http://localhost:6333",
        collection_name: str = "arabic_documents",
        embedding_dimension: int = 1024,
    ):
        """
        Initialize Qdrant vector store.

        Args:
            url: Qdrant server URL
            collection_name: Name of the collection to use
            embedding_dimension: Dimension of embedding vectors (BGE-M3 = 1024)
        """
        self.client = QdrantClient(url=url)
        self.collection_name = collection_name
        self.embedding_dimension = embedding_dimension

        self._ensure_collection()

    def _ensure_collection(self) -> None:
        """
        Create collection if it doesn't exist.

        Uses cosine distance metric for similarity search.
        HNSW indexing provides sub-linear search complexity.
        """
        collections = self.client.get_collections().collections
        collection_names = [c.name for c in collections]

        if self.collection_name not in collection_names:
            self.client.create_collection(
                collection_name=self.collection_name,
                vectors_config=VectorParams(
                    size=self.embedding_dimension,
                    distance=Distance.COSINE,
                ),
            )

    def add_documents(
        self,
        documents: List[Document],
        embeddings: List[List[float]],
    ) -> None:
        """
        Add documents with their embeddings to the collection.

        Args:
            documents: List of documents to add
            embeddings: Corresponding embedding vectors

        Example:
            >>> store = QdrantStore()
            >>> docs = [Document(page_content="مرحبا", metadata={"source": "test"})]
            >>> embeddings = [[0.1] * 1024]
            >>> store.add_documents(docs, embeddings)
        """
        # Get current max ID to avoid overwriting
        try:
            info = self.client.get_collection(self.collection_name)
            start_id = info.points_count or 0
        except Exception:
            start_id = 0

        points = [
            PointStruct(
                id=start_id + i,
                vector=embedding,
                payload={"text": doc.page_content, **doc.metadata},
            )
            for i, (doc, embedding) in enumerate(zip(documents, embeddings))
        ]

        self.client.upsert(
            collection_name=self.collection_name,
            points=points,
        )

        logger.info(
            f"Added {len(documents)} documents to Qdrant collection '{self.collection_name}' "
            f"(IDs: {start_id} to {start_id + len(documents) - 1})"
        )

    def search(
        self,
        query_vector: List[float],
        limit: int = 10,
    ) -> List[Document]:
        """
        Search for similar documents using vector similarity.

        Args:
            query_vector: Query embedding vector
            limit: Maximum number of results

        Returns:
            List of most similar documents

        Example:
            >>> store = QdrantStore()
            >>> query_vector = [0.1] * 1024
            >>> results = store.search(query_vector, limit=5)
            >>> len(results) <= 5
            True
        """
        results = self.client.query_points(
            collection_name=self.collection_name,
            query=query_vector,
            limit=limit,
        )

        return [
            Document(
                page_content=hit.payload.get("text", "") if hit.payload else "",
                metadata={
                    **({k: v for k, v in hit.payload.items() if k != "text"} if hit.payload else {}),
                    "score": hit.score,
                },
            )
            for hit in results.points
        ]
