# Backend (apps/backend)

## 🎯 Misión
Este directorio es el raíz operativo del backend: contiene el código de ejecución, la configuración, las migraciones, los scripts y la suite de pruebas necesarias para correr y evolucionar el servicio.

**Qué SÍ hace**
- Agrupa el código fuente del backend en `app/`.
- Centraliza migraciones, scripts de mantenimiento y configuración local.
- Incluye la suite de pruebas y su configuración.

**Qué NO hace**
- No contiene el frontend ni assets de UI (eso vive fuera de `apps/backend`).
- No define infraestructura de despliegue completa (eso está en `infra/` o `compose.yaml` del repo).

**Analogía (opcional)**
- Es el cuarto de máquinas del backend: cableado, planos y herramientas en un solo lugar.

## 🗺️ Mapa del territorio
| Recurso | Tipo | Responsabilidad (en humano) |
| :--- | :--- | :--- |
| 🧾 `.dockerignore` | Config | Exclusiones de Docker para el build de la imagen. |
| 🧾 `.env` | Config | Variables de entorno locales para el backend. |
| 📁 `alembic/` | Carpeta | Configuración y scripts de migración Alembic. |
| 🧾 `alembic.ini` | Config | Configuración de Alembic (CLI). |
| 📁 `app/` | Carpeta | Código ejecutable del backend (capas y entrypoints). |
| 🧾 `Dockerfile` | Config | Build de la imagen del backend. |
| 📁 `migrations/` | Carpeta | Carpeta auxiliar de migraciones/volúmenes (ver README). |
| 🧾 `pytest.ini` | Config | Configuración de Pytest (markers, coverage, etc.). |
| 📄 `rag-corp.lnk` | Documento | Acceso directo local (Windows) al backend. |
| 📄 `README.md` | Documento | Esta documentación. |
| 🧾 `requirements.txt` | Config | Dependencias Python del backend. |
| 📁 `scripts/` | Carpeta | Scripts de mantenimiento (admin, OpenAPI). |
| 📁 `tests/` | Carpeta | Tests unitarios, integración y e2e. |

## ⚙️ ¿Cómo funciona por dentro?
Input → Proceso → Output:
- **Input**: requests HTTP, jobs en cola (RQ) o ejecuciones de scripts.
- **Proceso**: `app/api/main.py` arma FastAPI, `app/container.py` cablea dependencias y los use cases orquestan el flujo.
- **Output**: respuestas HTTP, escritura en Postgres, encolado de jobs y/o storage de archivos.

Tecnologías/librerías usadas aquí:
- FastAPI, psycopg + pgvector, rq/redis, Alembic, pytest.

Flujo típico:
- Uvicorn importa `app.main:app` y sirve la API.
- Los routers llaman casos de uso en `app/application/usecases/`.
- Repositorios y servicios en `app/infrastructure/` ejecutan I/O.

## 🔗 Conexiones y roles
- Rol arquitectónico: Root de backend (composición y tooling).
- Recibe órdenes de: Uvicorn/Gunicorn, CLI de Alembic, scripts de `scripts/`.
- Llama a: `app/` como código fuente principal.
- Contratos y límites: el root no define lógica de negocio; solo organiza y configura.

## 👩‍💻 Guía de uso (Snippets)
```python
from app.api.main import create_fastapi_app

# Crea la instancia FastAPI (sin wrapper ASGI de rate limiting)
fastapi_app = create_fastapi_app()
```

## 🧩 Cómo extender sin romper nada
- Agrega lógica nueva en `app/application/usecases/` antes de tocar HTTP.
- Si necesitás persistencia nueva, crea el puerto en `app/domain/` y el adapter en `app/infrastructure/`.
- Para cambios de esquema, crea una migración en `alembic/versions/`.
- Expone endpoints en `app/interfaces/api/http/routers/` y DTOs en `schemas/`.
- Agrega tests en `tests/unit/` o `tests/integration/` según corresponda.

## 🆘 Troubleshooting
- Síntoma: `ModuleNotFoundError: No module named 'app'` → Causa probable: ejecutás fuera de `apps/backend` → Mirar `PYTHONPATH` o cwd.
- Síntoma: `Pool not initialized` → Causa probable: no se ejecutó `lifespan` → Mirar `app/api/main.py`.
- Síntoma: `alembic` no encuentra DB → Causa probable: `DATABASE_URL` faltante → Mirar `.env` y `alembic/env.py`.

## 🔎 Ver también
- [Código fuente (app)](./app/README.md)
- [Migraciones Alembic](./alembic/README.md)
- [Tests](./tests/README.md)
