# crosscutting

Como una **caja de herramientas común**: configura límites, formato de errores, logs, métricas y middlewares que usa todo el backend.

## 🎯 Misión

Este módulo agrupa preocupaciones transversales del backend que no pertenecen al negocio: **configuración runtime**, **observabilidad** (logs/métricas/tracing), **seguridad operativa** (headers, rate limit, límites de body) y **estandarización de errores**.

Recorridos rápidos por intención:

- **Quiero ver límites y settings** → `config.py`
- **Quiero errores HTTP consistentes (RFC7807)** → `error_responses.py` (+ `api/exception_handlers.py`)
- **Quiero logging correlacionable y seguro** → `logger.py` (+ `app/context.py`)
- **Quiero métricas / endpoint `/metrics`** → `metrics.py` (usado en `api/main.py`)
- **Quiero middlewares (request_id, body limit)** → `middleware.py`
- **Quiero rate limiting** → `rate_limit.py`
- **Quiero seguridad por headers** → `security.py`
- **Quiero medir etapas (timings)** → `timing.py`
- **Quiero tracing (opcional)** → `tracing.py`
- **Quiero SSE para respuestas del LLM** → `streaming.py`

### Qué SÍ hace

- Define settings tipados y validaciones de entorno (Pydantic Settings) con caching (`get_settings`).
- Estandariza errores HTTP como **Problem Details (RFC7807)** y provee factories para errores comunes.
- Provee logger estructurado (JSON) con contexto (`request_id`, `trace_id`, `span_id`) y redacción de secretos.
- Provee métricas Prometheus en modo **best‑effort** (no-op si falta `prometheus_client`).
- Implementa middlewares ASGI/Starlette para contexto, límites de body, headers de seguridad y rate limiting.
- Ofrece utilidades pequeñas y estables: paginación por cursor, timers por etapas y tracing opcional.

### Qué NO hace (y por qué)

- No define lógica de negocio (reglas de dominio) ni orquesta casos de uso.
  - **Razón:** esto vive en Domain/Application.
  - **Impacto:** si necesitás “decidir” comportamiento del sistema, va en use cases; acá solo se normaliza y se observa.

- No implementa almacenamiento ni acceso directo a datos.
  - **Razón:** IO concreto vive en Infrastructure.
  - **Impacto:** este módulo no debería hablar con Postgres/Redis/S3 de forma directa.

- No expone “features” por endpoints propios.
  - **Razón:** el transporte pertenece a Interfaces/API.
  - **Impacto:** cuando algo se registra como endpoint (ej. `/metrics`), se compone desde `api/main.py`.

## 🗺️ Mapa del territorio

| Recurso              | Tipo           | Responsabilidad (en humano)                                                                               |
| :------------------- | :------------- | :-------------------------------------------------------------------------------------------------------- |
| `README.md`          | Documento      | Portada + índice de utilidades transversales.                                                             |
| `config.py`          | Archivo Python | Settings tipados (env → config), defaults seguros y validaciones fail‑fast.                               |
| `error_responses.py` | Archivo Python | RFC7807: modelo `ErrorDetail`, `AppHTTPException`, factories y `OPENAPI_ERROR_RESPONSES`.                 |
| `exceptions.py`      | Archivo Python | Excepciones internas tipadas (`RAGError`, `DatabaseError`, `EmbeddingError`, `LLMError`) con `error_id`.  |
| `logger.py`          | Archivo Python | Logging JSON con contexto de request y redacción/truncado de datos sensibles.                             |
| `metrics.py`         | Archivo Python | Métricas Prometheus best‑effort (no-op si no hay dependencia) + helper `get_metrics_response`.            |
| `middleware.py`      | Archivo Python | Middlewares: `RequestContextMiddleware` (request_id + contextvars) y `BodyLimitMiddleware` (413 RFC7807). |
| `pagination.py`      | Archivo Python | Paginación por cursor base64 (`encode_cursor`, `decode_cursor`, `paginate`, `Page[T]`).                   |
| `rate_limit.py`      | Archivo Python | Token bucket in‑memory + `RateLimitMiddleware` (429 RFC7807 + headers).                                   |
| `security.py`        | Archivo Python | Middleware de security headers (CSP/HSTS/anti‑sniffing) con ajuste por entorno.                           |
| `streaming.py`       | Archivo Python | Streaming SSE para respuestas del LLM (`stream_answer`) con manejo de desconexión.                        |
| `timing.py`          | Archivo Python | Timers: `Timer` y `StageTimings` para medir etapas y total.                                               |
| `tracing.py`         | Archivo Python | Tracing OpenTelemetry opcional (`span()` no-op si está deshabilitado).                                    |

## ⚙️ ¿Cómo funciona por dentro?

Input → Proceso → Output, con recorridos reales del código.

### 1) Settings (configuración)

- **Input:** variables de entorno + `.env`.
- **Proceso:** `Settings` valida límites y flags; `get_settings()` cachea el resultado con `lru_cache`.
  - En producción aplica validaciones de hardening (ej. protección de `/metrics` si corresponde).

- **Output:** un objeto `Settings` único por proceso con límites (`max_body_bytes`, `max_upload_bytes`), flags (`otel_enabled`, `log_json`) y credenciales.

### 2) Request context + límites (middlewares)

- **Input:** request HTTP.
- **Proceso:**
  - `RequestContextMiddleware` genera/propaga `X-Request-Id`, setea contextvars (`request_id`, method/path), registra logs y métricas en `finally`.
  - `BodyLimitMiddleware` corta payloads grandes y devuelve 413 formateado como RFC7807 (usa `ErrorDetail`).

- **Output:** responses con header de correlación y defensa anti‑OOM por body grande.

### 3) Errores consistentes (RFC7807)

- **Input:** errores lanzados por routers/use cases.
- **Proceso:**
  - `AppHTTPException` transporta `ErrorCode` estable + `errors[]` opcional.
  - `app_exception_handler` serializa a `application/problem+json`.
  - El mapeo desde errores internos (`RAGError` y derivadas) se registra en `api/exception_handlers.py`.

- **Output:** payload Problem Details uniforme para clientes (con `code` + `request_id`/`error_id` cuando aplica).

### 4) Observabilidad (logs/métricas/tracing)

- **Logs:** `logger.py` formatea JSON y agrega contexto (`request_id`, `trace_id`, `span_id`); redacta claves sensibles y recorta tamaños.
- **Métricas:** `metrics.py` inicializa contadores/histogramas solo si `prometheus_client` está instalado; si no, opera como no-op.
- **Tracing:** `tracing.py` activa spans cuando `otel_enabled` está en settings y hay libs disponibles; si no, `span()` es no-op.

### 5) Seguridad operativa

- **Rate limiting:** `RateLimitMiddleware` usa token bucket in‑memory y responde 429 RFC7807 con `Retry-After`.
- **Security headers:** `SecurityHeadersMiddleware` agrega CSP y hardening; HSTS solo en producción y cuando el request es HTTPS (directo o vía `x-forwarded-proto`).

## 🔗 Conexiones y roles

- **Rol arquitectónico:** Crosscutting (utilities compartidas).

- **Recibe órdenes de:**
  - `app/api/main.py` (composición de middlewares, /metrics, exception handlers).
  - Routers HTTP y adaptadores (para RFC7807, paginación y streaming SSE).
  - Use cases y worker (para timing/métricas/logs).

- **Llama a:**
  - `app/context.py` (contextvars para correlación).
  - Dependencias externas de bajo acoplamiento (Pydantic Settings, Starlette/FastAPI, `prometheus_client`/OpenTelemetry de forma opcional).
  - En `streaming.py`, interfaces del dominio (`LLMService`, `ConversationRepository`, entidades `Chunk`).

- **Reglas de límites (imports/ownership):**
  - Evitar acoplar este paquete a Infrastructure concreta (Postgres/Redis/S3).
  - Mantener dependencias opcionales como no-op (`prometheus_client`, OpenTelemetry).
  - Si una utilidad necesita transporte (SSE, middlewares), puede depender de FastAPI/Starlette, pero no debe orquestar negocio.

## 👩‍💻 Guía de uso (Snippets)

### 1) Settings tipados (runtime)

```python
from app.crosscutting.config import get_settings

settings = get_settings()
print(settings.max_body_bytes, settings.rate_limit_rps)
```

### 2) Respuestas RFC7807 y OpenAPI (routers)

```python
from fastapi import APIRouter

from app.crosscutting.error_responses import OPENAPI_ERROR_RESPONSES, bad_request

router = APIRouter()

@router.get("/healthz", responses=OPENAPI_ERROR_RESPONSES)
def healthz():
    # Si necesitás cortar con un error consistente
    raise bad_request("Estado inválido")
```

### 3) Composición de middlewares (ASGI / FastAPI)

```python
from fastapi import FastAPI

from app.crosscutting.middleware import BodyLimitMiddleware, RequestContextMiddleware
from app.crosscutting.security import SecurityHeadersMiddleware

app = FastAPI()
app.add_middleware(RequestContextMiddleware)
app.add_middleware(BodyLimitMiddleware)
app.add_middleware(SecurityHeadersMiddleware)
```

### 4) Medición por etapas (use cases)

```python
from app.crosscutting.timing import StageTimings

timings = StageTimings()

with timings.measure("retrieve"):
    ...

with timings.measure("llm"):
    ...

print(timings.to_dict())
```

## 🧩 Cómo extender sin romper nada

Checklist práctico:

1. **Nuevo setting:** agregarlo en `config.py` con default seguro + validator si hay constraints.
2. **Nuevo error HTTP:** sumar un `ErrorCode` y una factory en `error_responses.py` (con status y mensaje).
3. **Nueva métrica:** agregarla en `metrics.py` cuidando cardinalidad (sin IDs dinámicos, sin user_id, sin SQL completo).
4. **Nuevo middleware:** ubicarlo acá solo si es transversal; que no importe repositorios ni infraestructura concreta.
5. **Dependencia opcional:** mantener no-op cuando falte la lib (como `prometheus_client` / OpenTelemetry).
6. **Tests:** cubrir helpers puros (paginación, timing, redacción de logger) con unit tests; middlewares con tests de request/response si hay suite HTTP.

## 🆘 Troubleshooting

- **`/metrics` muestra “prometheus_client no instalado”** → falta la dependencia → revisar `apps/backend/requirements.txt` y el endpoint en `app/api/main.py`.
- **413 al subir archivos** → límite de payload excedido → revisar `Settings.max_body_bytes` / `Settings.max_upload_bytes` en `config.py` y el `BodyLimitMiddleware`.
- **No aparece `X-Request-Id` en responses** → middleware no registrado → revisar `app/api/main.py` (cadena de middlewares).
- **Logs sin `request_id`** → request no pasó por `RequestContextMiddleware` (o el log ocurrió fuera del ciclo HTTP) → revisar composición y uso de `logger`.
- **429 demasiado frecuente** → rate limit bajo → ajustar `rate_limit_rps` / `rate_limit_burst` en settings; verificar que el ASGI wrapper `RateLimitMiddleware` está activo en `api/main.py`.
- **Headers CSP/HSTS no aparecen** → `SecurityHeadersMiddleware` no registrado o no es HTTPS (HSTS) → revisar `app/api/main.py` y `x-forwarded-proto` del proxy.

## 🔎 Ver también

- `../README.md` (índice del backend)
- `../api/main.py` (composición FastAPI/ASGI: middlewares, /metrics, handlers)
- `../api/exception_handlers.py` (mapeo de excepciones internas → RFC7807)
- `../context.py` (contextvars de request/trace para correlación)
- `../interfaces/api/http/README.md` (capa HTTP y adaptación)
- `../worker/README.md` (ejecución asíncrona y jobs)
