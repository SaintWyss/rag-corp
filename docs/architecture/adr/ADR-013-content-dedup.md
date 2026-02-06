# ADR-013: Content Deduplication por Workspace (SHA-256)

## Estado

**Aceptado** (2026-02)

## Contexto

El sistema RAG Corp permite ingerir documentos (texto y archivos) en workspaces. Sin un mecanismo de deduplicación, el mismo contenido puede ingresarse múltiples veces en un workspace, causando:

1. **Contaminación del ranking**: chunks duplicados aparecen en los resultados de búsqueda, reduciendo diversidad y relevancia.
2. **Desperdicio de recursos**: embeddings duplicados consumen API calls, storage y espacio en la base de datos.
3. **Confusión del usuario**: documentos duplicados dificultan la gestión del workspace.

### Opciones evaluadas

| Opción                      | Pros                           | Contras                                         |
| --------------------------- | ------------------------------ | ----------------------------------------------- |
| Sin dedup (status quo)      | Simple                         | Duplicados, ranking contaminado                 |
| Dedup por título            | Muy simple                     | Títulos cambian, falsos positivos               |
| Dedup por hash MD5          | Rápido                         | Vulnerable a colisiones intencionales           |
| **Dedup por hash SHA-256**  | Seguro, determinístico, scoped | Columna extra (~64 bytes/row)                   |
| Dedup por similarity search | Detecta parafraseo             | Costoso, threshold arbitrario, falsos positivos |

## Decisión

Implementamos **deduplicación de contenido por workspace usando SHA-256**, con las siguientes reglas:

### Algoritmo de hash

- **Texto (ingest)**: `SHA-256(workspace_id + ":" + normalize(text))`
  - Normalización: NFC unicode, trim, collapse whitespace (NO lowercase — preserva case original)
- **Archivo (upload)**: `SHA-256(workspace_id + ":" + raw_bytes)`
  - Sin normalización (bytes son determinísticos)

### Scoping por workspace

El hash incluye `workspace_id` como prefijo, garantizando que el mismo contenido en workspaces distintos no sea considerado duplicado. Esto respeta el aislamiento de datos entre workspaces.

### Esquema

```sql
ALTER TABLE documents ADD COLUMN content_hash VARCHAR(64);

CREATE UNIQUE INDEX ix_documents_workspace_content_hash
ON documents (workspace_id, content_hash)
WHERE content_hash IS NOT NULL;
```

- **Nullable**: documentos existentes (pre-migration) no tienen hash. NULLs no colisionan en el partial unique index.
- **Partial unique index**: solo aplica a filas con `content_hash IS NOT NULL`.
- **VARCHAR(64)**: SHA-256 hex digest tiene exactamente 64 caracteres.

### Comportamiento idempotente

Cuando se detecta un duplicado:

1. Se busca el documento existente por `(workspace_id, content_hash)`.
2. Si existe: se retorna el documento existente sin crear duplicados, chunks, ni llamar APIs externas.
3. Si no existe: se procede con la ingesta normal, persistiendo el hash.

### Race condition

Si dos inserts concurrentes del mismo contenido compiten:

1. El primero gana el constraint único.
2. El segundo falla con `UniqueViolation`.
3. Se captura la excepción, se re-lee el documento existente por hash, y se retorna idempotentemente.

### Capas afectadas (Clean Architecture)

- **Domain**: `Document.content_hash` field + `DocumentRepository.get_document_by_content_hash()` protocol
- **Infrastructure**: columna SQL + partial unique index + repositorio Postgres
- **Application**: `content_hash.py` (pure utility) + dedup logic en `IngestDocumentUseCase` y `UploadDocumentUseCase`
- **Observabilidad**: counter Prometheus `rag_dedup_hit_total`

## Consecuencias

### Positivas

- **Previene duplicados**: mismo contenido en un workspace no se re-ingesta.
- **Idempotente**: operaciones de ingesta/upload son seguras para retry.
- **Backward compatible**: columna nullable, documentos existentes no se ven afectados.
- **Zero maintenance**: SHA-256 es determinístico, no requiere reindexing ni calibración.
- **Bajo costo**: hash computation ~negligible vs. embedding API call.
- **Observable**: counter de dedup hits permite monitorear frecuencia.

### Negativas

- **Columna extra**: ~64 bytes por fila en `documents` (despreciable).
- **No detecta parafraseo**: solo detecta contenido exacto (normalizado). Variantes del mismo texto con cambios menores no son detectadas.
- **Documentos legacy**: documentos pre-migration no tienen hash y no participan en dedup.

## Referencias

- [Migration 004](../../../apps/backend/alembic/versions/004_content_hash_dedup.py)
- [content_hash.py](../../../apps/backend/app/application/content_hash.py)
- [PostgreSQL Schema](../../reference/data/postgres-schema.md)
