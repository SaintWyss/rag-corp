# Backend Application (paquete `app`)

Analogía breve: pensá este paquete como el **motor armado** del backend: piezas internas (reglas), cableado (dependencias) y dos llaves de arranque (API y worker). Todo lo que sea “taller” (build, scripts, tests, migraciones) queda fuera, en `apps/backend/`.

## 🎯 Misión

Este paquete contiene **todo el runtime** del backend: la arquitectura por capas, los puntos de entrada, el cableado de dependencias, los adaptadores a servicios externos y los assets versionados (prompts/policy). Si necesitás entender “qué corre” cuando levantás el backend, empezás acá.

### Cómo leer este paquete sin perderse

Si estás entrando por primera vez, este README funciona como **índice técnico**. Elegí el recorrido que te corresponda:

* **Quiero entender la arquitectura por capas (Clean Architecture)**

  * Portada de capas y convenciones → [`application/`](./application/README.md), [`domain/`](./domain/README.md), [`infrastructure/`](./infrastructure/README.md), [`interfaces/`](./interfaces/README.md)

* **Quiero saber cómo se levanta la API y qué endpoints existen**

  * Composición FastAPI + lifecycle + middlewares → [`api/`](./api/README.md)
  * Routers HTTP y DTOs → [`interfaces/api/http/`](./interfaces/api/http/README.md)
  * Entrypoint estable para el servidor ASGI → [`main.py`](./main.py)

* **Quiero entender el worker y la cola de documentos**

  * Proceso worker (bootstrap, health, HTTP liviano) → [`worker/`](./worker/README.md)
  * Entrypoints estables de jobs (import path para RQ) → [`jobs.py`](./jobs.py)

* **Quiero ubicar seguridad (API keys, JWT, RBAC) y cómo se aplica**

  * Autenticación por API key / scopes → [`identity/auth.py`](./identity/auth.py)
  * Principal unificado (JWT + API key) → [`identity/dual_auth.py`](./identity/dual_auth.py)
  * Permisos y RBAC → [`identity/rbac.py`](./identity/rbac.py)

* **Quiero ubicar observabilidad (logs, request_id, métricas, rate limit)**

  * Middlewares HTTP (contexto + límites) → [`crosscutting/middleware.py`](./crosscutting/middleware.py)
  * Errores RFC7807 (problem+json) → [`crosscutting/error_responses.py`](./crosscutting/error_responses.py)
  * Métricas Prometheus (dependencia opcional) → [`crosscutting/metrics.py`](./crosscutting/metrics.py)
  * Rate limiting token-bucket (in-memory) → [`crosscutting/rate_limit.py`](./crosscutting/rate_limit.py)
  * Contexto request/job (ContextVars) → [`context.py`](./context.py)

* **Quiero entender cómo se versionan y cargan los prompts/policies**

  * Assets (Markdown) → [`prompts/`](./prompts/README.md)
  * Loader (frontmatter + versioning) → [`infrastructure/prompts/`](./infrastructure/prompts/README.md)

---

**Qué SÍ hace**

* Implementa Clean Architecture con límites claros:

  * `domain/`: reglas/contratos estables.
  * `application/`: casos de uso (orquestación).
  * `infrastructure/`: IO real (DB/Redis/S3/LLM/parsers).
  * `interfaces/`: adaptación de entrada (HTTP/DTOs).
* Expone **entrypoints estables**:

  * `app.main:app` (ASGI) para correr la API.
  * `app.api.main.fastapi_app` (FastAPI) para tests.
  * `app.jobs.process_document_job` (job) para RQ.
* Centraliza el cableado en `container.py` con DI manual y singletons con cache.
* Estándariza errores (RFC7807), contexto (request_id), métricas y límites (body/rate limit).

**Qué NO hace (y por qué)**

* No contiene scripts de repo/CI ni tooling operativo.

  * **Por qué:** mezclar runtime con tooling termina generando imports cruzados y side-effects difíciles de reproducir.
* No contiene tests.

  * **Por qué:** tests dependen del runtime; el runtime nunca debe depender de tests.
* No define el “estado del entorno” (red/containers/volúmenes) como infraestructura completa.

  * **Por qué:** este paquete solo describe el **software**; el entorno se configura afuera (compose/infra) para que sea sustituible.

---

## 🗺️ Mapa del territorio

| Recurso              | Tipo         | Responsabilidad (en humano)                                                                                                     |
| :------------------- | :----------- | :------------------------------------------------------------------------------------------------------------------------------ |
| 📁 `api/`            | 📁 Carpeta   | **Composición FastAPI**: crea la app, define lifespan, registra middlewares, routers y endpoints operativos.                    |
| 📁 `application/`    | 📁 Carpeta   | **Casos de uso**: orquesta flujos (RAG chat, ingesta, workspaces, documentos).                                                  |
| 🐍 `audit.py`        | 🐍 Archivo   | Auditoría best-effort: construye y registra eventos sin romper el flujo si falla la persistencia.                               |
| 🐍 `container.py`    | 🐍 Archivo   | **Composition root**: inyección manual (DIP), selección de adapters (prod/test), singletons con `lru_cache`.                    |
| 🐍 `context.py`      | 🐍 Archivo   | Contexto request/job con `ContextVar`: request_id, tracing ids, método/path (correlación de logs).                              |
| 📁 `crosscutting/`   | 📁 Carpeta   | Preocupaciones transversales: config, logging, errores RFC7807, métricas, rate limiting, middlewares.                           |
| 📁 `domain/`         | 📁 Carpeta   | Dominio puro: entidades, value objects, puertos (repos/services) y reglas estables.                                             |
| 📁 `identity/`       | 📁 Carpeta   | Seguridad: API keys (scopes), JWT, principal unificado, RBAC/permisos y policy checks.                                          |
| 📁 `infrastructure/` | 📁 Carpeta   | Adaptadores salientes: DB Postgres/pgvector, cola Redis/RQ, storage S3/MinIO, parsers, servicios LLM/embeddings, prompts infra. |
| 📁 `interfaces/`     | 📁 Carpeta   | Adaptadores entrantes: HTTP (routers), schemas Pydantic, mapping request/response hacia Application.                            |
| 🐍 `jobs.py`         | 🐍 Archivo   | Re-export de jobs con import path estable (RQ encola por string).                                                               |
| 🐍 `main.py`         | 🐍 Archivo   | Entrypoint ASGI estable: re-export de `app` sin side-effects (lo ejecuta `uvicorn`).                                            |
| 📁 `prompts/`        | 📁 Carpeta   | Assets Markdown (policy + templates versionados) consumidos por el loader.                                                      |
| 📁 `worker/`         | 📁 Carpeta   | Proceso worker: bootstrap, health/readiness, server HTTP mínimo y ejecución de jobs.                                            |
| 📄 `README.md`       | 📄 Documento | Portada/índice del paquete `app/` (este archivo).                                                                               |

---

## ⚙️ ¿Cómo funciona por dentro?

### 1) Puntos de entrada estables (lo que “arranca” procesos)

Este repo evita entrypoints frágiles: los paths que usa runtime deben ser **estables**.

* **API (ASGI):** `app.main:app`

  * `app/main.py` es un módulo fino que **re-exporta** la app real desde `api/main.py` sin side-effects.
  * Motivo: cambiar imports internos no debería romper despliegues o tooling que depende del path.

* **FastAPI para tests:** `app.api.main.fastapi_app`

  * Se expone una instancia FastAPI “pura” para tests (sin wrapper ASGI de rate limit).

* **Jobs RQ:** `app.jobs.process_document_job`

  * RQ encola por string de import; el job vive en `worker/jobs.py` pero se re-exporta desde `app/jobs.py` para garantizar estabilidad.

### 2) API HTTP: FastAPI sobre ASGI

**ASGI** es el estándar que permite ejecutar apps web asíncronas en Python.

* FastAPI define endpoints + OpenAPI.
* Un servidor ASGI (por ejemplo `uvicorn`) ejecuta el objeto ASGI exportado.

**Composición real:** `api/main.py`

* Lifecycle por `lifespan`: inicializa pool de DB y cierra recursos al apagar.
* Middlewares relevantes:

  * `BodyLimitMiddleware`: defensa ante bodies gigantes (seguridad + anti-OOM).
  * `SecurityHeadersMiddleware`: headers de seguridad.
  * `RequestContextMiddleware`: request_id + contextvars para correlación.
  * `CORSMiddleware`: orígenes configurables.
  * `RateLimitMiddleware`: wrapper ASGI final (token bucket in-memory), habilitable por settings.
* Routers:

  * Router de negocio bajo **`/v1`**.
  * Alias adicional **`/api/v1`** para compatibilidad operativa (sin duplicar lógica).
* Endpoints operativos:

  * `GET /healthz` (incluye check de DB; con `full=true` puede chequear conectividad Google).
  * `GET /readyz` (readiness mínimo: DB).
  * `GET /metrics` (Prometheus; opcionalmente protegido por permisos).

**Errores:** RFC7807 (`problem+json`)

* La API normaliza errores en un formato consistente (catálogo de `ErrorCode`).
* Ventaja: el frontend puede manejar por `code` y el backend correlacionar por `request_id`.

### 3) Worker: jobs asíncronos (RQ + Redis)

Un **worker** es un proceso separado que ejecuta tareas que no conviene hacer dentro de un request (por costo/tiempo/latencia).

**Bootstrap del proceso:** `worker/worker.py`

* Fail-fast:

  * Redis debe responder al inicio.
  * Se inicializa el pool de DB antes de ejecutar trabajos.
* Best-effort:

  * Un HTTP server mínimo se levanta si se puede (si falla, el worker sigue).

**Job principal (document processing):** `worker/jobs.py`

* Validación fail-fast de UUIDs.
* Construcción del use case a través del contenedor (no conoce detalles de infra).
* Observabilidad:

  * setea `request_id` con el `job_id` y marca método/path como `WORKER`.
  * registra métricas de éxito/fallo y duración.
  * limpia contexto al finalizar para evitar filtraciones.

### 4) DI manual y composición: `container.py`

Acá se “arma el grafo” de dependencias siguiendo DIP:

* Los **casos de uso** reciben **puertos** (interfaces/contratos), no implementaciones concretas.
* `container.py` decide qué implementación concreta usar según `Settings` (por ejemplo, in-memory en test o Postgres en runtime).

Puntos importantes:

* **Single-thread / per-process singletons** con `lru_cache(maxsize=1)` para recursos pesados.
* **Feature flags**:

  * LLM/embeddings fake para entornos de desarrollo/test.
  * rewriter/reranker habilitables.
* **Deshabilitación segura**:

  * storage/queue pueden devolver `None` si no hay configuración mínima (degrada sin romper import-time).

### 5) Configuración runtime (Settings)

`crosscutting/config.py` es el “source of truth” de configuración:

* parsea `.env` (y variables de entorno), tipa y valida.
* concentra límites (body, upload, max_chars), toggles, rate limit, JWT, S3/MinIO, pool DB, etc.

### 6) Prompts/policy versionados

* Los assets viven en `prompts/` como Markdown.
* El loader en `infrastructure/prompts/` soporta:

  * versiones (`vN`) controladas por settings,
  * frontmatter YAML para metadatos/inputs,
  * composición “policy + template”.

---

## 🔗 Conexiones y roles

* **Rol arquitectónico:** source root del backend (runtime) con límites por capas.

* **Recibe órdenes de:**

  * Servidor ASGI (`uvicorn`/`gunicorn`): importa `app.main:app`.
  * Proceso worker: ejecuta `worker/worker.py` y resuelve jobs por import path.
  * Operaciones internas (health/metrics) expuestas por la API y por el worker.

* **Llama a (dependencias externas):**

  * Postgres/pgvector (repositorios y healthchecks).
  * Redis (cola RQ + healthchecks).
  * Proveedor LLM/embeddings (cuando está habilitado por settings).
  * Storage S3/MinIO (si está configurado).

* **Límites que se respetan (reglas de import):**

  * `domain/` no importa `infrastructure/` ni `interfaces/`.
  * `application/` depende de puertos del Domain; no de drivers.
  * `interfaces/` hace adaptación de protocolo (HTTP) y delega en `application/`.
  * `container.py` compone implementaciones; no agrega reglas de negocio.

---

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

Útil para pruebas de integración o scripts internos.

```python
from app.container import get_answer_query_use_case

use_case = get_answer_query_use_case()
# use_case.execute(...)  # el input concreto está definido en application/usecases
```

### D) Encolar un job (import path estable)

RQ serializa el path como string. Este repo garantiza que el path sea estable.

```python
# En el producer (queue adapter) se encola típicamente por string:
# "app.jobs.process_document_job"
# El job real está en worker/jobs.py pero se re-exporta por estabilidad.
from app.jobs import process_document_job

assert callable(process_document_job)
```

---

## 🧩 Cómo extender sin romper nada

### 1) Agregar un endpoint nuevo (HTTP)

1. Definí primero el comportamiento como **caso de uso** en `application/usecases/...`.
2. Si necesitás IO nuevo, definí el **puerto** en `domain/` (repository/service).
3. Implementá el adapter en `infrastructure/`.
4. Cableá en `container.py` (factory del use case / dependencia).
5. Exponé el endpoint en `interfaces/api/http/routers/...` y el esquema en `interfaces/api/http/schemas/...`.
6. Elegí el tipo de test:

   * unit (Application/Domain sin IO)
   * integration (DB/Redis)
   * e2e (flujo completo)

### 2) Agregar un job nuevo (worker)

1. Creá la función job en `worker/jobs.py` (validación fail-fast + observabilidad).
2. Re-exportá el entrypoint desde `app/jobs.py` si querés garantizar estabilidad del import path.
3. Reusá casos de uso de `application/` (evitá duplicar lógica en el job).
4. Registrá métricas y limpiá el contexto al finalizar.

### 3) Agregar un proveedor nuevo (LLM/Embeddings/Storage)

1. Definí el puerto en `domain/services` si aún no existe.
2. Implementá el adapter en `infrastructure/services/...` o `infrastructure/storage/...`.
3. Selección/feature-flag en `container.py` usando `Settings`.
4. Asegurate de degradación segura (si falta config, deshabilitar devolviendo `None` cuando aplique).

### 4) Versionar prompts/policy sin romper producción

1. Agregá archivos `.md` en `prompts/` siguiendo el esquema de frontmatter esperado.
2. Mantené `v1` como fallback.
3. Cambiá `prompt_version` en settings para habilitar la nueva versión.

---

## 🆘 Troubleshooting

* **Síntoma:** `ModuleNotFoundError: No module named 'app'`

  * **Causa probable:** ejecutás desde el directorio equivocado.
  * **Solución:** asegurate de estar en `apps/backend/` (WORKDIR) o ajustar `PYTHONPATH`.

* **Síntoma:** `/metrics` devuelve 401/403

  * **Causa probable:** `metrics_require_auth=true` y falta `X-API-Key` con permisos.
  * **Solución:** revisar configuración de API keys/RBAC y el header `X-API-Key`.

* **Síntoma:** CORS bloquea requests del frontend

  * **Causa probable:** `allowed_origins` no incluye el origen actual o `cors_allow_credentials` no coincide con el tipo de auth.
  * **Solución:** ajustar settings (orígenes permitidos y credenciales) y reiniciar.

* **Síntoma:** 429 (rate limited)

  * **Causa probable:** rate limit habilitado y se superó RPS/burst.
  * **Solución:** revisar `rate_limit_rps` / `rate_limit_burst`, y confirmar si el identificador es por API key o IP.

* **Síntoma:** worker no arranca (`REDIS_URL es requerido...`)

  * **Causa probable:** Redis no configurado.
  * **Solución:** setear `REDIS_URL`/`redis_url` en settings y validar conectividad.

* **Síntoma:** healthz/readyz reportan DB disconnected

  * **Causa probable:** `database_url` inválida o DB caída.
  * **Solución:** validar `DATABASE_URL` y que el pool se inicializa en lifespan.

---

## 🔎 Ver también

* [API composition (`api/`)](./api/README.md)
* [Application layer (`application/`)](./application/README.md)
* [Domain layer (`domain/`)](./domain/README.md)
* [Infrastructure layer (`infrastructure/`)](./infrastructure/README.md)
* [Interfaces HTTP (`interfaces/api/http/`)](./interfaces/api/http/README.md)
* [Worker (`worker/`)](./worker/README.md)
* [Backend root (`apps/backend/`)](../README.md)
