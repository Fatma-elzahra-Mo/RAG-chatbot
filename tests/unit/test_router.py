"""
Unit tests for QueryRouter.

Tests intelligent query routing for cost optimization.
"""

import pytest

from src.core.router import QueryRouter


class TestQueryRouter:
    """Test suite for QueryRouter."""

    @pytest.fixture
    def router(self):
        """Create router instance for testing."""
        return QueryRouter()

    # Greeting detection tests
    def test_greeting_arabic(self, router):
        """Test Arabic greeting detection."""
        assert router.route("مرحبا") == "greeting"
        assert router.route("أهلا") == "greeting"
        assert router.route("السلام عليكم") == "greeting"
        assert router.route("صباح الخير") == "greeting"
        assert router.route("مساء الخير") == "greeting"

    def test_greeting_english(self, router):
        """Test English greeting detection."""
        assert router.route("hello") == "greeting"
        assert router.route("hi") == "greeting"
        assert router.route("hey") == "greeting"
        assert router.route("good morning") == "greeting"

    def test_greeting_case_insensitive(self, router):
        """Test greeting detection is case-insensitive."""
        assert router.route("مرحبا") == "greeting"
        assert router.route("HELLO") == "greeting"
        assert router.route("Hello") == "greeting"

    # Simple question tests
    def test_simple_question_arabic(self, router):
        """Test Arabic simple question detection."""
        assert router.route("ما اسمك؟") == "simple"
        assert router.route("من أنت؟") == "simple"
        assert router.route("كيف حالك؟") == "simple"
        assert router.route("شكراً") == "simple"

    def test_simple_question_english(self, router):
        """Test English simple question detection."""
        assert router.route("what is your name") == "simple"
        assert router.route("who are you") == "simple"
        assert router.route("thank you") == "simple"

    # Calculator tests
    def test_calculator_math_operations(self, router):
        """Test math operation detection."""
        assert router.route("5 + 3") == "calculator"
        assert router.route("10 - 2") == "calculator"
        assert router.route("4 * 6") == "calculator"
        assert router.route("20 / 4") == "calculator"
        assert router.route("15×5") == "calculator"
        assert router.route("30÷6") == "calculator"

    def test_calculator_arabic(self, router):
        """Test Arabic calculator keywords."""
        assert router.route("احسب 5 + 3") == "calculator"
        assert router.route("ما ناتج 10 + 20") == "calculator"
        assert router.route("ما هو حاصل 5 في 6") == "calculator"

    def test_calculator_english(self, router):
        """Test English calculator keywords."""
        assert router.route("calculate 5 + 3") == "calculator"

    # RAG query tests
    def test_rag_complex_questions(self, router):
        """Test complex questions requiring RAG."""
        assert router.route("ما هي عاصمة مصر؟") == "rag"
        assert router.route("اشرح لي الذكاء الاصطناعي") == "rag"
        assert router.route("كيف يعمل التعلم العميق؟") == "rag"
        assert router.route("ما هي فوائد الطاقة الشمسية؟") == "rag"

    def test_rag_default_route(self, router):
        """Test that unknown queries default to RAG."""
        assert router.route("سؤال عشوائي معقد") == "rag"
        assert router.route("random complex query") == "rag"

    # Edge cases
    def test_empty_query(self, router):
        """Test empty query handling."""
        result = router.route("")
        # Empty query should default to RAG
        assert result == "rag"

    def test_whitespace_handling(self, router):
        """Test queries with extra whitespace."""
        assert router.route("  مرحبا  ") == "greeting"
        assert router.route("  5 + 3  ") == "calculator"

    def test_mixed_content(self, router):
        """Test queries with mixed greeting and question."""
        # Greetings are checked first, so should be greeting
        assert router.route("مرحبا، ما هي عاصمة مصر؟") == "greeting"

    # Performance/cost optimization verification
    def test_routing_reduces_cost(self, router):
        """Verify that routing can skip RAG for simple queries."""
        # These should NOT trigger RAG (cost savings)
        cost_saving_queries = [
            "مرحبا",
            "ما اسمك",
            "5 + 3",
            "شكراً",
        ]

        for query in cost_saving_queries:
            result = router.route(query)
            assert result != "rag", f"Query '{query}' should not use RAG"

    def test_complex_queries_use_rag(self, router):
        """Verify that complex queries use RAG."""
        rag_queries = [
            "ما هي عاصمة مصر؟",
            "اشرح الذكاء الاصطناعي",
            "كيف تعمل الخلايا الشمسية؟",
        ]

        for query in rag_queries:
            result = router.route(query)
            assert result == "rag", f"Query '{query}' should use RAG"
