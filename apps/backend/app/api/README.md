# API Application Layer

Esta capa contiene el **Entrypoint** de la aplicación web (FastAPI) y la orquestación del inicio del servicio.

## 🎯 Responsabilidad

- **Bootstrapping**: Inicializar la app, cargar configuración y conectar componentes.
- **Routing Global**: Definir prefijos (`/v1`, `/auth`) y montar routers de `interfaces`.
- **Middleware Chaining**: Configurar la cadena de responsabilidad (CORS, Auth, Logs, Rate Limit).
- **Lifespan Management**: Gestionar start/stop de pools de conexiones y recursos globales.

## 📂 Archivos Clave

| Archivo                 | Rol                  | Descripción                                                                |
| :---------------------- | :------------------- | :------------------------------------------------------------------------- |
| `main.py`               | **Composition Root** | Crea la instancia `FastAPI`, configura todo y la expone como `app` (ASGI). |
| `auth_routes.py`        | **Auth Controller**  | Endpoints de Login/Logout y gestión de usuarios (admin).                   |
| `admin_routes.py`       | **Admin Controller** | Provisionamiento de workspaces (ADR-008).                                  |
| `versioning.py`         | **Routing Alias**    | Maneja alias de compatibilidad (ej: `/api/v1` -> `/v1`).                   |
| `exception_handlers.py` | **Error Mapping**    | Traduce excepciones globales a RFC 7807 (JSON Problem Details).            |

## 🧩 Relación con otras capas

Esta capa **NO** contiene lógica de negocio.
Su trabajo es ser el "pegamento" entre:

1.  El servidor web (Uvicorn).
2.  La capa de presentación (`interfaces/api/http`).
3.  El contenedor de dependencias (`app/container.py`).

### Flujo de Inicialización (`main.lifespan`)

1.  Validar variables de entorno (Settings).
2.  Inicializar Pool de BD (`infrastructure.db.pool`).
3.  Ejecutar Dev Seed (si aplica).
4.  Servir peticiones...
5.  Cerrar Pool de BD (Shutdown).

## 🛡️ Seguridad

- Esta capa configura **CORS** y **Security Headers**.
- Define esquemas de **OpenAPI Security** (Bearer + API Key).
- Los endpoints de `auth_routes.py` son los únicos que generan tokens JWT.
