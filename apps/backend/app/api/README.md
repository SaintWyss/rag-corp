# API Composition (FastAPI)

Analogía breve: esta carpeta es la **torre de control** del backend HTTP. No “pilotea” la lógica de negocio, pero sí decide **cómo entra** un request, **qué protecciones se aplican**, **a qué router se deriva** y **cómo se responde** (incluyendo errores y endpoints operativos).

## 🎯 Misión

Esta carpeta construye la aplicación **FastAPI** y publica el objeto **ASGI** que ejecuta el servidor (p. ej. `uvicorn`). Es el punto donde se materializan decisiones transversales:

* **Lifecycle** del proceso (startup/shutdown): inicializar/cerrar recursos compartidos.
* **Middlewares**: límites de payload, headers de seguridad, request_id/correlación, CORS.
* **Rutas**: router de negocio (`/v1`), rutas auxiliares (`/auth/*`, `/admin/*`) y alias de compatibilidad (`/api/v1`).
* **Errores**: mapeo centralizado a respuestas **RFC7807** (`problem+json`).
* **Operación**: `healthz/readyz/metrics` para monitoreo.

### Qué SÍ hace

* Crea la instancia FastAPI con tags y un OpenAPI enriquecido.
* Define el `lifespan` del proceso (pool DB + seed de desarrollo si aplica).
* Registra middlewares y define el orden de ejecución.
* Incluye routers (negocio + auth + admin) y alias de rutas.
* Centraliza handlers de excepción para no filtrar detalles internos.
* Exporta dos entrypoints:

  * `fastapi_app`: la app FastAPI “pura” (ideal para tests).
  * `app`: la app ASGI final, envuelta con rate limiting.

### Qué NO hace (y por qué)

* No implementa reglas de negocio.

  * **Por qué:** los flujos deben vivir como casos de uso en `app/application/` para ser testeables y no depender de HTTP.
* No accede a DB directamente para lógica funcional.

  * **Por qué:** el IO real está encapsulado en `app/infrastructure/` y se invoca vía puertos/use cases.
* No compone routers a nivel “feature”.

  * **Por qué:** la composición del router de negocio está en `app/interfaces/api/http/` (para que esta carpeta sea solo composición web + operación).

---

## 🗺️ Mapa del territorio

| Recurso                    | Tipo             | Responsabilidad (en humano)                                                                                                                               |
| :------------------------- | :--------------- | :-------------------------------------------------------------------------------------------------------------------------------------------------------- |
| 🐍 `main.py`               | 🐍 Composición   | Crea `fastapi_app`, define `lifespan`, registra middlewares/routers/handlers, expone `healthz/readyz/metrics` y exporta el `app` ASGI final (rate limit). |
| 🐍 `exception_handlers.py` | 🐍 Error mapping | Registra handlers: traduce errores tipados (`DatabaseError`, `LLMError`, etc.) y no tipados a **RFC7807** con logging correlacionado.                     |
| 🐍 `versioning.py`         | 🐍 Routing       | Agrega alias de compatibilidad **`/api/v1`** reutilizando el mismo router de negocio que vive bajo `/v1`.                                                 |
| 🐍 `auth_routes.py`        | 🐍 Endpoints     | Endpoints `/auth/*`: login/logout/me y administración de usuarios. Maneja JWT y cookie httpOnly; emite auditoría best‑effort.                             |
| 🐍 `admin_routes.py`       | 🐍 Endpoints     | Endpoints `/admin/*` para provisionamiento: crea/lista workspaces por usuario. Usa casos de uso + autorización estricta + auditoría.                      |
| 📄 `README.md`             | 📄 Documento     | Guía técnica de la composición FastAPI (este documento).                                                                                                  |

---

## ⚙️ ¿Cómo funciona por dentro?

### 1) Export público: `fastapi_app` vs `app` (por qué existen dos)

Este módulo expone **dos niveles** de aplicación:

* `fastapi_app = create_fastapi_app()`

  * Es la FastAPI “pura” (rutas + middlewares + handlers).
  * Se usa para tests (por ejemplo `TestClient`) y para inspeccionar OpenAPI.

* `app = RateLimitMiddleware(fastapi_app)`

  * Es el **objeto ASGI final** que corre el servidor.
  * Se envuelve afuera para mantener el rate limiting como “capa externa” (y evitar contaminar tests o romper la composición).

Esto no es un detalle menor: evita que un test HTTP simple quede sujeto a throttling salvo que lo quieras explícitamente.

---

### 2) Lifespan (startup/shutdown): recursos compartidos sin side-effects en import-time

La inicialización pesada ocurre en `lifespan(app)`:

1. Se cargan `Settings` (variables de entorno tipadas).
2. Se inicializa el pool de DB:

   * `init_pool(database_url, min_size, max_size)`
3. Se ejecuta seed de desarrollo si corresponde:

   * `ensure_dev_admin(...)`
   * `ensure_dev_demo(...)`
4. En shutdown:

   * `close_pool()`

Notas de diseño importantes:

* **Fail-fast** en startup: si el seed está habilitado y falla, el proceso no arranca (mejor fallar claro que quedar “medio vivo”).
* **Sin side-effects en import-time**: todo lo sensible se hace dentro del lifecycle, no al importar módulos.

---

### 3) Middlewares: qué protegen y en qué orden corren

`create_fastapi_app()` registra middlewares (Starlette) y deja explícito que **se ejecutan en orden inverso al registro**.

Se agregan:

1. `BodyLimitMiddleware`

   * Defensa ante bodies gigantes (incluye uploads chunked).
   * Evita OOM y abuso.

2. `SecurityHeadersMiddleware`

   * Hardening OWASP: CSP, anti-clickjacking, no-sniff, y HSTS cuando corresponde.

3. `RequestContextMiddleware`

   * Propaga o genera `X-Request-Id`.
   * Setea `ContextVars` para correlación de logs.
   * Limpia contexto al final (evita leaks entre requests).

4. `CORSMiddleware`

   * Orígenes configurables (`allowed_origins`), headers permitidos (`X-API-Key`, `Authorization`, `X-Request-Id`), y `cors_allow_credentials`.

Y por fuera (wrapper ASGI):
5. `RateLimitMiddleware` (token bucket in-memory)

* Identifica por API key (si existe) o IP (fallback).
* Devuelve 429 en formato RFC7807 + headers de rate limit.

👉 Importante: la CORS y los headers de seguridad no sustituyen autorización. Son defensas de “frontera”; el acceso real se controla con dependencias de `identity/*`.

---

### 4) Routers: negocio bajo `/v1`, auxiliares fuera del prefijo

La composición separa “API de negocio” y “rutas auxiliares”:

* **Negocio (core):**

  * `app.include_router(business_router, prefix="/v1")`
  * `business_router` se importa desde `app.interfaces.api.http.routes` (shim que re-exporta el router real).

* **Auth:**

  * `app.include_router(auth_router)`
  * Define `/auth/login`, `/auth/logout`, `/auth/me` y administración `/auth/users*`.

* **Admin (provisionamiento):**

  * `app.include_router(admin_router)`
  * Define rutas `/admin/*` (fuera de `/v1`) para tareas administrativas puntuales.

* **Alias de compatibilidad:**

  * `include_versioned_routes(app)` agrega `/api/v1/...` apuntando al mismo router que `/v1/...`.
  * Esto permite migrar clientes sin duplicar lógica.

---

### 5) Endpoints operativos: healthz / readyz / metrics

Estos endpoints existen para operación real (monitoreo, readiness, scraping):

* `GET /healthz` (health ampliado)

  * **Siempre** chequea DB (`repo.ping()`).
  * Si `full=true`:

    * si `healthcheck_google_enabled=true` intenta una llamada mínima de embeddings usando `GOOGLE_API_KEY`.
  * Devuelve: `ok`, `db`, `google`, `request_id`.

* `GET /readyz` (readiness mínimo)

  * Chequea DB y devuelve `ok`, `db`, `request_id`.
  * La idea: readiness es “¿puedo recibir tráfico?”; health puede ser más amplio.

* `GET /metrics` (Prometheus)

  * Expone métricas si `prometheus_client` está instalado.
  * Si no está instalado, devuelve texto plano indicando que falta el paquete.
  * La autorización es opcional según `metrics_require_auth`:

    * si está activada, exige `X-API-Key` con permiso `ADMIN_METRICS`.

---

### 6) OpenAPI: documentación de seguridad dual + ajustes de parámetros

`main.py` reemplaza `app.openapi` por una versión personalizada:

* Agrega dos esquemas:

  * `ApiKeyAuth` → `X-API-Key`
  * `BearerAuth` → `Authorization: Bearer <JWT>` (o cookie httpOnly)

* Declara “seguridad dual” como default (ambas aceptadas):

  * `[{ApiKeyAuth: []}, {BearerAuth: []}]`

* Ajusta **por ruta**:

  * `/healthz`, `/readyz`, `/auth/login`, `/auth/logout` → públicas (sin security).
  * `/auth/me` → solo JWT.
  * `/metrics` → API key si `metrics_require_auth=true`, si no pública.
  * `/auth/*`, `/admin/*`, `/v1/*`, `/api/v1/*` → dual.

* Ajuste fino de documentación:

  * Marca `workspace_id` como query param **required** para endpoints `/v1/*` y `/api/v1/*` (con excepciones puntuales de rutas de workspaces).
  * Motivo: en runtime el caso de uso valida `workspace_id` como obligatorio, pero el schema HTTP podría no reflejarlo por defecto.

---

## 🔗 Conexiones y roles

* **Rol arquitectónico:** composición y borde HTTP (Interface Layer) + operación.

* **Recibe órdenes de:**

  * Servidor ASGI (`uvicorn`/`gunicorn`) importando `app.api.main:app` o `app.main:app`.

* **Llama a (dentro del backend):**

  * `app.interfaces.api.http.*` para routers de negocio.
  * `app.crosscutting.*` para middleware, límites, logging, errores y métricas.
  * `app.identity.*` para autenticación/autorización y permisos.
  * `app.infrastructure.db.pool` para lifecycle de conexiones.
  * `app.container` y repositorios mínimos para health y seed.

* **Llama a (fuera del backend):**

  * PostgreSQL (ping en health/ready y uso normal vía infraestructura).
  * Redis/RQ indirectamente (la API encola trabajos, no los ejecuta).
  * Google GenAI (solo si `full=true` y está habilitado).

* **Límites que se respetan:**

  * Esta carpeta no define reglas de negocio: solo composición + adaptadores HTTP.
  * Los errores se expresan como RFC7807 para contrato estable con clientes.

---

## 👩‍💻 Guía de uso (Snippets)

### A) Import recomendado para runtime (ASGI final)

```python
# Este es el objeto ASGI que ejecuta uvicorn.
from app.api.main import app

assert callable(app)
```

### B) Import recomendado para tests (FastAPI “puro”)

```python
from fastapi.testclient import TestClient
from app.api.main import fastapi_app

client = TestClient(fastapi_app)
resp = client.get("/readyz")
assert resp.status_code == 200
```

### C) Inspeccionar OpenAPI y confirmar seguridad documentada

```python
from app.api.main import fastapi_app

schema = fastapi_app.openapi()
assert "securitySchemes" in schema.get("components", {})
```

### D) Ejecutar local (comando típico)

```bash
uvicorn app.api.main:app --host 0.0.0.0 --port 8000
```

---

## 🧩 Cómo extender sin romper nada

### 1) Agregar endpoints de negocio

1. Creá el router/endpoint en `app/interfaces/api/http/routers/`.
2. Incluí ese router en el router raíz (`app/interfaces/api/http/router.py`).
3. No agregues lógica de negocio en el endpoint: delegá a casos de uso.

### 2) Agregar un endpoint operativo nuevo (admin/ops)

1. Declaralo en `app/api/main.py` (misma convención que health/metrics).
2. Decidí si es público o requiere permisos.
3. Si es sensible, usá una dependencia de `identity.rbac` o `identity.dual_auth`.
4. Documentalo en OpenAPI (tags adecuados).

### 3) Agregar un middleware nuevo

1. Implementalo en `app/crosscutting/*`.
2. Registralo en `create_fastapi_app()`.
3. Considerá el orden: recordá que Starlette ejecuta en orden inverso al registro.
4. Asegurá `clear_context()` si toca contextvars.

### 4) Expandir mapeo de errores (RFC7807)

1. Tipá el error en `app/crosscutting/exceptions.py`.
2. Asociá `ErrorCode` en `app/crosscutting/error_responses.py`.
3. Registrá un handler específico en `app/api/exception_handlers.py`.
4. Verificá que el handler:

   * loguee con `request_id` y `error_id`.
   * no filtre detalles en producción.

### 5) Mantener compatibilidad de rutas

1. Si agregás un nuevo prefijo o alias, hacelo en `versioning.py`.
2. Evitá duplicar routers: reusá el mismo `business_router`.

---

## 🆘 Troubleshooting

* **Síntoma:** CORS bloquea requests del frontend

  * **Causa probable:** `allowed_origins` no incluye el origen actual o `cors_allow_credentials` no coincide con el tipo de auth.
  * **Qué mirar:** `crosscutting/config.py` (campos `allowed_origins`, `cors_allow_credentials`).

* **Síntoma:** `/metrics` devuelve 401/403

  * **Causa probable:** `metrics_require_auth=true` y falta API key con permiso `ADMIN_METRICS`.
  * **Qué mirar:** `identity/rbac.py` (require_metrics_permission) + header `X-API-Key`.

* **Síntoma:** `/metrics` devuelve “prometheus_client no instalado”

  * **Causa probable:** dependencia opcional ausente.
  * **Solución:** instalar `prometheus_client` o mantenerlo deshabilitado conscientemente.

* **Síntoma:** `/healthz` reporta `db=disconnected`

  * **Causa probable:** DB caída, `database_url` mal configurada o pool no inicializado.
  * **Qué mirar:** `DATABASE_URL`, logs de startup, `infrastructure/db/pool.py`.

* **Síntoma:** `/healthz?full=true` reporta `google=unavailable`

  * **Causa probable:** `GOOGLE_API_KEY` faltante, API caída o modelo no accesible.
  * **Qué mirar:** variable `GOOGLE_API_KEY`, settings `healthcheck_google_enabled`, logs del warning.

* **Síntoma:** muchos 429 (rate limit)

  * **Causa probable:** límites bajos (`rate_limit_rps`, `rate_limit_burst`) o identificación por IP (sin API key).
  * **Qué mirar:** settings de rate limit y si el cliente envía `X-API-Key`.

* **Síntoma:** OpenAPI muestra seguridad “incorrecta” en un endpoint

  * **Causa probable:** el path no está cubierto por las reglas del `_custom_openapi`.
  * **Qué mirar:** `api/main.py::_custom_openapi` (sets `public_paths`, `jwt_only_paths`, condiciones por prefijo).

---

## 🔎 Ver también

* [Root del paquete `app/`](../README.md)
* [Interfaces HTTP (routers + schemas)](../interfaces/api/http/README.md)
* [Router raíz v1](../interfaces/api/http/router.py)
* [Crosscutting (middleware/errores/métricas)](../crosscutting/README.md)
* [Auth & RBAC](../identity/README.md)
* [DB pool](../infrastructure/db/README.md)
