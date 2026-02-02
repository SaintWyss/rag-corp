# Crosscutting (preocupaciones transversales)

## 🎯 Misión
Agrupar utilidades transversales del backend: configuración, logging, métricas, middlewares, seguridad, errores tipados y helpers de observabilidad.

**Qué SÍ hace**
- Define settings y validaciones de entorno (Pydantic Settings).
- Estandariza errores HTTP (RFC7807) y excepciones internas.
- Provee middlewares, métricas, tracing y utilidades de timing.

**Qué NO hace**
- No implementa lógica de negocio ni acceso a datos.
- No define endpoints; solo helpers usados por la capa HTTP y worker.

**Analogía (opcional)**
- Es la “caja de herramientas” común que usan todas las capas.

## 🗺️ Mapa del territorio
| Recurso | Tipo | Responsabilidad (en humano) |
| :--- | :--- | :--- |
| 🐍 `config.py` | Archivo Python | Settings tipados y validaciones (env → config). |
| 🐍 `error_responses.py` | Archivo Python | RFC7807: errores HTTP estandarizados y factories. |
| 🐍 `exceptions.py` | Archivo Python | Excepciones internas tipadas (RAGError y derivadas). |
| 🐍 `logger.py` | Archivo Python | Logging JSON con contexto y redacción de secretos. |
| 🐍 `metrics.py` | Archivo Python | Métricas Prometheus (best‑effort/no‑op). |
| 🐍 `middleware.py` | Archivo Python | Middlewares de contexto y límites de body. |
| 🐍 `pagination.py` | Archivo Python | Cursor base64 + Page[T] para listados. |
| 🐍 `rate_limit.py` | Archivo Python | Rate limiting in‑memory (token bucket). |
| 📄 `README.md` | Documento | Esta documentación. |
| 🐍 `security.py` | Archivo Python | Security headers (CSP, HSTS, etc.). |
| 🐍 `streaming.py` | Archivo Python | Streaming SSE para respuestas del LLM. |
| 🐍 `timing.py` | Archivo Python | Timer + StageTimings para medir etapas. |
| 🐍 `tracing.py` | Archivo Python | Tracing OpenTelemetry opcional. |

## ⚙️ ¿Cómo funciona por dentro?
Input → Proceso → Output:
- **Input**: valores de env, requests HTTP, eventos de logging/métricas.
- **Proceso**: settings se cachean; middlewares agregan contexto; errores se formatean a RFC7807.
- **Output**: logs JSON, métricas Prometheus, respuestas con headers de seguridad.

Tecnologías/librerías usadas aquí:
- Pydantic Settings, FastAPI/Starlette (middlewares), prometheus_client (opcional).

Flujo típico:
- `get_settings()` valida config y se usa en composición (`app/api/main.py`).
- Middlewares agregan `request_id` y límites de payload.
- `error_responses` y `exception_handlers` estandarizan errores HTTP.

## 🔗 Conexiones y roles
- Rol arquitectónico: Crosscutting (shared utilities).
- Recibe órdenes de: API, worker, use cases.
- Llama a: `app/context.py`, settings, logging, métricas.
- Contratos y límites: no depende de infraestructura específica ni de dominio.

## 👩‍💻 Guía de uso (Snippets)
```python
from app.crosscutting.config import get_settings

settings = get_settings()
max_upload = settings.max_upload_bytes
```

## 🧩 Cómo extender sin romper nada
- Agrega nuevos settings en `config.py` con validadores claros.
- Si sumás un error nuevo, crea un `ErrorCode` y factory en `error_responses.py`.
- Mantén no‑op cuando la dependencia sea opcional (ej. métricas/tracing).
- En middlewares, no importes infraestructura ni repositorios.
- Actualiza tests unitarios de utilidades si el contrato cambia.

## 🆘 Troubleshooting
- Síntoma: `/metrics` responde texto “no instalado” → Causa: falta `prometheus_client` → Mirar `requirements.txt`.
- Síntoma: 413 al subir archivos → Causa: `max_upload_bytes` → Mirar `config.py`.
- Síntoma: headers de seguridad no aparecen → Causa: middleware no registrado → Mirar `app/api/main.py`.

## 🔎 Ver también
- [API composition](../api/README.md)
- [Interfaces HTTP](../interfaces/api/http/README.md)
- [Context](../context.py)
