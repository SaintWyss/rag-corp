# ADR-011: Migración de IVFFlat a HNSW para índice vectorial

## Estado

**Aceptado** (2026-02)

## Contexto

ADR-002 eligió IVFFlat (lists=100) como índice ANN para `chunks.embedding`. Tras evaluar el comportamiento en producción:

1. **Recall**: IVFFlat requiere tuning de `probes` y puede perder resultados relevantes si el número de listas no se ajusta al volumen real de datos.
2. **Mantenimiento**: IVFFlat necesita `REINDEX` periódico después de bulk inserts/deletes para mantener la calidad de los clusters. HNSW no tiene este problema.
3. **Volumen actual**: < 100K chunks. HNSW tiene mejor recall que IVFFlat en este rango sin trade-offs significativos de memoria.
4. **pgvector 0.5+**: HNSW está disponible y estable desde pgvector 0.5.0. RAG Corp usa pgvector 0.8.1.

## Decisión

Reemplazamos el índice IVFFlat por **HNSW** en `chunks.embedding`.

### Parámetros

| Parámetro         | Valor               | Razón                                                                                           |
| ----------------- | ------------------- | ----------------------------------------------------------------------------------------------- |
| `m`               | 16                  | Default pgvector. Conexiones por nodo en el grafo. Buen balance recall/memoria para < 1M filas. |
| `ef_construction` | 64                  | Default pgvector. Calidad de construcción. Suficiente para el volumen actual.                   |
| Operator class    | `vector_cosine_ops` | Consistente con ADR-002 (cosine distance).                                                      |

### Migración

```sql
-- Eliminar IVFFlat (si existe)
DROP INDEX IF EXISTS chunks_embedding_idx;

-- Crear HNSW
CREATE INDEX ix_chunks_embedding_hnsw
  ON chunks USING hnsw (embedding vector_cosine_ops)
  WITH (m = 16, ef_construction = 64);
```

Alembic: `002_hnsw_vector_index.py` (downgrade recrea IVFFlat con lists=100).

### Tuning en runtime

```sql
-- Aumentar ef_search para mejor recall (default 40)
SET hnsw.ef_search = 100;
```

A diferencia de IVFFlat (`probes`), HNSW solo tiene un knob de query-time: `ef_search`. Más alto = mejor recall, mayor latencia.

## Consecuencias

### Positivas

- **Mejor recall**: HNSW tiene recall superior a IVFFlat para el mismo nivel de latencia, especialmente con < 1M filas.
- **Sin mantenimiento periódico**: No requiere `REINDEX` para mantener calidad tras inserts/deletes.
- **Parámetros simples**: Solo `ef_search` en query-time (vs `probes` + `lists` en IVFFlat).
- **Backward compatible**: La query SQL (operador `<=>`, `ORDER BY ... LIMIT`) no cambia. Transparente para la capa de aplicación.

### Negativas

- **Build time**: HNSW es más lento de construir que IVFFlat para tablas muy grandes (> 1M filas). No aplica al volumen actual.
- **Memoria**: HNSW usa ~2-3x más memoria de índice que IVFFlat. Aceptable para el volumen actual.
- **Migración**: Requiere recrear el índice (downtime breve durante `CREATE INDEX`). Para DBs grandes en producción, usar `CREATE INDEX CONCURRENTLY` fuera de Alembic.

### Riesgos

| Riesgo                             | Probabilidad        | Mitigación                                                |
| ---------------------------------- | ------------------- | --------------------------------------------------------- |
| Build time largo en tablas grandes | Baja (< 100K filas) | `CREATE INDEX CONCURRENTLY` para producción               |
| Mayor uso de memoria               | Baja                | Monitorear `pg_relation_size('ix_chunks_embedding_hnsw')` |
| Regresión de latencia              | Muy baja            | Benchmark `EXPLAIN ANALYZE` antes/después                 |

### Rollback

```sql
DROP INDEX ix_chunks_embedding_hnsw;
CREATE INDEX chunks_embedding_idx
  ON chunks USING ivfflat (embedding vector_cosine_ops)
  WITH (lists = 100);
```

O vía Alembic: `alembic downgrade 001_foundation`.

## Referencias

- [pgvector HNSW](https://github.com/pgvector/pgvector#hnsw)
- [ADR-002: pgvector](./ADR-002-pgvector.md)
- Migración: `apps/backend/alembic/versions/002_hnsw_vector_index.py`
