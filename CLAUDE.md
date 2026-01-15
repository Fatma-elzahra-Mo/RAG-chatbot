# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Production-ready Arabic RAG chatbot with conversation memory, built using 2025 AI benchmarks. The system uses:
- **BGE-M3 embeddings** (70.99% avg score - best for Arabic)
- **ARA-Reranker-V1** (0.934 MRR, +6% improvement)
- **Sentence-aware chunking** (74.78% vs 69.41% fixed-size)
- **Intelligent query routing** (40% cost savings by skipping retrieval for simple queries)
- **Qdrant** for both vector storage and conversation memory

## Development Commands

### Setup & Installation
```bash
# Install dependencies (uses uv package manager)
uv pip install -e ".[dev]"

# Or use Make for full setup
make dev-setup
```

### Running the API
```bash
# Development mode with auto-reload
uvicorn src.api.main:app --reload

# Or use the script
./run_api.sh

# Production mode with Docker
docker-compose up -d
```

### Testing
```bash
# Run all tests with coverage
pytest tests/ --cov=src

# Run specific test categories
pytest tests/unit/              # Unit tests only
pytest tests/integration/       # Integration tests
pytest tests/e2e/ -m e2e       # E2E tests

# Run with Make
make test                       # All tests
make test-unit                  # Unit only
make test-integration           # Integration only
make test-cov                   # With HTML coverage report

# Run single test file
pytest tests/unit/test_normalizer.py

# Run specific test
pytest tests/unit/test_normalizer.py::test_normalize_text_removes_diacritics -v
```

### Code Quality
```bash
# Format code
black src/ tests/
make format

# Lint
ruff check src/ tests/
ruff check --fix src/ tests/    # Auto-fix issues

# Type checking
mypy src/

# Run all checks
make lint

# Pre-commit hooks
pre-commit install
pre-commit run --all-files
```

### Docker
```bash
# Start all services (Qdrant, Redis, PostgreSQL, API)
docker-compose up -d

# Start in development mode
docker-compose -f docker-compose.yml -f docker-compose.dev.yml up

# View logs
docker-compose logs -f

# Stop services
docker-compose down
```

### Data Ingestion
```bash
# Ingest sample Arabic documents
./scripts/ingest_sample_data.sh
```

### Running with vLLM (Local Models)
```bash
# Install vLLM (requires CUDA for GPU acceleration)
pip install vllm

# Start vLLM server with a model
python -m vllm.entrypoints.openai.api_server \
  --model meta-llama/Llama-2-7b-chat-hf \
  --port 8000 \
  --host 0.0.0.0

# Configure environment to use vLLM
export LLM_PROVIDER=local
export VLLM_BASE_URL=http://localhost:8000/v1
export VLLM_MODEL=meta-llama/Llama-2-7b-chat-hf

# Run the API
uvicorn src.api.main:app --reload

# Or use huggingface provider (same vLLM backend)
export LLM_PROVIDER=huggingface
```

## Architecture

### Core Pipeline Flow (src/core/pipeline.py)
The RAG pipeline follows this sequence:
1. **Normalize query** - Arabic text normalization (remove diacritics, normalize forms)
2. **Get conversation history** - Retrieve from Qdrant using session_id metadata filtering
3. **Route query** - Determine query type (greeting/simple/calculator/rag)
4. **Process based on type**:
   - **Greeting**: Direct LLM response (no retrieval)
   - **Simple**: LLM response with chat history (no retrieval)
   - **Calculator**: Math-specific prompt
   - **RAG**: Full retrieval pipeline (see below)
5. **Save to memory** - Store exchange in Qdrant

### RAG Query Processing (_handle_rag_query)
When query routing determines RAG is needed:
1. **Embed query** - BGE-M3 embeddings (1024-dim)
2. **Retrieve top-k** - Vector search in Qdrant (default k=10)
3. **Rerank to top-n** - ARA-Reranker-V1 (default n=3)
4. **Build context** - Join reranked document content
5. **Generate response** - LLM with context and chat history
6. **Format sources** - Return documents with metadata

### Query Router (src/core/router.py)
**Critical for cost optimization** - saves ~40% by skipping retrieval:
- **Greeting patterns**: "مرحبا", "أهلا", "hello", "hi", etc.
- **Simple patterns**: "ما اسمك", "من أنت", "what's your name", etc.
- **Calculator patterns**: Math expressions, "احسب", "calculate"
- **Default to RAG**: Complex queries requiring retrieval

### Conversation Memory (src/memory/conversation.py)
Uses **Qdrant metadata filtering** (not a separate database):
- Stores messages with dummy vectors (metadata-only storage)
- Fast retrieval via `session_id` filter (<5ms)
- Automatic TTL-based cleanup (default: 24 hours)
- LangChain message format (HumanMessage, AIMessage)
- Methods: `add_exchange()`, `get_history()`, `clear_session()`, `cleanup_expired()`

### Configuration (src/config/settings.py)
Uses **pydantic-settings** with environment variables:
- All settings override via `.env` file or ENV vars
- Key settings:
  - `LLM_PROVIDER` - LLM provider: "openai", "gemini", "openrouter", "local", "huggingface"
  - `OPENAI_API_KEY` - Required for OpenAI provider
  - `GEMINI_API_KEY` - Required for Gemini provider
  - `OPENROUTER_API_KEY` - Required for OpenRouter provider
  - `VLLM_BASE_URL` - vLLM server URL (default: http://localhost:8000/v1)
  - `VLLM_MODEL` - vLLM model name (default: meta-llama/Llama-2-7b-chat-hf)
  - `VLLM_TEMPERATURE` - vLLM response creativity (default: 0.7)
  - `VLLM_MAX_TOKENS` - vLLM max response tokens (default: 512)
  - `QDRANT_URL` - Vector database (default: localhost:6333)
  - `embeddings_model` - BAAI/bge-m3 (do not change without benchmarking)
  - `reranker_model` - ARA-Reranker-V1 (optimized for Arabic)
  - `chunk_size` - 512 tokens (sentence-aware chunking)
  - `retrieval_top_k` - 10 documents (before reranking)
  - `reranker_top_n` - 3 documents (after reranking)

### Key Components

**Embeddings** (`src/retrieval/embeddings.py`):
- Uses BGE-M3 from HuggingFace
- 1024-dimensional vectors
- Optimized for Arabic multilingual tasks

**Reranker** (`src/retrieval/reranker.py`):
- ARA-Reranker-V1 cross-encoder
- Reranks retrieved documents by relevance
- Improves accuracy by 6% over embedding-only

**Vector Store** (`src/retrieval/vectorstore.py`):
- Qdrant client wrapper
- COSINE distance metric
- Handles collection management and search

**Normalizer** (`src/preprocessing/normalizer.py`):
- Removes Arabic diacritics (tashkeel)
- Normalizes Arabic letter forms
- Essential for consistent embeddings

**Chunker** (`src/preprocessing/chunker.py`):
- Sentence-aware chunking (74.78% accuracy)
- Respects sentence boundaries
- Default: 512 tokens with 50 overlap

## API Structure

**Main App** (`src/api/main.py`):
- FastAPI application with CORS
- Routers: chat, documents, health
- Lifespan events for startup/shutdown

**Routes**:
- `/chat` - Chat endpoint with session support
- `/documents` - Document ingestion
- `/health` - Health check

## Important Patterns

### Adding New Documents
```python
from src.core.pipeline import RAGPipeline

pipeline = RAGPipeline()
pipeline.ingest_documents(
    texts=["النص العربي هنا"],
    metadatas=[{"source": "document.pdf", "page": 1}]
)
```

### Querying with Memory
```python
result = pipeline.query(
    query="ما هي عاصمة مصر؟",
    session_id="user-123",  # Required for conversation memory
    use_rag=True
)
# Returns: {response, sources, query_type, session_id}
```

### Using vLLM for Local Models
```python
# Option 1: Set environment variables
import os
os.environ["LLM_PROVIDER"] = "local"
os.environ["VLLM_BASE_URL"] = "http://localhost:8000/v1"
os.environ["VLLM_MODEL"] = "meta-llama/Llama-2-7b-chat-hf"

# Option 2: Direct initialization with custom vLLM wrapper
from src.models.vllm_model import VLLMLLMWrapper

llm = VLLMLLMWrapper(
    base_url="http://localhost:8000/v1",
    model_name="meta-llama/Llama-2-7b-chat-hf",
    temperature=0.7,
    max_tokens=512,
    verify_connection=True  # Check server health on init
)

# Use in pipeline
from src.core.pipeline import RAGPipeline
pipeline = RAGPipeline()  # Will use settings.llm_provider
result = pipeline.query("ما هي عاصمة مصر؟")

# Streaming responses (optional)
from langchain_core.messages import HumanMessage
for chunk in llm.stream([HumanMessage(content="مرحبا")]):
    print(chunk.content, end="", flush=True)
```

### Switching Between LLM Providers
```python
# In .env file or environment:
# LLM_PROVIDER=openai       # Use OpenAI GPT models
# LLM_PROVIDER=gemini       # Use Google Gemini
# LLM_PROVIDER=openrouter   # Use OpenRouter (300+ models)
# LLM_PROVIDER=local        # Use local vLLM server
# LLM_PROVIDER=huggingface  # Use vLLM with HF models (same as local)

# No code changes needed - just restart the application
```

### Testing Patterns
- **Unit tests**: Mock external dependencies (Qdrant, OpenAI)
- **Integration tests**: Use in-memory Qdrant client (`:memory:`)
- **Fixtures**: Use `conftest.py` fixtures for reusable test data
- **Markers**: `@pytest.mark.unit`, `@pytest.mark.integration`, `@pytest.mark.e2e`

## Dependencies

**Core**:
- `langchain` - RAG framework
- `haystack-ai` - Document processing
- `qdrant-client` - Vector database
- `sentence-transformers` - Embeddings and reranking
- `transformers` - Model loading
- `camel-tools` - Arabic NLP
- `pyarabic` - Arabic text processing

**API**:
- `fastapi` - REST API framework
- `uvicorn` - ASGI server
- `pydantic` - Settings and validation

**Dev**:
- `pytest` - Testing framework
- `ruff` - Fast linting
- `black` - Code formatting
- `mypy` - Type checking
- `pre-commit` - Git hooks

## Code Style Requirements

- **Type hints required** on all functions
- **Docstrings required** on public functions/classes
- **Line length**: 100 characters (black/ruff configured)
- **Python version**: 3.11+ (3.12 supported)
- **Import order**: Use ruff's isort integration
- **Error handling**: Use specific exceptions, not generic `Exception`

## Important Notes

1. **Do NOT change model configurations** (BGE-M3, ARA-Reranker-V1) without proper benchmarking
2. **Conversation memory uses Qdrant** - not Redis or PostgreSQL (those are optional for other purposes)
3. **Query routing is critical** - saves 40% cost by skipping retrieval for simple queries
4. **Sentence-aware chunking** - do not replace with fixed-size chunking (5.37% accuracy loss)
5. **Test coverage target**: >80% (configured in pytest.ini)
6. **Package manager**: Project uses `uv` for fast dependency management

## Troubleshooting

**Qdrant connection issues**:
- Check `QDRANT_URL` in `.env`
- Ensure Qdrant is running: `docker-compose up -d qdrant`
- Verify health: `curl http://localhost:6333/healthz`

**Missing models**:
- Models auto-download on first use from HuggingFace
- Requires internet connection for initial setup
- Cached in `~/.cache/huggingface/`

**Memory issues with GPU**:
- Default configuration uses CPU (`embeddings_device: cpu`)
- For GPU: Set `EMBEDDINGS_DEVICE=cuda` in `.env`
- Requires PyTorch with CUDA support

**Tests failing**:
- Ensure virtual environment is activated
- Install dev dependencies: `uv pip install -e ".[dev]"`
- Check Qdrant is not running on default port during unit tests

**vLLM connection issues**:
- Check vLLM server is running: `curl http://localhost:8000/v1/models`
- Verify `VLLM_BASE_URL` in `.env` (should end with `/v1`)
- Start vLLM server:
  ```bash
  python -m vllm.entrypoints.openai.api_server \
    --model meta-llama/Llama-2-7b-chat-hf \
    --port 8000
  ```
- Ensure sufficient GPU memory (7B models need ~16GB VRAM)
- For CPU-only: Add `--device cpu` flag (slower but no GPU required)
- Check firewall settings if using remote vLLM server
- Connection health check happens on pipeline initialization
- To skip health check: Use `verify_connection=False` in VLLMLLMWrapper

**vLLM model loading issues**:
- Models download from HuggingFace Hub on first use
- Requires internet connection for initial download
- Cached in `~/.cache/huggingface/hub/`
- For gated models (Llama 2, Mistral): Set `HF_TOKEN` environment variable
- Check model compatibility with vLLM: [vLLM supported models](https://docs.vllm.ai/en/latest/models/supported_models.html)

**vLLM performance optimization**:
- Use `--dtype half` for FP16 (2x faster, half memory)
- Enable tensor parallelism: `--tensor-parallel-size 2` (multi-GPU)
- Adjust `--max-model-len` to reduce memory usage
- Use `--gpu-memory-utilization 0.9` to maximize GPU usage
- For production: Use `--disable-log-requests` to reduce overhead

## Active Technologies
- Python 3.11 + FastAPI, LangChain, python-docx, beautifulsoup4, markdown-it-py, Pillow, python-magic (001-multi-format-ingestion)
- Qdrant vector database (existing), file system for temporary uploads (001-multi-format-ingestion)

## Recent Changes
- 001-multi-format-ingestion: Added Python 3.11 + FastAPI, LangChain, python-docx, beautifulsoup4, markdown-it-py, Pillow, python-magic
