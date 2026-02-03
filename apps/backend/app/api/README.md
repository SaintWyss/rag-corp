# api
Como una **torre de control**: compone FastAPI, aplica middlewares y publica endpoints operativos.

## 🎯 Misión
Este módulo construye la aplicación FastAPI y expone los entrypoints ASGI que ejecuta el servidor. Es donde se concentran decisiones transversales: lifecycle, middlewares, composición de routers, errores RFC7807 y endpoints de operación.

### Qué SÍ hace
- Crea `fastapi_app` (FastAPI “pura”) y `app` (ASGI envuelta con rate limiting).
- Registra middlewares de contexto, límites de body, headers de seguridad y CORS.
- Incluye routers de negocio y rutas auxiliares (`/auth`, `/admin`).
- Expone endpoints `/healthz`, `/readyz` y `/metrics`.
- Enriquecen OpenAPI con seguridad dual (API key + JWT) y ajustes de parámetros.

### Qué NO hace (y por qué)
- No implementa reglas de negocio. Razón: las decisiones viven en `application/`. Consecuencia: este módulo solo compone HTTP, no decide permisos/estados.
- No accede a DB para lógica funcional. Razón: el IO real está en `infrastructure/`. Consecuencia: la API solo usa repos mínimos para health/seed.

## 🗺️ Mapa del territorio
| Recurso | Tipo | Responsabilidad (en humano) |
| :-- | :-- | :-- |
| `README.md` | Documento | Guía de composición FastAPI. |
| `admin_routes.py` | Archivo Python | Endpoints administrativos `/admin/*`. |
| `auth_routes.py` | Archivo Python | Endpoints `/auth/*` (login/logout/me). |
| `exception_handlers.py` | Archivo Python | Handlers de excepciones y mapeo a RFC7807. |
| `main.py` | Archivo Python | Composición FastAPI, middlewares y endpoints operativos. |
| `versioning.py` | Archivo Python | Alias `/api/v1` sobre el router principal. |
## ⚙️ ¿Cómo funciona por dentro?
Input → Proceso → Output.

- **Input:** requests HTTP.
- **Proceso:**
- `create_fastapi_app()` registra middlewares y routers.
- `lifespan()` inicializa y cierra el pool de DB.
- `app = RateLimitMiddleware(fastapi_app)` envuelve el ASGI final.
- `_custom_openapi()` agrega esquemas de seguridad y marca `workspace_id` requerido en rutas `/v1/*`.
- **Output:** respuestas HTTP (JSON o RFC7807) y endpoints operativos.

## 🔗 Conexiones y roles
- **Rol arquitectónico:** Interface/Composition (borde HTTP).
- **Recibe órdenes de:** servidor ASGI (`uvicorn`, `gunicorn`).
- **Llama a:** `interfaces/api/http` (routers), `crosscutting` (middlewares/errores), `infrastructure/db` (pool) y seeds de `application`.
- **Reglas de límites:** sin reglas de negocio ni SQL directo.

## 👩‍💻 Guía de uso (Snippets)
```python
# ASGI final (rate limit aplicado)
from app.api.main import app
```

```python
# FastAPI “pura” para tests
from app.api.main import fastapi_app
```

```bash
# Levantar API local
uvicorn app.api.main:app --host 0.0.0.0 --port 8000
```

## 🧩 Cómo extender sin romper nada
- Si agregás un router nuevo, incluilo en `interfaces/api/http/router.py` y montalo acá vía `include_router`.
- Si agregás un middleware nuevo, registralo en `create_fastapi_app()` respetando el orden.
- Si agregás endpoints operativos, documentalos en `_custom_openapi()`.
- Cableado: dependencias concretas se seleccionan en `app/container.py`.
- Tests: unit en `apps/backend/tests/unit/`, integration en `apps/backend/tests/integration/`, e2e en `apps/backend/tests/e2e/`.

## 🆘 Troubleshooting
- **Síntoma:** `/metrics` devuelve 401/403.
- **Causa probable:** `metrics_require_auth=true`.
- **Dónde mirar:** `app/crosscutting/config.py` y `app/api/main.py`.
- **Solución:** enviar `X-API-Key` con permiso o desactivar el flag.
- **Síntoma:** `/healthz` reporta `db=disconnected`.
- **Causa probable:** `DATABASE_URL` incorrecta o DB caída.
- **Dónde mirar:** logs del startup y `infrastructure/db/pool.py`.
- **Solución:** corregir URL y reiniciar.
- **Síntoma:** CORS bloquea requests.
- **Causa probable:** origen no permitido.
- **Dónde mirar:** `crosscutting/config.py` (`allowed_origins`).
- **Solución:** ajustar settings y reiniciar.
- **Síntoma:** OpenAPI muestra seguridad incorrecta.
- **Causa probable:** reglas de `_custom_openapi()` no cubren la ruta.
- **Dónde mirar:** `app/api/main.py`.
- **Solución:** ajustar reglas por path/prefijo.
- **Síntoma:** 429 frecuentes.
- **Causa probable:** límites bajos en rate limit.
- **Dónde mirar:** `crosscutting/config.py` (`rate_limit_rps`, `rate_limit_burst`).
- **Solución:** ajustar límites o enviar API key.

## 🔎 Ver también
- `../interfaces/api/http/README.md`
- `../crosscutting/README.md`
- `../container.py`
- `../../README.md`
