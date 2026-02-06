# ADR-016: 2-Tier Hierarchical Retrieval (Nodes → Chunks)

## Estado

**Aceptado** (2026-02)

## Contexto

El pipeline de retrieval actual opera a nivel de chunks individuales. Para documentos largos con múltiples secciones, este enfoque puede perder contexto de sección: chunks relevantes de una misma sección pueden quedar dispersos en el ranking, y la búsqueda carece de una señal de "relevancia temática" a nivel macro.

### Opciones evaluadas

| Opcion                                      | Pros                                                  | Contras                                                       |
| ------------------------------------------- | ----------------------------------------------------- | ------------------------------------------------------------- |
| Single-tier chunks (status quo)             | Simple, funcional, zero overhead                      | Pierde contexto de sección, chunks dispersos                  |
| Chunks más grandes                          | Más contexto por chunk                                | Pierde granularidad, embeddings menos precisos                |
| LLM summarization por sección              | Resúmenes semánticos de alta calidad                  | No determinístico, costoso, rompe CI con fake embeddings      |
| **Nodos determinísticos (concatenación)**   | Determinístico, sin costo API extra, feature-flagged  | Concatenación naïve, no captura jerarquía semántica real      |

## Decisión

Implementamos **retrieval jerárquico 2-tier** con nodos determinísticos:

### Nodos (Secciones)

- Cada nodo agrupa N chunks consecutivos (`node_group_size`, default: 5).
- `node_text` = concatenación del contenido de los chunks, truncado a `node_text_max_chars` (default: 2000).
- Embedding generado via `embed_batch()` (compatible con `FakeEmbeddingService`).
- `span_start` / `span_end` definen el rango de `chunk_index` cubierto.

### Flujo de Retrieval

1. **Coarse**: `find_similar_nodes(embedding, node_top_k)` → top nodos por cosine distance.
2. **Fine**: `find_chunks_by_node_spans(spans)` → chunks dentro de los spans de nodos seleccionados.
3. **Ranking**: Cosine similarity en Python puro (sin numpy) entre query embedding y chunk embeddings.
4. **Fallback**: Si no hay nodos → retrieval dense estándar (backward compatible).

### Feature Flag

- `ENABLE_2TIER_RETRIEVAL=false` (default) → zero cambio en comportamiento.
- Flag controlado via `Settings` y pasado a use cases por DI.

### Ingesta

- Si flag ON: `build_nodes()` se ejecuta después de chunk creation.
- Nodos se persisten atómicamente con documento+chunks (`save_document_with_chunks`).
- Fallo en node generation es graceful: log warning, ingesta continúa sin nodos.

### Tabla `nodes`

```sql
CREATE TABLE nodes (
    id UUID PRIMARY KEY,
    workspace_id UUID NOT NULL REFERENCES workspaces(id) ON DELETE CASCADE,
    document_id UUID NOT NULL REFERENCES documents(id) ON DELETE CASCADE,
    node_index INTEGER NOT NULL,
    node_text TEXT NOT NULL,
    span_start INTEGER NOT NULL,
    span_end INTEGER NOT NULL,
    embedding vector(768) NOT NULL,
    metadata JSONB NOT NULL DEFAULT '{}',
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
```

Con índice HNSW (m=16, ef_construction=64) para búsqueda vectorial.

## Consecuencias

### Positivas

- Retrieval con señal de contexto de sección, improving precision para documentos multi-sección.
- Backward compatible: flag OFF = zero cambio.
- Determinístico: reproducible en CI con `FakeEmbeddingService`.
- Graceful degradation: fallo en nodos no bloquea ingesta ni retrieval.
- Pure Python cosine similarity: sin dependencia de numpy para ranking tier-2.

### Negativas

- +1 tabla en PostgreSQL (`nodes`), +1 embedding por nodo en ingesta.
- Concatenación naïve: nodos no capturan jerarquía semántica real del documento.
- Overhead de storage: cada documento genera ~N/group_size nodos adicionales.

### Mitigaciones

- Flag OFF por default: solo se activa cuando se valida mejora en métricas.
- `node_group_size` y `node_text_max_chars` son configurables.
- El eval harness (ADR-015) permite medir impacto cuantitativamente.
