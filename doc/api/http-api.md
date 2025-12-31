# HTTP API Documentation

**Project:** RAG Corp  
**Base URL:** `http://localhost:8000`  
**API Prefix:** `/v1`  
**Version:** 0.1.0  
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
4. [OpenAPI Specification](#openapi-specification)

---

## Authentication

**Current:** No authentication required (development mode)  
**Planned:** API key authentication via `X-API-Key` header

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
**Authentication:** None

#### Request

**Headers:**
```
Content-Type: application/json
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
**Authentication:** None

#### Request

**Headers:**
```
Content-Type: application/json
```

**Body:**
```json
{
  "query": "What is RAG Corp?",
  "top_k": 5
}
```

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
**Authentication:** None  
**Implementation:** Uses Clean Architecture (`AnswerQueryUseCase`)

#### Request

**Headers:**
```
Content-Type: application/json
```

**Body:**
```json
{
  "query": "How does RAG Corp work?",
  "top_k": 5
}
```

**Note:** The endpoint currently uses a fixed `top_k=3` internally.

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

Generate OpenAPI JSON schema:

```bash
# Opcion 1: desde root con Docker
pnpm contracts:export

# Opcion 2: desde backend (ruta absoluta)
cd services/rag-api
python scripts/export_openapi.py --out /repo/packages/contracts/openapi.json
```

View interactive docs:
- **Swagger UI:** http://localhost:8000/docs
- **ReDoc:** http://localhost:8000/redoc

---

## References

- **OpenAPI Spec:** `packages/contracts/openapi.json`
- **FastAPI Docs:** http://localhost:8000/docs
- **Source Code:** `services/rag-api/app/routes.py`

---

**Last Updated:** 2025-12-30  
**Maintainer:** Engineering Team
