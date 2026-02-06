# RAG Corp — Registro completo PR1–PR8 (mejoras RAG core)

## 0) Objetivo y alcance

- Objetivo: elevar la **calidad y operabilidad** del motor RAG de RAG Corp con mejoras “core” (retrieval, ranking, índices, ingesta, observabilidad, evaluación).
- Fuera de alcance: features de producto tipo “podcasts”, extensiones u otros verticales no alineados.
- Estrategia: 1 PR por área, **ramas separadas**, commits atómicos, ADRs y tests.
- Regla editorial: en el repo **no se menciona** ningún repo externo de referencia en docs/commits/ADRs.

---

## PR1 — Vector Search: HNSW

**Rama:** `feat/rag-hnsw-index`
**Estado:** ✅ mergeado

### Qué se hizo

- Se detectó drift: no había ANN real creado por migraciones.
- Se agregó migración Alembic para crear **índice HNSW** sobre `chunks.embedding vector(768) NOT NULL`.
- Se agregó ADR y se alineó documentación de schema/tuning.
- Tests de integración (gated con `RUN_INTEGRATION=1`) para validar índice/plan.

### Resultado esperado

- Mejor recall/latencia en vector search sin tocar contratos de API.

---

## PR2 — Retrieval: Hybrid Search + RRF + Full-Text (ES)

**Rama:** `feat/rag-hybrid-rrf`
**Estado:** ✅ mergeado

### Qué se hizo

- DB: columna `tsv` (`tsvector`) + índice GIN para full-text.
- Infra: búsqueda sparse con `websearch_to_tsquery('spanish', ...)` + `ts_rank_cd`.
- Application: `RankFusionService` con RRF (k=60) puro, dedup determinístico.
- Pipeline: integración en `SearchChunksUseCase` y `AnswerQueryUseCase`.
- Feature flag: `ENABLE_HYBRID_SEARCH=false` (off por default).
- Fallback: si sparse falla → dense-only con warning.
- Tests unit para RRF e integración híbrida.
- ADR correspondiente.

### Resultado esperado

- Con `ENABLE_HYBRID_SEARCH=true`, mejora fuerte en queries con keywords exactas (IDs/siglas/nombres/errores).

---

## PR3 — Ingest/Storage: Content Dedup por workspace

**Rama:** `feat/rag-content-dedup`
**Estado:** ✅ listo y mergeado

### Qué se hizo

- DB: `documents.content_hash VARCHAR(64)` + índice único parcial `(workspace_id, content_hash) WHERE content_hash IS NOT NULL`.
- Utils puras: `normalize_text()` (NFC + strip + collapse whitespace), `compute_content_hash()`, `compute_file_hash()`.
- Use cases:
  - Ingest: dedup antes de ingestar + recuperación de race.
  - Upload: dedup antes de subir a storage.

- Métrica: `rag_dedup_hit_total`.
- ADR-013 + tests (26 nuevos).

### Notas

- Follow-up opcional: recovery de race también en upload + hashing streaming para archivos grandes.

---

## PR4 — Streaming: Hybrid en `/ask/stream` + limpieza

**Rama:** `feat/rag-stream-hybrid`
**Estado:** ✅ listo y mergeado

### Qué se hizo

- Se confirmó que `/ask/stream` ya componía `SearchChunksUseCase` → hereda hybrid automáticamente.
- Se eliminó `StreamAnswerQueryUseCase` (código muerto no cableado).
- Se agregó metadata `hybrid_used` en resultados.
- Métrica: `rag_hybrid_retrieval_total{endpoint}` instrumentada en `/ask` y `/ask/stream`.
- Tests (6): hybrid ON/OFF, fallback sparse, metadata.
- ADR-014.

---

## PR5 — Observabilidad: métricas por etapas del pipeline RAG

**Rama:** `feat/rag-observability-stages`
**Estado:** ✅ listo y mergeado

### Qué se hizo

- Nuevas métricas:
  - Histograms sin labels: `rag_dense_latency_seconds`, `rag_sparse_latency_seconds`, `rag_fusion_latency_seconds`, `rag_rerank_latency_seconds`.
  - Counter: `rag_retrieval_fallback_total{stage="sparse"|"rerank"}`.

- Instrumentación en `SearchChunksUseCase` y `AnswerQueryUseCase` con `perf_counter()`.
- Tests: exposición de series en `/metrics` + asserts de registro por caso.
- Docs: `observability.md` con tabla de métricas, PromQL y umbrales.
- Dashboard: fila/paneles para latencias sub-etapa + fallbacks.

---

## PR6 — Evaluación offline: harness + dataset dorado + CI informativa

**Rama:** `feat/rag-eval-harness`
**Estado:** ✅ listo y mergeado

### Qué se hizo

- Módulo `apps/backend/eval/` con métricas puras: MRR, Recall@k, Hit@1, NDCG@k (con tests).
- Dataset dorado: 15 docs + 30 queries (JSONL) con juicios de relevancia.
- Script standalone: `apps/backend/scripts/eval_rag.py` (sin DB), índice en memoria, reporte JSON.
- CI: workflow `eval.yml` (manual + trigger por paths) que sube artifact de reporte (no bloqueante).
- ADR-015 + doc `docs/quality/rag-evaluation.md`.

### Nota

- Follow-up opcional: unificar chunking del harness con el chunker real para mayor fidelidad.

---

## PR7 — 2-tier / Hierarchical retrieval (Nodes -> Chunks)

**Rama:** `feat/rag-hierarchical-2tier`
**Estado:** ✅ listo (merge recomendado)

### Qué se hizo

- Nueva capa 2-tier:
  - Ingest: genera “nodes” por documento (agrupación determinística) y embeddings.
  - Retrieval: primero busca nodes (coarse) y luego chunks dentro del subset (fine).
  - Graceful degradation: si nodes falla/vacío → fallback a retrieval estándar.

- DB: migración para tabla de nodes + índices (HNSW) + FKs con cascade.
- Tests: cubre flag OFF/ON, fallback, scoping, ranking coseno.
- ADR-016.

### Nota importante

- Con `ENABLE_2TIER_RETRIEVAL=true`, hoy bypass-ea Hybrid/FTS+RRF (trade-off aceptable como MVP).
  Follow-up sugerido: PR7.1 “2-tier + Hybrid fusion con RRF”.

---

## PR8 — FTS multi-idioma por workspace

**Rama:** `feat/rag-multilang-fts`
**Estado:** ✅ listo (merge recomendado)

### Qué se hizo

- `workspace.fts_language` con allowlist: `{spanish, english, simple}`.
- Seguridad triple:
  - Validador de dominio + allowlist.
  - DB CHECK constraint.
  - Cast `::regconfig` en queries.

- `chunks.tsv` pasa de GENERATED a columna regular (computada al insertar/actualizar en repo).
- Backward compatible: default `'spanish'` en workspaces existentes.
- Tests: dominio/config/app + integración (gated con `RUN_INTEGRATION=1`) por idioma y aislamiento cross-workspace.
- ADR-017.

### Nota operativa

- Migración hace backfill `UPDATE chunks SET tsv=...` (puede ser costosa en tablas enormes).
  Follow-up sugerido: PR8.1 backfill por batches/online.

---

## Checklist rápido post-merge (operación)

1. Activar en staging:
   - `ENABLE_HYBRID_SEARCH=true`

2. Probar query con keyword exacta rara → debería mejorar.
3. Probar dedup:
   - subir/ingestar mismo doc/texto 2 veces en mismo workspace → `rag_dedup_hit_total` incrementa.

4. Verificar observabilidad:
   - dashboards de Dense/Sparse/Fusion/Rerank p95/p99
   - `rag_retrieval_fallback_total` bajo control

5. Correr evaluación:
   - `python apps/backend/scripts/eval_rag.py --out reports/rag_eval_report.json`

---

## Follow-ups sugeridos (no bloqueantes)

- PR7.1: 2-tier + Hybrid (fusionar sparse con resultados de 2-tier vía RRF)
- PR8.1: backfill tsv por batches/online
- PR3.1: recovery de race en upload + hashing streaming para archivos grandes
- PR6.1: unificar chunking del harness con chunker real
