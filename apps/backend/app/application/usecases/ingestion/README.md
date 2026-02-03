# ingestion
Como una **línea de producción**: convierte archivos o texto en chunks + embeddings.

## 🎯 Misión
Este módulo agrupa los casos de uso de ingesta: upload, procesamiento asíncrono, ingesta directa de texto, reprocesamiento y consulta de estado.

### Qué SÍ hace
- Aplica policy de acceso al workspace.
- Encola procesamiento cuando corresponde (RQ).
- Ejecuta pipeline async: download → extract → chunk → embed → persist.
- Maneja transiciones de status (`PENDING/PROCESSING/READY/FAILED`).

### Qué NO hace (y por qué)
- No implementa storage/queue/embeddings concretos.
  - Razón: se usa puertos del dominio.
  - Consecuencia: el adapter se inyecta desde `container.py`.
- No expone HTTP.
  - Razón: el transporte vive en `interfaces/`.
  - Consecuencia: routers solo adaptan y delegan.

## 🗺️ Mapa del territorio
| Recurso | Tipo | Responsabilidad (en humano) |
| :-- | :-- | :-- |
| `README.md` | Documento | Guía del bounded context Ingestion. |
| `__init__.py` | Archivo Python | Exports públicos de ingesta. |
| `upload_document.py` | Archivo Python | Upload + persistencia + enqueue. |
| `process_uploaded_document.py` | Archivo Python | Pipeline async de procesamiento. |
| `ingest_document.py` | Archivo Python | Ingesta directa de texto. |
| `reprocess_document.py` | Archivo Python | Reencola y transiciona estado. |
| `cancel_document_processing.py` | Archivo Python | Cancela procesamiento en curso. |
| `get_document_status.py` | Archivo Python | Consulta de estado para polling. |

## ⚙️ ¿Cómo funciona por dentro?
Input → Proceso → Output.

- **Upload**
  - Valida acceso, sube a storage y deja status `PENDING`.
  - Encola el job con `DocumentProcessingQueue`.
- **Process (worker)**
  - Obtiene lock lógico (`PROCESSING`) y aplica idempotencia.
  - Extrae texto, chunking, embeddings y persistencia de chunks.
  - Transiciona a `READY` o `FAILED` con error truncado.
- **Ingest directo**
  - Procesa texto en memoria y persiste documento + chunks.

## 🔗 Conexiones y roles
- **Rol arquitectónico:** Application (ingesta).
- **Recibe órdenes de:** routers HTTP (upload/status/reprocess) y worker (process).
- **Llama a:** `DocumentRepository`, `FileStoragePort`, `DocumentTextExtractor`, `TextChunkerService`, `EmbeddingService`, `DocumentProcessingQueue`.
- **Reglas de límites:** sin SQL ni SDKs directos; errores tipados `DocumentError`.

## 👩‍💻 Guía de uso (Snippets)
```python
from app.container import get_upload_document_use_case
from app.application.usecases.ingestion.upload_document import UploadDocumentInput

use_case = get_upload_document_use_case()
use_case.execute(UploadDocumentInput(workspace_id="...", actor=None, title="Doc", file_name="a.pdf", mime_type="application/pdf", content=b"..."))
```

```python
from app.container import get_ingest_document_use_case
from app.application.usecases.ingestion.ingest_document import IngestDocumentInput

use_case = get_ingest_document_use_case()
use_case.execute(IngestDocumentInput(workspace_id="...", actor=None, title="Notas", text="...") )
```

```python
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
