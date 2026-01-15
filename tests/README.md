# Test Suite Documentation

## Test Organization

```
tests/
├── unit/           # Fast, isolated tests
├── integration/    # Tests with external dependencies
├── e2e/            # Complete workflow tests
├── performance/    # Benchmark tests
└── conftest.py     # Shared fixtures
```

## Running Tests

```bash
# All tests
pytest tests/

# Unit tests only
pytest tests/unit/

# Integration tests
pytest tests/integration/

# E2E tests
pytest tests/e2e/ -m e2e

# Performance benchmarks
pytest tests/performance/ -m performance

# With coverage
pytest --cov=src --cov-report=html

# Specific markers
pytest -m unit
pytest -m e2e
pytest -m performance

# Run all test suites
./scripts/run_tests.sh
```

## Coverage Goals

- **Target**: >80% code coverage
- **Current**: Run `pytest --cov=src --cov-report=term`
- **Report**: `htmlcov/index.html`

## Test Markers

- `unit` - Fast, isolated unit tests
- `integration` - Tests with external dependencies
- `e2e` - End-to-end workflow tests
- `performance` - Performance benchmarks

## Adding Tests

1. Write test in appropriate directory
2. Use fixtures from `conftest.py`
3. Mark with appropriate marker using `@pytest.mark.<marker>`
4. Ensure test is isolated (no side effects)

## Fixtures Available

- `sample_arabic_text` - Sample Arabic text
- `sample_query` - Sample query text
- `qdrant_memory_client` - In-memory Qdrant client
- `arabic_test_texts` - Dictionary of test data
- `mock_openai_response` - Mock OpenAI response

## Pre-commit Hooks

Install pre-commit hooks:
```bash
pip install pre-commit
pre-commit install
```

Run manually:
```bash
pre-commit run --all-files
```

## RAGAS Evaluation

Run RAG evaluation:
```bash
python scripts/evaluate_rag.py
```

Requires: `pip install ragas`
