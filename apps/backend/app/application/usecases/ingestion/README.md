# Feature: Document Ingestion

## 🎯 Misión

Este módulo gestiona el ciclo de vida de **Ingesta**: desde que el usuario sube un archivo hasta que está listo para ser buscado (indexado).
Es un proceso complejo y asíncrono.

**Qué SÍ hace:**

- Recibe subidas de archivos (Upload).
- Inicia el procesamiento en background (Encolar tarea).
- Consulta el estado (Polling status).
- Permite cancelar o reprocesar.

**Qué NO hace:**

- No hace el parsing del PDF (lo delega a Infra/Parsers).
- No hace el embedding (lo delega a Infra/Services).
- Solo **ORQUESTA** estos pasos.

**Analogía:**
Es la Oficina de Admisiones. Recibe los papeles, les pone un sello "Pendiente", y los manda a las oficinas de atrás (Workers) para que los lean y archiven.

## 🗺️ Mapa del territorio

| Recurso                         | Tipo       | Responsabilidad (en humano)                                            |
| :------------------------------ | :--------- | :--------------------------------------------------------------------- |
| `cancel_document_processing.py` | 🐍 Archivo | Detiene un proceso atascado.                                           |
| `get_document_status.py`        | 🐍 Archivo | Consulta progreso (ej. 45% completado).                                |
| `ingest_document.py`            | 🐍 Archivo | **Worker Logic**. La lógica real del Worker (Parse -> Chunk -> Embed). |
| `process_uploaded_document.py`  | 🐍 Archivo | Encola la tarea después del upload.                                    |
| `reprocess_document.py`         | 🐍 Archivo | Fuerza re-ingesta de un doc existente.                                 |
| `upload_document.py`            | 🐍 Archivo | Guarda el binario en Storage y crea el registro DB inicial.            |

## ⚙️ ¿Cómo funciona por dentro?

### Pipeline de Ingesta (Happy Path)

1.  **Upload:** `UploadDocumentUseCase` guarda bytes en S3/MinIO y crea `Document(status=PENDING)`.
2.  **Enqueue:** `ProcessUploadedDocument` manda job a Redis Queue.
3.  **Worker:** El Worker ejecuta `IngestDocumentUseCase.execute()`.
    - Descarga de S3.
    - Extrae texto (ParserService).
    - Genera Chunks (Chunker).
    - Genera Embeddings (EmbeddingService).
    - Guarda en DB (DocumentRepository).
    - Actualiza status a `READY`.

## 🔗 Conexiones y roles

- **Rol Arquitectónico:** Use Cases (Ingestion Feature).
- **Colabora con:** `FileStorage`, `QueueService`, `ParserService`.

## 👩‍💻 Guía de uso (Snippets)

### Subir un archivo

```python
use_case = UploadDocumentUseCase(storage, doc_repo)
doc = use_case.execute(
    file_stream=my_file,
    filename="factura.pdf",
    workspace_id=ws_id
)
# doc.status es PENDING
```

## 🧩 Cómo extender sin romper nada

1.  **Nuevos formatos:** Si quieres soportar `.docx`, registra el parser en Infraestructura, la orquestación aquí suele ser agnóstica.
2.  **Pasos extra:** Si quieres agregar un paso de "Resumen" post-ingesta, agrégalo al flujo de `ingest_document.py`.

## 🆘 Troubleshooting

- **Síntoma:** El documento se queda en `PROCESSING` por siempre.
  - **Causa:** El worker murió o dio error silencioso. Revisa logs del container `worker`.
  - **Solución:** `CancelDocumentProcessingUseCase` para desbloquear.

## 🔎 Ver también

- [Infraestructura de Texto/Parsers](../../../infrastructure/parsers/README.md)
