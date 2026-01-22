# Architecture Overview (v6)

**Project:** RAG Corp
**Last Updated:** 2026-01-22
**Status:** Active

---

## System Purpose

RAG Corp es un sistema de Retrieval-Augmented Generation (RAG) con scoping estricto por **Workspace**.
Todas las operaciones de documentos y consultas se realizan dentro de un `workspace_id`.

---

## High-Level Architecture

```mermaid
graph TB
    User[User] --> Web[Next.js Web App]
    Web --> API[FastAPI Backend]
    API --> PG[(PostgreSQL + pgvector)]
    API --> Cache[Embedding Cache (memory/Redis)]
    API --> S3[(S3/MinIO)]
    API --> Redis[(Redis Queue)]
    Redis --> Worker[RQ Worker]
    Worker --> S3
    Worker --> Gemini[Google GenAI]
    API --> Gemini
```

---

## Core Components

| Component | Technology | Purpose |
|-----------|------------|---------|
| Frontend | Next.js 16.1.1 | UI para workspaces, documentos y chat |
| Backend | FastAPI (Python 3.11) | API HTTP y orquestacion |
| Vector DB | PostgreSQL 16 + pgvector 0.8.1 | chunks + embeddings |
| Worker | RQ + Redis | Procesamiento async de uploads |
| Storage | S3/MinIO | Archivos binarios |
| Observability | Prometheus/Grafana | metricas y dashboards (opcional) |

---

## Architecture Layers (Clean Architecture)

### Domain (`backend/app/domain`)

- Entidades: `Workspace`, `Document`, `Chunk`, `User`
- Policy: `WorkspacePolicy` (autorizacion)
- Protocols (ports): repositorios y servicios (`DocumentRepository`, `WorkspaceRepository`, `EmbeddingService`, `LLMService`)

### Application (`backend/app/application`)

- Use cases para workspaces, documentos y query/ask
- DTOs input/output explicitos
- Orquestacion de politicas + adapters

### Infrastructure (`backend/app/infrastructure`)

- PostgreSQL repositories
- Google GenAI adapters
- S3/MinIO storage
- Redis queue + embedding cache

### API (`backend/app/routes.py`, `backend/app/main.py`)

- FastAPI routers versionados
- Auth dual (JWT + X-API-Key)
- SSE para streaming de `/ask/stream`

---

## Workspace scoping (v6)

Regla principal: **toda operacion de documentos y RAG requiere `workspace_id`**.
Los endpoints canonicos son nested bajo `/v1/workspaces/{workspace_id}/...`.
Los endpoints legacy existen solo por compatibilidad y se documentan como **DEPRECATED**.

---

## Flujos principales

### Workspace lifecycle

1. Crear workspace (`POST /v1/workspaces`)
2. Publicar/share (`/publish`, `/share`) y/o archivar (`/archive`)
3. Listar visibles (`GET /v1/workspaces`)

### Upload async (scoped)

1. `POST /v1/workspaces/{workspace_id}/documents/upload`
2. API guarda metadata (PENDING) y binario en S3/MinIO
3. Worker procesa (PROCESSING -> READY/FAILED)

### Ingest sync (scoped)

1. `POST /v1/workspaces/{workspace_id}/ingest/text`
2. Chunking + embeddings
3. Persistencia de documentos/chunks

### Ask/query (scoped)

1. `POST /v1/workspaces/{workspace_id}/query` (retrieval)
2. `POST /v1/workspaces/{workspace_id}/ask` (RAG)
3. `POST /v1/workspaces/{workspace_id}/ask/stream` (SSE)

---

## Source of Truth

- OpenAPI: `shared/contracts/openapi.json`
- DB schema: `backend/alembic/`

---

## Context Assembly (RAG Quality)

- Prompts versionados: `backend/app/prompts/`
- Context builder: `backend/app/application/context_builder.py`
- Limites: `MAX_CONTEXT_CHARS`, `PROMPT_VERSION`
- Cache de embeddings: memory/Redis (segun `EMBEDDING_CACHE_BACKEND`)

---

## Observability

- API: `/healthz`, `/readyz`, `/metrics`
- Worker: `/readyz` en `WORKER_HTTP_PORT` (default `8001`)
- Perfiles compose: `observability`, `full`

