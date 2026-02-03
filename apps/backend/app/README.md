# app

Pensá este paquete como el **motor armado** del backend: reglas internas, cableado de dependencias y dos llaves de arranque (API y worker).

## 🎯 Misión

Este paquete contiene **todo el runtime** del backend: la arquitectura por capas, los puntos de entrada, el cableado de dependencias, los adaptadores a servicios externos y los assets versionados (prompts/policy). Si necesitás entender “qué corre” cuando levantás el backend, empezás acá.

Recorridos rápidos por intención:

- **Quiero entender la arquitectura por capas (Clean Architecture)** → `application/`, `domain/`, `infrastructure/`, `interfaces/`
- **Quiero saber cómo se levanta la API y qué endpoints existen** → `api/` y `interfaces/api/http/` (entrypoint estable: `main.py`)
- **Quiero entender el worker y la cola de documentos** → `worker/` (jobs estables: `jobs.py`)
- **Quiero ubicar seguridad (API keys, JWT, RBAC)** → `identity/`
- **Quiero ubicar observabilidad (logs, request_id, métricas, rate limit)** → `crosscutting/` y `context.py`
- **Quiero entender prompts/policies (versionado + loader)** → `prompts/` y `infrastructure/prompts/`

### Qué SÍ hace

- Implementa Clean Architecture con límites claros:
  - `domain/`: reglas/contratos estables.
  - `application/`: casos de uso (orquestación).
  - `infrastructure/`: IO real (DB/Redis/S3/LLM/parsers).
  - `interfaces/`: adaptación de entrada (HTTP/DTOs).

- Expone **entrypoints estables**:
  - `app.main:app` (ASGI) para correr la API.
  - `app.api.main.fastapi_app` (FastAPI) para tests.
  - `app.jobs.process_document_job` (job) para RQ.

- Centraliza el cableado en `container.py` con DI manual y singletons con cache.
- Estandariza errores (RFC7807), contexto (request_id), métricas y límites (body/rate limit).

### Qué NO hace (y por qué)

- No contiene scripts de repo/CI ni tooling operativo.
  - **Razón:** mezclar runtime con tooling genera imports cruzados y side‑effects difíciles de reproducir.
  - **Impacto:** el tooling vive fuera (`apps/backend/`) y el runtime queda importable sin sorpresas.

- No contiene tests.
  - **Razón:** tests dependen del runtime; el runtime nunca depende de tests.
  - **Impacto:** los tests consumen entrypoints estables (`app.api.main.fastapi_app`, `app.main:app`).

- No define el “estado del entorno” (red/containers/volúmenes) como infraestructura completa.
  - **Razón:** este paquete describe el **software**; el entorno se configura afuera (compose/infra) para ser sustituible.
  - **Impacto:** cambiar compose/infra no fuerza cambios en el código del runtime.

## 🗺️ Mapa del territorio

| Recurso           | Tipo           | Responsabilidad (en humano)                                                                                                     |
| :---------------- | :------------- | :------------------------------------------------------------------------------------------------------------------------------ |
| `api/`            | Carpeta        | Composición FastAPI: crea la app, define lifespan, registra middlewares, routers y endpoints operativos.                        |
| `application/`    | Carpeta        | Casos de uso: orquesta flujos (RAG chat, ingesta, workspaces, documentos).                                                      |
| `audit.py`        | Archivo Python | Auditoría best‑effort: construye y registra eventos sin romper el flujo si falla la persistencia.                               |
| `container.py`    | Archivo Python | Composition root: DI manual (DIP), selección de adapters (prod/test), singletons con `lru_cache`.                               |
| `context.py`      | Archivo Python | Contexto request/job con `ContextVar`: request_id, tracing ids, método/path (correlación de logs).                              |
| `crosscutting/`   | Carpeta        | Preocupaciones transversales: config, logging, errores RFC7807, métricas, rate limiting, middlewares.                           |
| `domain/`         | Carpeta        | Dominio puro: entidades, value objects, puertos (repos/services) y reglas estables.                                             |
| `identity/`       | Carpeta        | Seguridad: API keys (scopes), JWT, principal unificado, RBAC/permisos y policy checks.                                          |
| `infrastructure/` | Carpeta        | Adaptadores salientes: DB Postgres/pgvector, cola Redis/RQ, storage S3/MinIO, parsers, servicios LLM/embeddings, prompts infra. |
| `interfaces/`     | Carpeta        | Adaptadores entrantes: HTTP (routers), schemas Pydantic, mapping request/response hacia Application.                            |
| `jobs.py`         | Archivo Python | Re-export de jobs con import path estable (RQ encola por string).                                                               |
| `main.py`         | Archivo Python | Entrypoint ASGI estable: re-export de `app` sin side-effects (lo ejecuta `uvicorn`).                                            |
| `prompts/`        | Carpeta        | Assets Markdown (policy + templates versionados) consumidos por el loader.                                                      |
| `worker/`         | Carpeta        | Proceso worker: bootstrap, health/readiness, server HTTP mínimo y ejecución de jobs.                                            |
| `README.md`       | Documento      | Portada/índice del paquete `app/` (este archivo).                                                                               |

## ⚙️ ¿Cómo funciona por dentro?

### 1) Puntos de entrada estables

Este repo evita entrypoints frágiles: los paths que usa runtime deben ser **estables**.

- **API (ASGI):** `app.main:app`
  - `main.py` re-exporta la app real desde `api/main.py` sin side-effects.

- **FastAPI para tests:** `app.api.main.fastapi_app`
  - Expone una instancia FastAPI “pura” para tests.

- **Jobs RQ:** `app.jobs.process_document_job`
  - El job vive en `worker/jobs.py` pero se re-exporta desde `app/jobs.py` para estabilidad.

### 2) API HTTP: FastAPI sobre ASGI

- `api/main.py` compone la app y define `lifespan` para inicializar/cerrar recursos.
- Middlewares típicos: límites de body (anti‑OOM), headers de seguridad, contexto request_id, CORS y rate limit (habilitable por settings).
- Routers: negocio bajo `/v1` y alias `/api/v1` para compatibilidad.
- Endpoints operativos: `/healthz`, `/readyz`, `/metrics`.

### 3) Worker: jobs asíncronos (RQ + Redis)

- `worker/worker.py` inicializa Redis y DB antes de consumir jobs.
- `worker/jobs.py` valida inputs (fail‑fast), arma el use case desde el container y ejecuta.
- Observabilidad: request_id = job_id, métricas y limpieza de contexto al finalizar.

### 4) DI manual y composición: `container.py`

- Los casos de uso dependen de **puertos** del Domain.
- `container.py` elige implementaciones concretas según Settings.
- Recursos pesados como singletons por proceso (`lru_cache(maxsize=1)`).
- Degradación segura: storage/queue pueden ser `None` si falta configuración mínima.

### 5) Configuración runtime (Settings)

- `crosscutting/config.py` es el source of truth: parsea `.env`, valida y concentra límites/toggles.

### 6) Prompts/policy versionados

- Assets en `prompts/` (Markdown).
- Loader en `infrastructure/prompts/`: frontmatter YAML, versioning `vN`, composición `policy + template`.

## 🔗 Conexiones y roles

- **Rol arquitectónico:** source root del backend (runtime) con límites por capas.

- **Recibe órdenes de:**
  - Servidor ASGI (ej. `uvicorn`): importa `app.main:app`.
  - Proceso worker: ejecuta `worker/worker.py` y resuelve jobs por import path.
  - Operaciones internas: health/metrics expuestas por API y worker.

- **Llama a (dependencias externas):**
  - Postgres/pgvector, Redis, storage S3/MinIO, proveedor LLM/embeddings (según settings).

- **Reglas de límites (imports/ownership):**
  - `domain/` no importa `infrastructure/` ni `interfaces/`.
  - `application/` depende de puertos del Domain; no de drivers.
  - `interfaces/` adapta HTTP y delega en `application/`.
  - `container.py` compone implementaciones; no agrega reglas de negocio.

## 👩‍💻 Guía de uso (Snippets)

### A) Import estable para servir la API

```python
# Uvicorn/Gunicorn esperan un objeto ASGI importable.
from app.main import app  # "app.main:app" es el contrato

assert callable(app)
```

### B) FastAPI “puro” para tests

```python
from fastapi.testclient import TestClient
from app.api.main import fastapi_app

client = TestClient(fastapi_app)
resp = client.get("/healthz")
assert resp.status_code == 200
```

### C) Ejecutar un caso de uso desde el contenedor (sin HTTP)

```python
from app.container import get_answer_query_use_case

use_case = get_answer_query_use_case()
# use_case.execute(...)  # el input concreto está definido en application/usecases
```

### D) Import path estable para jobs

```python
# RQ encola por string: "app.jobs.process_document_job".
from app.jobs import process_document_job

assert callable(process_document_job)
```

## 🧩 Cómo extender sin romper nada

### 1) Agregar un endpoint nuevo (HTTP)

1. Definí el comportamiento como caso de uso en `application/usecases/...`.
2. Si necesitás IO nuevo, definí el puerto en `domain/`.
3. Implementá el adapter en `infrastructure/`.
4. Cableá en `container.py`.
5. Exponé el endpoint en `interfaces/api/http/routers/...` y schemas en `interfaces/api/http/schemas/...`.
6. Test: unit / integration / e2e según el alcance.

### 2) Agregar un job nuevo (worker)

1. Creá la función job en `worker/jobs.py` (validación fail‑fast + observabilidad).
2. Re-exportá desde `app/jobs.py` si necesitás estabilidad de import path.
3. Delegá en casos de uso (Application).
4. Registrá métricas y limpiá el contexto al finalizar.

### 3) Agregar un proveedor nuevo (LLM/Embeddings/Storage)

1. Definí el puerto en `domain/services`.
2. Implementá el adapter en `infrastructure/services/...` o `infrastructure/storage/...`.
3. Selección/feature-flag en `container.py` con `Settings`.
4. Degradación segura: si falta config, deshabilitar de forma controlada.

### 4) Versionar prompts/policy sin romper producción

1. Agregá `.md` en `prompts/` con frontmatter esperado.
2. Mantené `v1` como fallback.
3. Cambiá `prompt_version` en settings para habilitar.

## 🆘 Troubleshooting

- **`ModuleNotFoundError: No module named 'app'`** → ejecutás desde el directorio equivocado → correr desde `apps/backend/` (WORKDIR) o ajustar `PYTHONPATH`.
- **`/metrics` devuelve 401/403** → `metrics_require_auth=true` y falta `X-API-Key` con permisos → revisar API keys/RBAC y header.
- **CORS bloquea requests** → `allowed_origins` no incluye el origen o `cors_allow_credentials` no coincide → ajustar settings y reiniciar.
- **429 (rate limited)** → rate limit habilitado y superaste RPS/burst → revisar `rate_limit_rps` / `rate_limit_burst`.
- **Worker no arranca (Redis requerido)** → `REDIS_URL` no configurada → setear y validar conectividad.
- **healthz/readyz reportan DB disconnected** → `DATABASE_URL` inválida o DB caída → validar URL y pool en lifespan.

## 🔎 Ver también

- `./api/README.md` (composición API)
- `./application/README.md` (capa Application)
- `./domain/README.md` (capa Domain)
- `./infrastructure/README.md` (capa Infrastructure)
- `./interfaces/api/http/README.md` (entrada HTTP)
- `./worker/README.md` (worker)
- `../README.md` (backend root en `apps/backend/`)
