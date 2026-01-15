"""Unit tests for conversation memory manager."""

import pytest
from datetime import datetime, timedelta
from uuid import UUID

from langchain_core.messages import AIMessage, HumanMessage
from qdrant_client import QdrantClient

from src.memory.conversation import ConversationMemory


class TestConversationMemory:
    """Test ConversationMemory class."""

    @pytest.fixture
    def qdrant_client(self):
        """Create in-memory Qdrant client."""
        return QdrantClient(":memory:")

    @pytest.fixture
    def memory(self, qdrant_client):
        """Create conversation memory instance."""
        return ConversationMemory(
            qdrant_client=qdrant_client,
            collection_name="test_conversations",
            max_history=10,
            ttl_hours=24,
        )

    def test_collection_creation(self, memory):
        """Test that collection is created on init."""
        collections = memory.client.get_collections().collections
        collection_names = [c.name for c in collections]

        assert "test_conversations" in collection_names

    def test_add_message(self, memory):
        """Test adding a single message."""
        msg_id = memory.add_message("session1", "human", "مرحبا")

        assert msg_id is not None
        assert isinstance(msg_id, UUID)

        count = memory.get_session_count("session1")
        assert count == 1

    def test_add_message_with_metadata(self, memory):
        """Test adding message with custom metadata."""
        msg_id = memory.add_message(
            "session1",
            "ai",
            "مرحبا بك",
            metadata={"confidence": 0.95, "source": "rag"},
        )

        assert msg_id is not None
        history = memory.get_history("session1")
        assert len(history) == 1

    def test_add_exchange(self, memory):
        """Test adding user + AI exchange."""
        user_id, ai_id = memory.add_exchange(
            "session1", "ما هي عاصمة مصر؟", "عاصمة مصر هي القاهرة."
        )

        assert user_id != ai_id
        assert isinstance(user_id, UUID)
        assert isinstance(ai_id, UUID)
        assert memory.get_session_count("session1") == 2

    def test_get_history(self, memory):
        """Test retrieving conversation history."""
        memory.add_message("session1", "human", "مرحبا")
        memory.add_message("session1", "ai", "مرحبا بك")

        history = memory.get_history("session1")

        assert len(history) == 2
        assert isinstance(history[0], HumanMessage)
        assert isinstance(history[1], AIMessage)
        assert history[0].content == "مرحبا"
        assert history[1].content == "مرحبا بك"

    def test_history_ordering(self, memory):
        """Test that history is ordered chronologically."""
        messages = ["أول", "ثاني", "ثالث"]

        for msg in messages:
            memory.add_message("session1", "human", msg)

        history = memory.get_history("session1")

        assert len(history) == 3
        assert history[0].content == "أول"
        assert history[1].content == "ثاني"
        assert history[2].content == "ثالث"

    def test_history_limit(self, memory):
        """Test history retrieval with custom limit."""
        # Add 10 messages
        for i in range(10):
            memory.add_message("session1", "human", f"message {i}")

        # Get only 5
        history = memory.get_history("session1", limit=5)
        assert len(history) == 5

    def test_clear_session(self, memory):
        """Test clearing a session."""
        memory.add_message("session1", "human", "test")
        memory.add_message("session1", "ai", "response")

        assert memory.get_session_count("session1") == 2

        memory.clear_session("session1")

        assert memory.get_session_count("session1") == 0

    def test_multi_session_isolation(self, memory):
        """Test that sessions are isolated."""
        memory.add_message("session1", "human", "message1")
        memory.add_message("session2", "human", "message2")

        history1 = memory.get_history("session1")
        history2 = memory.get_history("session2")

        assert len(history1) == 1
        assert len(history2) == 1
        assert history1[0].content != history2[0].content

    def test_multiple_sessions_count(self, memory):
        """Test counting messages across multiple sessions."""
        memory.add_message("session1", "human", "msg1")
        memory.add_message("session1", "ai", "response1")
        memory.add_message("session2", "human", "msg2")

        assert memory.get_session_count("session1") == 2
        assert memory.get_session_count("session2") == 1

    def test_get_empty_history(self, memory):
        """Test getting history for non-existent session."""
        history = memory.get_history("nonexistent_session")
        assert len(history) == 0

    def test_clear_empty_session(self, memory):
        """Test clearing a session that doesn't exist."""
        # Should not raise an error
        memory.clear_session("nonexistent_session")
        assert memory.get_session_count("nonexistent_session") == 0

    def test_max_history_enforcement(self, memory):
        """Test that max_history limit is enforced."""
        # Add 15 messages (more than max_history=10)
        for i in range(15):
            memory.add_message("session1", "human", f"message {i}")

        # Should only return max_history (10)
        history = memory.get_history("session1")
        assert len(history) <= 10

    def test_conversation_flow(self, memory):
        """Test a realistic conversation flow."""
        session_id = "conversation_test"

        # Turn 1
        memory.add_exchange(
            session_id, "ما هي عاصمة السعودية؟", "عاصمة السعودية هي الرياض."
        )

        # Turn 2
        memory.add_exchange(session_id, "وما عدد سكانها؟", "حوالي 7 مليون نسمة.")

        # Turn 3
        memory.add_exchange(session_id, "شكرا لك", "العفو، سعيد بخدمتك.")

        history = memory.get_history(session_id)

        assert len(history) == 6  # 3 turns × 2 messages
        assert isinstance(history[0], HumanMessage)
        assert isinstance(history[1], AIMessage)
        assert history[0].content == "ما هي عاصمة السعودية؟"

    def test_cleanup_expired_no_messages(self, memory):
        """Test cleanup when no messages are expired."""
        memory.add_message("session1", "human", "recent message")

        deleted = memory.cleanup_expired()
        assert deleted == 0

    def test_get_session_count_zero(self, memory):
        """Test getting count for empty session."""
        count = memory.get_session_count("empty_session")
        assert count == 0

    def test_mixed_roles_in_conversation(self, memory):
        """Test conversation with mixed human/AI messages."""
        session_id = "mixed_test"

        memory.add_message(session_id, "human", "First human")
        memory.add_message(session_id, "ai", "First AI")
        memory.add_message(session_id, "human", "Second human")
        memory.add_message(session_id, "ai", "Second AI")

        history = memory.get_history(session_id)

        assert len(history) == 4
        assert history[0].content == "First human"
        assert history[1].content == "First AI"
        assert history[2].content == "Second human"
        assert history[3].content == "Second AI"

    def test_add_exchange_with_metadata(self, memory):
        """Test adding exchange with metadata."""
        user_id, ai_id = memory.add_exchange(
            "session1",
            "سؤال",
            "جواب",
            metadata={"confidence": 0.9},
        )

        assert user_id != ai_id
        assert memory.get_session_count("session1") == 2
