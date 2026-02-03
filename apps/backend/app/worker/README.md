# worker
Como un **taller**: consume jobs de RQ y ejecuta tareas pesadas fuera de la API, con health/ready/metrics propios.

## 🎯 Misión

Este módulo implementa el **runtime del worker** basado en RQ: levanta un proceso que consume jobs desde Redis (por ejemplo, procesamiento de documentos) y expone endpoints livianos para **health**, **readiness** y **metrics**.

Recorridos rápidos por intención:

- **Quiero ver qué jobs existen y cómo se invocan** → `jobs.py`
- **Quiero entender cómo arranca y consume la cola** → `worker.py`
- **Quiero diagnosticar DB/Redis** → `worker_health.py` y endpoints `/healthz`/`/readyz`
- **Quiero ver el server HTTP de observabilidad** → `worker_server.py`
- **Quiero ver el pipeline que ejecuta** → `../application/usecases/ingestion/README.md`

### Qué SÍ hace

- Consume jobs de RQ (Redis) y ejecuta entrypoints definidos en `jobs.py`.
- Inicializa dependencias runtime necesarias en el proceso worker (Redis + pool de DB).
- Expone un HTTP server mínimo para `/healthz`, `/readyz` y `/metrics`.
- Orquesta casos de uso (Application) sin meter reglas de negocio dentro del worker.

### Qué NO hace (y por qué)

- No expone la API HTTP de negocio. Razón: ** la API vive en _Interfaces_ (routers FastAPI). Impacto: ** este módulo solo sirve observabilidad del worker; no maneja endpoints de producto.

- No contiene reglas de negocio. Razón: ** la lógica pertenece a _Application/Domain_. Impacto: ** agregar un job nuevo implica delegar a un use case (y cablear en el container), no escribir lógica ad‑hoc acá.

## 🗺️ Mapa del territorio

| Recurso | Tipo | Responsabilidad (en humano) |
| :----------------- | :------------- | :----------------------------------------------------------------------------------------- |
| `jobs.py` | Archivo Python | Entrypoints de jobs RQ: validan inputs serializables y delegan a casos de uso. |
| `worker.py` | Archivo Python | Entrypoint del proceso worker: configura conexión Redis, crea `rq.Worker` y entra al loop. |
| `worker_health.py` | Archivo Python | Checks de DB/Redis para readiness; arma payloads de diagnóstico simples. |
| `worker_server.py` | Archivo Python | HTTP server mínimo para `/healthz`, `/readyz` y `/metrics` (observabilidad). |
| `README.md` | Documento | Portada + guía de navegación del runtime del worker. |

## ⚙️ ¿Cómo funciona por dentro?

Input → Proceso → Output, con pasos reales del runtime.

### 1) Consumo de jobs (RQ)

- **Input:** un job en Redis con parámetros serializables (generalmente strings): `document_id`, `workspace_id`.
- **Proceso:**
  1. `worker.py` lee settings (ej. `REDIS_URL`, `DATABASE_URL`).
  2. Inicializa Redis client/connection usada por RQ.
  3. Inicializa el pool/conexión de DB para que los jobs puedan persistir estado.
  4. Crea `rq.Worker(queues=...)` y comienza el loop de consumo.
  5. Al ejecutar un job, RQ llama la función definida en `jobs.py`.

### 2) Ejecución de un job (ej. procesamiento de documento)

- **Input:** `process_document_job(document_id: str, workspace_id: str, ...)`.
- **Proceso:**
  1. `jobs.py` valida/partea UUIDs (fail‑fast).
  2. Construye el caso de uso vía `app.container` (inyección de puertos/servicios).
  3. Ejecuta `ProcessUploadedDocumentUseCase.execute(...)`.
  4. El use case actualiza status del documento y persiste chunks/embeddings.
  5. Registra métricas (si están habilitadas).

- **Output:**
- Cambios persistidos (status/chunks/embeddings) y logs/metrics del job.

### 3) Observabilidad del worker (HTTP liviano)

- **Input:** request HTTP a `/healthz`, `/readyz` o `/metrics`.
- **Proceso:** `worker_server.py` responde con payloads simples:
- `/healthz`: proceso vivo.
- `/readyz`: DB + Redis OK (usa `worker_health.py`).
- `/metrics`: métricas (si están habilitadas y autorizadas).

- **Output:** status code + body JSON/text.

Conceptos en contexto:

- **RQ:** cola simple sobre Redis; serializa parámetros del job.
- **Readiness:** “puedo trabajar” (dependencias listas), distinto de “estoy vivo”.

## 🔗 Conexiones y roles

- **Rol arquitectónico:** Operational runtime / Infrastructure adapter (ejecución de jobs).

- **Recibe órdenes de:**
- Redis/RQ (jobs encolados).

- **Llama a:**
- Application: `app/application/usecases/ingestion` (pipeline real).
- Composition: `app/container.py` (builders / dependencias).
- Infrastructure: repositorios, storage, embeddings, extractores (inyectados).
- Crosscutting: métricas/logs/config.

- **Reglas de límites (contratos):**
- Los jobs reciben solo tipos serializables (strings, ints, bools).
- Ningún job implementa negocio: delega a un use case.
- Los paths de jobs deben ser estables para el enqueuer (ver `job_paths.py`).

## 👩‍💻 Guía de uso (Snippets)
```python
# Por qué: muestra el contrato mínimo del módulo.
from app.worker.worker_health import readiness_payload
status = readiness_payload()
```

```python
# Por qué: ejemplo de integración sin infraestructura real.
from app.worker.jobs import process_document_job
process_document_job(document_id="...", workspace_id="...")
```

```python
# Por qué: deja visible el flujo principal.
from app.worker.worker_server import serve
serve(host="0.0.0.0", port=8081)
```

## 🧩 Cómo extender sin romper nada
- Definí el job en `jobs.py` con validación fail-fast.
- Registrá el path en `app/infrastructure/queue/job_paths.py`.
- Delegá a un use case de Application.
- Cableá dependencias en `app/container.py`.
- Tests: unit en `apps/backend/tests/unit/worker/`, integration si usa Redis/DB.

## 🆘 Troubleshooting
- **Síntoma:** `REDIS_URL es requerido`.
- **Causa probable:** variable ausente.
- **Dónde mirar:** `.env` / settings.
- **Solución:** setear `REDIS_URL`.
- **Síntoma:** `/readyz` reporta DB/Redis disconnected.
- **Causa probable:** servicios caídos.
- **Dónde mirar:** `worker_health.py` y logs.
- **Solución:** levantar servicios y reintentar.
- **Síntoma:** jobs en cola no se procesan.
- **Causa probable:** worker escucha otra cola.
- **Dónde mirar:** `DOCUMENT_QUEUE_NAME` y `worker.py`.
- **Solución:** alinear nombres de cola.
- **Síntoma:** job falla por UUID inválido.
- **Causa probable:** enqueue con strings mal formadas.
- **Dónde mirar:** adapter de cola.
- **Solución:** validar inputs antes de encolar.

## 🔎 Ver también
- `../application/usecases/ingestion/README.md`
- `../infrastructure/queue/README.md`
- `../crosscutting/README.md`
