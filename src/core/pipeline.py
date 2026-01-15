"""
Complete RAG pipeline with memory integration.

Pipeline flow:
1. Normalize query
2. Get conversation history
3. Retrieve → Rerank → Generate
4. Save response to memory
"""

from __future__ import annotations

from typing import Any


def extract_text_content(content: Any) -> str:
    """
    Extract text from LLM response content.

    Handles Gemini 3 responses which return structured data like:
    [{'type': 'text', 'text': '...', 'extras': {...}}]
    """
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        # Gemini 3 format: list of content blocks
        texts = []
        for item in content:
            if isinstance(item, dict) and item.get("type") == "text":
                texts.append(item.get("text", ""))
            elif isinstance(item, str):
                texts.append(item)
        return "".join(texts)
    return str(content)


from langchain_core.documents import Document
from langchain_core.messages import BaseMessage
from langchain_openai import ChatOpenAI
from qdrant_client import QdrantClient

from src.config.settings import settings

# Using Egyptian prompts for all providers (bilingual support)
from src.core.prompts_egyptian import (
    NO_INFO_RESPONSE_AR,
    WE_CONVERSATIONAL_PROMPT,
    WE_QA_PROMPT,
)
from src.memory.conversation import ConversationMemory
from src.models.embeddings import create_embeddings
from src.models.gemini import GeminiLLM, OpenRouterLLM
from src.models.vllm_model import VLLMLLMWrapper
from src.preprocessing.chunker import ArabicSentenceChunker
from src.preprocessing.normalizer import ArabicNormalizer
from src.preprocessing.pdf_chunker import PDFAwareChunker
from src.retrieval.reranker import ArabicReranker
from src.retrieval.vectorstore import QdrantStore


class RAGPipeline:
    """
    Complete RAG pipeline with memory integration.

    Features:
    - Query normalization
    - Conversation memory
    - Document retrieval with reranking
    - LLM generation with Arabic prompts
    """

    def __init__(
        self,
        qdrant_url: str | None = None,
        collection_name: str | None = None,
        use_memory: bool = True,
    ):
        """
        Initialize RAG pipeline.

        Args:
            qdrant_url: Qdrant server URL
            collection_name: Qdrant collection name
            use_memory: Whether to use conversation memory
        """
        # Configuration
        self.qdrant_url = qdrant_url or settings.qdrant_url
        self.collection_name = collection_name or settings.qdrant_collection
        self.use_memory = use_memory

        # Initialize components
        self.normalizer = ArabicNormalizer()
        self.embeddings = create_embeddings(provider=settings.embeddings_provider)

        # Vector store
        self.qdrant_client = QdrantClient(url=self.qdrant_url)
        self.vectorstore = QdrantStore(
            url=self.qdrant_url,
            collection_name=self.collection_name,
            embedding_dimension=settings.embeddings_dimension,
        )

        # Reranker
        self.reranker = ArabicReranker(
            model_name=settings.reranker_model,
            top_n=settings.reranker_top_n,
        )

        # Memory
        if self.use_memory:
            self.memory = ConversationMemory(
                qdrant_client=self.qdrant_client,
                max_history=settings.max_conversation_history,
                ttl_hours=settings.conversation_ttl_hours,
            )

        # LLM provider selection
        self.llm_provider = settings.llm_provider
        self.llm: ChatOpenAI | GeminiLLM | OpenRouterLLM | VLLMLLMWrapper

        if settings.llm_provider == "gemini":
            self.llm = GeminiLLM(
                model_name=settings.gemini_model,
                temperature=settings.gemini_temperature,
            )
        elif settings.llm_provider == "openai":
            self.llm = ChatOpenAI(
                model=settings.openai_model,
                temperature=settings.openai_temperature,
                api_key=(
                    settings.openai_api_key.get_secret_value() if settings.openai_api_key else None
                ),
            )
        elif settings.llm_provider == "openrouter":
            self.llm = OpenRouterLLM(
                model_name=settings.openrouter_model,
                temperature=settings.openrouter_temperature,
            )
        elif settings.llm_provider in ("local", "huggingface"):
            # Both "local" and "huggingface" use vLLM
            # The difference is only in naming convention
            self.llm = VLLMLLMWrapper(
                base_url=settings.vllm_base_url,
                model_name=settings.vllm_model,
                temperature=settings.vllm_temperature,
                max_tokens=settings.vllm_max_tokens,
                verify_connection=True,
            )
        else:
            raise ValueError(f"Unsupported LLM provider: {settings.llm_provider}")

    def query(
        self,
        query: str,
        session_id: str | None = None,
        use_rag: bool = True,
    ) -> dict:
        """
        Process a query through the RAG pipeline.

        Args:
            query: User question
            session_id: Optional session for memory
            use_rag: Whether to use RAG retrieval

        Returns:
            Dict with:
            - response: Generated answer
            - sources: Retrieved documents (if RAG used)
            - query_type: Type of query processed
            - session_id: Session identifier
        """
        # 1. Normalize query
        normalized_query = self.normalizer.normalize(query)

        # 2. Get conversation history
        chat_history: list[BaseMessage] = []
        if session_id and self.use_memory:
            chat_history = self.memory.get_history(session_id)

        # 3. Process query through RAG
        query_type = "rag"
        response, sources = self._handle_rag_query(normalized_query, chat_history)

        # 5. Save to memory
        if session_id and self.use_memory:
            self.memory.add_exchange(session_id, query, response)

        return {
            "response": response,
            "sources": sources,
            "query_type": query_type,
            "session_id": session_id,
        }

    def _handle_rag_query(
        self,
        query: str,
        chat_history: list[BaseMessage],
    ) -> tuple[str, list[dict]]:
        """
        Handle RAG queries with retrieval.

        Flow:
        1. Embed query
        2. Retrieve top-k documents
        3. Rerank to top-n
        4. Build context
        5. Generate response
        """
        # 1. Embed query
        query_vector = self.embeddings.embed_query(query)

        # 2. Retrieve top-k documents
        documents = self.vectorstore.search(
            query_vector=query_vector,
            limit=settings.retrieval_top_k,
        )

        if not documents:
            no_info_msg = (
                NO_INFO_RESPONSE_AR
                if self.llm_provider == "gemini"
                else "لا توجد معلومات متاحة للإجابة على هذا السؤال."
            )
            return no_info_msg, []

        # 3. Rerank to top-n
        reranked_docs = self.reranker.rerank(query, documents)

        # 4. Build context
        context = "\n\n".join([doc.page_content for doc in reranked_docs])

        # 5. Generate response - use Egyptian prompts for all providers
        prompt = WE_CONVERSATIONAL_PROMPT if chat_history else WE_QA_PROMPT

        # Build format args - only include chat_history if it exists
        format_args = {"context": context, "query": query}
        if chat_history:
            format_args["chat_history"] = chat_history

        formatted_prompt = prompt.format_messages(**format_args)

        response = self.llm.invoke(formatted_prompt)

        # 6. Format sources
        sources = [
            {
                "content": doc.page_content[:200] + "..."
                if len(doc.page_content) > 200
                else doc.page_content,
                "metadata": doc.metadata,
            }
            for doc in reranked_docs
        ]

        return extract_text_content(response.content), sources

    def ingest_documents(
        self,
        texts: list[str],
        metadatas: list[dict] | None = None,
        document_type: str | None = None,
    ) -> None:
        """
        Ingest documents into the vector store.

        Pipeline:
        1. Create documents
        2. Auto-detect or use specified document type
        3. Chunk with appropriate chunker (PDF-aware or sentence-aware)
        4. Normalize text
        5. Embed chunks
        6. Store in Qdrant

        Args:
            texts: List of document texts
            metadatas: Optional metadata for each document
            document_type: Optional document type ("pdf", "text", or None for auto-detect)
        """
        # Create documents
        documents = [
            Document(page_content=text, metadata=meta or {})
            for text, meta in zip(texts, metadatas or [{}] * len(texts))
        ]

        # Auto-detect document type if not specified
        if document_type is None:
            document_type = self._detect_document_type(documents)

        # Choose appropriate chunker based on document type
        if document_type == "pdf":
            chunker = PDFAwareChunker(
                max_chunk_size=settings.pdf_chunk_size,
                overlap=settings.chunk_overlap,
                preserve_tables=settings.pdf_preserve_tables,
                preserve_lists=settings.pdf_preserve_lists,
                respect_headers=settings.pdf_respect_headers,
                use_dynamic_sizing=settings.pdf_use_dynamic_sizing,
                clean_pdf_artifacts=settings.pdf_clean_artifacts,
            )
        else:
            chunker = ArabicSentenceChunker(
                max_chunk_size=settings.chunk_size,
                overlap=settings.chunk_overlap,
            )

        chunked_docs = chunker.chunk_documents(documents)

        # Normalize text
        for doc in chunked_docs:
            doc.page_content = self.normalizer.normalize(doc.page_content)

        # Embed chunks
        texts = [doc.page_content for doc in chunked_docs]
        embeddings = self.embeddings.embed_documents(texts)

        # Store in Qdrant
        self.vectorstore.add_documents(chunked_docs, embeddings)

    def _detect_document_type(self, documents: list[Document]) -> str:
        """
        Auto-detect document type based on metadata and content patterns.

        Args:
            documents: List of documents to analyze

        Returns:
            Detected document type: "pdf" or "text"
        """
        # Check metadata for PDF indicators
        for doc in documents:
            source = doc.metadata.get("source", "").lower()
            doc_type = doc.metadata.get("document_type", "").lower()

            if source.endswith(".pdf") or doc_type == "pdf":
                return "pdf"

        # Check content for PDF-like patterns
        if documents:
            sample_text = documents[0].page_content
            pdf_indicators = [
                r"Page\s+\d+",  # Page numbers
                r"صفحة\s+\d+",  # Arabic page numbers
                r"\|.*\|.*\|",  # Table markers
                r"[\n\r]{3,}",  # Multiple consecutive newlines
            ]

            import re

            indicator_count = sum(
                1 for pattern in pdf_indicators if re.search(pattern, sample_text)
            )

            # If 2+ indicators present in first document, likely all are PDFs
            if indicator_count >= 2:
                return "pdf"

        return "text"

    def clear_collection(self) -> None:
        """Clear the vector store collection."""
        self.vectorstore.delete_collection()
        self.vectorstore.create_collection()
