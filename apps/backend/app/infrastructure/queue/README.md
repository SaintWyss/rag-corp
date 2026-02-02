# Queue (RQ)

## 🎯 Misión
Implementar el adaptador de cola para encolar procesamiento de documentos con RQ, con configuración y validaciones fail‑fast.

**Qué SÍ hace**
- Encola jobs de procesamiento con RQ.
- Valida paths de jobs importables.
- Tipifica errores de configuración y enqueue.

**Qué NO hace**
- No ejecuta los jobs (eso lo hace el worker).
- No contiene lógica de negocio.

**Analogía (opcional)**
- Es la “bandeja de tareas” que pasa trabajos al taller (worker).

## 🗺️ Mapa del territorio
| Recurso | Tipo | Responsabilidad (en humano) |
| :--- | :--- | :--- |
| 🐍 `__init__.py` | Archivo Python | Facade del adaptador de cola. |
| 🐍 `errors.py` | Archivo Python | Errores tipados de cola. |
| 🐍 `import_utils.py` | Archivo Python | Validación de dotted paths importables. |
| 🐍 `job_paths.py` | Archivo Python | Paths y nombres de cola (constantes). |
| 📄 `README.md` | Documento | Esta documentación. |
| 🐍 `rq_queue.py` | Archivo Python | Adapter RQ para `DocumentProcessingQueue`. |

## ⚙️ ¿Cómo funciona por dentro?
Input → Proceso → Output:
- **Input**: `document_id` y `workspace_id` desde el caso de uso.
- **Proceso**: `RQDocumentProcessingQueue` valida config y encola job.
- **Output**: `job_id` o error tipado.

Tecnologías/librerías usadas aquí:
- rq, redis-py.

Flujo típico:
- `UploadDocumentUseCase` llama `enqueue_document_processing()`.
- El adapter valida `job_paths.PROCESS_DOCUMENT_JOB_PATH`.
- RQ encola el job en Redis.

## 🔗 Conexiones y roles
- Rol arquitectónico: Infrastructure Adapter (queue).
- Recibe órdenes de: Application (ingestion).
- Llama a: RQ/Redis.
- Contratos y límites: implementa `DocumentProcessingQueue` del dominio.

## 👩‍💻 Guía de uso (Snippets)
```python
from redis import Redis
from app.infrastructure.queue import RQDocumentProcessingQueue, RQQueueConfig

queue = RQDocumentProcessingQueue(
    redis=Redis.from_url("redis://localhost:6379"),
    config=RQQueueConfig(),
)
```

## 🧩 Cómo extender sin romper nada
- Si agregas un nuevo job, registra el dotted path en `job_paths.py`.
- Mantén la validación `is_importable_dotted_path` para fail‑fast.
- Documenta nuevos nombres de cola (ENV) si los agregas.

## 🆘 Troubleshooting
- Síntoma: `Job path no importable` → Causa probable: path inválido → Mirar `job_paths.py` y `app/worker/jobs.py`.
- Síntoma: enqueue falla → Causa probable: Redis no disponible → Revisar `REDIS_URL`.
- Síntoma: jobs no se procesan → Causa probable: worker apagado → Revisar `app/worker/worker.py`.

## 🔎 Ver también
- [Worker](../../worker/README.md)
- [Ingestion use cases](../../application/usecases/ingestion/README.md)
