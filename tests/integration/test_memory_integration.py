"""Integration tests for conversation memory with real Qdrant."""

import pytest
from qdrant_client import QdrantClient

from src.config.settings import settings
from src.memory.conversation import ConversationMemory


@pytest.mark.integration
class TestMemoryIntegration:
    """Integration tests with real Qdrant instance."""

    @pytest.fixture
    def real_qdrant(self):
        """
        Connect to real Qdrant instance (requires Docker).

        Start Qdrant with:
        docker run -p 6333:6333 qdrant/qdrant
        """
        try:
            client = QdrantClient(url=settings.qdrant_url)
            # Test connection
            client.get_collections()
            yield client
        except Exception as e:
            pytest.skip(f"Qdrant not available: {e}")

    def test_full_conversation_flow(self, real_qdrant):
        """Test complete conversation flow with real Qdrant."""
        memory = ConversationMemory(
            qdrant_client=real_qdrant,
            collection_name="integration_test_conversations",
            max_history=10,
            ttl_hours=24,
        )

        # Simulate conversation
        session_id = "integration_test_session"

        try:
            # Turn 1
            memory.add_exchange(
                session_id, "ما هي عاصمة السعودية؟", "عاصمة السعودية هي الرياض."
            )

            # Turn 2
            memory.add_exchange(
                session_id, "وما عدد سكانها؟", "عدد سكان الرياض حوالي 7 مليون نسمة."
            )

            # Turn 3
            memory.add_exchange(session_id, "شكرا لك", "العفو، كيف يمكنني مساعدتك أيضا؟")

            # Verify history
            history = memory.get_history(session_id)
            assert len(history) == 6  # 3 turns × 2 messages

            # Verify ordering
            assert history[0].content == "ما هي عاصمة السعودية؟"
            assert history[1].content == "عاصمة السعودية هي الرياض."

            # Verify count
            count = memory.get_session_count(session_id)
            assert count == 6

        finally:
            # Cleanup
            memory.clear_session(session_id)

    def test_metadata_filtering_performance(self, real_qdrant):
        """Test that metadata filtering is fast (<5ms target)."""
        import time

        memory = ConversationMemory(
            qdrant_client=real_qdrant,
            collection_name="integration_test_performance",
        )

        session_id = "performance_test_session"

        try:
            # Add multiple messages
            for i in range(20):
                memory.add_message(session_id, "human", f"Message {i}")

            # Measure retrieval time
            start = time.perf_counter()
            history = memory.get_history(session_id)
            elapsed_ms = (time.perf_counter() - start) * 1000

            # Should be fast (< 10ms for integration test)
            assert elapsed_ms < 10, f"Query took {elapsed_ms}ms (target: <10ms)"
            assert len(history) <= 10  # max_history default

        finally:
            memory.clear_session(session_id)

    def test_multi_session_isolation_real_qdrant(self, real_qdrant):
        """Test session isolation with real Qdrant."""
        memory = ConversationMemory(
            qdrant_client=real_qdrant,
            collection_name="integration_test_isolation",
        )

        session1 = "user_1_session"
        session2 = "user_2_session"

        try:
            # User 1 conversation
            memory.add_exchange(session1, "مرحبا", "مرحبا بك")

            # User 2 conversation
            memory.add_exchange(session2, "Hello", "Hi there")

            # Verify isolation
            history1 = memory.get_history(session1)
            history2 = memory.get_history(session2)

            assert len(history1) == 2
            assert len(history2) == 2
            assert history1[0].content == "مرحبا"
            assert history2[0].content == "Hello"

        finally:
            memory.clear_session(session1)
            memory.clear_session(session2)

    def test_cleanup_expired_real_qdrant(self, real_qdrant):
        """Test cleanup of expired messages."""
        memory = ConversationMemory(
            qdrant_client=real_qdrant,
            collection_name="integration_test_cleanup",
            ttl_hours=0,  # Expire immediately for testing
        )

        session_id = "cleanup_test_session"

        try:
            # Add message
            memory.add_message(session_id, "human", "Old message")

            # Message should be there
            assert memory.get_session_count(session_id) == 1

            # Cleanup (with ttl_hours=0, all messages are expired)
            deleted = memory.cleanup_expired()
            assert deleted >= 1

            # Message should be gone
            assert memory.get_session_count(session_id) == 0

        finally:
            memory.clear_session(session_id)

    def test_long_conversation_persistence(self, real_qdrant):
        """Test that long conversations persist correctly."""
        memory = ConversationMemory(
            qdrant_client=real_qdrant,
            collection_name="integration_test_long_conversation",
        )

        session_id = "long_conversation_session"

        try:
            # Simulate 50 message exchanges
            for i in range(50):
                memory.add_exchange(session_id, f"سؤال {i}", f"جواب {i}")

            # Should have 100 messages total
            total_count = memory.get_session_count(session_id)
            assert total_count == 100

            # Get history (limited to max_history)
            history = memory.get_history(session_id)
            assert len(history) <= 10  # Default max_history

            # Get more history with custom limit
            history_20 = memory.get_history(session_id, limit=20)
            assert len(history_20) == 20

        finally:
            memory.clear_session(session_id)
