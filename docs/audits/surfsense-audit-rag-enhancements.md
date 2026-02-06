# Informe: SurfSense -> RAG Corp — Audit & Roadmap de Mejoras RAG

---

## 1. Executive Summary (5 bullets)

1. **Hybrid Search es la brecha #1**: RAG Corp solo tiene retrieval por vector (cosine + IVFFlat). SurfSense implementa hybrid search (vector + BM25/tsvector) con RRF fusion en PostgreSQL nativo. Agregar esto mejoraría significativamente recall en queries con keywords exactos (nombres, IDs, siglas).

2. **RRF + Two-Tier retrieval es la mejora de mayor ROI**: SurfSense combina búsqueda a nivel chunk Y a nivel documento con Reciprocal Rank Fusion (k=60). RAG Corp solo busca chunks. Implementar RRF two-tier daría mejor ranking sin agregar dependencias externas.

3. **HNSW > IVFFlat para indexes**: SurfSense usa HNSW (mejor recall, sin re-training). RAG Corp usa IVFFlat (lists=100). Migrar a HNSW es un cambio de 1 migración con impacto directo en calidad de retrieval.

4. **Document summaries como tier adicional**: SurfSense genera resúmenes por documento con embedding propio, habilitando búsqueda coarse-to-fine. RAG Corp no tiene embeddings a nivel documento. Esto complementa el hybrid search.

5. **Content deduplication falta en RAG Corp**: SurfSense usa SHA-256 hashes (`content_hash`, `unique_identifier_hash`) para evitar duplicados. RAG Corp no tiene mecanismo de dedup, lo que puede degradar retrieval con documentos re-subidos.

---

## 2. Inventario de Features con Evidencia

### F1: Hybrid Search (Vector + BM25/tsvector)
- **Qué hace**: Combina búsqueda semántica (pgvector cosine) con búsqueda léxica (PostgreSQL full-text search) para mejorar recall en queries mixtos.
- **Evidencia SurfSense**:
  - `surfsense_backend/app/retriever/documents_hybrid_search.py:69-122` — `full_text_search()`: usa `to_tsvector('english', Document.content)` + `plainto_tsquery` + `ts_rank_cd`
  - `surfsense_backend/app/retriever/chunks_hybrid_search.py:68-122` — mismo patrón a nivel chunk
  - `surfsense_backend/app/db.py:1731-1742` — GIN indexes: `CREATE INDEX document_search_index ON documents USING gin (to_tsvector('english', content))`
- **Dependencias**: PostgreSQL built-in (no nuevas libs). Solo agregar columna tsvector generada + GIN index.
- **Complejidad**: **M** (migración + nuevo repo method + integración en use case)
- **RAG Corp gap**: Solo tiene `find_similar_chunks()` y `find_similar_chunks_mmr()`. No hay búsqueda keyword.

### F2: Reciprocal Rank Fusion (RRF)
- **Qué hace**: Combina rankings de múltiples retrievers con la fórmula `score = 1/(k+rank_semantic) + 1/(k+rank_keyword)` donde k=60. Produce mejor ranking que cualquier retriever individual.
- **Evidencia SurfSense**:
  - `surfsense_backend/app/retriever/documents_hybrid_search.py:158-244` — RRF con CTEs, FULL OUTER JOIN, coalesce para ranks faltantes
  - `surfsense_backend/app/services/connector_service.py:216-338` — `_combined_rrf_search()`: segundo nivel de RRF combinando chunk-results + doc-results
  - Constante k=60 (línea 159, 250)
- **Dependencias**: Ninguna nueva. Puro SQL + lógica Python.
- **Complejidad**: **M** (algoritmo bien definido, implementar en application layer como servicio puro)
- **RAG Corp gap**: Solo tiene MMR (diversidad), no tiene fusion de rankings.

### F3: Two-Tier Retrieval (Document + Chunk)
- **Qué hace**: Busca tanto a nivel documento (summary+embedding) como a nivel chunk, luego fusiona con RRF. Mejora contexto al encontrar documentos relevantes que no tienen chunks con match exacto.
- **Evidencia SurfSense**:
  - `surfsense_backend/app/services/connector_service.py:262-277` — ejecuta `chunk_retriever.hybrid_search()` + `document_retriever.hybrid_search()` secuencialmente
  - `surfsense_backend/app/utils/document_converters.py:103-151` — `generate_document_summary()`: genera summary + embedding por documento
  - `surfsense_backend/app/db.py:850-910` — Document model con `embedding: Vector(dimension)` propio
- **Dependencias**: Requiere F1 y F2 primero. Columna `embedding vector(768)` en tabla documents + summary text.
- **Complejidad**: **L** (columnas nuevas, pipeline de ingest modificado, nuevo retriever)
- **RAG Corp gap**: Solo busca en chunks. La tabla `documents` no tiene embedding ni summary.

### F4: HNSW Index (reemplazo de IVFFlat)
- **Qué hace**: HNSW tiene mejor recall que IVFFlat, no requiere re-training con VACUUM, y escala mejor con pocas filas.
- **Evidencia SurfSense**:
  - `surfsense_backend/app/db.py:1726-1730` — `CREATE INDEX document_vector_index ON documents USING hnsw (embedding public.vector_cosine_ops)`
  - Mismo para chunks: `CREATE INDEX chucks_vector_index ON chunks USING hnsw (embedding public.vector_cosine_ops)`
- **Dependencias**: pgvector >= 0.5.0 (ya disponible en RAG Corp).
- **Complejidad**: **S** (1 migración Alembic: DROP INDEX + CREATE INDEX)
- **RAG Corp gap**: Usa IVFFlat (lists=100), inferior en recall para datasets < 1M filas.

### F5: Content Deduplication (Hash)
- **Qué hace**: Evita indexar el mismo contenido dos veces mediante SHA-256 hash del contenido.
- **Evidencia SurfSense**:
  - `surfsense_backend/app/utils/document_converters.py:231-271` — `generate_content_hash(search_space_id, content)` = `SHA256(space_id:content)`, `generate_unique_identifier_hash()` para IDs de connectors
  - `surfsense_backend/app/db.py:~870` — `content_hash: String (unique, indexed)`, `unique_identifier_hash: String (unique, indexed)`
- **Dependencias**: Solo hashlib (stdlib).
- **Complejidad**: **S** (columna nueva + check en ingest pipeline)
- **RAG Corp gap**: No tiene mecanismo de dedup. Re-subir un PDF crea chunks duplicados.

### F6: Reranking con `rerankers` Library
- **Qué hace**: Reranking post-retrieval usando modelos cross-encoder (ms-marco-MiniLM, Cohere, flashrank).
- **Evidencia SurfSense**:
  - `surfsense_backend/app/services/reranker_service.py:21-110` — `rerank_documents()`: convierte a RerankerDocument, llama `reranker_instance.rank(query, docs)`, preserva chunks
  - `pyproject.toml` línea 27: `"rerankers[flashrank]>=0.7.1"`
  - Config: `RERANKERS_ENABLED` env var
- **Dependencias**: `rerankers` library (lightweight, flashrank es local sin API).
- **Complejidad**: **S** (RAG Corp **ya tiene** reranking HEURISTIC+LLM. Agregar flashrank como tercer modo sería incremental)
- **RAG Corp estado**: Ya tiene `ChunkRerankerService` con modos DISABLED/HEURISTIC/LLM. Solo falta modo CROSS_ENCODER con lib dedicada.

### F7: Vercel AI SDK Streaming Protocol
- **Qué hace**: Protocolo estructurado de SSE con tipos de mensaje (text_delta, reasoning, sources, tool_calls, thinking_step).
- **Evidencia SurfSense**:
  - `surfsense_backend/app/services/new_streaming_service.py:37-750` — `VercelStreamingService`: format_text_delta, format_reasoning, format_sources, format_thinking_step
  - Header: `x-vercel-ai-ui-message-stream: v1`
  - Protocolo: `data: {json}\n\n` con tipos tipados
- **Dependencias**: Vercel AI SDK en frontend (Next.js). RAG Corp ya usa Next.js.
- **Complejidad**: **M** (reemplazar streaming actual por protocolo estructurado, adaptar frontend)
- **RAG Corp estado**: Tiene SSE con eventos custom (sources/token/done/error). Menos estructurado que Vercel protocol.

### F8: Document Summary Generation (Context-Window Aware)
- **Qué hace**: Genera resúmenes inteligentes que respetan el context window del modelo usando binary search para encontrar el máximo de contenido que cabe.
- **Evidencia SurfSense**:
  - `surfsense_backend/app/utils/document_converters.py:29-100` — `optimize_content_for_context_window()`: binary search left=0, right=len(content), reserva 2000 tokens
  - `surfsense_backend/app/utils/document_converters.py:103-151` — `generate_document_summary()`: combina metadata + contenido optimizado + LLM summary + embedding
- **Dependencias**: LiteLLM para token counting (RAG Corp podría usar tiktoken o google-generativeai).
- **Complejidad**: **M** (nuevo step en pipeline de ingest + lógica de truncado)
- **RAG Corp gap**: Usa `MAX_CONTEXT_CHARS` fijo (12000). No tiene summaries por documento.

### F9: Connector Framework / Multi-Source ETL
- **Qué hace**: Framework extensible para indexar desde 20+ fuentes (Google Drive, Slack, Notion, GitHub, etc.) con pipeline unificado de chunking+embedding.
- **Evidencia SurfSense**:
  - `surfsense_backend/app/connectors/` — base connector pattern
  - `surfsense_backend/app/tasks/connector_indexers/` — indexers por tipo
  - `surfsense_backend/app/tasks/document_processors/` — processors (file, markdown, youtube, etc.)
- **Dependencias**: APIs externas, OAuth, Celery.
- **Complejidad**: **L** (infraestructura significativa, cada connector es un esfuerzo separado)
- **RAG Corp gap**: Solo soporta upload manual (PDF/DOCX/TXT). No tiene connectors.

### F10: LLM Router (Multi-Model Load Balancing)
- **Qué hace**: Usa LiteLLM Router para distribuir requests entre múltiples modelos/proveedores con fallback y retry.
- **Evidencia SurfSense**:
  - `surfsense_backend/app/config/__init__.py:134-156` — LiteLLM Router con usage-based routing strategy
  - `surfsense_backend/app/services/llm_router_service.py` — Router service
  - `surfsense_backend/app/config/global_llm_config.example.yaml:177` — RPM rate limiting per model
- **Dependencias**: LiteLLM library.
- **Complejidad**: **M** (reemplazar Google-only LLM service por router multi-provider)
- **RAG Corp gap**: Hardcoded a Google Gemini (ADR-003). Cambiar requiere nuevo ADR.

### F11: Chunking Avanzado (Chonkie / Semantic)
- **Qué hace**: Chunking semántico con `RecursiveChunker` (texto general) y `CodeChunker` (código), usando max_seq_length del embedding model como chunk_size.
- **Evidencia SurfSense**:
  - `surfsense_backend/app/config/__init__.py:319-324` — `RecursiveChunker(chunk_size=max_seq_length)`, `CodeChunker(chunk_size=max_seq_length)`
  - Usa Chonkie library para chunking inteligente basado en estructura
- **Dependencias**: `chonkie` library (o madurar el chunker existente en RAG Corp).
- **Complejidad**: **S** (ya existe `semantic_chunker.py` experimental — madurar y habilitar)
- **RAG Corp estado**: Tiene `app/infrastructure/text/semantic_chunker.py` (EXPERIMENTAL, no en producción) + `SimpleTextChunker` (producción, sliding window 900/120). El semantic chunker ya soporta headers/listas/code blocks pero no está wired al pipeline de ingest.

### F12: Search Space Scoping (Multi-Tenant Isolation)
- **Qué hace**: Todo query filtrado por `search_space_id` a nivel SQL. Cada usuario tiene space personal + spaces compartidos.
- **Evidencia SurfSense**:
  - `surfsense_backend/app/retriever/documents_hybrid_search.py:49` — `.where(Document.search_space_id == search_space_id)`
  - `surfsense_backend/app/db.py` — FK search_space_id en Document, Chunk
  - `surfsense_backend/app/users.py:120-170` — Auto-crea space personal al registrarse
- **Dependencias**: Ninguna.
- **Complejidad**: N/A — **RAG Corp ya tiene esto** con Workspaces + ACL + visibility.
- **RAG Corp estado**: Implementado. Similar diseño con `workspace_id` scoping.

---

## 3. Tabla de Priorización

| # | Feature | Impacto | Esfuerzo | Riesgo | Dependencias | PR #1 (MVP) | PR #2 (Mejora) | Validación |
|---|---------|---------|----------|--------|--------------|-------------|----------------|------------|
| 1 | **F4: HNSW Index** | H | **S** | L | pgvector >=0.5 | Migración: DROP IVFFlat + CREATE HNSW en chunks | Tunear `ef_construction`, `m` params | `EXPLAIN ANALYZE` comparando recall antes/después con dataset de test |
| 2 | **F1: Hybrid Search** | **H** | M | M | F4 completado | Agregar GIN index tsvector + `full_text_search()` en repo + flag `enable_hybrid` | Tunear weights BM25 vs vector | Test: query con keyword exacto (nombre propio) debe mejorar posición vs vector-only |
| 3 | **F2: RRF Fusion** | **H** | M | L | F1 completado | `RankFusionService` en application layer con k=60 | Hacer k configurable, A/B testing hooks | Unit test: dado rankings [A,B,C] y [C,A,D], verificar score fusion correcto |
| 4 | **F5: Content Dedup** | M | **S** | L | Ninguna | Columna `content_hash` + UNIQUE constraint + check en ingest | Index y reject con 409 Conflict en API | Test: subir mismo PDF 2 veces, segundo debe fallar/skip |
| 5 | **F11: Semantic Chunking** | M | **S** | L | Ninguna (chunker experimental ya existe) | Madurar `semantic_chunker.py` + wire al pipeline con flag `CHUNKER_TYPE` | Incorporar ideas de Chonkie (CodeChunker) para archivos de código | Test: comparar chunk boundaries en markdown con headers |
| 6 | **F8: Doc Summaries** | M | M | M | F1+F2 | Columna `summary` + `summary_embedding` en documents + generation en ingest | Two-tier search integrado | Test: query vago ("resumen del proyecto") encuentra docs por summary |
| 7 | **F3: Two-Tier Retrieval** | H | **L** | M | F1+F2+F8 | Document-level retriever + RRF dual-tier en `AnswerQueryUseCase` | Weights configurables chunk vs doc tier | E2E test: query que matchea summary pero no chunks específicos |
| 8 | **F6: Cross-Encoder Rerank** | M | S | L | Ninguna | Agregar modo CROSS_ENCODER a `ChunkRerankerService` con `rerankers[flashrank]` | Benchmark HEURISTIC vs LLM vs CROSS_ENCODER | Test: medir latencia + nDCG con dataset anotado |
| 9 | **F7: Vercel Streaming** | L | M | M | Frontend changes | Refactor `streaming.py` a protocolo Vercel-compatible | Agregar thinking_step, further_questions | Test: frontend consume stream sin errores, tokens llegan < 200ms TTFT |
| 10 | **F10: LLM Router** | M | M | H | Nuevo ADR | LiteLLM wrapper sobre `LLMService` port | Multi-provider fallback + rate limiting | Test: failover a modelo B cuando A da 429 |
| 11 | **F9: Connectors** | H | **L** | H | Mucha infra | 1 connector (Google Drive) como prueba de concepto | Framework base + 2-3 connectors más | Test: sync Google Drive folder, verifica documentos indexados |

---

## 4. Plan de PRs con Pruebas

### PR 1: HNSW Index Migration
**Archivos a modificar:**
- `apps/backend/alembic/versions/` — nueva migración
- `docs/reference/data/postgres-schema.md` — actualizar documentación de indexes

**Migración Alembic:**
```sql
-- upgrade
DROP INDEX IF EXISTS chunks_embedding_idx;
CREATE INDEX chunks_embedding_hnsw_idx ON chunks USING hnsw (embedding vector_cosine_ops)
  WITH (m = 16, ef_construction = 64);

-- downgrade
DROP INDEX IF EXISTS chunks_embedding_hnsw_idx;
CREATE INDEX chunks_embedding_idx ON chunks USING ivfflat (embedding vector_cosine_ops) WITH (lists = 100);
```

**Tests:**
- `EXPLAIN ANALYZE SELECT ... ORDER BY embedding <=> $vec LIMIT 10` — verificar que usa HNSW scan
- Benchmark: comparar recall@10 con 100 queries de test

**Riesgo:** Index build time en tablas grandes (mitigar con `CREATE INDEX CONCURRENTLY`).

---

### PR 2: Hybrid Search (BM25 + Vector)
**Archivos a modificar:**
- `apps/backend/alembic/versions/` — migración para GIN index
- `apps/backend/app/domain/repositories.py` — agregar `find_chunks_full_text(query, workspace_id, top_k)` al protocol
- `apps/backend/app/infrastructure/repositories/postgres/document_repository.py` — implementar full-text search con `to_tsvector` + `plainto_tsquery` + `ts_rank_cd`
- `apps/backend/app/crosscutting/config.py` — agregar `ENABLE_HYBRID_SEARCH: bool = False`
- `apps/backend/app/application/usecases/chat/search_chunks.py` — integrar full-text como segundo canal

**Migración:**
```sql
CREATE INDEX chunks_content_fts_idx ON chunks USING gin (to_tsvector('spanish', content));
```

**Capa por capa (Clean Architecture):**
- **Domain**: Nuevo método en `DocumentRepository` protocol: `find_chunks_full_text(query_text, workspace_id, top_k) -> list[ScoredChunk]`
- **Infrastructure**: Implementación con raw SQL usando `to_tsvector('spanish', content)`, `plainto_tsquery('spanish', query)`, `ts_rank_cd()` (default `'spanish'`, configurable via env var `FTS_LANGUAGE` si se necesita multi-idioma a futuro)
- **Application**: Flag `enable_hybrid` en `SearchChunksUseCase`. Si habilitado, ejecutar ambos channels.

**Tests:**
- Unit: mock repo retorna resultados keyword, verificar que use case los incluye
- Integration: insertar chunk con "Acme Corporation quarterly report", buscar "Acme Corporation" — debe rankear #1 con BM25, puede no ser #1 con vector-only
- Negative: query semánticamente similar pero sin keywords exactos, verificar que BM25 no domina

---

### PR 3: RRF Fusion Service
**Archivos a modificar:**
- `apps/backend/app/application/rank_fusion.py` — **nuevo** `RankFusionService` (domain puro, sin IO)
- `apps/backend/app/application/usecases/chat/search_chunks.py` — integrar RRF cuando hybrid habilitado
- `apps/backend/app/crosscutting/config.py` — `RRF_K: int = 60`

**Implementación (application layer, lógica pura):**
```python
class RankFusionService:
    def __init__(self, k: int = 60):
        self.k = k

    def fuse(self, *ranked_lists: list[ScoredChunk]) -> list[ScoredChunk]:
        """RRF: score(d) = sum(1/(k + rank_i(d))) for each ranker i"""
        scores: dict[str, float] = {}
        items: dict[str, ScoredChunk] = {}
        for ranked_list in ranked_lists:
            for rank, chunk in enumerate(ranked_list, start=1):
                key = chunk.chunk_id
                scores[key] = scores.get(key, 0.0) + 1.0 / (self.k + rank)
                if key not in items:
                    items[key] = chunk
        return sorted(items.values(), key=lambda c: scores[c.chunk_id], reverse=True)
```

**Tests:**
- Unit puro (sin DB): dados 2 rankings, verificar fórmula RRF exacta
- Property test: resultado siempre contiene unión de ambos inputs
- Edge case: un item solo en 1 ranking, verificar score = 1/(k+rank)

---

### PR 4: Content Deduplication
**Archivos a modificar:**
- `apps/backend/alembic/versions/` — agregar columna `content_hash VARCHAR(64) UNIQUE`
- `apps/backend/app/domain/entities.py` — agregar `content_hash: str | None` a Document
- `apps/backend/app/infrastructure/repositories/postgres/document_repository.py` — check hash antes de insert
- `apps/backend/app/application/usecases/documents/upload_document.py` — generar hash, verificar duplicado

**Lógica:**
```python
import hashlib
def content_hash(workspace_id: str, content: str) -> str:
    return hashlib.sha256(f"{workspace_id}:{content}".encode()).hexdigest()
```

**Tests:**
- Unit: hash determinístico para mismo input
- Integration: insertar doc, intentar insertar mismo contenido — debe rechazar/skip
- API: POST /documents dos veces con mismo archivo — segundo retorna 409 o referencia al existente

---

### PR 5: Habilitar Semantic Chunking (ya existe experimental)
**Archivos a modificar:**
- `apps/backend/app/infrastructure/text/semantic_chunker.py` — madurar: agregar tests faltantes, edge cases
- `apps/backend/app/crosscutting/config.py` — `CHUNKER_TYPE: str = "simple"` (simple | semantic)
- `apps/backend/app/application/usecases/ingestion/ingest_document.py` — wiring condicional del chunker semántico
- `apps/backend/app/application/usecases/ingestion/process_uploaded_document.py` — idem

**RAG Corp ya tiene** `app/infrastructure/text/semantic_chunker.py` (experimental). El trabajo es:
1. Agregar integration tests comparando output con SimpleTextChunker
2. Benchmark performance con documentos reales
3. Wire al pipeline de ingest via feature flag `CHUNKER_TYPE`

**Tests:**
- Unit: markdown con headers produce chunks que respetan boundaries de sección
- Integration: comparar chunks simple vs semantic en PDFs reales (calidad + cantidad)
- Benchmark: latencia de chunking semantic vs simple

---

### PR 6: Document Summaries + Embeddings
**Archivos a modificar:**
- `apps/backend/alembic/versions/` — columnas `summary TEXT`, `summary_embedding vector(768)` en documents + HNSW index
- `apps/backend/app/domain/entities.py` — agregar campos a Document
- `apps/backend/app/domain/repositories.py` — `find_similar_documents(embedding, workspace_id, top_k)`
- `apps/backend/app/infrastructure/repositories/postgres/document_repository.py` — implementar document-level vector search
- `apps/backend/app/application/usecases/documents/upload_document.py` — generar summary + embedding en pipeline de ingest (post-chunking)

**Tests:**
- Integration: subir PDF, verificar que documents.summary_embedding NOT NULL
- Query: buscar término que está en summary pero no en chunks individuales

---

### PR 7: Two-Tier Retrieval con RRF
**Archivos a modificar:**
- `apps/backend/app/application/usecases/chat/search_chunks.py` — búsqueda en ambos tiers + RRF fusion
- `apps/backend/app/crosscutting/config.py` — `ENABLE_TWO_TIER: bool = False`

**Flow:**
1. Chunk hybrid search → ranked list A
2. Document summary search → ranked list B (expandir a chunks del documento)
3. RRF fusion de A + B → resultado final

**Tests:**
- E2E: documento cuyo summary matchea pero chunks individuales no — debe aparecer en resultados
- Benchmark: comparar nDCG con y sin two-tier en dataset anotado

---

## 5. Top 3 Highest-ROI — Orden de Implementación

### #1: HNSW Index (PR 1)
- **Por qué primero**: Esfuerzo mínimo (1 migración), impacto directo en calidad de retrieval, zero risk funcional.
- **Criterio de aceptación**: `EXPLAIN ANALYZE` muestra HNSW index scan. Recall@10 >= recall anterior en benchmark.
- **Licencia/atribución**: No requiere — HNSW es feature de pgvector, no código de SurfSense.

### #2: Hybrid Search + RRF (PR 2 + PR 3)
- **Por qué segundo**: Es la mejora arquitectural más significativa. Queries con keywords exactos (nombres de empresas, IDs de producto, siglas) van a mejorar drásticamente. RRF es algoritmo público (paper de Cormack et al. 2009), no requiere atribución a SurfSense.
- **Criterio de aceptación**:
  - Feature flag `ENABLE_HYBRID_SEARCH=true` activa búsqueda dual.
  - Query "Acme Corporation" con documentos que contienen esa frase: BM25 rankea #1, vector puede no.
  - RRF combina ambos rankings correctamente (unit test con valores exactos).
  - Latencia de retrieval < 500ms p95 con hybrid habilitado.
- **Licencia/atribución**: RRF es algoritmo académico público. La implementación SQL con CTEs es un patrón conocido. Si se adapta la estructura de CTEs de SurfSense, agregar comentario: `# Hybrid search pattern inspired by SurfSense (Apache 2.0)`.

### #3: Content Deduplication (PR 4)
- **Por qué tercero**: Previene degradación silenciosa del retrieval. Esfuerzo mínimo, protege la calidad de las mejoras anteriores. Sin dedup, documentos duplicados contaminan los rankings.
- **Criterio de aceptación**:
  - Columna `content_hash` con UNIQUE constraint existe.
  - Re-subir mismo PDF retorna 409 o skip silencioso (configurable).
  - Hash es determinístico: mismo contenido + workspace = mismo hash.
- **Licencia/atribución**: SHA-256 hashing es patrón estándar, no requiere atribución.

---

## 6. Checklist "Definition of Done" para RAG vNext

- [ ] **HNSW Migration**: Index HNSW creado en chunks (y futuro documents). `EXPLAIN ANALYZE` confirma uso. Migración reversible.
- [ ] **GIN FTS Index**: `chunks_content_fts_idx` creado. Queries `to_tsvector` usan el index.
- [ ] **Full-Text Search Method**: `find_chunks_full_text()` en repo con `ts_rank_cd`. Tests de integración pasan.
- [ ] **RRF Service**: `RankFusionService.fuse()` con k configurable. 100% unit tested (edge cases incluidos).
- [ ] **Hybrid Search Use Case**: `SearchChunksUseCase` combina vector + BM25 cuando `ENABLE_HYBRID_SEARCH=true`. Feature flag funciona.
- [ ] **Content Hash**: Columna `content_hash` en documents. Pipeline de ingest genera hash y verifica duplicados.
- [ ] **Docs actualizados**: `postgres-schema.md` refleja nuevos indexes/columnas. ADR nuevo para hybrid search.
- [ ] **Metrics**: `rag_retrieval_duration_seconds` histograma con labels `{method=vector|bm25|hybrid|rrf}`. `rag_dedup_hits_total` counter.
- [ ] **Feature flags**: `ENABLE_HYBRID_SEARCH`, `RRF_K` en config. Defaults conservadores (hybrid off por default).
- [ ] **Performance**: p95 latencia retrieval < 500ms con hybrid. p99 < 1s. Benchmark documentado.
- [ ] **Security**: Todos los queries filtran por `workspace_id` (sin bypass). Injection filter compatible con hybrid results.
- [ ] **Tests**: Unit (RRF puro, hash), Integration (FTS query, dedup check), E2E (upload + query hybrid via API).
- [ ] **Backward compat**: Hybrid off por default. API response schema no cambia. Existing clients no se rompen.

---

## Notas sobre Licencia (SurfSense)

SurfSense está bajo **Apache License 2.0**. Esto permite:
- Uso, modificación y distribución libre
- **Requiere**: preservar notices de copyright y licencia en archivos derivados
- **Requiere**: documentar cambios si se crea trabajo derivado
- **No requiere**: open-source del código derivado

**Recomendación**: No copiar código textual. Los patrones (RRF, hybrid SQL, hash dedup) son técnicas públicas. Si se adapta estructura de queries SQL de SurfSense, agregar un comentario de atribución en el archivo correspondiente. No se requiere incluir la licencia Apache completa en RAG Corp para usar *patrones* (no código literal).

---

## Riesgos y Mitigaciones

| Riesgo | Probabilidad | Impacto | Mitigación |
|--------|-------------|---------|------------|
| GIN index degrada write performance | Baja | Medio | Benchmark INSERT con/sin index. GIN es append-only, impacto menor que B-tree. |
| HNSW build time en tabla existente grande | Media | Bajo | Usar `CREATE INDEX CONCURRENTLY`. Estimado < 5 min para < 100K chunks. |
| Full-text search en español (no solo english) | Media | Alto | Agregar soporte `'spanish'` configurable. SurfSense hardcodea 'english'. RAG Corp debería parametrizar. |
| RRF k=60 no óptimo para RAG Corp | Baja | Bajo | Hacer configurable (env var). Default 60 es estándar del paper. |
| Dedup hash collision | Extremadamente baja | Bajo | SHA-256 tiene collision resistance de 128 bits. Negligible. |
| Latencia con 2 queries (vector + FTS) | Media | Medio | Ejecutar en paralelo con `asyncio.gather()`. PostgreSQL maneja bien queries concurrentes. |

---

## Archivos Clave de RAG Corp (Referencia para implementación)

| Componente | Path relativo (desde `apps/backend/`) |
|---|---|
| **Domain entities** | `app/domain/entities.py` (Document, Chunk, Workspace) |
| **Domain repositories (ports)** | `app/domain/repositories.py` (DocumentRepository protocol) |
| **Domain services** | `app/domain/services.py` (EmbeddingService, TextChunkerService ports) |
| **Search Chunks use case** | `app/application/usecases/chat/search_chunks.py` |
| **Answer Query use case** | `app/application/usecases/chat/answer_query.py` |
| **Stream Answer use case** | `app/application/usecases/chat/stream_answer_query.py` |
| **Reranker** | `app/application/reranker.py` (ChunkReranker, modes: DISABLED/HEURISTIC/LLM) |
| **Query rewriter** | `app/application/query_rewriter.py` |
| **Injection detector** | `app/application/prompt_injection_detector.py` |
| **Context builder** | `app/application/context_builder.py` |
| **Config** | `app/crosscutting/config.py` (feature flags, env vars) |
| **Streaming** | `app/crosscutting/streaming.py` (SSE helpers) |
| **Metrics** | `app/crosscutting/metrics.py` |
| **Postgres document repo** | `app/infrastructure/repositories/postgres/document.py` |
| **Simple chunker** | `app/infrastructure/text/chunker.py` (producción) |
| **Semantic chunker** | `app/infrastructure/text/semantic_chunker.py` (EXPERIMENTAL) |
| **Embeddings service** | `app/infrastructure/services/google_embedding_service.py` |
| **Cached embeddings** | `app/infrastructure/services/cached_embedding_service.py` |
| **DB pool** | `app/infrastructure/db/pool.py` |
| **Ingest use case** | `app/application/usecases/ingestion/ingest_document.py` |
| **Process uploaded** | `app/application/usecases/ingestion/process_uploaded_document.py` |
| **Upload use case** | `app/application/usecases/ingestion/upload_document.py` |
| **Query router** | `app/interfaces/api/http/routers/query.py` |
| **Query schemas** | `app/interfaces/api/http/schemas/query.py` |
| **Alembic migrations** | `alembic/versions/` |
| **Schema docs** | `docs/reference/data/postgres-schema.md` |
| **ADRs** | `docs/architecture/adr/` |
