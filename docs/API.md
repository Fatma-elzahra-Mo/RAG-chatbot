# API Documentation

## Overview

The Arabic RAG Chatbot provides a RESTful API built with FastAPI. All endpoints are asynchronous and include comprehensive validation, error handling, and OpenAPI documentation.

**Base URL**: `http://localhost:8000`
**Interactive Docs**: `http://localhost:8000/docs`
**OpenAPI Schema**: `http://localhost:8000/openapi.json`

## Endpoints

### Health Check

#### `GET /health`

Check API health and service status.

**Response**:
```json
{
  "status": "healthy",
  "version": "1.0.0",
  "timestamp": "2025-01-09T12:00:00Z"
}
```

**Example**:
```bash
curl http://localhost:8000/health
```

---

### Chat Query

#### `POST /chat/query`

Submit a query to the Arabic RAG chatbot.

**Request Body**:
```json
{
  "query": "ما هي عاصمة مصر؟",
  "session_id": "user-123",
  "max_history": 5
}
```

**Parameters**:
- `query` (required, string): User's question in Arabic or English
- `session_id` (required, string): Unique session identifier for conversation memory
- `max_history` (optional, integer, default=5): Number of previous messages to include in context

**Response**:
```json
{
  "response": "عاصمة مصر هي القاهرة. هي أكبر مدينة في مصر والعالم العربي...",
  "session_id": "user-123",
  "sources": [
    {
      "content": "القاهرة هي عاصمة مصر...",
      "metadata": {
        "source": "egypt_facts.txt",
        "chunk_id": "12"
      },
      "score": 0.89
    }
  ],
  "query_type": "rag",
  "processing_time_ms": 1250
}
```

**Response Fields**:
- `response` (string): Generated answer from the chatbot
- `session_id` (string): Session identifier
- `sources` (array): Retrieved documents used for answer generation
  - `content` (string): Document text excerpt
  - `metadata` (object): Document metadata
  - `score` (float): Relevance score (0-1)
- `query_type` (string): Type of query routing used (`greeting`, `simple`, `rag`, `calculator`)
- `processing_time_ms` (integer): Processing time in milliseconds

**Example**:
```bash
curl -X POST http://localhost:8000/chat/query \
  -H "Content-Type: application/json" \
  -d '{
    "query": "ما هي عاصمة مصر؟",
    "session_id": "user-123"
  }'
```

**Query Types**:
1. **greeting**: Simple greetings (e.g., "مرحبا", "Hello")
2. **simple**: General questions not requiring document retrieval
3. **rag**: Document-based queries requiring retrieval
4. **calculator**: Mathematical expressions

---

### Document Ingestion

#### `POST /documents/ingest`

Ingest documents into the vector database.

**Request Body**:
```json
{
  "documents": [
    {
      "text": "القاهرة هي عاصمة مصر وأكبر مدنها...",
      "metadata": {
        "source": "egypt_facts.txt",
        "category": "geography"
      }
    }
  ],
  "chunk_size": 512,
  "chunk_overlap": 50
}
```

**Parameters**:
- `documents` (required, array): List of documents to ingest
  - `text` (required, string): Document text content
  - `metadata` (optional, object): Document metadata
- `chunk_size` (optional, integer, default=512): Characters per chunk
- `chunk_overlap` (optional, integer, default=50): Overlap between chunks

**Response**:
```json
{
  "status": "success",
  "documents_ingested": 1,
  "chunks_created": 5,
  "processing_time_ms": 3200
}
```

**Example**:
```bash
curl -X POST http://localhost:8000/documents/ingest \
  -H "Content-Type: application/json" \
  -d '{
    "documents": [
      {
        "text": "القاهرة هي عاصمة مصر وأكبر مدنها",
        "metadata": {"source": "test.txt"}
      }
    ]
  }'
```

---

### Conversation History

#### `GET /chat/history/{session_id}`

Retrieve conversation history for a session.

**Path Parameters**:
- `session_id` (required, string): Session identifier

**Query Parameters**:
- `limit` (optional, integer, default=10): Maximum number of messages to retrieve

**Response**:
```json
{
  "session_id": "user-123",
  "messages": [
    {
      "role": "user",
      "content": "ما هي عاصمة مصر؟",
      "timestamp": "2025-01-09T12:00:00Z"
    },
    {
      "role": "assistant",
      "content": "عاصمة مصر هي القاهرة...",
      "timestamp": "2025-01-09T12:00:01Z"
    }
  ],
  "total_messages": 2
}
```

**Example**:
```bash
curl http://localhost:8000/chat/history/user-123?limit=10
```

---

#### `DELETE /chat/history/{session_id}`

Clear conversation history for a session.

**Path Parameters**:
- `session_id` (required, string): Session identifier

**Response**:
```json
{
  "status": "success",
  "session_id": "user-123",
  "messages_deleted": 8
}
```

**Example**:
```bash
curl -X DELETE http://localhost:8000/chat/history/user-123
```

---

### Vector Store Management

#### `GET /documents/search`

Search documents in the vector store.

**Query Parameters**:
- `query` (required, string): Search query
- `limit` (optional, integer, default=10): Number of results to return
- `score_threshold` (optional, float, default=0.7): Minimum relevance score

**Response**:
```json
{
  "query": "عاصمة مصر",
  "results": [
    {
      "content": "القاهرة هي عاصمة مصر...",
      "metadata": {
        "source": "egypt_facts.txt"
      },
      "score": 0.89
    }
  ],
  "total_results": 1
}
```

**Example**:
```bash
curl "http://localhost:8000/documents/search?query=عاصمة%20مصر&limit=5"
```

---

#### `DELETE /documents/clear`

Clear all documents from the vector store.

**Response**:
```json
{
  "status": "success",
  "documents_deleted": 150
}
```

**Example**:
```bash
curl -X DELETE http://localhost:8000/documents/clear
```

---

## Error Responses

All endpoints return standardized error responses:

```json
{
  "error": {
    "code": "VALIDATION_ERROR",
    "message": "Query must not be empty",
    "details": {
      "field": "query",
      "value": ""
    }
  }
}
```

**HTTP Status Codes**:
- `200`: Success
- `400`: Bad Request (validation error)
- `404`: Not Found
- `500`: Internal Server Error
- `503`: Service Unavailable

**Error Codes**:
- `VALIDATION_ERROR`: Invalid request parameters
- `RESOURCE_NOT_FOUND`: Requested resource not found
- `INTERNAL_ERROR`: Server processing error
- `SERVICE_UNAVAILABLE`: External service unavailable

---

## Rate Limiting

Currently, no rate limiting is implemented. For production deployments, consider adding rate limiting using middleware.

---

## Authentication

Currently, no authentication is required. For production deployments, consider adding:
- API key authentication
- OAuth2/JWT tokens
- Session-based authentication

---

## WebSocket Support

WebSocket support for streaming responses is planned for future releases.

---

## Examples

### Python Client

```python
import requests

# Chat query
response = requests.post(
    "http://localhost:8000/chat/query",
    json={
        "query": "ما هي عاصمة مصر؟",
        "session_id": "user-123"
    }
)
result = response.json()
print(result["response"])

# Document ingestion
response = requests.post(
    "http://localhost:8000/documents/ingest",
    json={
        "documents": [
            {
                "text": "القاهرة هي عاصمة مصر",
                "metadata": {"source": "test.txt"}
            }
        ]
    }
)
print(response.json())
```

### JavaScript Client

```javascript
// Chat query
const response = await fetch('http://localhost:8000/chat/query', {
  method: 'POST',
  headers: {
    'Content-Type': 'application/json'
  },
  body: JSON.stringify({
    query: 'ما هي عاصمة مصر؟',
    session_id: 'user-123'
  })
});

const result = await response.json();
console.log(result.response);
```

### cURL Examples

```bash
# Multi-turn conversation
curl -X POST http://localhost:8000/chat/query \
  -H "Content-Type: application/json" \
  -d '{"query": "ما هي عاصمة مصر؟", "session_id": "demo-1"}'

curl -X POST http://localhost:8000/chat/query \
  -H "Content-Type: application/json" \
  -d '{"query": "وما هو عدد سكانها؟", "session_id": "demo-1"}'

# View history
curl http://localhost:8000/chat/history/demo-1
```

---

## OpenAPI Schema

Access the full OpenAPI schema at `http://localhost:8000/openapi.json` for automatic client generation.

**Supported Tools**:
- Swagger Codegen
- OpenAPI Generator
- Postman
- Insomnia

---

## Performance Considerations

- **Query Processing**: Typically 500-2000ms depending on complexity
- **Document Ingestion**: ~100ms per document
- **Concurrent Requests**: Supports 100+ concurrent connections
- **Memory Usage**: ~2GB for typical workloads

---

## Monitoring

Recommended monitoring metrics:
- Request latency (p50, p95, p99)
- Error rate
- Document count
- Memory usage
- Qdrant query performance

---

For more information, see the [Architecture Documentation](ARCHITECTURE.md).
