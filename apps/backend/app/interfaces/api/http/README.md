# API HTTP (FastAPI)

## 🎯 Misión
Implementar el adaptador HTTP del backend: routers, schemas, dependencias y mapeo de errores a RFC7807.

**Qué SÍ hace**
- Define rutas HTTP por feature (workspaces, documents, query, admin).
- Mapea DTOs de request/response con Pydantic.
- Traduce errores de use cases a RFC7807.

**Qué NO hace**
- No contiene lógica de negocio ni acceso a DB.
- No ejecuta tareas de background (eso va al worker/cola).

**Analogía (opcional)**
- Es el “mostrador” que recibe pedidos y entrega respuestas formateadas.

## 🗺️ Mapa del territorio
| Recurso | Tipo | Responsabilidad (en humano) |
| :--- | :--- | :--- |
| 🐍 `dependencies.py` | Archivo Python | Helpers comunes (actor, metadata, uploads). |
| 🐍 `error_mapping.py` | Archivo Python | Mapear errores de use cases a RFC7807. |
| 📄 `README.md` | Documento | Esta documentación. |
| 🐍 `router.py` | Archivo Python | Router raíz y composición de sub‑routers. |
| 📁 `routers/` | Carpeta | Endpoints por feature. |
| 🐍 `routes.py` | Archivo Python | Shim de compatibilidad (re‑export router). |
| 📁 `schemas/` | Carpeta | DTOs HTTP (Pydantic). |

## ⚙️ ¿Cómo funciona por dentro?
Request → Router → Schema/DTO → Application → Response:
- **Request**: FastAPI recibe la llamada.
- **Router**: `router.py` enruta al módulo correcto.
- **Schema**: Pydantic valida el payload.
- **Application**: se ejecuta el caso de uso.
- **Response**: se mapea a JSON o RFC7807 si hay error.

Tecnologías/librerías usadas aquí:
- FastAPI, Pydantic.

Flujo típico:
- `routers/*` usa helpers en `dependencies.py`.
- `error_mapping.py` traduce `DocumentError`/`WorkspaceError`.
- `router.py` compone sub‑routers con responses RFC7807.

## 🔗 Conexiones y roles
- Rol arquitectónico: Interface (HTTP adapter).
- Recibe órdenes de: clientes HTTP.
- Llama a: Application (use cases) y Crosscutting (errores, config).
- Contratos y límites: no negocio, no SQL.

## 👩‍💻 Guía de uso (Snippets)
```python
from app.interfaces.api.http.router import build_router

api_router = build_router()
```

## 🧩 Cómo extender sin romper nada
- Agrega un router nuevo en `routers/`.
- Define los schemas en `schemas/`.
- Inclúyelo en `router.py`.
- Mapea errores nuevos en `error_mapping.py`.

## 🆘 Troubleshooting
- Síntoma: `422 Unprocessable Entity` → Causa probable: schema inválido → Revisar `schemas/`.
- Síntoma: `500` sin RFC7807 → Causa probable: excepción sin mapping → Revisar `error_mapping.py` y `api/exception_handlers.py`.
- Síntoma: rutas no aparecen → Causa probable: router no incluido → Revisar `router.py`.

## 🔎 Ver también
- [Routers](./routers/README.md)
- [Schemas](./schemas/README.md)
- [API composition](../../../api/README.md)
