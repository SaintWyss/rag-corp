# Informe de Auditoría: SurfSense -> RAG Corp Adapters

## 1. Executive Summary

- **Maturity**: SurfSense tiene un backend sólido (FastAPI + SQLModel/SQLAlchemy) con un RAG "state-of-the-art" (Hybrid + RRF + Rerank).
- **Core Value**: La joya es `chunks_hybrid_search.py`, que implementa recíproco rank fusion (RRF) sobre pgvector y tsvector de manera eficiente en SQL puro.
- **UX**: Implementa el protocolo "Vercel AI SDK Data Stream" (SSE), crítico para una experiencia "ChatGPT-like" fluida.
- **Ingest**: Pipeline robusto con `LlamaCloud` y `Docling`, manejando reintentos y timeouts dinámicos para archivos grandes.
- **Security**: Modelo RBAC granular (Search Spaces) que debería ser el estándar para RAG Corp si planea multi-tenancy.

---

## 2. Inventario de Features (SurfSense)

| Feature                | Descripción                                              | Evidencia (Paths & Symbols)                                                            | Deps                     | Complejidad |
| :--------------------- | :------------------------------------------------------- | :------------------------------------------------------------------------------------- | :----------------------- | :---------- |
| **Hybrid Search**      | Combina Dense (Vector) + Sparse (Keyword) search.        | `app/retriever/chunks_hybrid_search.py` (`keywords_search_cte`, `semantic_search_cte`) | pgvector, postgres       | M           |
| **Rank Fusion (RRF)**  | Fusiona resultados usando Reciprocal Rank Fusion (k=60). | `app/retriever/chunks_hybrid_search.py` (`1.0/(k+rank)`)                               | SQLAlchemy               | M           |
| **Reranking**          | Reordena top-k resultados con cross-encoder/FlashRank.   | `app/services/reranker_service.py` (`RerankerService.rank`)                            | `rerankers` lib          | L           |
| **Streaming (SSE)**    | Protocolo standard para streaming de texto/tools.        | `app/services/new_streaming_service.py` (`VercelStreamingService`)                     | `sse-starlette`          | S           |
| **Ingestion Pipeline** | Parseo de PDFs/Office con reintentos y fallback.         | `app/tasks/document_processors/file_processors.py` (`parse_with_llamacloud_retry`)     | `llama-cloud`, `docling` | H           |
| **Multi-tenancy**      | Aislamiento lógico de datos por "Search Space".          | `app/db.py` (`SearchSpace`, `Permission`, `SearchSpaceRole`)                           | SQLAlchemy               | H           |
| **Chunking Logic**     | Estrategia de split y hashing para deduplicación.        | `app/utils/document_converters.py` (`create_document_chunks`)                          | LangChain                | M           |
| **Citation Support**   | Estructura de respuesta agrupada por documento.          | `app/retriever/chunks_hybrid_search.py` (`hybrid_search` returns `final_docs`)         | N/A                      | S           |

---

## 3. Mapeo a RAG Corp (Clean Architecture)

### 3.1 Domain Layer (Entidades & Reglas)

- **Entities**: Adoptar `Document` y `Chunk` (con `embedding` y `content_hash`) en `rag_corp/backend/domain/models`.
  - _Cambio Clave_: Agregar `search_space_id` si vamos a multi-tenant ya.
- **Value Objects**: Copiar `DocumentStatus` (JSONB) para control granular estado de ingestión.

### 3.2 Application Layer (Use Cases)

- **RetrievalService**: Portar la lógica de orquestación de `hybrid_search` aquí.
- **RerankerService**: Crear como servicio de dominio puro en `rag_corp/backend/application/services`.
- **IngestService**: Adaptar `file_processors.py` como casos de uso (`UploadDocument`, `ProcessDocument`).

### 3.3 Infrastructure Layer (Repos & Adapters)

- **PostgresRetriever**: Implementar la lógica SQL de `chunks_hybrid_search.py` aquí. Es SQL puro (SQLAlchemy Core/ORM), fácil de portar.
- **StreamingAdapter**: Adaptar `VercelStreamingService` como un presentador en `rag_corp/backend/infrastructure/streaming`.

### 3.4 Riesgos & Tests

- **Riesgos**: La consulta RRF es costosa en DBs grandes. Requiere índices adecuados (`hnsw` para vector, `gin` para tsvector).
- **Tests**:
  - _Unit_: Testear `RRF` logic con mocks de scores.
  - _Integration_: Testear `hybrid_search` con TestContainers (Postgres+pgvector).

---

## 4. Priorización & Roadmap

| #   | Feature                    | Impacto  | Esfuerzo | Riesgo   | Dependencias   | PRs Sugeridos                                       |
| :-- | :------------------------- | :------- | :------- | :------- | :------------- | :-------------------------------------------------- |
| 1   | **Hybrid Retrieval + RRF** | **High** | Medium   | Low      | pgvector       | 1. Estructura DB (Chunks)<br>2. Repo Implementation |
| 2   | **Streaming (SSE)**        | **High** | Low      | Low      | -              | 1. Streaming Service<br>2. Endpoint integration     |
| 3   | **Ingestion Resilience**   | Medium   | **High** | Medium   | LlamaParser    | 1. Retry Logic Wrapper<br>2. Async Task Queue       |
| 4   | **Reranking**              | Medium   | Low      | Low      | GPU (opcional) | 1. Reranker Service                                 |
| 5   | **Multi-tenancy RBAC**     | High     | **High** | **High** | Auth           | 1. Schema migration                                 |

---

## 5. Recomendación Final (Top 3 Highest ROI)

### Paso 1: "The Brain" - Hybrid Retrieval Engine

**Objetivo**: Mejorar drásticamente la calidad de respuesta.

- **Implementación**: Copiar `chunks_hybrid_search.py`.
- **Adaptación**: Mover a `Infrastructure/Repositories/SqlAlchemyRetriever`.
- **Validación**: Test de integración comparando resultados (Vector vs Keyword vs Hybrid).

### Paso 2: "The Voice" - SSE Streaming Protocol

**Objetivo**: UX fluida y moderna.

- **Implementación**: Adaptar `new_streaming_service.py`.
- **Adaptación**: Usar en `Interfaces/API/Endpoints`.
- **Validación**: `curl -N` al endpoint y verificar chunks `data: ...`.

### Paso 3: "The Precision" - Reranking Service

**Objetivo**: Refinar el contexto entregado al LLM.

- **Implementación**: Portar `reranker_service.py` usando `flashrank` (CPU friendly).
- **Adaptación**: Inyectar en `Application/UseCases/AskQuestion`.
- **Validación**: Evaluar MRR (Mean Reciprocal Rank) en dataset de prueba.

---

## 6. Definition of Done (Checklist)

- [ ] Tablas `documents` y `chunks` con índices `hnsw` y `gin`.
- [ ] Retriever implementa `vector_search`, `full_text_search` y `hybrid_search` (RRF).
- [ ] Endpoints retornan `Transfer-Encoding: chunked` (SSE).
- [ ] Pipeline maneja archivos duplicados vía `content_hash`.
