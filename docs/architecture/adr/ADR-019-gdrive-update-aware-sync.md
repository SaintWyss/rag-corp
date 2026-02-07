# ADR-019: Google Drive Connector — Update-Aware Sync

## Estado

**Aceptado** (2026-02)

## Contexto

El conector de Google Drive (ADR-018) implementaba sincronización básica:

- Primera ejecución: ingestar todos los archivos encontrados.
- Ejecuciones posteriores: usar `cursor_json` (Changes API) para obtener deltas.

Sin embargo, el flujo original **solo impedía duplicados** pero no detectaba cambios:

- Si un archivo ya existía (mismo `external_source_id`), se skipeaba.
- Si el contenido del archivo cambió en Drive, RAG Corp mantenía la versión obsoleta.

### Problema

| Situación                | Comportamiento anterior | Impacto                      |
| ------------------------ | ----------------------- | ---------------------------- |
| Archivo editado en Drive | SKIP (no re-ingestado)  | Datos obsoletos (stale data) |
| Archivo renombrado       | SKIP                    | Título desactualizado        |
| Archivo reemplazado      | SKIP                    | Contenido incorrecto         |

### Opciones evaluadas

| Opción                               | Pros                             | Contras                      |
| ------------------------------------ | -------------------------------- | ---------------------------- |
| Ignorar cambios (status quo)         | Simplicidad                      | Datos obsoletos              |
| **Detección por modified_time/etag** | Detección robusta, bajo overhead | Requiere schema extra        |
| Siempre re-ingestar                  | Consistencia garantizada         | Costo alto (CPU, tokens LLM) |
| Versionado de documentos             | Historial completo               | Complejidad, storage         |

## Decisión

### 1. Detección de cambios (Change Detection)

Usamos metadata externa para detectar si un archivo cambió:

```
if document.external_etag != drive_file.etag:
    return CHANGED
elif document.external_modified_time != drive_file.modified_time:
    return CHANGED
else:
    return UNCHANGED
```

**Campos utilizados**:

- **`md5Checksum`** (preferido): Hash MD5 del contenido, reportado por Drive.
  - Solo disponible para archivos binarios (PDF, imágenes, etc.).
  - Google Docs, Sheets, Slides NO tienen `md5Checksum`.
- **`modifiedTime`** (fallback): Timestamp de última modificación.
  - Siempre disponible en todos los tipos de archivo.
  - Puede generar falsos positivos (ej: permisos, metadata).

### 2. Schema de metadata externa

Nueva migración `010_external_source_metadata` agrega columnas:

| Columna                    | Tipo         | Nullable | Propósito                                  |
| -------------------------- | ------------ | -------- | ------------------------------------------ |
| `external_source_provider` | VARCHAR(100) | YES      | Identificador del proveedor (google_drive) |
| `external_modified_time`   | TIMESTAMPTZ  | YES      | Timestamp de Drive                         |
| `external_etag`            | VARCHAR(500) | YES      | md5Checksum de Drive                       |
| `external_mime_type`       | VARCHAR(200) | YES      | MIME type reportado                        |

### 3. Flujo de sync (Update-Aware)

```
for file in delta.files:
    existing = document_repo.get_by_external_source_id(workspace_id, f"gdrive:{file.id}")

    if existing is None:
        ACTION = CREATE
        # Ingestar nuevo documento

    elif file_has_changed(existing, file):
        ACTION = UPDATE
        # 1. Borrar chunks y nodos anteriores
        # 2. Descargar contenido nuevo
        # 3. Actualizar metadata externa
        # 4. (Delegado a pipeline) Re-indexar chunks

    else:
        ACTION = SKIP_UNCHANGED
        # No hacer nada (idempotente)
```

### 4. Estrategia de UPDATE

**Enfoque MVP (Delete + Re-Insert)**:

1. Descargar contenido actualizado de Drive.
2. `delete_chunks_for_document(doc_id)` — Borrar vector chunks.
3. `delete_nodes_for_document(doc_id)` — Borrar nodos (2-tier retrieval).
4. `update_external_source_metadata()` — Guardar nueva metadata.
5. El documento mantiene el mismo `id` (no duplicar).

**Trade-offs**:

- ✅ Simple de implementar.
- ✅ Garantiza consistencia (sin chunks huérfanos).
- ❌ Costo de re-embedding (LLM tokens).
- ❌ Pérdida de historial (sin versioning).

### 5. Métricas de observabilidad

```prometheus
rag_connector_files_created_total      # Nuevos documentos
rag_connector_files_updated_total      # Documentos actualizados
rag_connector_files_skipped_unchanged_total  # Sin cambios (idempotencia)
```

### 6. Concurrencia

**Problema**: Si dos syncs corren en paralelo y modifican el mismo documento.

**Solución (MVP)**: Confiar en serialización a nivel de aplicación.

- Los syncs de un mismo source se ejecutan secuencialmente (worker queue).
- El use case usa transacciones para delete+insert atómico.

**Futuro (si es necesario)**: Optimistic locking con `version` o `updated_at`.

## Consecuencias

### Positivas

- Documentos se mantienen actualizados con la fuente externa.
- Idempotencia preservada: syncs repetidos sin cambios = no-op.
- Métricas permiten alertar sobre "stale data" o "excessive updates".
- Schema extensible para otros proveedores (OneDrive, Dropbox).

### Negativas

- Costo de re-embedding en updates frecuentes (mitigable con rate-limiting).
- Sin versionado: no hay rollback a versiones anteriores.
- `modifiedTime` puede generar falsos positivos (re-index innecesarios).

## Alternativas rechazadas

### Versionado de documentos

Mantener historial de versiones permitiría rollback y auditoría.
Rechazado por:

- Complejidad de schema (tabla `document_versions`).
- Storage multiplica con cada edición.
- No hay caso de uso claro para historial en MVP.

### Re-ingestar siempre

Forzar re-ingesta de todos los archivos en cada sync.
Rechazado por:

- Costo prohibitivo (LLM tokens, CPU).
- No escala con +1000 archivos.

## Riesgos

| Riesgo                                  | Probabilidad | Impacto           | Mitigación                            |
| --------------------------------------- | ------------ | ----------------- | ------------------------------------- |
| Falsos positivos (re-index innecesario) | Media        | Bajo (solo costo) | Priorizar etag sobre modified_time    |
| Sync concurrentes                       | Baja         | Medio             | Queue por source_id                   |
| Drive API rate limits                   | Media        | Medio             | Backoff exponencial (ya implementado) |
| Datos obsoletos si sync falla           | Media        | Alto              | Alertas en métricas, retry automático |

## Referencias

- ADR-018: Google Drive OAuth Token Storage
- ADR-001: Clean Architecture
- [Google Drive API: Files Resource](https://developers.google.com/drive/api/v3/reference/files)
- [Google Drive Changes API](https://developers.google.com/drive/api/v3/reference/changes)
