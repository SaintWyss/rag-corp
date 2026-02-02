# Worker RQ

## 🎯 Misión
Implementar el proceso worker que consume jobs de RQ para tareas pesadas (procesamiento de documentos) y exponer health/readiness/metrics del worker.

**Qué SÍ hace**
- Ejecuta jobs RQ (ej. `process_document_job`).
- Inicializa Redis y pool de DB en el proceso worker.
- Expone health/readiness/metrics con un HTTP server liviano.

**Qué NO hace**
- No expone la API HTTP de negocio (eso vive en `app/api/`).
- No contiene reglas de negocio; solo orquesta el caso de uso correspondiente.

**Analogía (opcional)**
- Es el “taller” que ejecuta trabajos pesados fuera de la API principal.

## 🗺️ Mapa del territorio
| Recurso | Tipo | Responsabilidad (en humano) |
| :--- | :--- | :--- |
| 🐍 `jobs.py` | Archivo Python | Entrypoints de jobs RQ (procesamiento de documentos). |
| 📄 `README.md` | Documento | Esta documentación. |
| 🐍 `worker.py` | Archivo Python | Entrypoint del proceso worker (arranque y loop RQ). |
| 🐍 `worker_health.py` | Archivo Python | Health/readiness del worker (DB + Redis). |
| 🐍 `worker_server.py` | Archivo Python | HTTP server mínimo para health/ready/metrics. |

## ⚙️ ¿Cómo funciona por dentro?
Input → Proceso → Output:
- **Input**: job en cola RQ con `document_id` + `workspace_id`.
- **Proceso**: `worker.py` crea Worker RQ; `jobs.py` valida UUIDs y ejecuta el use case.
- **Output**: actualización de estado del documento, chunks persistidos, métricas.

Tecnologías/librerías usadas aquí:
- rq, redis, psycopg (health), http.server (health/metrics).

Flujo típico:
- `worker.py` inicializa Redis y pool DB.
- `process_document_job()` ejecuta `ProcessUploadedDocumentUseCase`.
- `worker_server.py` sirve `/healthz`, `/readyz` y `/metrics`.

## 🔗 Conexiones y roles
- Rol arquitectónico: Infrastructure Adapter (worker runtime).
- Recibe órdenes de: RQ (jobs en Redis).
- Llama a: `app/application/usecases/ingestion`, `app/container`, `app/infrastructure/*`.
- Contratos y límites: el job no conoce detalles HTTP; solo usa casos de uso y puertos.

## 👩‍💻 Guía de uso (Snippets)
```python
from app.worker.worker_health import readiness_payload

status = readiness_payload()
assert "db" in status and "redis" in status
```

## 🧩 Cómo extender sin romper nada
- Define un nuevo job en `jobs.py` con firma simple (strings serializables).
- Asegura que el job construye el caso de uso vía `app.container`.
- Registra el path del job en `app/infrastructure/queue/job_paths.py`.
- Actualiza tests de integración si el job toca DB/cola.

## 🆘 Troubleshooting
- Síntoma: worker no inicia → Causa probable: `REDIS_URL` faltante → Mirar `worker.py`.
- Síntoma: `/readyz` devuelve `db: disconnected` → Causa probable: `DATABASE_URL` → Mirar `.env`.
- Síntoma: `/metrics` 403 → Causa probable: `metrics_require_auth` → Mirar `app/crosscutting/config.py`.

## 🔎 Ver también
- [Ingestion use cases](../application/usecases/ingestion/README.md)
- [Queue adapter](../infrastructure/queue/README.md)
- [Crosscutting metrics](../crosscutting/metrics.py)
