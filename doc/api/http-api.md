# HTTP API Documentation

**Project:** RAG Corp  
**Base URL:** `http://localhost:8000`  
**API Prefix:** `/v1`  
**Version:** 0.1.0  
**Last Updated:** 2026-01-02

---

## Table of Contents

1. [Authentication](#authentication)
2. [Endpoints](#endpoints)
   - [Health Check](#health-check)
   - [Ingest Text](#ingest-text)
   - [Query Documents](#query-documents)
   - [Ask Question (RAG)](#ask-question-rag)
3. [Error Responses](#error-responses)
4. [OpenAPI Specification](#openapi-specification)

---

## Authentication

**Current:** API key authentication via `X-API-Key` header  
**Default:** Disabled when `API_KEYS_CONFIG` is empty

### Configuration

Set API keys and their scopes via environment variable:

```bash
# Format: JSON object {"key": ["scope1", "scope2"], ...}
API_KEYS_CONFIG='{"prod-ingest-key":["ingest"],"prod-query-key":["ask"],"admin-key":["ingest","ask","metrics"]}'
```

### Scopes

| Scope | Endpoints | Description |
|-------|-----------|-------------|
| `ingest` | `POST /v1/ingest/*` | Document ingestion |
| `ask` | `POST /v1/query`, `POST /v1/ask` | Search and RAG queries |
| `metrics` | `GET /metrics` | Prometheus metrics (optional) |
| `*` | All | Wildcard scope (admin) |

### Public Endpoints (No Auth Required)

- `GET /healthz` - Health check
- `GET /docs` - Swagger UI
- `GET /redoc` - ReDoc documentation
- `GET /openapi.json` - OpenAPI schema

### Request Examples

```bash
# With API key
curl -H "X-API-Key: your-api-key" \
     -H "Content-Type: application/json" \
     -d '{"query": "What is RAG?"}' \
     http://localhost:8000/v1/ask

# Without auth (when API_KEYS_CONFIG is empty)
curl -H "Content-Type: application/json" \
     -d '{"query": "What is RAG?"}' \
     http://localhost:8000/v1/ask
```

### Error Responses

| Status | Condition | Response |
|--------|-----------|----------|
| `401` | Missing `X-API-Key` header | `{"detail": "Missing API key. Provide X-API-Key header."}` |
| `403` | Invalid API key | `{"detail": "Invalid API key."}` |
| `403` | Key lacks required scope | `{"detail": "API key does not have required scope: ingest"}` |

---

## Rate Limiting

Token bucket rate limiting per API key (or IP if unauthenticated).

### Configuration

```bash
RATE_LIMIT_RPS=10    # Tokens per second (refill rate)
RATE_LIMIT_BURST=20  # Maximum burst (bucket size)
```

### Response Headers

| Header | Description |
|--------|-------------|
| `X-RateLimit-Limit` | Maximum tokens (burst) |
| `X-RateLimit-Remaining` | Tokens remaining |
| `Retry-After` | Seconds until next token (when rate limited) |

### Rate Limit Exceeded

**Status:** `429 Too Many Requests`

```json
{
  "detail": "Rate limit exceeded. Try again later."
}
```

---

## Body Size Limit

Maximum request body size is enforced via `MAX_BODY_BYTES` (default: 10MB).

**Status:** `413 Payload Too Large`

```json
{
  "detail": "Request body too large. Maximum size: 10485760 bytes"
}
```

---

## Endpoints

### Health Check

Check if the API is running and if the DB responds.

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
  "ok": true,
  "db": "connected"
}
```

---

### Ingest Text

Upload a text document for indexing and embedding.

**Endpoint:** `POST /v1/ingest/text`  
**Authentication:** Required (scope: `ingest`)  
**Tag:** `ingest`

#### Request

**Headers:**
```
Content-Type: application/json
X-API-Key: your-api-key
```

**Body:**
```json
{
  "title": "User Guide 2024",
  "text": "RAG Corp is a retrieval-augmented generation system...",
  "source": "https://example.com/docs/user-guide",
  "metadata": { "team": "docs" }
}
```

**Constraints:**

| Field | Type | Required | Limits | Default |
|-------|------|----------|--------|--------|
| `title` | string | ✅ | 1-200 chars (trimmed) | - |
| `text` | string | ✅ | 1-100,000 chars (trimmed) | - |
| `source` | string | ❌ | max 500 chars | `null` |
| `metadata` | object | ❌ | - | `{}` |

> Limits configurable via `MAX_TITLE_CHARS`, `MAX_INGEST_CHARS`, `MAX_SOURCE_CHARS` env vars.

#### Response

**Status:** `200 OK`

```json
{
  "document_id": "3c0b6f96-2f4b-4d67-9aa3-5e5f7a6e9a1d",
  "chunks": 5
}
```

---

### Query Documents

Perform semantic search over ingested documents.

**Endpoint:** `POST /v1/query`  
**Authentication:** Required (scope: `ask`)  
**Tag:** `query`

#### Request

**Headers:**
```
Content-Type: application/json
X-API-Key: your-api-key
```

**Body:**
```json
{
  "query": "What is RAG Corp?",
  "top_k": 5
}
```

**Constraints:**

| Field | Type | Required | Limits | Default |
|-------|------|----------|--------|--------|
| `query` | string | ✅ | 1-2,000 chars (trimmed) | - |
| `top_k` | integer | ❌ | 1-20 | `5` |

> Limits configurable via `MAX_QUERY_CHARS`, `MAX_TOP_K` env vars.

#### Response

**Status:** `200 OK`

```json
{
  "matches": [
    {
      "chunk_id": "6e7c4f4b-2a84-4e67-9f0f-0b11cc6cc8a1",
      "document_id": "3c0b6f96-2f4b-4d67-9aa3-5e5f7a6e9a1d",
      "content": "RAG Corp is a retrieval-augmented generation system...",
      "score": 0.8923
    }
  ]
}
```

---

### Ask Question (RAG)

Get an AI-generated answer based on retrieved documents.

**Endpoint:** `POST /v1/ask`  
**Authentication:** Required (scope: `ask`)  
**Tag:** `query`  
**Implementation:** Uses Clean Architecture (`AnswerQueryUseCase`)

#### Request

**Headers:**
```
Content-Type: application/json
X-API-Key: your-api-key
```

**Body:**
```json
{
  "query": "How does RAG Corp work?",
  "top_k": 5
}
```

**Constraints:** Same as `/v1/query` (see above).

| Field | Type | Required | Limits | Default |
|-------|------|----------|--------|--------|
| `query` | string | ✅ | 1-2,000 chars (trimmed) | - |
| `top_k` | integer | ❌ | 1-20 | `5` |

#### Response

**Status:** `200 OK`

```json
{
  "answer": "RAG Corp combina retrieval y generación para responder preguntas...",
  "sources": [
    "RAG Corp is a retrieval-augmented generation system...",
    "The system uses Google Gemini for embeddings..."
  ]
}
```

---

## Error Responses

### Validation Errors (FastAPI)

**Status:** `422 Unprocessable Entity`

```json
{
  "detail": [
    {
      "loc": ["body", "query"],
      "msg": "Field required",
      "type": "missing"
    }
  ]
}
```

### Domain Errors (Custom Exceptions)

Custom exceptions return a structured payload:

```json
{
  "error_code": "DATABASE_ERROR",
  "message": "Failed to save document: ...",
  "error_id": "6b9a94a1-0a3b-4c75-8c71-1b1c4ef5e4df"
}
```

**Error Codes:**
- `DATABASE_ERROR`
- `EMBEDDING_ERROR`
- `LLM_ERROR`
- `RAG_ERROR`

**HTTP Status Codes:**
- `500` for generic `RAG_ERROR`
- `503` for database/embedding/LLM failures

---

## OpenAPI Specification

Generate OpenAPI JSON schema (source of truth):

```bash
# Desde root con Docker (oficial)
pnpm contracts:export
pnpm contracts:gen

# Desde backend (local)
cd backend
python3 scripts/export_openapi.py --out ../shared/contracts/openapi.json
```

View interactive docs:
- **Swagger UI:** http://localhost:8000/docs
- **ReDoc:** http://localhost:8000/redoc

---

## References

- **OpenAPI Spec:** `shared/contracts/openapi.json`
- **FastAPI Docs:** http://localhost:8000/docs
- **Source Code:** `backend/app/routes.py`

---

**Last Updated:** 2026-01-02  
**Maintainer:** Engineering Team
