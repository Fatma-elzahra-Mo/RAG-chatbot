"""
Conversation memory manager using Qdrant metadata filtering.

Implements session-based conversation history with fast metadata retrieval
and automatic TTL-based cleanup.
"""

from datetime import datetime, timedelta
from typing import List, Optional
from uuid import UUID

from langchain_core.messages import AIMessage, BaseMessage, HumanMessage
from qdrant_client import QdrantClient
from qdrant_client.models import (
    Distance,
    FieldCondition,
    Filter,
    MatchValue,
    PointStruct,
    Range,
    VectorParams,
)

from src.memory.models import ConversationMessage


class ConversationMemory:
    """
    Conversation history manager using Qdrant metadata filtering.

    Features:
    - Session-based storage with session_id
    - Fast retrieval via metadata filters (<5ms)
    - Automatic TTL-based cleanup
    - Multi-user support
    - LangChain message compatibility

    Architecture:
    - Uses Qdrant for storage with dummy vectors (metadata-only)
    - Leverages Qdrant's high-performance metadata filtering
    - Single source of truth (no separate database needed)
    - Built-in TTL support for automatic cleanup

    Example:
        >>> from qdrant_client import QdrantClient
        >>> client = QdrantClient(":memory:")
        >>> memory = ConversationMemory(client)
        >>> memory.add_exchange("session1", "مرحبا", "مرحبا بك")
        >>> history = memory.get_history("session1")
        >>> print(len(history))  # 2
    """

    def __init__(
        self,
        qdrant_client: QdrantClient,
        collection_name: str = "conversation_history",
        max_history: int = 10,
        ttl_hours: int = 24,
    ):
        """
        Initialize conversation memory.

        Args:
            qdrant_client: Qdrant client instance
            collection_name: Collection name for storing conversations
            max_history: Maximum messages to return in history
            ttl_hours: Hours before conversations expire
        """
        self.client = qdrant_client
        self.collection_name = collection_name
        self.max_history = max_history
        self.ttl_hours = ttl_hours

        self._ensure_collection()

    def _ensure_collection(self) -> None:
        """Create collection if not exists (dummy vector for metadata)."""
        collections = self.client.get_collections().collections
        collection_names = [c.name for c in collections]

        if self.collection_name not in collection_names:
            self.client.create_collection(
                collection_name=self.collection_name,
                vectors_config=VectorParams(size=1, distance=Distance.COSINE),
            )

    def add_message(
        self,
        session_id: str,
        role: str,
        content: str,
        metadata: Optional[dict] = None,
    ) -> UUID:
        """
        Add message to conversation history.

        Stores message in Qdrant with session_id in payload for fast filtering.
        Uses dummy vector (metadata storage only).

        Args:
            session_id: Unique session identifier
            role: "human" or "ai"
            content: Message text
            metadata: Additional metadata (confidence, sources, etc.)

        Returns:
            Message UUID

        Example:
            >>> msg_id = memory.add_message("session1", "human", "Hello")
            >>> print(msg_id)
            UUID('...')
        """
        message = ConversationMessage(
            session_id=session_id,
            role=role,
            content=content,
            metadata=metadata or {},
        )

        point = PointStruct(
            id=str(message.id),
            vector=[0.0],  # Dummy vector (metadata storage only)
            payload={
                "session_id": session_id,
                "role": role,
                "content": content,
                "timestamp": message.timestamp.timestamp(),  # Unix epoch float
                "metadata": message.metadata,
            },
        )

        self.client.upsert(
            collection_name=self.collection_name,
            points=[point],
        )

        return message.id

    def get_history(
        self,
        session_id: str,
        limit: Optional[int] = None,
    ) -> List[BaseMessage]:
        """
        Retrieve conversation history for session.

        Uses Qdrant metadata filtering for fast retrieval (<5ms).
        Automatically filters out expired messages based on TTL.

        Args:
            session_id: Session to retrieve
            limit: Max messages to return (default: max_history)

        Returns:
            List of LangChain messages (HumanMessage, AIMessage)

        Example:
            >>> history = memory.get_history("session1")
            >>> for msg in history:
            ...     print(f"{msg.__class__.__name__}: {msg.content}")
        """
        limit = limit or self.max_history

        # Calculate cutoff time
        cutoff_time = datetime.utcnow() - timedelta(hours=self.ttl_hours)

        # Build filter for session_id + recent messages
        filter_conditions = Filter(
            must=[
                FieldCondition(
                    key="session_id",
                    match=MatchValue(value=session_id),
                ),
                FieldCondition(
                    key="timestamp",
                    range=Range(gte=cutoff_time.timestamp()),
                ),
            ]
        )

        # Scroll through results
        results, _ = self.client.scroll(
            collection_name=self.collection_name,
            scroll_filter=filter_conditions,
            limit=limit,
            with_payload=True,
            with_vectors=False,
        )

        # Sort by timestamp (oldest first)
        results.sort(key=lambda x: x.payload.get("timestamp", 0) if x.payload else 0)

        # Convert to LangChain messages
        messages = []
        for point in results:
            payload = point.payload
            if payload["role"] == "human":
                messages.append(HumanMessage(content=payload["content"]))
            else:
                messages.append(AIMessage(content=payload["content"]))

        return messages

    def add_exchange(
        self,
        session_id: str,
        user_message: str,
        ai_response: str,
        metadata: Optional[dict] = None,
    ) -> tuple[UUID, UUID]:
        """
        Add a complete conversation exchange (user + AI).

        Convenience method for adding both sides of a conversation turn.

        Args:
            session_id: Session identifier
            user_message: User's question
            ai_response: AI's answer
            metadata: Additional metadata (applied to both messages)

        Returns:
            Tuple of (user_message_id, ai_message_id)

        Example:
            >>> user_id, ai_id = memory.add_exchange(
            ...     "session1",
            ...     "ما هي عاصمة مصر؟",
            ...     "عاصمة مصر هي القاهرة."
            ... )
        """
        user_id = self.add_message(session_id, "human", user_message, metadata)
        ai_id = self.add_message(session_id, "ai", ai_response, metadata)
        return user_id, ai_id

    def clear_session(self, session_id: str) -> None:
        """
        Delete all messages for a session.

        Args:
            session_id: Session to clear

        Example:
            >>> memory.clear_session("session1")
            >>> history = memory.get_history("session1")
            >>> print(len(history))  # 0
        """
        filter_conditions = Filter(
            must=[
                FieldCondition(
                    key="session_id",
                    match=MatchValue(value=session_id),
                )
            ]
        )

        self.client.delete(
            collection_name=self.collection_name,
            points_selector=filter_conditions,
        )

    def cleanup_expired(self) -> int:
        """
        Remove expired conversations.

        Deletes all messages older than TTL threshold.

        Returns:
            Number of messages deleted

        Example:
            >>> deleted = memory.cleanup_expired()
            >>> print(f"Deleted {deleted} expired messages")
        """
        cutoff_time = datetime.utcnow() - timedelta(hours=self.ttl_hours)

        filter_conditions = Filter(
            must=[
                FieldCondition(
                    key="timestamp",
                    range=Range(lt=cutoff_time.timestamp()),
                )
            ]
        )

        # Get count before deletion
        results, _ = self.client.scroll(
            collection_name=self.collection_name,
            scroll_filter=filter_conditions,
            limit=10000,
            with_payload=False,
            with_vectors=False,
        )

        count = len(results)

        if count > 0:
            self.client.delete(
                collection_name=self.collection_name,
                points_selector=filter_conditions,
            )

        return count

    def get_session_count(self, session_id: str) -> int:
        """
        Get message count for a session.

        Args:
            session_id: Session to count

        Returns:
            Number of messages in session

        Example:
            >>> count = memory.get_session_count("session1")
            >>> print(f"Session has {count} messages")
        """
        filter_conditions = Filter(
            must=[
                FieldCondition(
                    key="session_id",
                    match=MatchValue(value=session_id),
                )
            ]
        )

        results, _ = self.client.scroll(
            collection_name=self.collection_name,
            scroll_filter=filter_conditions,
            limit=10000,
            with_payload=False,
            with_vectors=False,
        )

        return len(results)
