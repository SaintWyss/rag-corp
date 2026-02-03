# crosscutting
Como una **caja de herramientas común**: settings, logs, métricas, errores y middlewares.

## 🎯 Misión
Este módulo agrupa preocupaciones transversales que no pertenecen al negocio: configuración, observabilidad, seguridad operativa, errores RFC7807 y utilidades compartidas.

### Qué SÍ hace
- Define settings tipados y validaciones de entorno.
- Estandariza errores HTTP como RFC7807.
- Provee logging estructurado y métricas best-effort.
- Implementa middlewares (request_id, body limit, security headers, rate limit).
- Ofrece utilidades como paginación, timings, streaming SSE y tracing opcional.

### Qué NO hace (y por qué)
- No implementa reglas de negocio. Razón: el negocio vive en Domain/Application. Consecuencia: acá solo se normaliza y observa.
- No contiene IO de infraestructura (DB/Redis/S3). Razón: el IO real está en `infrastructure/`. Consecuencia: este módulo no habla con servicios externos directos.

## 🗺️ Mapa del territorio
| Recurso | Tipo | Responsabilidad (en humano) |
| :-- | :-- | :-- |
| `README.md` | Documento | Guía de utilidades transversales. |
| `config.py` | Archivo Python | Settings tipados y validaciones. |
| `error_responses.py` | Archivo Python | RFC7807, `ErrorCode` y factories. |
| `exceptions.py` | Archivo Python | Excepciones internas tipadas. |
| `logger.py` | Archivo Python | Logging JSON con redacción. |
| `metrics.py` | Archivo Python | Métricas Prometheus (best-effort). |
| `middleware.py` | Archivo Python | Middlewares de contexto y límite de body. |
| `pagination.py` | Archivo Python | Paginación por cursor. |
| `rate_limit.py` | Archivo Python | Rate limit in-memory + middleware. |
| `security.py` | Archivo Python | Security headers (CSP, HSTS, etc.). |
| `streaming.py` | Archivo Python | SSE para respuestas de LLM. |
| `timing.py` | Archivo Python | Timers y métricas por etapas. |
| `tracing.py` | Archivo Python | Tracing opcional (no-op si falta). |

## ⚙️ ¿Cómo funciona por dentro?
Input → Proceso → Output.

- **Settings**
- Input: env + `.env`.
- Proceso: `get_settings()` valida y cachea.
- Output: objeto Settings por proceso.
- **Middlewares**
- Request context: genera/propaga `X-Request-Id`, setea contextvars y métricas.
- Body limit: corta payloads grandes con 413 RFC7807.
- **Errores RFC7807**
- Factories en `error_responses.py` construyen Problem Details uniformes.
- **Observabilidad**
- Logs estructurados + métricas Prometheus best-effort.

## 🔗 Conexiones y roles
- **Rol arquitectónico:** Crosscutting (utilities compartidas).
- **Recibe órdenes de:** `app/api/main.py`, routers y use cases.
- **Llama a:** stdlib + libs opcionales (`prometheus_client`, OpenTelemetry).
- **Reglas de límites:** no IO de infraestructura ni reglas de negocio.

## 👩‍💻 Guía de uso (Snippets)
```python
# Por qué: muestra el contrato mínimo del módulo.
from app.crosscutting.config import get_settings
settings = get_settings()
```

```python
# Por qué: ejemplo de integración sin infraestructura real.
from app.crosscutting.error_responses import bad_request
raise bad_request("Payload inválido")
```

```python
# Por qué: deja visible el flujo principal.
from app.crosscutting.timing import StageTimings

t = StageTimings()
with t.measure("db"):
    ...
```

## 🧩 Cómo extender sin romper nada
- Si agregás un setting, definilo en `config.py` con default seguro.
- Si agregás un error, sumalo en `error_responses.py` y mapealo en la API.
- Si agregás un middleware, registralo en `app/api/main.py`.
- Wiring: dependencias del runtime se cablean en `app/container.py`.
- Tests: unit en `apps/backend/tests/unit/`, integration si toca HTTP en `apps/backend/tests/integration/`.

## 🆘 Troubleshooting
- **Síntoma:** `/metrics` muestra “prometheus_client no instalado”.
- **Causa probable:** dependencia opcional ausente.
- **Dónde mirar:** `requirements.txt`.
- **Solución:** instalar `prometheus_client` o aceptar el no-op.
- **Síntoma:** 413 al subir archivos.
- **Causa probable:** `max_body_bytes` bajo.
- **Dónde mirar:** `config.py` y `middleware.py`.
- **Solución:** ajustar settings.
- **Síntoma:** no aparece `X-Request-Id`.
- **Causa probable:** middleware no registrado.
- **Dónde mirar:** `app/api/main.py`.
- **Solución:** registrar `RequestContextMiddleware`.
- **Síntoma:** 429 frecuentes.
- **Causa probable:** rate limit bajo.
- **Dónde mirar:** `config.py` y `rate_limit.py`.
- **Solución:** ajustar `rate_limit_rps`/`rate_limit_burst`.

## 🔎 Ver también
- `../api/README.md`
- `../interfaces/api/http/README.md`
- `../worker/README.md`
