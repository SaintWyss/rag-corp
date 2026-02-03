# app
Como un **motor armado**: acá están las capas, los contratos y el cableado que hacen funcionar el backend.

## 🎯 Misión
Este paquete concentra el **runtime del backend**: capas (Domain/Application/Infrastructure/Interfaces), entrypoints, composition root y assets versionados (prompts). Si querés entender “qué corre” cuando levantás el backend, este es el punto de partida.

Rutas rápidas por intención:
- Arquitectura por capas → `./application/README.md`, `./domain/README.md`, `./infrastructure/README.md`, `./interfaces/README.md`
- API HTTP (routers + schemas) → `./interfaces/api/http/README.md`
- Worker y jobs → `./worker/README.md`
- Prompts versionados → `./prompts/README.md`
- Composition root (DI manual) → `./container.py`

### Qué SÍ hace
- Implementa Clean Architecture con límites claros entre capas.
- Expone entrypoints estables: `app.main:app` (ASGI), `app.api.main.fastapi_app` (tests) y `app.jobs.process_document_job` (RQ).
- Centraliza wiring de dependencias en `container.py` usando puertos del dominio.
- Mantiene assets versionados de prompts para LLM.

### Qué NO hace (y por qué)
- No contiene scripts operativos ni tooling de repo. Razón: mezclar runtime con tooling genera imports cruzados y side-effects. Consecuencia: los scripts viven en `apps/backend/scripts/`.
- No contiene tests. Razón: tests dependen del runtime; el runtime no depende de tests. Consecuencia: las suites están en `apps/backend/tests/`.

## 🗺️ Mapa del territorio
| Recurso | Tipo | Responsabilidad (en humano) |
| :-- | :-- | :-- |
| `README.md` | Documento | Portada del paquete `app/`. |
| `api` | Carpeta | Composición FastAPI y endpoints operativos. |
| `application` | Carpeta | Casos de uso y servicios de aplicación (orquestación). |
| `audit.py` | Archivo Python | Helpers de auditoría best-effort del runtime. |
| `container.py` | Archivo Python | Composition root (DI manual, singletons). |
| `context.py` | Archivo Python | Contexto de request/job con `ContextVar` (request_id, tracing). |
| `crosscutting` | Carpeta | Config, errores RFC7807, logging, métricas, middlewares. |
| `domain` | Carpeta | Entidades, value objects y puertos (contratos). |
| `identity` | Carpeta | Autenticación, autorización y principal unificado (API key/JWT). |
| `infrastructure` | Carpeta | Adaptadores concretos (DB, queue, storage, LLM, parsers). |
| `interfaces` | Carpeta | Adaptadores entrantes (HTTP). |
| `jobs.py` | Archivo Python | Entrypoints estables de jobs para RQ. |
| `main.py` | Archivo Python | Entrypoint ASGI estable (`app.main:app`). |
| `prompts` | Carpeta | Assets de prompts versionados (policy + templates). |
| `worker` | Carpeta | Runtime del worker (RQ + health/metrics). |
## ⚙️ ¿Cómo funciona por dentro?
Input → Proceso → Output en el runtime del paquete.

- **Entrada (API)**: `uvicorn` importa `app.main:app`.
- **Composición**: `app/api/main.py` crea la FastAPI app, registra middlewares y routers.
- **Orquestación**: routers llaman casos de uso en `application/` usando puertos del dominio.
- **IO real**: infraestructura implementa esos puertos (DB, storage, LLM, queue).
- **Worker**: consume jobs RQ y ejecuta casos de uso sin HTTP.

## 🔗 Conexiones y roles
- **Rol arquitectónico:** source root del backend (runtime por capas).
- **Recibe órdenes de:** API (ASGI), worker (RQ) y scripts internos que importan entrypoints estables.
- **Llama a:** Postgres, Redis, storage S3/MinIO y proveedores LLM según settings.
- **Reglas de límites:** `domain/` no importa `infrastructure/` ni `interfaces/`; `application/` depende de puertos; `container.py` compone implementaciones.

## 👩‍💻 Guía de uso (Snippets)
```python
# ASGI para runtime
from app.main import app as asgi_app
assert callable(asgi_app)
```

```python
# FastAPI “puro” para tests
from app.api.main import fastapi_app
assert hasattr(fastapi_app, "openapi")
```

```python
# Use case desde el container
from app.container import get_answer_query_use_case
use_case = get_answer_query_use_case()
```

```python
# Job con path estable
from app.jobs import process_document_job
assert callable(process_document_job)
```

## 🧩 Cómo extender sin romper nada
- Si agregás un puerto nuevo, definilo en `domain/` y creá el adapter en `infrastructure/`.
- Cableá la implementación en `container.py` (factory `get_*`).
- Si es entrada HTTP, sumá router en `interfaces/api/http/routers/` y schemas en `interfaces/api/http/schemas/`.
- Tests: unit en `tests/unit/`, integration en `tests/integration/`, e2e en `tests/e2e/`.

## 🆘 Troubleshooting
- **Síntoma:** `ModuleNotFoundError: No module named 'app'`.
- **Causa probable:** ejecutás desde un directorio incorrecto.
- **Dónde mirar:** `pwd` y `PYTHONPATH`.
- **Solución:** correr desde `apps/backend/`.
- **Síntoma:** `/metrics` devuelve 401/403.
- **Causa probable:** auth de métricas habilitada.
- **Dónde mirar:** `app/crosscutting/config.py` (`metrics_require_auth`).
- **Solución:** enviar `X-API-Key` con permiso o desactivar flag.
- **Síntoma:** CORS bloquea requests.
- **Causa probable:** `allowed_origins` no incluye el origen.
- **Dónde mirar:** `app/crosscutting/config.py` y `app/api/main.py`.
- **Solución:** ajustar config y reiniciar.
- **Síntoma:** rate limit demasiado agresivo (429).
- **Causa probable:** límites bajos.
- **Dónde mirar:** `app/crosscutting/config.py` (`rate_limit_rps`, `rate_limit_burst`).
- **Solución:** ajustar settings o enviar API key para identificar cliente.
- **Síntoma:** worker no procesa jobs.
- **Causa probable:** Redis/cola sin conectar o worker apagado.
- **Dónde mirar:** `app/worker/README.md` y logs del worker.
- **Solución:** levantar Redis/worker y validar `REDIS_URL`.

## 🔎 Ver también
- `./api/README.md`
- `./application/README.md`
- `./domain/README.md`
- `./infrastructure/README.md`
- `./interfaces/README.md`
- `./worker/README.md`
- `../README.md`
