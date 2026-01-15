# QA Testing Guide - Arabic RAG Chatbot

This guide provides comprehensive QA testing procedures for the Arabic RAG chatbot, focusing on end-to-end browser testing and manual validation.

## 🎯 Test Objectives

Validate three major features:
1. **JSON Ingestion** - Verify data can be loaded into Qdrant successfully
2. **vLLM Integration** - Test local model inference functionality
3. **PDF Chunking** - Validate improved document processing

## 📋 Prerequisites

### Required Services
```bash
# 1. Start Qdrant (vector database)
docker run -d -p 6333:6333 qdrant/qdrant:latest

# OR use docker-compose
docker-compose up -d qdrant

# Verify Qdrant is running
curl http://localhost:6333/healthz
# Expected: {"title":"qdrant - vector search engine","version":"1.x.x"}
```

### Environment Setup
```bash
# Required environment variables
export LLM_PROVIDER=gemini  # or openai, openrouter, local
export GEMINI_API_KEY=your_key_here
export OPENAI_API_KEY=your_key_here  # if using OpenAI
export GOOGLE_API_KEY=your_key_here  # for image analysis

# For vLLM testing
export LLM_PROVIDER=local
export VLLM_BASE_URL=http://localhost:8000/v1
```

### Start Application
```bash
# Option 1: Start Streamlit UI (recommended for QA testing)
streamlit run streamlit_app/app.py

# Option 2: Start FastAPI backend
uvicorn src.api.main:app --reload --port 8000
```

## 🧪 Test Suite 1: JSON Ingestion

### Objective
Verify the JSON ingestion script correctly loads documents into Qdrant.

### Test Data
Located in `data/`:
- `sample_firecrawl.json` - Firecrawl format (WE Egypt telecom data)
- `sample_generic.json` - Generic format
- `results/firecrawl_fixed_20260112_022656.json` - Real scraped data

### Test Cases

#### TC1.1: Dry-Run Preview
**Steps:**
```bash
python scripts/ingest_json.py \
  --file data/sample_firecrawl.json \
  --dry-run
```

**Expected Results:**
- ✅ Format auto-detected as "firecrawl"
- ✅ Shows document count (3 documents)
- ✅ Preview displays document titles and character counts
- ✅ No actual ingestion occurs
- ✅ No Qdrant connection required

**Success Criteria:**
- Script completes without errors
- Output clearly shows "[DRY RUN]" indicator
- Document previews match expected content

#### TC1.2: Basic Ingestion (Firecrawl Format)
**Steps:**
```bash
# Clear collection first
python scripts/ingest_json.py \
  --file data/sample_firecrawl.json \
  --clear

# Verify in Qdrant
curl http://localhost:6333/collections/arabic_documents
```

**Expected Results:**
- ✅ Format auto-detected correctly
- ✅ Progress bar shows completion
- ✅ Final statistics report:
  - Documents: 3
  - Chunks created: ~10-15 (depends on content)
  - Time: <5 seconds
- ✅ Qdrant collection contains vectors

**Success Criteria:**
- No errors during ingestion
- Vector count in Qdrant matches expected chunks
- Documents are searchable

#### TC1.3: Large Dataset Ingestion
**Steps:**
```bash
python scripts/ingest_json.py \
  --file results/firecrawl_fixed_20260112_022656.json \
  --batch-size 5 \
  --clear
```

**Expected Results:**
- ✅ Auto-detects firecrawl format
- ✅ Processes all 20 pages
- ✅ Progress bar updates smoothly
- ✅ Statistics show reasonable chunks (~150-200)
- ✅ Processing rate: ~1-2 docs/sec

**Success Criteria:**
- All documents ingested successfully
- No memory issues
- Chunk count is reasonable (7-10 chunks per doc average)

#### TC1.4: Generic Format
**Steps:**
```bash
python scripts/ingest_json.py \
  --file data/sample_generic.json \
  --format generic
```

**Expected Results:**
- ✅ Recognizes generic format
- ✅ Extracts text and metadata correctly
- ✅ No errors or warnings

**Success Criteria:**
- Metadata preserved (source, custom fields)
- Text content matches original

#### TC1.5: Error Handling
**Steps:**
```bash
# Invalid file
python scripts/ingest_json.py --file nonexistent.json

# Invalid JSON
echo "invalid json" > /tmp/bad.json
python scripts/ingest_json.py --file /tmp/bad.json

# Unsupported format
echo '{"wrong": "format"}' > /tmp/wrong.json
python scripts/ingest_json.py --file /tmp/wrong.json
```

**Expected Results:**
- ✅ Clear error messages for each case
- ✅ No crashes or stack traces
- ✅ Helpful suggestions in error messages

---

## 🧪 Test Suite 2: vLLM Integration

### Objective
Verify local vLLM models work as an LLM provider.

### Prerequisites
```bash
# Install vLLM (requires CUDA or CPU mode)
pip install vllm

# Start vLLM server
python -m vllm.entrypoints.openai.api_server \
  --model meta-llama/Llama-2-7b-chat-hf \
  --port 8000 \
  --host 0.0.0.0

# Verify server is running
curl http://localhost:8000/v1/models
```

### Test Cases

#### TC2.1: Health Check
**Steps:**
```python
from src.models.vllm_model import VLLMLLMWrapper

llm = VLLMLLMWrapper(
    base_url="http://localhost:8000/v1",
    model_name="meta-llama/Llama-2-7b-chat-hf",
    verify_connection=True
)
print("✅ vLLM connection successful")
```

**Expected Results:**
- ✅ No VLLMConnectionError raised
- ✅ Health check passes
- ✅ Success message printed

**Success Criteria:**
- Connection established without errors
- Server responds to health checks

#### TC2.2: Simple Query (CLI)
**Steps:**
```python
from langchain_core.messages import HumanMessage
from src.models.vllm_model import VLLMLLMWrapper

llm = VLLMLLMWrapper()
response = llm.invoke([HumanMessage(content="What is 2+2?")])
print(response.content)
```

**Expected Results:**
- ✅ Response generated successfully
- ✅ Answer is coherent (e.g., "4" or "The answer is 4")
- ✅ Response time: <5 seconds (7B model)

**Success Criteria:**
- No errors during inference
- Response is relevant to question
- Latency is acceptable

#### TC2.3: Arabic Query
**Steps:**
```python
llm = VLLMLLMWrapper()
response = llm.invoke([HumanMessage(content="ما هي عاصمة مصر؟")])
print(response.content)
```

**Expected Results:**
- ✅ Response in Arabic (if model supports)
- ✅ Correct answer: القاهرة (Cairo)
- ✅ No encoding issues

**Success Criteria:**
- Arabic text handled correctly
- Response is coherent
- No character corruption

#### TC2.4: Integration with Pipeline
**Steps:**
```bash
# Set environment to use vLLM
export LLM_PROVIDER=local
export VLLM_BASE_URL=http://localhost:8000/v1

# Start Streamlit app
streamlit run streamlit_app/app.py
```

**Browser Testing:**
1. Open app at http://localhost:8501
2. Type question: "Hello, how are you?"
3. Verify response is generated by vLLM
4. Check response quality and latency

**Expected Results:**
- ✅ App loads without errors
- ✅ Queries routed to vLLM correctly
- ✅ Responses displayed in UI
- ✅ Acceptable latency (<10s for 7B model)

**Success Criteria:**
- No backend errors in logs
- UI remains responsive
- Conversation memory works

#### TC2.5: Provider Switching
**Steps:**
```bash
# Test switching between providers
export LLM_PROVIDER=gemini
streamlit run streamlit_app/app.py  # Restart required

# Ask question, verify Gemini response

# Switch to vLLM
export LLM_PROVIDER=local
streamlit run streamlit_app/app.py  # Restart

# Ask same question, verify vLLM response
```

**Expected Results:**
- ✅ Both providers work without code changes
- ✅ No configuration errors
- ✅ Responses differ based on model

**Success Criteria:**
- Clean switch between providers
- No API key issues
- Application state maintained

---

## 🧪 Test Suite 3: PDF Chunking

### Objective
Verify improved PDF chunking handles documents better than generic chunking.

### Test Data
Create test PDFs with various artifacts:
- Page numbers (header/footer)
- Repeated headers
- Tables
- Multi-column layouts
- Arabic text with formatting issues

### Test Cases

#### TC3.1: PDF Cleaning
**Steps:**
```python
from src.preprocessing.pdf_cleaner import PDFCleaner

cleaner = PDFCleaner()

# Test with PDF artifacts
text_with_artifacts = """
الصفحة 1
============================
باقات WE للإنترنت المنزلي
============================

نقدم لكم أفضل الباقات...

============================
الصفحة 1
============================
"""

cleaned, metadata = cleaner.clean(text_with_artifacts)
print("Cleaned:", cleaned)
print("Metadata:", metadata)
```

**Expected Results:**
- ✅ Page numbers removed
- ✅ Repeated headers detected and removed
- ✅ Clean content without artifacts
- ✅ Metadata contains structure info

**Success Criteria:**
- No manual artifacts remain
- Content is readable
- Important text preserved

#### TC3.2: PDF Chunking vs Generic
**Steps:**
```python
from src.preprocessing.pdf_chunker import ArabicPDFChunker
from src.preprocessing.chunker import ArabicSentenceChunker
from langchain_core.documents import Document

pdf_text = """PDF content with tables and sections..."""
doc = Document(page_content=pdf_text, metadata={"source": "test.pdf", "document_type": "pdf"})

# Generic chunking
generic_chunker = ArabicSentenceChunker(max_chunk_size=350, overlap=100)
generic_chunks = generic_chunker.chunk_documents([doc])

# PDF-aware chunking
pdf_chunker = ArabicPDFChunker(max_chunk_size=350, overlap=100)
pdf_chunks = pdf_chunker.chunk_documents([doc])

print(f"Generic chunks: {len(generic_chunks)}")
print(f"PDF chunks: {len(pdf_chunks)}")

# Compare chunk quality
for i, (g, p) in enumerate(zip(generic_chunks[:3], pdf_chunks[:3])):
    print(f"\nChunk {i+1}:")
    print(f"Generic ({len(g.page_content)} chars): {g.page_content[:100]}...")
    print(f"PDF ({len(p.page_content)} chars): {p.page_content[:100]}...")
    print(f"PDF metadata: {p.metadata}")
```

**Expected Results:**
- ✅ PDF chunks have better boundaries (respect sections)
- ✅ Tables kept intact in PDF chunks
- ✅ PDF metadata richer (content_type, section_header)
- ✅ Both produce similar chunk counts

**Success Criteria:**
- PDF chunks respect semantic boundaries
- No tables split mid-content
- Metadata useful for retrieval

#### TC3.3: Pipeline Integration
**Steps:**
```python
from src.core.pipeline import RAGPipeline

pipeline = RAGPipeline()

# Ingest with document_type hint
pdf_content = """Your PDF text here..."""
pipeline.ingest_documents(
    texts=[pdf_content],
    metadatas=[{"source": "test.pdf", "document_type": "pdf"}]
)

# Query
result = pipeline.query("ما هو محتوى المستند؟")
print(result["response"])
```

**Expected Results:**
- ✅ PDF-aware chunking used automatically
- ✅ Chunks stored with enhanced metadata
- ✅ Retrieval quality improved

**Success Criteria:**
- No errors during ingestion
- Metadata preserved in vector store
- Query results relevant

#### TC3.4: Streamlit Document Upload
**Steps:**
1. Start Streamlit: `streamlit run streamlit_app/app.py`
2. Navigate to sidebar → "Add Documents"
3. Upload a test JSON file (PDF upload not yet supported in UI)
4. Click "Add to Knowledge"
5. Ask a question about the uploaded document

**Expected Results:**
- ✅ File uploads successfully
- ✅ Success message displayed
- ✅ Document is queryable immediately
- ✅ Responses reference uploaded content

**Success Criteria:**
- No errors in upload flow
- Document indexed correctly
- Retrieval works

---

## 🌐 Browser Testing with Chrome

### Setup Chrome Testing
```bash
# Ensure application is running
streamlit run streamlit_app/app.py

# Application should be at http://localhost:8501
```

### TC4.1: UI Smoke Test
**Manual Steps:**
1. Open Chrome → http://localhost:8501
2. Verify page loads completely
3. Check all UI elements visible:
   - Title "WE Assistant"
   - Frequent questions grid
   - Chat input field
   - Sidebar with upload sections

**Expected Results:**
- ✅ Page loads without errors
- ✅ Arabic text displays correctly (RTL)
- ✅ Frequent questions visible
- ✅ No console errors in DevTools

### TC4.2: Chat Functionality
**Manual Steps:**
1. Click a frequent question (e.g., "ما هو سعر باقة X الشهرية؟")
2. Wait for response
3. Type follow-up question in chat input
4. Verify response

**Expected Results:**
- ✅ Question appears in chat
- ✅ Loading spinner shows
- ✅ Response generated within <5 seconds
- ✅ Arabic text displays RTL
- ✅ Conversation context maintained

### TC4.3: Document Upload
**Manual Steps:**
1. Click sidebar "Add Documents"
2. Upload `data/sample_firecrawl.json`
3. Click "Add to Knowledge"
4. Wait for success message
5. Ask: "ما هي باقات WE؟"

**Expected Results:**
- ✅ Upload completes successfully
- ✅ Success message: "Added: sample_firecrawl.json"
- ✅ Response references uploaded data
- ✅ No errors in console

### TC4.4: Session Management
**Manual Steps:**
1. Have a conversation (3-4 exchanges)
2. Verify messages display correctly
3. Click "Clear Chat"
4. Verify chat cleared
5. Send new message
6. Verify new session started

**Expected Results:**
- ✅ All messages display in order
- ✅ Clear button resets chat
- ✅ New session ID generated
- ✅ Previous context forgotten

---

## 📊 QA Test Report Template

### Test Execution Summary

**Date:** YYYY-MM-DD
**Tester:** [Name]
**Environment:**
- OS: macOS/Linux/Windows
- Python: 3.11
- LLM Provider: [gemini/openai/local]
- Qdrant: [version]

### Results

| Test Suite | Test Case | Status | Notes |
|------------|-----------|--------|-------|
| JSON Ingestion | TC1.1 Dry-Run | ✅/❌ | |
| JSON Ingestion | TC1.2 Basic | ✅/❌ | |
| JSON Ingestion | TC1.3 Large Dataset | ✅/❌ | |
| vLLM Integration | TC2.1 Health Check | ✅/❌ | |
| vLLM Integration | TC2.2 Simple Query | ✅/❌ | |
| vLLM Integration | TC2.4 Pipeline | ✅/❌ | |
| PDF Chunking | TC3.1 Cleaning | ✅/❌ | |
| PDF Chunking | TC3.2 Comparison | ✅/❌ | |
| Browser Testing | TC4.1 Smoke Test | ✅/❌ | |
| Browser Testing | TC4.2 Chat | ✅/❌ | |

### Issues Found
1. [Issue description]
   - **Severity:** Critical/High/Medium/Low
   - **Steps to reproduce:**
   - **Expected vs Actual:**

### Performance Metrics
- Average query latency: X ms
- Document ingestion rate: X docs/sec
- Vector search latency: X ms
- UI responsiveness: [Good/Fair/Poor]

### Recommendations
- [Improvement suggestions]
- [Performance optimization ideas]
- [Feature requests]

---

## 🚀 Quick Start QA Checklist

```bash
# 1. Start services
docker-compose up -d qdrant
streamlit run streamlit_app/app.py

# 2. Run quick smoke tests
python scripts/ingest_json.py --file data/sample_firecrawl.json --dry-run
curl http://localhost:6333/healthz
curl http://localhost:8501  # Should return HTML

# 3. Open browser
open http://localhost:8501

# 4. Test basic flow
# - Click a frequent question
# - Upload a document
# - Ask a follow-up
# - Clear chat

# 5. Check logs
# - Streamlit console output
# - Browser DevTools console
# - Qdrant logs: docker logs [qdrant-container-id]
```

---

## 📝 Notes for QA Engineers

### Common Issues
1. **Qdrant not starting:** Check Docker daemon, port 6333 available
2. **vLLM connection failed:** Ensure server running on port 8000
3. **Arabic text broken:** Check browser encoding (UTF-8)
4. **Slow responses:** Check LLM provider latency, Qdrant performance

### Debug Commands
```bash
# Check Qdrant collection
curl http://localhost:6333/collections/arabic_documents

# Check vector count
curl http://localhost:6333/collections/arabic_documents/points/count

# Test embeddings
python -c "from src.models.embeddings import create_embeddings; e=create_embeddings('gemini'); print(e.embed_query('test')[:5])"

# Test normalizer
python -c "from src.preprocessing.normalizer import ArabicNormalizer; n=ArabicNormalizer(); print(n.normalize('مرحباً بك'))"
```

### Performance Benchmarks
- **Embedding:** ~50-100ms per query (Gemini API)
- **Vector search:** <10ms (Qdrant local)
- **Reranking:** ~100-200ms (ARA-Reranker-V1)
- **LLM generation:** 1-5s (Gemini), 3-10s (vLLM 7B)
- **Total query latency:** 2-8s end-to-end

---

## ✅ Sign-off Checklist

Before approving release:
- [ ] All critical test cases pass
- [ ] No regression from previous version
- [ ] Performance meets SLAs
- [ ] Arabic text displays correctly
- [ ] Error handling is user-friendly
- [ ] Documentation is up-to-date
- [ ] Security review completed
- [ ] Load testing passed (if applicable)
