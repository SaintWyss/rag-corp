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

- **Razón:** mantener Application testeable y desacoplada.
- **Impacto:** si el contenedor no inyecta dependencias, algunos casos de uso devuelven `SERVICE_UNAVAILABLE`.
* No expone endpoints HTTP.

- **Razón:** la capa *Interfaces* es la única dueña del transporte.
- **Impacto:** los routers solo delegan en estos casos de uso y mapean resultados/errores.

## 🗺️ Mapa del territorio

| Recurso | Tipo | Responsabilidad (en humano) |
| :------------------------------ | :------------- | :------------------------------------------------------------------------------------------------------------------------------------- |
| `__init__.py` | Archivo Python | Exporta casos de uso y DTOs de ingesta para imports estables. |
| `cancel_document_processing.py` | Archivo Python | “Destraba” documentos zombis: si está `PROCESSING`, lo pasa a `FAILED` con motivo (auditoría). |
| `get_document_status.py` | Archivo Python | Consulta liviana de status (polling): devuelve `status`, `file_name`, `error_message` e `is_ready`. |
| `ingest_document.py` | Archivo Python | Ingesta directa de **texto**: valida, chunking, embeddings (si hay chunks) y persistencia **atómica** documento+chunks. |
| `process_uploaded_document.py` | Archivo Python | Pipeline **asíncrono** para documentos subidos: lock a `PROCESSING`, download, extract, chunk, embed, persist chunks y `READY/FAILED`. |
| `reprocess_document.py` | Archivo Python | Reencola un documento existente: valida y transiciona a `PENDING`, luego enqueue (si falla, deja `FAILED`). |
| `upload_document.py` | Archivo Python | Upload de archivo: valida acceso, sube a storage, persiste metadata, setea `PENDING` y encola job. |
| `README.md` | Documento | Portada + guía de navegación de estos casos de uso. |

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

- si falla el enqueue: transiciona a `FAILED` y devuelve `SERVICE_UNAVAILABLE`.
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

- *Interfaces* (routers HTTP) para `upload`, `reprocess`, `status`, `cancel`.
- *Worker* (jobs) para `process_uploaded_document`.

* **Llama a (interno/externo):**

- Repositorios: `DocumentRepository`, `WorkspaceRepository`, `WorkspaceAclRepository`.
- Servicios/puertos: `FileStoragePort`, `DocumentProcessingQueue`, `EmbeddingService`, `DocumentTextExtractor`, `TextChunkerService`.
- Crosscutting: métricas de seguridad (`record_prompt_injection_detected`).

* **Reglas de límites (imports/ownership):**

- No importa implementaciones de infraestructura (S3/Redis/Postgres, etc.).
- Las dependencias se inyectan desde composición: `app/container.py` y (en worker) `app/worker/jobs.py`.
- El transporte (HTTP) solo adapta entrada/salida; este módulo no conoce FastAPI.

## 👩‍💻 Guía de uso (Snippets)
```python
# Por qué: muestra el contrato mínimo del módulo.
from app.container import get_upload_document_use_case
from app.application.usecases.ingestion.upload_document import UploadDocumentInput

use_case = get_upload_document_use_case()
use_case.execute(UploadDocumentInput(workspace_id="...", actor=None, title="Doc", file_name="a.pdf", mime_type="application/pdf", content=b"..."))
```

```python
# Por qué: ejemplo de integración sin infraestructura real.
from app.container import get_ingest_document_use_case
from app.application.usecases.ingestion.ingest_document import IngestDocumentInput

use_case = get_ingest_document_use_case()
use_case.execute(IngestDocumentInput(workspace_id="...", actor=None, title="Notas", text="...") )
```

```python
# Por qué: deja visible el flujo principal.
from app.application.usecases.ingestion import ProcessUploadedDocumentUseCase, ProcessUploadedDocumentInput
from app.container import get_document_repository, get_file_storage, get_document_text_extractor, get_text_chunker, get_embedding_service

use_case = ProcessUploadedDocumentUseCase(
    repository=get_document_repository(),
    storage=get_file_storage(),
    extractor=get_document_text_extractor(),
    chunker=get_text_chunker(),
    embedding_service=get_embedding_service(),
)
use_case.execute(ProcessUploadedDocumentInput(document_id="...", workspace_id="..."))
```

## 🧩 Cómo extender sin romper nada
- Si agregás un paso nuevo del pipeline, mantenelo en `process_uploaded_document.py` y reflejalo en `ingest_document.py` si aplica.
- Respetá idempotencia y lock lógico por status.
- Cableá dependencias nuevas en `app/container.py` y en `app/worker/jobs.py`.
- Tests: unit en `apps/backend/tests/unit/application/`, integration en `apps/backend/tests/integration/`, e2e si el flujo es completo.

## 🆘 Troubleshooting
- **Síntoma:** documento queda en `PENDING`.
- **Causa probable:** worker/cola no corren.
- **Dónde mirar:** `app/worker/README.md` y `infrastructure/queue`.
- **Solución:** levantar worker y validar `REDIS_URL`.
- **Síntoma:** `SERVICE_UNAVAILABLE` en upload.
- **Causa probable:** storage/queue no configurados.
- **Dónde mirar:** `app/container.py` (`get_file_storage`, `get_document_queue`).
- **Solución:** setear settings y reiniciar.
- **Síntoma:** `FAILED` por metadata faltante.
- **Causa probable:** `storage_key`/`mime_type` vacío.
- **Dónde mirar:** `upload_document.py`.
- **Solución:** revisar persistencia de metadata.
- **Síntoma:** `chunks_created=0` inesperado.
- **Causa probable:** extractor devolvió vacío.
- **Dónde mirar:** `infrastructure/parsers`.
- **Solución:** validar MIME y parser.

## 🔎 Ver también
- `../README.md`
- `../../../worker/README.md`
- `../../../infrastructure/storage/README.md`
- `../../../infrastructure/queue/README.md`
- `../../../infrastructure/text/README.md`
