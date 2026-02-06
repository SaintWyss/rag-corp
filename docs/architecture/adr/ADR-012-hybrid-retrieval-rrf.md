# ADR-012: Hybrid Retrieval (Dense + Sparse) con Reciprocal Rank Fusion

## Estado

**Aceptado** (2026-02)

## Contexto

El sistema RAG de RAG Corp usa exclusivamente búsqueda vectorial (dense retrieval) con pgvector para recuperar chunks relevantes. Esto funciona bien para queries semánticos ("¿cómo funciona el sistema de autenticación?") pero presenta limitaciones con queries que contienen keywords exactos:

1. **Nombres propios**: "Acme Corporation" puede ser semánticamente lejano al embedding de un chunk que lo menciona textualmente.
2. **IDs y códigos**: "REQ-2024-001" o "CAS-456" no tienen representación semántica útil.
3. **Siglas y acrónimos**: "SLA", "KPI", "CUIT" pueden perderse en dense retrieval.

PostgreSQL ofrece full-text search nativo (`tsvector` + `ts_rank_cd`) con GIN indexes, lo cual permite agregar un canal de sparse retrieval sin dependencias externas.

### Opciones evaluadas

| Opción                   | Pros                         | Contras                        |
| ------------------------ | ---------------------------- | ------------------------------ |
| Solo dense (status quo)  | Simple, un canal             | Pierde keywords exactos        |
| Elasticsearch/OpenSearch | FTS maduro                   | Nueva dependencia operativa    |
| PostgreSQL tsvector      | Nativo, sin deps extra, ACID | Menos features que ES          |
| BM25 custom (Python)     | Control total                | Reinventar la rueda, sin index |

## Decisión

Implementamos **hybrid retrieval** combinando:

1. **Dense retrieval**: búsqueda vectorial existente (pgvector cosine distance)
2. **Sparse retrieval**: PostgreSQL full-text search (`tsvector` + `websearch_to_tsquery` + `ts_rank_cd`)
3. **Reciprocal Rank Fusion (RRF)**: algoritmo de fusión de rankings (Cormack et al., 2009)

### Diseño por capas (Clean Architecture)

- **Domain**: `DocumentRepository` protocol extendido con `find_chunks_full_text()`
- **Infrastructure**: columna `tsv` generada en `chunks` + GIN index + implementación SQL
- **Application**: `RankFusionService` (puro, sin IO) + integración en use cases
- **Config**: feature flags `ENABLE_HYBRID_SEARCH` y `RRF_K`

### Migración

```sql
-- Columna tsvector generada (zero-maintenance: se actualiza con el contenido)
ALTER TABLE chunks ADD COLUMN tsv tsvector
  GENERATED ALWAYS AS (to_tsvector('spanish', coalesce(content, ''))) STORED;

-- GIN index para búsqueda eficiente
CREATE INDEX ix_chunks_tsv ON chunks USING gin (tsv);
```

Alembic: `003_fts_tsvector_column.py`.

### Algoritmo RRF

```
score(d) = Σ 1/(k + rank_i(d))  para cada ranker i
```

- `k = 60` (constante estándar del paper, configurable via `RRF_K`)
- Deduplicación por `chunk_id` (fallback: `(document_id, chunk_index)`)
- Preserva la primera aparición del chunk para metadata consistente

### Feature Flags

| Variable               | Default | Descripción                   |
| ---------------------- | ------- | ----------------------------- |
| `ENABLE_HYBRID_SEARCH` | `false` | Activa sparse retrieval + RRF |
| `RRF_K`                | `60`    | Constante k del algoritmo RRF |

### Graceful Degradation

- Si sparse retrieval falla (ej: query vacío para tsquery), se usa solo dense (log warning).
- Si `ENABLE_HYBRID_SEARCH=true` pero no se inyecta `RankFusionService`, se usa solo dense.
- El feature flag permite rollback instantáneo sin deploy.

## Consecuencias

### Positivas

- **Mejor recall en keywords**: queries con nombres, IDs, siglas, ahora matchean por texto exacto además de semántica.
- **Sin dependencias externas**: PostgreSQL nativo, sin Elasticsearch/Solr.
- **ACID**: la columna `tsv` es generada y consistente con inserts/updates.
- **Zero-maintenance**: `GENERATED ALWAYS AS ... STORED` se actualiza automáticamente.
- **Rollback instantáneo**: feature flag `ENABLE_HYBRID_SEARCH=false` desactiva sin migración.
- **Backward compatible**: API response schema no cambia. Hybrid off por default.

### Negativas

- **Latencia adicional**: una query SQL extra (FTS) por request cuando hybrid está habilitado (~5-15ms).
- **GIN index storage**: ~10-20% del tamaño de la tabla `chunks` (aceptable).
- **Idioma hardcodeado**: `to_tsvector('spanish', ...)` — requiere migración para cambiar idioma.
- **Write overhead**: columna generada STORED agrega costo a INSERTs (~5%).

### Riesgos

| Riesgo                   | Probabilidad | Mitigación                                                                    |
| ------------------------ | ------------ | ----------------------------------------------------------------------------- |
| GIN index impacta writes | Baja         | Benchmark INSERT con/sin index. GIN es append-only.                           |
| FTS en español subóptimo | Media        | `websearch_to_tsquery` soporta operadores. Evaluar `unaccent` si se necesita. |
| RRF k=60 no óptimo       | Baja         | Configurable via env var. Default 60 es estándar del paper.                   |
| Latencia p95 > 500ms     | Baja         | Queries en serie por ahora. Paralelizar si se observa impacto.                |

## Validación

- **Unit tests**: `test_rank_fusion.py` (15 tests: fórmula RRF, dedup, edge cases)
- **Unit tests**: `test_hybrid_search.py` (10 tests: feature flags, fallback, fusión)
- **Criterio de aceptación**: query "Acme Corporation" con documentos que contienen esa frase debe rankear alto con hybrid habilitado.

## Referencias

- Cormack, G. V., Clarke, C. L., & Buettcher, S. (2009). Reciprocal rank fusion outperforms condorcet and individual rank learning methods. _SIGIR '09_.
- [PostgreSQL Full-Text Search](https://www.postgresql.org/docs/16/textsearch.html)
- [ADR-002: pgvector](./ADR-002-pgvector.md)
- [ADR-011: HNSW index](./ADR-011-hnsw-vector-index.md)
- Migración: `apps/backend/alembic/versions/003_fts_tsvector_column.py`
