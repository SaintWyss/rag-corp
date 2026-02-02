# Infra: Task Queue (Async Jobs)

## 🎯 Misión

Permite encolar tareas para ser procesadas en background por los Workers.
Desacopla la recepción de la tarea de su ejecución inmediata.

**Qué SÍ hace:**

- Encola jobs en Redis Queue (RQ).
- Define helpers para importar funciones de jobs dinámicamente.

**Qué NO hace:**

- No ejecuta los jobs (eso lo hace el `app.worker`).

## 🗺️ Mapa del territorio

| Recurso           | Tipo       | Responsabilidad (en humano)                                      |
| :---------------- | :--------- | :--------------------------------------------------------------- |
| `errors.py`       | 🐍 Archivo | Errores de encolado.                                             |
| `import_utils.py` | 🐍 Archivo | Helpers para cargar módulos por path string (necesario para RQ). |
| `job_paths.py`    | 🐍 Archivo | Constantes con los strings de importación de los jobs.           |
| `rq_queue.py`     | 🐍 Archivo | Implementación concreta usando `rq`.                             |

## ⚙️ ¿Cómo funciona por dentro?

Usa `redis` y `rq`.
Cuando la aplicación llama a `enqueue`, serializa los argumentos con `pickle` y los guarda en una lista de Redis.

## 🔗 Conexiones y roles

- **Rol Arquitectónico:** Infrastructure Adapter.
- **Llama a:** Redis.

## 👩‍💻 Guía de uso (Snippets)

### Encolar un trabajo

```python
from app.infrastructure.queue.rq_queue import RQQueue
from app.infrastructure.queue.job_paths import INGEST_DOC_JOB

queue = RQQueue(redis_conn)
job_id = queue.enqueue(
    job_name=INGEST_DOC_JOB,
    params={"doc_id": "123"}
)
```

## 🧩 Cómo extender sin romper nada

1.  **Nuevos Jobs:** Si creas un nuevo job en `app.worker.jobs`, registra su path en `job_paths.py` para evitar hardcoding de strings.

## 🆘 Troubleshooting

- **Síntoma:** `job not found`.
  - **Causa:** El worker no tiene el código actualizado o el path del job cambió.

## 🔎 Ver también

- [Worker Entrypoint (Consumidor)](../../worker/README.md)
