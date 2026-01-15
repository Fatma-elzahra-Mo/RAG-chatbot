"""
Arabic document reranker using ARA-Reranker-V1.

Achieves 0.934 MRR with +6% improvement over base retrieval.
Best strategy: Retrieve top-10, rerank to top-3.
"""

from typing import List, Optional, Tuple

import numpy as np
from langchain_core.documents import Document
from sentence_transformers import CrossEncoder


class ArabicReranker:
    """
    Arabic document reranker using ARA-Reranker-V1.

    Performance (2025 benchmarks):
    - MRR@10: 0.934 (best for Arabic)
    - +6% improvement over base retrieval
    - Recommended: Retrieve 10, rerank to 3
    """

    def __init__(
        self,
        model_name: str = "Omartificial-Intelligence-Space/ARA-Reranker-V1",
        top_n: int = 3,
        device: str = "cpu",
    ):
        """
        Initialize Arabic reranker.

        Args:
            model_name: HuggingFace model name for reranking
            top_n: Number of top documents to return after reranking
            device: Device for model inference (cpu/cuda)
        """
        self.model_name = model_name
        self.top_n = top_n
        self.device = device

        # Load cross-encoder model
        self.model = CrossEncoder(model_name, device=device)

    def rerank(
        self,
        query: str,
        documents: List[Document],
        top_n: Optional[int] = None,
    ) -> List[Document]:
        """
        Rerank documents based on relevance to query.

        Args:
            query: User query
            documents: Retrieved documents from vector store
            top_n: Number of top docs to return (default: self.top_n)

        Returns:
            Reranked documents (most relevant first)
        """
        if not documents:
            return []

        top_n = top_n or self.top_n

        # Create query-document pairs for cross-encoder
        pairs = [(query, doc.page_content) for doc in documents]

        # Get relevance scores
        scores = self.model.predict(pairs)

        # Sort documents by score (descending)
        doc_scores = list(zip(documents, scores))
        doc_scores.sort(key=lambda x: x[1], reverse=True)

        # Return top N documents
        return [doc for doc, _ in doc_scores[:top_n]]

    def rerank_with_scores(
        self,
        query: str,
        documents: List[Document],
    ) -> List[Tuple[Document, float]]:
        """
        Rerank documents and return with relevance scores.

        Args:
            query: User query
            documents: Retrieved documents

        Returns:
            List of (document, score) tuples, sorted by relevance
        """
        if not documents:
            return []

        # Create query-document pairs
        pairs = [(query, doc.page_content) for doc in documents]

        # Get relevance scores
        scores = self.model.predict(pairs)

        # Sort by score (descending)
        doc_scores = list(zip(documents, scores))
        doc_scores.sort(key=lambda x: x[1], reverse=True)

        return doc_scores[: self.top_n]

    def _compute_similarity_matrix(self, documents: List[Document]) -> np.ndarray:
        """
        Compute pairwise cosine similarity between documents using cross-encoder.

        Args:
            documents: List of documents

        Returns:
            Symmetric similarity matrix of shape (n_docs, n_docs)
        """
        n = len(documents)
        similarity_matrix = np.zeros((n, n))

        # Compute pairwise similarities
        for i in range(n):
            for j in range(i, n):
                if i == j:
                    similarity_matrix[i][j] = 1.0
                else:
                    # Use cross-encoder to score document similarity
                    score = self.model.predict(
                        [(documents[i].page_content, documents[j].page_content)]
                    )[0]
                    # Normalize score to [0, 1] range
                    normalized_score = (score + 1) / 2 if score < 0 else min(score, 1.0)
                    similarity_matrix[i][j] = normalized_score
                    similarity_matrix[j][i] = normalized_score

        return similarity_matrix

    def rerank_with_mmr(
        self,
        query: str,
        documents: List[Document],
        top_n: Optional[int] = None,
        mmr_lambda: float = 0.7,
    ) -> List[Document]:
        """
        Rerank documents using Maximal Marginal Relevance (MMR) for diversity.

        MMR balances relevance to query with diversity among selected documents.
        Formula: MMR = argmax[lambda * Sim(doc, query) - (1-lambda) * max(Sim(doc, selected))]

        Args:
            query: User query
            documents: Retrieved documents from vector store
            top_n: Number of top docs to return (default: self.top_n)
            mmr_lambda: Balance between relevance (1.0) and diversity (0.0).
                        Default 0.7 means 70% relevance, 30% diversity.

        Returns:
            Reranked documents with diversity (most relevant and diverse first)
        """
        if not documents:
            return []

        top_n = top_n or self.top_n
        n_docs = len(documents)

        if n_docs <= top_n:
            # Not enough docs to apply MMR, just return reranked
            return self.rerank(query, documents, top_n)

        # Step 1: Get relevance scores from cross-encoder
        pairs = [(query, doc.page_content) for doc in documents]
        relevance_scores = self.model.predict(pairs)

        # Normalize relevance scores to [0, 1]
        min_score = np.min(relevance_scores)
        max_score = np.max(relevance_scores)
        if max_score > min_score:
            relevance_scores = (relevance_scores - min_score) / (max_score - min_score)
        else:
            relevance_scores = np.ones(n_docs)

        # Step 2: Compute document-document similarity matrix
        similarity_matrix = self._compute_similarity_matrix(documents)

        # Step 3: Apply MMR iteratively
        selected_indices: List[int] = []
        unselected_indices = list(range(n_docs))

        for _ in range(top_n):
            if not unselected_indices:
                break

            mmr_scores = []
            for idx in unselected_indices:
                # Relevance component
                relevance = relevance_scores[idx]

                # Diversity component: max similarity to already selected docs
                if selected_indices:
                    max_sim_to_selected = max(
                        similarity_matrix[idx][sel_idx] for sel_idx in selected_indices
                    )
                else:
                    max_sim_to_selected = 0.0

                # MMR score
                mmr_score = mmr_lambda * relevance - (1 - mmr_lambda) * max_sim_to_selected
                mmr_scores.append((idx, mmr_score))

            # Select document with highest MMR score
            best_idx = max(mmr_scores, key=lambda x: x[1])[0]
            selected_indices.append(best_idx)
            unselected_indices.remove(best_idx)

        # Return selected documents in MMR order
        return [documents[idx] for idx in selected_indices]
