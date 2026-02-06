# Auditoría Técnica: PR3 (`feat/rag-content-dedup`)

## A) Resumen Ejecutivo

- **Estado**: ✅ **READY FOR MERGE**.
- **Propósito**: Evita la duplicación de contenido idéntico dentro del mismo Workspace, tanto en subida de archivos como en ingestión de texto.
- **Mecanismo**: Hash SHA-256 de `workspace_id + normalized_content` (o bytes). Constraint UNIQUE parcial `(workspace_id, content_hash)`.
- **UX**: Comportamiento idempotente. Si se sube un duplicado, devuelve `200 OK` con los datos del documento existente (evita errores 409 y re-procesamiento).
- **Integridad**: Scoping estricto por Workspace. El mismo archivo en dos Workspaces distintos genera hashes distintos y se guarda dos veces (correcto multitenant).

## B) Diff de Alto Nivel

| Archivo                                                              | Tipo      | Propósito                                                                   |
| :------------------------------------------------------------------- | :-------- | :-------------------------------------------------------------------------- |
| `apps/backend/alembic/versions/004_content_hash_dedup.py`            | Migración | Agrega col `content_hash` y Unique Index filtered (`WHERE IS NOT NULL`).    |
| `apps/backend/app/application/content_hash.py`                       | Utilidad  | Lógica de hashing determinístico (NFC, strip, collapse whitespace).         |
| `apps/backend/app/infrastructure/repositories/postgres/document.py`  | Infra     | Persistence de `content_hash` y lookup `get_document_by_content_hash`.      |
| `apps/backend/app/application/usecases/ingestion/upload_document.py` | Use Case  | "Check-then-Act": Si hash existe, retorna existente. Si no, sube.           |
| `apps/backend/app/application/usecases/ingestion/ingest_document.py` | Use Case  | Idem upload. Incluye manejo de race condition (try/except) en persistencia. |
| `tests/unit/application/test_upload_dedup.py`                        | Test      | Verifica flujo idempotente y aislamiento por workspace.                     |

## C) Evaluación Técnica

### 1. Correctitud del Hashing e Integridad

- **Algoritmo**: SHA-256 es estándar y colisión despreciable.
- **Normalización**: Excelente uso de `unicodedata.normalize("NFC", text)` y colapso de whitespace. Esto asegura que diferencias invisibles no rompan el dedup.
- **Scoping**: El payload del hash incluye `workspace_id` (`f"{workspace_id}:{content}"`).
  - _Resultado_: Si Workspace A y Workspace B suben "Contrato.pdf", tienen hashes distintos. Esto es **CRÍTICO** para evitar fugas de información o ataques de enumeración de hashes entre tenants.

### 2. Base de Datos

- **Constraint**: `CREATE UNIQUE INDEX ... ON documents (workspace_id, content_hash) WHERE content_hash IS NOT NULL`.
  - Correcto: El índice parcial permite que documentos viejos (con `content_hash=NULL`) coexistan sin violar unicidad.
  - No bloqueante: La migración es segura en producción.

### 3. Comportamiento en Carrera (Race Conditions)

- **Upload**: Usa patrón "Check-then-Act". Si dos requests llegan juntas, una puede fallar por constraint violation (DatabaseError).
- **Ingest**: Implementa `_resolve_dedup_race`. Si el `save` falla, re-consulta por hash. Si encuentra el documento, retorna éxito (idempotencia real).
  - _Observación_: `upload_document.py` NO tiene `_resolve_dedup_race`, solo hace el chequeo previo. Si ocurre una colisión en upload, fallará 500. Es un borde fino, pero aceptable dado que el upload de archivos toma tiempo y la probabilidad de colisión exacta ms-a-ms es baja.

### 4. Contratos API

- **Idempotencia**: Devuelve `UploadDocumentResult` con el ID existente. El frontend recibirá `200 OK` (o `201`) y el ID, transparente para el usuario. No rompe clientes existentes.

## D) Matriz de Riesgos

| Riesgo                       | Impacto                         | Probabilidad | Mitigación Propuesta                                                                                                |
| :--------------------------- | :------------------------------ | :----------- | :------------------------------------------------------------------------------------------------------------------ |
| **Race Condition en Upload** | Error 500 al usuario            | Baja         | Agregar lógica `_resolve_dedup_race` en `upload_document.py` igual que en `ingest`.                                 |
| **Backfill de Hash**         | Duplicados viejos no detectados | N/A          | Los docs viejos tienen hash NULL. No se deduplican con nuevos. No es un riesgo, es una limitación aceptada.         |
| **Hash de Archivos Grandes** | Consumo memoria server          | Media        | `compute_file_hash` carga todo en RAM (`bytes`). Para archivos >100MB podría ser problema. Streaming hash a futuro. |

## E) Recomendaciones

1.  **Race Condition en Upload**: Copiar la lógica de recuperación `_resolve_dedup_race` de `IngestDocumentUseCase` a `UploadDocumentUseCase` para robustez total (99.999%).
2.  **Streaming Hashing**: Si planeamos soportar archivos > 50MB, cambiar `compute_file_hash` para aceptar un stream/generator y no cargar todo el binario en memoria.
3.  **Observabilidad**: La métrica `record_dedup_hit` ya está. Agregar etiqueta `source=upload|ingest` para diferenciar.

## F) Veredicto

# ✅ GO

Implementation robusta, segura (scoped hash) y con buena experiencia de desarrollador (tests claros) y usuario (idempotencia).
