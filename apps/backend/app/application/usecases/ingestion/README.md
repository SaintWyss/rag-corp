# Use Cases: Ingestion

## 🎯 Misión
Gestionar la ingesta de documentos: upload, procesamiento asíncrono, re‑procesamiento y consulta de estado.

**Qué SÍ hace**
- Sube archivos y encola su procesamiento.
- Procesa documentos: descarga, extracción, chunking y embeddings.
- Reintenta/reprocesa documentos y expone estado.

**Qué NO hace**
- No define storage ni cola concretos (usa puertos del dominio).
- No expone endpoints HTTP.

**Analogía (opcional)**
- Es la “línea de producción” que transforma archivos en conocimiento buscable.

## 🗺️ Mapa del territorio
| Recurso | Tipo | Responsabilidad (en humano) |
| :--- | :--- | :--- |
| 🐍 `__init__.py` | Archivo Python | Exports de casos de uso de ingesta. |
| 🐍 `cancel_document_processing.py` | Archivo Python | Cancelar procesamiento en curso (si aplica). |
| 🐍 `get_document_status.py` | Archivo Python | Obtener estado de procesamiento. |
| 🐍 `ingest_document.py` | Archivo Python | Ingesta sin upload (texto ya disponible). |
| 🐍 `process_uploaded_document.py` | Archivo Python | Pipeline asíncrono: extract → chunk → embed. |
| 📄 `README.md` | Documento | Esta documentación. |
| 🐍 `reprocess_document.py` | Archivo Python | Reprocesar documentos existentes. |
| 🐍 `upload_document.py` | Archivo Python | Upload + persistencia + enqueue. |

## ⚙️ ¿Cómo funciona por dentro?
Input → Proceso → Output:
- **Input**: `UploadDocumentInput` o `ProcessUploadedDocumentInput`.
- **Proceso**: policy de workspace → storage/queue → extracción → chunking → embeddings.
- **Output**: `UploadDocumentResult` o `ProcessUploadedDocumentOutput` con status.

Tecnologías/librerías usadas aquí:
- dataclasses/typing; I/O via puertos (storage, queue, embeddings).

Flujo típico:
- `UploadDocumentUseCase` guarda metadata y encola job.
- `ProcessUploadedDocumentUseCase` corre en worker y genera chunks/embeddings.
- `ReprocessDocumentUseCase` fuerza el pipeline nuevamente.

## 🔗 Conexiones y roles
- Rol arquitectónico: Application (Use Cases).
- Recibe órdenes de: Interfaces HTTP y Worker.
- Llama a: FileStoragePort, DocumentProcessingQueue, EmbeddingService, DocumentTextExtractor.
- Contratos y límites: sin storage/queue concretos; usa puertos del dominio.

## 👩‍💻 Guía de uso (Snippets)
```python
from uuid import uuid4
from app.application.usecases.ingestion.upload_document import UploadDocumentInput
from app.container import get_upload_document_use_case

use_case = get_upload_document_use_case()
result = use_case.execute(
    UploadDocumentInput(
        workspace_id=uuid4(),
        actor=None,
        title="Manual",
        file_name="manual.pdf",
        mime_type="application/pdf",
        content=b"%PDF-1.4...",
    )
)
```

## 🧩 Cómo extender sin romper nada
- Mantén el pipeline idempotente (chequeos de status en `process_uploaded_document`).
- Usa `DocumentErrorCode` para errores tipados y consistentes.
- Si agregas un paso nuevo (p. ej. OCR), hazlo en `process_uploaded_document.py`.
- Actualiza métricas si cambia el flujo (ver `crosscutting/metrics.py`).

## 🆘 Troubleshooting
- Síntoma: `SERVICE_UNAVAILABLE` en upload → Causa probable: storage/queue no configurados → Mirar `upload_document.py`.
- Síntoma: documento queda en PROCESSING → Causa probable: job falló → Mirar logs del worker.
- Síntoma: chunks = 0 → Causa probable: extractor devolvió texto vacío → Mirar `DocumentTextExtractor`.

## 🔎 Ver también
- [Worker jobs](../../../worker/README.md)
- [Infrastructure storage](../../../infrastructure/storage/README.md)
- [Infrastructure queue](../../../infrastructure/queue/README.md)
