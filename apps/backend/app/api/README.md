# Layer: API (Composition Root)

## 🎯 Misión

Esta carpeta es el **Punto de Entrada** y **Raíz de Composición** de la aplicación web.
Aquí es donde se "ensambla" el servidor: se configura FastAPI, se registran los middlewares, se montan las rutas y se maneja el ciclo de vida (startup/shutdown).

**Qué SÍ hace:**

- Inicializa la instancia `FastAPI`.
- Configura Middlewares globales (CORS, Rate Limit, Security Headers).
- Gestiona el `lifespan` (conexión a DB al iniciar, desconexión al cerrar).
- Define rutas " administrativas" o de "fontanería" (`/healthz`, `/metrics`, `/auth`).
- Integra las rutas de negocio desde `interfaces/api`.

**Qué NO hace:**

- No contiene lógica de negocio (eso va en `application`).
- No define los esquemas de datos JSON (eso va en `interfaces`).
- No implementa los controladores de endpoints de negocio (eso va en `interfaces/routers`).

**Analogía:**
Si la app es un coche, este módulo es el **Chasis y el contacto de encendido**. Conecta el motor, las ruedas y la carrocería, y se asegura de que todo arranque cuando giras la llave.

## 🗺️ Mapa del territorio

| Recurso                 | Tipo       | Responsabilidad (en humano)                                        |
| :---------------------- | :--------- | :----------------------------------------------------------------- |
| `admin_routes.py`       | 🐍 Archivo | Endpoints solo para administradores (ej. gestión de usuarios).     |
| `auth_routes.py`        | 🐍 Archivo | Endpoints de autenticación (login, refresh, me).                   |
| `exception_handlers.py` | 🐍 Archivo | Manejo global de errores (transforma excepciones en JSON RFC7807). |
| `main.py`               | 🐍 Archivo | **Entrypoint Principal**. Crea la app `app` y `fastapi_app`.       |
| `versioning.py`         | 🐍 Archivo | Utilidades para versionado de API (alias `/api/v1` -> `/v1`).      |

## ⚙️ ¿Cómo funciona por dentro?

El archivo `main.py` es el protagonista:

1.  **Lifespan:** Al arrancar, valida configuración (`get_settings`) e inicializa el pool de base de datos (`init_pool`).
2.  **Factory:** `create_fastapi_app()` instancia FastAPI.
3.  **Middlewares:** Se añaden capas de seguridad y observabilidad (`SecurityHeaders`, `BodyLimit`, `Metrics`).
4.  **Routing:** Incluye los routers de `interfaces.api.http.routes` (Negocio) y los locales (`auth`, `admin`).
5.  **OpenAPI Custom:** Reescribe el esquema OpenAPI para soportar autenticación dual (API Key + JWT) corrección de docs.

## 🔗 Conexiones y roles

- **Rol Arquitectónico:** Composition Root / Framework Binding.
- **Recibe órdenes de:** Servidor ASGI (Uvicorn/Hypercorn).
- **Llama a:**
  - `interfaces/api/http` (para montar rutas de negocio).
  - `infrastructure/db` (para iniciar pool).
  - `application/dev_seed_*` (para sembrar datos dev).

## 👩‍💻 Guía de uso (Snippets)

### Cómo se inicia la app (Contexto Uvicorn)

El servidor Uvicorn busca la variable `app` en `main.py`.

```python
from app.api.main import app

# 'app' es en realidad un Middleware ASGI (RateLimitMiddleware)
# que envuelve a la instancia real de FastAPI ('fastapi_app').
```

### Agregar un nuevo Middleware global

En `main.py`, dentro de `create_fastapi_app()`:

```python
# ...
app.add_middleware(SecurityHeadersMiddleware)
app.add_middleware(MiNuevoMiddleware)  # <--- Aquí
# ...
```

## 🧩 Cómo extender sin romper nada

1.  **Nuevas Rutas de Negocio:** No las agregues aquí. Agrégalas en `app/interfaces/api/http/routes.py`.
2.  **Configuración de Inicio:** Si necesitas ejecutar código al inicio (ej. cargar un modelo ML), úsalo dentro de la función `lifespan` en `main.py`.

## 🆘 Troubleshooting

- **Síntoma:** "404 Not Found" en endpoints `/v1/...`.
  - **Causa:** El router no está incluido en `main.py` o el prefijo está mal.
- **Síntoma:** Error de CORS al llamar desde el frontend.
  - **Solución:** Revisa `_get_allowed_origins()` en `main.py` y la variable de entorno `CORS_ORIGINS`.

## 🔎 Ver también

- [Interfaces HTTP (Routers de Negocio)](../interfaces/api/http/README.md)
- [Configuración (Settings)](../crosscutting/README.md)
