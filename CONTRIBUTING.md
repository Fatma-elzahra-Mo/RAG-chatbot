# Contributing Guidelines

Thank you for your interest in contributing to the Arabic RAG Chatbot! This document provides guidelines and instructions for contributing to the project.

## Table of Contents

- [Code of Conduct](#code-of-conduct)
- [Getting Started](#getting-started)
- [Development Setup](#development-setup)
- [Development Workflow](#development-workflow)
- [Code Standards](#code-standards)
- [Testing Guidelines](#testing-guidelines)
- [Pull Request Process](#pull-request-process)
- [Issue Reporting](#issue-reporting)

## Code of Conduct

We are committed to providing a welcoming and inclusive environment for all contributors. Please be respectful and professional in all interactions.

### Our Standards

- Use welcoming and inclusive language
- Be respectful of differing viewpoints and experiences
- Gracefully accept constructive criticism
- Focus on what is best for the community
- Show empathy towards other community members

## Getting Started

### Prerequisites

- Python 3.11 or 3.12
- Git
- uv package manager
- Docker & Docker Compose (for integration testing)
- Basic understanding of RAG systems and NLP

### Fork and Clone

1. Fork the repository on GitHub
2. Clone your fork locally:

```bash
git clone https://github.com/YOUR_USERNAME/arabic-rag-chatbot.git
cd arabic-rag-chatbot
```

3. Add the upstream repository:

```bash
git remote add upstream https://github.com/ORIGINAL_OWNER/arabic-rag-chatbot.git
```

## Development Setup

### 1. Install uv

```bash
# macOS/Linux
curl -LsSf https://astral.sh/uv/install.sh | sh

# Windows
powershell -c "irm https://astral.sh/uv/install.ps1 | iex"
```

### 2. Create Virtual Environment

```bash
uv venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate
```

### 3. Install Dependencies

```bash
# Install project with development dependencies
uv pip install -e ".[dev]"
```

### 4. Install Pre-commit Hooks

```bash
pre-commit install
```

### 5. Configure Environment

```bash
cp .env.example .env
# Edit .env with your configuration
```

### 6. Start Services

```bash
# Start Qdrant and dependencies
docker-compose up -d qdrant
```

## Development Workflow

### Creating a Feature Branch

```bash
# Update main branch
git checkout main
git pull upstream main

# Create feature branch
git checkout -b feature/your-feature-name
```

### Branch Naming Convention

- `feature/`: New features (e.g., `feature/add-streaming`)
- `fix/`: Bug fixes (e.g., `fix/memory-leak`)
- `docs/`: Documentation updates (e.g., `docs/api-examples`)
- `test/`: Test additions (e.g., `test/add-reranker-tests`)
- `refactor/`: Code refactoring (e.g., `refactor/simplify-pipeline`)
- `perf/`: Performance improvements (e.g., `perf/optimize-embeddings`)

### Making Changes

1. Make your changes in small, logical commits
2. Write clear commit messages (see [Commit Messages](#commit-messages))
3. Add tests for new functionality
4. Update documentation as needed
5. Run tests locally before pushing

### Commit Messages

We follow [Conventional Commits](https://www.conventionalcommits.org/):

```
<type>(<scope>): <subject>

<body>

<footer>
```

**Types**:
- `feat`: New feature
- `fix`: Bug fix
- `docs`: Documentation changes
- `test`: Test additions or modifications
- `refactor`: Code refactoring
- `perf`: Performance improvements
- `style`: Code style changes (formatting, etc.)
- `chore`: Maintenance tasks

**Examples**:
```bash
feat(retrieval): add support for hybrid search

Implement hybrid search combining dense and sparse retrieval
for improved accuracy on rare terms.

Closes #123

---

fix(memory): resolve session isolation bug

Sessions were sharing memory due to incorrect filtering.
Added session_id validation and tests.

Fixes #456

---

docs(api): add streaming endpoint examples

Added Python and JavaScript examples for the new
streaming API endpoint.
```

## Code Standards

### Python Style

We use the following tools to maintain code quality:

- **Black**: Code formatting (line length: 100)
- **Ruff**: Fast linting and import sorting
- **MyPy**: Static type checking (strict mode)
- **isort**: Import organization

### Running Code Quality Tools

```bash
# Format code
black src/ tests/

# Lint code
ruff check src/ tests/

# Fix linting issues
ruff check --fix src/ tests/

# Type checking
mypy src/

# Run all checks
make lint
```

### Code Style Guidelines

1. **Type Hints**: All functions must have type hints

```python
# Good
def process_query(query: str, session_id: str) -> dict[str, Any]:
    """Process a user query."""
    ...

# Bad
def process_query(query, session_id):
    """Process a user query."""
    ...
```

2. **Docstrings**: All public functions/classes must have docstrings

```python
def embed_text(text: str) -> list[float]:
    """
    Generate embeddings for the given text.

    Args:
        text: Input text to embed

    Returns:
        List of 1024-dimensional embedding values

    Raises:
        ValueError: If text is empty
    """
    ...
```

3. **Error Handling**: Use specific exceptions

```python
# Good
if not query:
    raise ValueError("Query cannot be empty")

# Bad
if not query:
    raise Exception("Error")
```

4. **Logging**: Use structured logging

```python
# Good
logger.info(
    "Query processed",
    extra={
        "session_id": session_id,
        "query_type": query_type,
        "processing_time_ms": elapsed_ms
    }
)

# Bad
print(f"Processed query for {session_id}")
```

5. **Constants**: Use UPPERCASE for constants

```python
# Good
DEFAULT_CHUNK_SIZE = 512
MAX_HISTORY_MESSAGES = 5

# Bad
default_chunk_size = 512
```

## Testing Guidelines

### Test Structure

```
tests/
├── unit/              # Unit tests (fast, isolated)
├── integration/       # Integration tests (with services)
└── e2e/              # End-to-end tests (full workflow)
```

### Writing Tests

1. **Test Coverage**: Aim for >80% coverage

```bash
pytest --cov=src --cov-report=html
```

2. **Test Naming**: Use descriptive names

```python
# Good
def test_normalize_text_removes_diacritics():
    ...

def test_query_router_detects_greeting():
    ...

# Bad
def test_1():
    ...
```

3. **Test Structure**: Use Arrange-Act-Assert

```python
def test_embedding_generation():
    # Arrange
    embedder = BGEEmbedder()
    text = "مرحبا بك"

    # Act
    embedding = embedder.embed(text)

    # Assert
    assert len(embedding) == 1024
    assert all(isinstance(x, float) for x in embedding)
```

4. **Fixtures**: Use pytest fixtures for reusable setup

```python
@pytest.fixture
def sample_query():
    return "ما هي عاصمة مصر؟"

@pytest.fixture
def mock_embedder():
    return Mock(spec=BGEEmbedder)
```

### Running Tests

```bash
# Run all tests
pytest

# Run specific test file
pytest tests/unit/test_normalizer.py

# Run with coverage
pytest --cov=src --cov-report=html

# Run specific test
pytest tests/unit/test_normalizer.py::test_normalize_text_removes_diacritics

# Run with verbose output
pytest -v

# Run and stop on first failure
pytest -x
```

## Pull Request Process

### Before Submitting

1. **Run Tests**: Ensure all tests pass

```bash
pytest
```

2. **Check Code Quality**: Run linting and formatting

```bash
black src/ tests/
ruff check --fix src/ tests/
mypy src/
```

3. **Update Documentation**: Update relevant docs

4. **Test Manually**: Test your changes in a real environment

### Submitting a PR

1. Push your branch to your fork:

```bash
git push origin feature/your-feature-name
```

2. Open a Pull Request on GitHub

3. Fill out the PR template completely

4. Link related issues using keywords:
   - `Closes #123` (for features)
   - `Fixes #456` (for bugs)

### PR Template

```markdown
## Description
Brief description of changes

## Type of Change
- [ ] Bug fix
- [ ] New feature
- [ ] Documentation update
- [ ] Performance improvement
- [ ] Refactoring

## Testing
- [ ] Added unit tests
- [ ] Added integration tests
- [ ] Manual testing completed

## Checklist
- [ ] Code follows style guidelines
- [ ] All tests pass
- [ ] Documentation updated
- [ ] No breaking changes (or documented)

## Related Issues
Closes #123
```

### PR Review Process

1. Automated checks must pass (CI/CD)
2. At least one maintainer review required
3. All review comments addressed
4. No merge conflicts
5. Documentation updated if needed

### Addressing Review Comments

```bash
# Make changes based on review
git add .
git commit -m "address review comments"
git push origin feature/your-feature-name
```

## Issue Reporting

### Bug Reports

Use the bug report template and include:

- Clear description of the bug
- Steps to reproduce
- Expected vs actual behavior
- Environment details (Python version, OS, etc.)
- Relevant logs or error messages

**Example**:
```markdown
**Bug Description**
Memory not being properly isolated between sessions

**Steps to Reproduce**
1. Create session A with query "مرحبا"
2. Create session B with query "Hello"
3. Query session A with "وما اسمك؟"

**Expected Behavior**
Session A should not see messages from session B

**Actual Behavior**
Session A responses include context from session B

**Environment**
- Python: 3.11
- OS: macOS 14
- Version: 1.0.0
```

### Feature Requests

Use the feature request template and include:

- Clear description of the feature
- Use case and benefits
- Proposed implementation (optional)
- Alternative solutions considered

### Questions

For questions:
- Check existing documentation first
- Search closed issues
- Open a discussion (not an issue)

## Development Tips

### Useful Make Commands

```bash
# Run tests
make test

# Run linting
make lint

# Format code
make format

# Start development server
make dev

# Build Docker image
make build
```

### Debugging

1. **Enable Debug Logging**:

```python
import logging
logging.basicConfig(level=logging.DEBUG)
```

2. **Use Debugger**:

```bash
# Run with debugger
python -m pdb src/api/main.py
```

3. **Interactive Testing**:

```bash
# Start Python REPL with project loaded
python -i -c "from src.core.pipeline import RAGPipeline; pipeline = RAGPipeline()"
```

### Performance Profiling

```bash
# Profile code
python -m cProfile -o profile.stats script.py

# Analyze profile
python -m pstats profile.stats
```

## Getting Help

- **Documentation**: Check [docs/](docs/) folder
- **Issues**: Search existing issues on GitHub
- **Discussions**: Start a discussion for questions
- **Email**: Contact maintainers for sensitive issues

## Recognition

Contributors will be recognized in:
- CONTRIBUTORS.md file
- Release notes
- Project documentation

Thank you for contributing to the Arabic RAG Chatbot!
