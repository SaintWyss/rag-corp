# ingestion

Como una **línea de producción**: recibe un archivo o texto y lo transforma en **chunks + embeddings** listos para búsqueda.

## 🎯 Misión

Este módulo agrupa los **casos de uso de ingesta** (capa *Application*) para convertir contenido en “conocimiento buscable” dentro de un workspace.

Recorridos rápidos por intención:

* **Quiero subir un archivo y que se procese** → `upload_document.py` (persist + storage + enqueue) + `process_uploaded_document.py` (worker)
* **Quiero ingerir texto ya disponible (sin storage/queue)** → `ingest_document.py`
* **Quiero ver estado para polling/UI** → `get_document_status.py`
* **Quiero reprocesar o destrabar un documento** → `reprocess_document.py` / `cancel_document_processing.py`

### Qué SÍ hace

* Aplica **política de acceso al workspace** (read/write) de forma centralizada.
* Maneja el flujo de **upload**: sube el archivo, persiste metadata y **encola** el procesamiento.
* Ejecuta el pipeline asíncrono de procesamiento: **download → extract → chunk → embed → persist chunks**.
* Expone operaciones de **reprocesamiento**, **cancelación** (recuperación) y **consulta de estado**.
* Mantiene transiciones de status **PENDING/PROCESSING/READY/FAILED** con reglas de concurrencia (lock lógico).

### Qué NO hace (y por qué)

* No define implementaciones concretas de **storage/cola/embeddings/extractor**: usa puertos/servicios del dominio.

  * **Razón:** mantener Application testeable y desacoplada.
  * **Impacto:** si el contenedor no inyecta dependencias, algunos casos de uso devuelven `SERVICE_UNAVAILABLE`.
* No expone endpoints HTTP.

  * **Razón:** la capa *Interfaces* es la única dueña del transporte.
  * **Impacto:** los routers solo delegan en estos casos de uso y mapean resultados/errores.

## 🗺️ Mapa del territorio

| Recurso                         | Tipo           | Responsabilidad (en humano)                                                                                                            |
| :------------------------------ | :------------- | :------------------------------------------------------------------------------------------------------------------------------------- |
| `__init__.py`                   | Archivo Python | Exporta casos de uso y DTOs de ingesta para imports estables.                                                                          |
| `cancel_document_processing.py` | Archivo Python | “Destraba” documentos zombis: si está `PROCESSING`, lo pasa a `FAILED` con motivo (auditoría).                                         |
| `get_document_status.py`        | Archivo Python | Consulta liviana de status (polling): devuelve `status`, `file_name`, `error_message` e `is_ready`.                                    |
| `ingest_document.py`            | Archivo Python | Ingesta directa de **texto**: valida, chunking, embeddings (si hay chunks) y persistencia **atómica** documento+chunks.                |
| `process_uploaded_document.py`  | Archivo Python | Pipeline **asíncrono** para documentos subidos: lock a `PROCESSING`, download, extract, chunk, embed, persist chunks y `READY/FAILED`. |
| `reprocess_document.py`         | Archivo Python | Reencola un documento existente: valida y transiciona a `PENDING`, luego enqueue (si falla, deja `FAILED`).                            |
| `upload_document.py`            | Archivo Python | Upload de archivo: valida acceso, sube a storage, persiste metadata, setea `PENDING` y encola job.                                     |
| `README.md`                     | Documento      | Portada + guía de navegación de estos casos de uso.                                                                                    |

## ⚙️ ¿Cómo funciona por dentro?

Input → Proceso → Output, con flujos reales del código.

### 1) Upload de archivo (comando)

* **Input:** `UploadDocumentInput`.
* **Proceso:**

  1. `resolve_workspace_for_write(...)` (policy de escritura).
  2. valida que **storage** y **queue** existan (no `None`).
  3. genera `document_id` + `storage_key = documents/{document_id}/{file_name}`.
  4. sube bytes a storage **antes** de tocar DB (evita metadata apuntando a un key inexistente).
  5. persiste `Document` + metadata del archivo y deja status `PENDING`.
  6. encola `enqueue_document_processing(document_id, workspace_id)`.

     * si falla el enqueue: transiciona a `FAILED` y devuelve `SERVICE_UNAVAILABLE`.
* **Output:** `UploadDocumentResult` con `document_id`, `status`, `file_name`, `mime_type` o `error` tipado.

### 2) Procesamiento asíncrono (worker)

* **Input:** `ProcessUploadedDocumentInput`.
* **Proceso:**

  1. carga `Document` scoped por workspace; si no existe → `MISSING`.
  2. idempotencia: si `READY` o `PROCESSING` → devuelve ese status.
  3. lock lógico: transición atómica a `PROCESSING` desde `[None, PENDING, FAILED]`.
  4. valida `storage` y metadata obligatoria (`storage_key`, `mime_type`).
  5. `download_file(storage_key)` → `extract_text(mime_type, bytes)`.
  6. chunking (`TextChunkerService.chunk`).
  7. borra chunks previos (`delete_chunks_for_document`) y guarda nuevos.
  8. embeddings batch **solo si hay chunks**; valida longitud 1:1.
  9. detección de prompt injection por chunk: agrega metadata y registra métricas.
  10. transición a `READY` o, ante excepción, a `FAILED` con `error_message` truncado.
* **Output:** `ProcessUploadedDocumentOutput(status, chunks_created)`.

### 3) Ingesta directa de texto (comando)

* **Input:** `IngestDocumentInput`.
* **Proceso:** valida `workspace_id` y `title`, aplica policy de escritura, chunking; si no hay chunks **no llama embeddings**; persiste documento+chunks en una operación atómica (`save_document_with_chunks`).
* **Output:** `IngestDocumentResult(document_id, chunks_created)` o `error`.

### 4) Reprocesar / Cancelar / Consultar estado

* **Reprocess:** si no está `PROCESSING`, transiciona a `PENDING` y encola; si falla el enqueue, deja `FAILED`.
* **Cancel:** solo permite cancelar si está `PROCESSING` (si no, `CONFLICT`).
* **Status:** consulta mínima para polling; no devuelve el documento completo.

## 🔗 Conexiones y roles

* **Rol arquitectónico:** *Application* (casos de uso).

* **Recibe órdenes de:**

  * *Interfaces* (routers HTTP) para `upload`, `reprocess`, `status`, `cancel`.
  * *Worker* (jobs) para `process_uploaded_document`.

* **Llama a (interno/externo):**

  * Repositorios: `DocumentRepository`, `WorkspaceRepository`, `WorkspaceAclRepository`.
  * Servicios/puertos: `FileStoragePort`, `DocumentProcessingQueue`, `EmbeddingService`, `DocumentTextExtractor`, `TextChunkerService`.
  * Crosscutting: métricas de seguridad (`record_prompt_injection_detected`).

* **Reglas de límites (imports/ownership):**

  * No importa implementaciones de infraestructura (S3/Redis/Postgres, etc.).
  * Las dependencias se inyectan desde composición: `app/container.py` y (en worker) `app/worker/jobs.py`.
  * El transporte (HTTP) solo adapta entrada/salida; este módulo no conoce FastAPI.

## 👩‍💻 Guía de uso (Snippets)

### 1) Upload desde runtime (container)

```python
from uuid import UUID

from app.application.usecases.ingestion.upload_document import UploadDocumentInput
from app.container import get_upload_document_use_case
from app.domain.workspace_policy import WorkspaceActor
from app.identity.users import UserRole

workspace_id = UUID("00000000-0000-0000-0000-000000000000")  # workspace existente
actor = WorkspaceActor(user_id=UUID("11111111-1111-1111-1111-111111111111"), role=UserRole.ADMIN)

use_case = get_upload_document_use_case()
result = use_case.execute(
    UploadDocumentInput(
        workspace_id=workspace_id,
        actor=actor,
        title="Manual",
        file_name="manual.pdf",
        mime_type="application/pdf",
        content=b"%PDF-1.4...",
    )
)

if result.error:
    raise RuntimeError(result.error.message)
print(result.document_id, result.status)
```

### 2) Ingesta directa de texto (sin storage/queue)

```python
from uuid import UUID

from app.application.usecases.ingestion.ingest_document import IngestDocumentInput
from app.container import get_ingest_document_use_case
from app.domain.workspace_policy import WorkspaceActor
from app.identity.users import UserRole

use_case = get_ingest_document_use_case()
result = use_case.execute(
    IngestDocumentInput(
        workspace_id=UUID("00000000-0000-0000-0000-000000000000"),
        actor=WorkspaceActor(user_id=UUID("11111111-1111-1111-1111-111111111111"), role=UserRole.ADMIN),
        title="Notas",
        text="Contenido ya disponible en memoria...",
        metadata={"tags": ["clase"], "allowed_roles": ["employee"]},
    )
)

print(result.document_id, result.chunks_created)
```

### 3) Polling de estado (UI / integración)

```python
from uuid import UUID

from app.application.usecases.ingestion.get_document_status import (
    GetDocumentProcessingStatusInput,
    GetDocumentProcessingStatusUseCase,
)
from app.container import (
    get_document_repository,
    get_workspace_repository,
    get_workspace_acl_repository,
)
from app.domain.workspace_policy import WorkspaceActor
from app.identity.users import UserRole

use_case = GetDocumentProcessingStatusUseCase(
    document_repository=get_document_repository(),
    workspace_repository=get_workspace_repository(),
    acl_repository=get_workspace_acl_repository(),
)

result = use_case.execute(
    GetDocumentProcessingStatusInput(
        workspace_id=UUID("00000000-0000-0000-0000-000000000000"),
        document_id=UUID("22222222-2222-2222-2222-222222222222"),
        actor=WorkspaceActor(user_id=UUID("11111111-1111-1111-1111-111111111111"), role=UserRole.EMPLOYEE),
    )
)

print(result.status, result.is_ready)
```

### 4) Procesamiento desde el worker (patrón de job)

```python
from app.application.usecases.ingestion import ProcessUploadedDocumentInput, ProcessUploadedDocumentUseCase
from app.container import (
    get_document_repository,
    get_document_text_extractor,
    get_embedding_service,
    get_file_storage,
    get_text_chunker,
)

use_case = ProcessUploadedDocumentUseCase(
    repository=get_document_repository(),
    storage=get_file_storage(),
    extractor=get_document_text_extractor(),
    chunker=get_text_chunker(),
    embedding_service=get_embedding_service(),
)

# Nota: en RQ, document_id/workspace_id suelen venir como strings serializados.
output = use_case.execute(ProcessUploadedDocumentInput(document_id=doc_id, workspace_id=ws_id))
print(output.status, output.chunks_created)
```

## 🧩 Cómo extender sin romper nada

Checklist práctico:

1. **Elegí el punto del pipeline**:

   * Nuevo paso solo para uploads → `process_uploaded_document.py`.
   * Nuevo paso también para ingesta directa → `ingest_document.py`.
2. **Mantené concurrencia/idempotencia**:

   * respetá el lock lógico (`transition_document_status` a `PROCESSING`).
   * no reproceses si ya está `READY`.
3. **Mantené cotas de seguridad/robustez**:

   * mensajes de error acotados (ver truncado en `process_uploaded_document.py`).
   * si agregás metadata por chunk, mantenela pequeña (evita payloads enormes).
4. **Cableá dependencias**:

   * runtime: `app/container.py` (getters / settings / feature flags).
   * worker: `app/worker/jobs.py` (builder del use case).
5. **Testea donde corresponde**:

   * unit: use cases con doubles (storage/queue/embeddings).
   * integration: repos + DB.
   * e2e: flujo HTTP → enqueue → worker → polling (si aplica en el repo).

## 🆘 Troubleshooting

* **Upload devuelve `SERVICE_UNAVAILABLE`** → storage/queue no inyectados → mirar `app/container.py` (`get_file_storage()`, `get_document_queue()`) → configurar settings y reiniciar servicios.
* **Documento queda en `PENDING` y nunca pasa a `PROCESSING`** → worker no consume la cola / RQ no corre → mirar `app/worker/README.md` y logs del worker → levantar worker y verificar conexión a Redis.
* **Documento queda “zombie” en `PROCESSING`** → el worker murió en medio del job → usar `CancelDocumentProcessingUseCase` (pasa a `FAILED`) → luego `ReprocessDocumentUseCase`.
* **`FAILED` con “Missing file metadata for processing”** → documento sin `storage_key`/`mime_type` → mirar `upload_document.py` + persistencia `update_document_file_metadata(...)` → verificar migraciones/DB.
* **`FAILED` con “Embedding batch size mismatch”** → `EmbeddingService.embed_batch` devuelve cantidad distinta → revisar implementación en infraestructura y límites de batch → agregar test que valide 1 embedding por chunk.
* **`chunks_created = 0` pero esperabas contenido** → extractor devolvió vacío (MIME incorrecto o parser) → mirar `DocumentTextExtractor` (infra/text) + `mime_type` persistido → probar con otro tipo de archivo.

## 🔎 Ver también

* `../README.md` (índice de casos de uso)
* `../../../worker/README.md` (jobs y ejecución asíncrona)
* `../../../infrastructure/storage/README.md` (implementaciones de `FileStoragePort`)
* `../../../infrastructure/queue/README.md` (implementaciones de `DocumentProcessingQueue`)
* `../../../infrastructure/text/README.md` (extractores/parsers de texto)
* `../../../crosscutting/README.md` (métricas/logs/tracing)
