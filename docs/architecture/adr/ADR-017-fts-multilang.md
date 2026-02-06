# ADR-017: FTS Multi-idioma (Per-Workspace Language)

## Estado

**Aceptado** (2026-02)

## Contexto

El full-text search (FTS) del sistema estaba hardcoded a `'spanish'`:

- La columna `chunks.tsv` era `GENERATED ALWAYS AS (to_tsvector('spanish', content)) STORED`.
- Las queries usaban `websearch_to_tsquery('spanish', ...)`.

Esto funciona para workspaces en español, pero impide buscar correctamente en otros idiomas: PostgreSQL necesita el regconfig correcto para stemming, stop words, y normalización.

### Opciones evaluadas

| Opcion                                 | Pros                        | Contras                                                                 |
| -------------------------------------- | --------------------------- | ----------------------------------------------------------------------- |
| Config global (`FTS_LANGUAGE_DEFAULT`) | Simple, un solo valor       | No permite workspaces multi-idioma                                      |
| Trigger PostgreSQL                     | Transparente a la app       | Complejidad oculta, difícil de testear                                  |
| GENERATED con función custom           | Automático en INSERT        | GENERATED no soporta expresiones que varían por fila                    |
| **Per-workspace `fts_language`**       | Flexible, explícito, seguro | Migration destructiva para tsv, requiere reprocessing al cambiar idioma |

## Decisión

Implementamos **per-workspace FTS language** con allowlist estricta:

### Modelo

- Columna `workspaces.fts_language VARCHAR(20) NOT NULL DEFAULT 'spanish'`.
- Constraint: `CHECK (fts_language IN ('spanish', 'english', 'simple'))`.
- Domain: `FTS_ALLOWED_LANGUAGES = frozenset({"spanish", "english", "simple"})` + `validate_fts_language()` con fallback a `"spanish"`.

### Columna `tsv` (regular, no GENERATED)

La columna `chunks.tsv` pasa de GENERATED a regular. Se computa en la capa de aplicación durante INSERT:

```sql
INSERT INTO chunks (..., tsv)
VALUES (..., to_tsvector(%s::regconfig, coalesce(%s, '')))
```

Motivo: `GENERATED ALWAYS AS` no puede variar por fila — todas las filas deben usar la misma expresión. Con columna regular, cada workspace puede tener su idioma.

### Seguridad (doble barrera)

1. **DB CHECK constraint**: PostgreSQL rechaza valores fuera del allowlist.
2. **Domain validator**: `validate_fts_language()` sanitiza cualquier input antes de llegar a SQL.
3. **`%s::regconfig` cast**: PostgreSQL valida el regconfig. Si la allowlist fuera bypaseada, el cast falla con error SQL (no inyección).

### Ingesta (zero cambio de firma)

El repository hace lookup interno del `fts_language` del workspace (`_lookup_workspace_fts_language`) al inicio de `save_chunks` / `save_document_with_chunks`. Los use cases de ingesta no necesitan cambios.

### Search path

Los use cases de búsqueda (`SearchChunksUseCase`, `AnswerQueryUseCase`) ya obtienen el workspace via `resolve_workspace_for_read`. Extraen `workspace.fts_language` y lo pasan a `find_chunks_full_text(fts_language=...)`.

### Feature flag

- `FTS_LANGUAGE_DEFAULT=spanish` en config (default global, documentación).
- Per-workspace override via columna `fts_language`.
- Sin flag habilitado = comportamiento idéntico al anterior (todos los workspaces usan `'spanish'`).

## Consecuencias

### Positivas

- FTS funciona correctamente para workspaces en inglés y español.
- Extensible: agregar idiomas solo requiere ampliar allowlist + CHECK constraint.
- Backward compatible: default `'spanish'`, zero cambio para workspaces existentes.
- Seguridad: triple barrera (allowlist + CHECK + regconfig cast).

### Negativas

- Migration destructiva para `tsv`: DROP columna GENERATED + recrear como regular + backfill.
- Cambiar `fts_language` de un workspace NO reindexea chunks existentes automáticamente.
- Requiere reprocessing de documentos para actualizar `tsv` al cambiar idioma.

### Mitigaciones

- Backfill en migration con `to_tsvector('spanish'::regconfig, ...)` para datos existentes.
- `validate_fts_language(None)` retorna `"spanish"` — nunca falla.
- El allowlist `simple` da una opción language-agnostic (no stemming) para workspaces mixtos.
