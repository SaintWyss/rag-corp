# HTTP API Documentation

**Project:** RAG Corp  
**Base URL:** `http://localhost:8000`  
**Version:** 1.0.0  
**Last Updated:** 2025-12-30

---

## Table of Contents

1. [Authentication](#authentication)
2. [Endpoints](#endpoints)
   - [Health Check](#health-check)
   - [Ingest Text](#ingest-text)
   - [Query Documents](#query-documents)
   - [Ask Question (RAG)](#ask-question-rag)
3. [Error Responses](#error-responses)
4. [Rate Limiting](#rate-limiting)

---

## Authentication

**Current:** No authentication required (development mode)  
**Planned:** API key authentication via `X-API-Key` header

```bash
# Future authentication
curl -H "X-API-Key: your-api-key" http://localhost:8000/ask
```

---

## Endpoints

### Health Check

Check if the API is running.

**Endpoint:** `GET /healthz`  
**Authentication:** None

#### Request

```bash
curl http://localhost:8000/healthz
```

#### Response

**Status:** `200 OK`

```json
{
  "status": "ok",
  "timestamp": "2025-12-30T10:30:00Z",
  "version": "1.0.0"
}
```

---

### Ingest Text

Upload a text document for indexing and embedding.

**Endpoint:** `POST /ingest/text`  
**Authentication:** None (planned)

#### Request

**Headers:**
```
Content-Type: application/json
```

**Body:**
```json
{
  "doc_id": "user-guide-2024",
  "text": "RAG Corp is a retrieval-augmented generation system for corporate documents. It enables semantic search and question answering using vector embeddings and large language models."
}
```

**Example:**
```bash
curl -X POST http://localhost:8000/ingest/text \
  -H "Content-Type: application/json" \
  -d '{
    "doc_id": "user-guide-2024",
    "text": "RAG Corp is a retrieval-augmented generation system..."
  }'
```

#### Response

**Status:** `201 Created`

```json
{
  "doc_id": "user-guide-2024",
  "chunks_created": 5,
  "message": "Document ingested successfully"
}
```

#### Error Responses

**400 Bad Request** - Invalid input
```json
{
  "detail": "Text field is required and cannot be empty"
}
```

**500 Internal Server Error** - Ingestion failed
```json
{
  "detail": "Failed to generate embeddings: API rate limit exceeded"
}
```

---

### Query Documents

Perform semantic search over ingested documents.

**Endpoint:** `POST /query`  
**Authentication:** None (planned)

#### Request

**Headers:**
```
Content-Type: application/json
```

**Body:**
```json
{
  "query": "What is RAG Corp?",
  "limit": 5
}
```

**Parameters:**
- `query` (string, required): Search query text
- `limit` (integer, optional): Number of results to return (default: 5, max: 20)

**Example:**
```bash
curl -X POST http://localhost:8000/query \
  -H "Content-Type: application/json" \
  -d '{
    "query": "What is RAG Corp?",
    "limit": 5
  }'
```

#### Response

**Status:** `200 OK`

```json
{
  "query": "What is RAG Corp?",
  "results": [
    {
      "doc_id": "user-guide-2024",
      "chunk_index": 0,
      "content": "RAG Corp is a retrieval-augmented generation system for corporate documents. It enables semantic search and question answering using vector embeddings and large language models.",
      "similarity": 0.8923
    },
    {
      "doc_id": "user-guide-2024",
      "chunk_index": 1,
      "content": "The system uses Google Gemini for embeddings (text-embedding-004) and text generation (gemini-1.5-flash).",
      "similarity": 0.7654
    }
  ],
  "total": 2
}
```

**Response Fields:**
- `query`: Original search query
- `results`: Array of matching chunks
  - `doc_id`: Document identifier
  - `chunk_index`: Chunk position in document (0-based)
  - `content`: Chunk text content
  - `similarity`: Cosine similarity score (0-1, higher = more similar)
- `total`: Number of results returned

#### Error Responses

**400 Bad Request**
```json
{
  "detail": "Query field is required"
}
```

**404 Not Found**
```json
{
  "detail": "No documents found matching query"
}
```

---

### Ask Question (RAG)

Get an AI-generated answer based on retrieved documents (Retrieval-Augmented Generation).

**Endpoint:** `POST /ask`  
**Authentication:** None (planned)  
**Implementation:** Uses Clean Architecture (`AnswerQueryUseCase`)

#### Request

**Headers:**
```
Content-Type: application/json
```

**Body:**
```json
{
  "query": "How does RAG Corp work?"
}
```

**Parameters:**
- `query` (string, required): Question to answer

**Example:**
```bash
curl -X POST http://localhost:8000/ask \
  -H "Content-Type: application/json" \
  -d '{
    "query": "How does RAG Corp work?"
  }'
```

#### Response

**Status:** `200 OK`

```json
{
  "query": "How does RAG Corp work?",
  "answer": "RAG Corp works by combining retrieval and generation. First, it converts your query into a vector embedding using Google's text-embedding-004 model. Then, it searches a PostgreSQL database with pgvector extension to find the most semantically similar document chunks. Finally, it uses Google's Gemini 1.5 Flash model to generate a natural language answer based on the retrieved context.",
  "sources": [
    {
      "doc_id": "architecture-guide",
      "chunk_index": 2,
      "content": "The system follows a three-step RAG process: embed query, retrieve similar chunks, generate answer using LLM.",
      "similarity": 0.9123
    },
    {
      "doc_id": "user-guide-2024",
      "chunk_index": 0,
      "content": "RAG Corp is a retrieval-augmented generation system...",
      "similarity": 0.8756
    }
  ],
  "confidence": "high"
}
```

**Response Fields:**
- `query`: Original question
- `answer`: AI-generated answer text
- `sources`: Document chunks used to generate answer
  - `doc_id`: Source document ID
  - `chunk_index`: Chunk position
  - `content`: Chunk text (may be truncated)
  - `similarity`: Relevance score (0-1)
- `confidence`: Answer confidence (`high` | `medium` | `low`)

**Confidence Levels:**
- `high`: Multiple relevant sources (similarity > 0.8)
- `medium`: Some relevant sources (similarity 0.6-0.8)
- `low`: Few or no relevant sources (similarity < 0.6)

#### Error Responses

**400 Bad Request**
```json
{
  "detail": "Query field is required and must be at least 3 characters"
}
```

**404 Not Found**
```json
{
  "detail": "No relevant documents found for your query"
}
```

**503 Service Unavailable** - LLM API failure
```json
{
  "detail": "LLM service temporarily unavailable. Please try again."
}
```

---

## Error Responses

All error responses follow this format:

```json
{
  "detail": "Error message describing what went wrong",
  "error_code": "SPECIFIC_ERROR_CODE",
  "timestamp": "2025-12-30T10:30:00Z"
}
```

### HTTP Status Codes

| Code | Meaning | When Used |
|------|---------|-----------|
| `200` | OK | Successful request |
| `201` | Created | Resource created (ingestion) |
| `400` | Bad Request | Invalid input parameters |
| `401` | Unauthorized | Missing/invalid API key (future) |
| `404` | Not Found | No results found |
| `429` | Too Many Requests | Rate limit exceeded |
| `500` | Internal Server Error | Server-side failure |
| `503` | Service Unavailable | External service down (Gemini API) |

### Error Codes

| Code | Description |
|------|-------------|
| `INVALID_INPUT` | Request body validation failed |
| `EMBEDDING_FAILED` | Failed to generate embeddings |
| `LLM_UNAVAILABLE` | Gemini API is down |
| `DATABASE_ERROR` | PostgreSQL connection/query failed |
| `RATE_LIMIT_EXCEEDED` | Too many requests |

---

## Rate Limiting

**Current:** No rate limiting (development)  
**Planned:** 100 requests/minute per API key

**Response when limit exceeded:**

**Status:** `429 Too Many Requests`

```json
{
  "detail": "Rate limit exceeded. Please try again in 30 seconds.",
  "error_code": "RATE_LIMIT_EXCEEDED",
  "retry_after": 30
}
```

**Headers:**
```
X-RateLimit-Limit: 100
X-RateLimit-Remaining: 0
X-RateLimit-Reset: 1704020400
Retry-After: 30
```

---

## Full Example Workflow

### 1. Check API Health

```bash
curl http://localhost:8000/healthz
# Response: {"status": "ok", ...}
```

### 2. Ingest Document

```bash
curl -X POST http://localhost:8000/ingest/text \
  -H "Content-Type: application/json" \
  -d '{
    "doc_id": "company-policy",
    "text": "Our company policy states that all employees must follow the code of conduct. Remote work is allowed 3 days per week. Vacation days must be requested 2 weeks in advance."
  }'
# Response: {"doc_id": "company-policy", "chunks_created": 3}
```

### 3. Search Documents

```bash
curl -X POST http://localhost:8000/query \
  -H "Content-Type: application/json" \
  -d '{
    "query": "remote work policy",
    "limit": 3
  }'
# Response: {"query": "remote work policy", "results": [...]}
```

### 4. Ask Question (RAG)

```bash
curl -X POST http://localhost:8000/ask \
  -H "Content-Type: application/json" \
  -d '{
    "query": "How many days can I work remotely?"
  }'
# Response: {"answer": "According to company policy, remote work is allowed 3 days per week.", ...}
```

---

## OpenAPI Specification

Generate OpenAPI JSON schema:

```bash
cd services/rag-api
python scripts/export_openapi.py
# Output: packages/contracts/openapi.json
```

View interactive docs:
- **Swagger UI:** http://localhost:8000/docs
- **ReDoc:** http://localhost:8000/redoc

---

## Client Libraries

### Python

```python
import requests

BASE_URL = "http://localhost:8000"

# Ingest document
response = requests.post(
    f"{BASE_URL}/ingest/text",
    json={"doc_id": "doc1", "text": "..."}
)
print(response.json())

# Ask question
response = requests.post(
    f"{BASE_URL}/ask",
    json={"query": "How does it work?"}
)
result = response.json()
print(result["answer"])
```

### TypeScript/JavaScript

```typescript
const BASE_URL = "http://localhost:8000";

// Ingest document
const ingestResponse = await fetch(`${BASE_URL}/ingest/text`, {
  method: "POST",
  headers: { "Content-Type": "application/json" },
  body: JSON.stringify({
    doc_id: "doc1",
    text: "..."
  })
});
const ingestData = await ingestResponse.json();

// Ask question
const askResponse = await fetch(`${BASE_URL}/ask`, {
  method: "POST",
  headers: { "Content-Type": "application/json" },
  body: JSON.stringify({ query: "How does it work?" })
});
const askData = await askResponse.json();
console.log(askData.answer);
```

### cURL

See examples throughout this document.

---

## References

- **OpenAPI Spec:** `packages/contracts/openapi.json`
- **FastAPI Docs:** http://localhost:8000/docs
- **Source Code:** `services/rag-api/app/routes.py`

---

**Last Updated:** 2025-12-30  
**Maintainer:** Engineering Team
