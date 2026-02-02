# API Composition (FastAPI)

## 🎯 Misión
Esta carpeta compone la aplicación FastAPI: registra middlewares, routers, endpoints operativos (health/metrics) y el mapeo centralizado de errores a RFC7807.

**Qué SÍ hace**
- Construye la instancia FastAPI y su OpenAPI.
- Registra middlewares transversales (CORS, límites, contexto, seguridad).
- Incluye routers de negocio y rutas auxiliares (auth/admin).
- Mapea excepciones de la app a respuestas RFC7807.

**Qué NO hace**
- No implementa reglas de negocio (eso vive en `app/application/usecases/`).
- No contiene lógica de persistencia (repos en `app/infrastructure/`).

**Analogía (opcional)**
- Es la torre de control: coordina entradas/salidas sin pilotear los aviones.

## 🗺️ Mapa del territorio
| Recurso | Tipo | Responsabilidad (en humano) |
| :--- | :--- | :--- |
| 🐍 `admin_routes.py` | Archivo Python | Endpoints admin (provisionamiento) + auditoría best‑effort. |
| 🐍 `auth_routes.py` | Archivo Python | Endpoints de login/logout/me y admin de usuarios. |
| 🐍 `exception_handlers.py` | Archivo Python | Registro de handlers y mapeo de errores a RFC7807. |
| 🐍 `main.py` | Archivo Python | Composición principal de FastAPI + health/metrics. |
| 📄 `README.md` | Documento | Esta documentación. |
| 🐍 `versioning.py` | Archivo Python | Alias de rutas (compatibilidad /api/v1). |

## ⚙️ ¿Cómo funciona por dentro?
Input → Proceso → Output:
- **Input**: import de `app.api.main.app` por Uvicorn/Gunicorn.
- **Proceso**: `create_fastapi_app()` registra middlewares, routers y handlers; luego se envuelve con `RateLimitMiddleware`.
- **Output**: ASGI app lista para servir HTTP.

Tecnologías/librerías usadas aquí:
- FastAPI, Pydantic (DTOs en rutas), Starlette (middlewares).

Flujo típico:
- `create_fastapi_app()` crea la app y define `/healthz`, `/readyz`, `/metrics`.
- `include_versioned_routes()` agrega alias `/api/v1`.
- `register_exception_handlers()` mapea errores internos a RFC7807.

## 🔗 Conexiones y roles
- Rol arquitectónico: Interface (HTTP composition).
- Recibe órdenes de: servidor ASGI (Uvicorn/Gunicorn).
- Llama a: `app.interfaces.api.http.routes`, `app.container`, `app.crosscutting`.
- Contratos y límites: no contiene reglas de negocio ni acceso a DB directo.

## 👩‍💻 Guía de uso (Snippets)
```python
from app.api.main import create_fastapi_app

app = create_fastapi_app()
openapi = app.openapi()
```

## 🧩 Cómo extender sin romper nada
- Agrega nuevos routers en `app/interfaces/api/http/routers/`.
- Inclúyelos en `app/interfaces/api/http/router.py`.
- Si necesitás una ruta operativa nueva, declárala en `app/api/main.py`.
- Para nuevos errores tipados, amplía `app/crosscutting/error_responses.py`.
- Revisa permisos en `app/identity/*` si el endpoint es sensible.

## 🆘 Troubleshooting
- Síntoma: `422` inesperado → Causa probable: validación Pydantic → Mirar schema en `app/interfaces/api/http/schemas/`.
- Síntoma: `/metrics` devuelve 401/403 → Causa probable: permiso `ADMIN_METRICS` → Mirar `app/identity/rbac.py`.
- Síntoma: CORS bloquea el frontend → Causa probable: `allowed_origins` → Mirar `app/crosscutting/config.py`.

## 🔎 Ver también
- [Interfaces HTTP](../interfaces/api/http/README.md)
- [Crosscutting](../crosscutting/README.md)
- [Root app](../README.md)
