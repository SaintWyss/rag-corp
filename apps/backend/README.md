# backend
Como un **taller operativo**: acá vivís entrypoints, migraciones, scripts y tests para correr y operar el backend.

## 🎯 Misión
Este directorio es la **unidad operativa** del backend. Desde aquí se levanta la API, se ejecuta el worker, se mantienen migraciones y se corre la suite de pruebas. El código de negocio está en `app/`, pero todo lo que necesitas para **operarlo** y **testearlo** vive en este nivel.

Si venís con una intención concreta, estas son las rutas rápidas:
- Arquitectura y capas → `./app/README.md`
- HTTP (routers + schemas) → `./app/interfaces/api/http/README.md`
- Worker y jobs → `./app/worker/README.md`
- DB y repositorios → `./app/infrastructure/db/README.md` y `./app/infrastructure/repositories/README.md`
- Migraciones → `./alembic/README.md`
- Scripts operativos → `./scripts/README.md`
- Tests (unit/integration/e2e) → `./tests/README.md`

### Qué SÍ hace
- Agrupa runtime, tooling y pruebas del backend en un solo lugar.
- Expone entrypoints estables para API y worker (ASGI y RQ).
- Centraliza configuración operativa del backend (dependencias, pytest y Alembic).

### Qué NO hace (y por qué)
- No define lógica de negocio. Razón: el negocio vive en `app/` por capas (Domain/Application/Infrastructure/Interfaces). Consecuencia: los cambios funcionales se implementan en `app/`, no en scripts o configuración.
- No describe infraestructura completa de despliegue. Razón: el entorno (compose/infra/CI) puede variar por deployment. Consecuencia: este directorio es “app + tooling”, no “infra como código”.

## 🗺️ Mapa del territorio
| Recurso | Tipo | Responsabilidad (en humano) |
| :-- | :-- | :-- |
| `.dockerignore` | Config | Evita que archivos innecesarios entren al build de Docker. |
| `.env` | Config | Variables locales de entorno para el backend (no es código). |
| `Dockerfile` | Config | Construye la imagen del backend. |
| `README.md` | Documento | Portada y mapa operativo del backend. |
| `alembic` | Carpeta | Migraciones del esquema de base de datos. |
| `alembic.ini` | Config | Configuración de Alembic (CLI de migraciones). |
| `app` | Carpeta | Código del backend por capas y entrypoints. |
| `pytest.ini` | Config | Configuración de Pytest (markers, coverage, warnings). |
| `requirements.txt` | Config | Dependencias Python del backend. |
| `scripts` | Carpeta | Scripts operativos (bootstrap, export de contratos). |
| `tests` | Carpeta | Tests unit/integration/e2e y fixtures compartidas. |
## ⚙️ ¿Cómo funciona por dentro?
Input → Proceso → Output, a nivel de operación del backend.

- **API (ASGI)**
- Input: requests HTTP.
- Proceso: FastAPI compone routers → use cases → repos/adapters.
- Output: JSON, streaming o errores RFC7807.
- **Worker (RQ + Redis)**
- Input: jobs en Redis (paths estables).
- Proceso: consume jobs y ejecuta casos de uso pesados (ingesta, parsing, embeddings).
- Output: persistencia, logs y métricas.
- **Migraciones (Alembic)**
- Input: comando `alembic ...`.
- Proceso: aplica revisiones en orden y actualiza `alembic_version`.
- Output: esquema actualizado.
- **Testing (Pytest)**
- Input: comando `pytest` con markers.
- Proceso: carga fixtures, ejecuta unit/integration/e2e según markers.
- Output: reporte + coverage (si está habilitado).

## 🔗 Conexiones y roles
- **Rol arquitectónico:** root operativo del backend (runtime + tooling + pruebas).
- **Recibe órdenes de:** `uvicorn` (API), worker RQ, CLI de Alembic, scripts CLI.
- **Llama a:** `app/` como núcleo del sistema y servicios externos (DB, Redis, storage, LLM) según settings.
- **Reglas de límites:** la lógica de negocio está en `app/`; acá solo se opera, se compone y se prueba.

## 👩‍💻 Guía de uso (Snippets)
```python
# Import ASGI para uvicorn
from app.main import app as asgi_app
assert callable(asgi_app)
```

```bash
# Levantar API local
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

```bash
# Migraciones
alembic upgrade head
```

```bash
# Tests
pytest -q
```

Variables de entorno comunes (según entorno/compose):
- `DATABASE_URL` (Postgres).
- `REDIS_URL` (Redis/RQ).
- `GOOGLE_API_KEY` (LLM/embeddings si se usan providers reales).

## 🧩 Cómo extender sin romper nada
- Si agregás un caso de uso, cablealo en `app/container.py` y expone su entrypoint desde `app/application/usecases/`.
- Si agregás infraestructura nueva (DB/cola/storage), creá el adapter en `app/infrastructure/` y conéctalo en el container.
- Si agregás un endpoint, sumalo en `app/interfaces/api/http/routers/` y schemas en `schemas/`.
- Tests: unit en `tests/unit/`, integration en `tests/integration/`, e2e en `tests/e2e/`.

## 🆘 Troubleshooting
- **Síntoma:** `ModuleNotFoundError: No module named 'app'`.
- **Causa probable:** ejecutás desde un directorio incorrecto.
- **Dónde mirar:** `pwd` / `PYTHONPATH`.
- **Solución:** ejecutar comandos desde `apps/backend/`.
- **Síntoma:** migraciones fallan por conexión.
- **Causa probable:** `DATABASE_URL` ausente o incorrecta.
- **Dónde mirar:** `.env` y `alembic/env.py`.
- **Solución:** setear `DATABASE_URL` válido y reintentar.
- **Síntoma:** worker no consume jobs.
- **Causa probable:** `REDIS_URL` incorrecta o worker apagado.
- **Dónde mirar:** settings y logs del worker.
- **Solución:** corregir Redis y levantar worker.
- **Síntoma:** `/metrics` devuelve 401/403.
- **Causa probable:** auth de métricas habilitada.
- **Dónde mirar:** `app/crosscutting/config.py` (`metrics_require_auth`).
- **Solución:** enviar `X-API-Key` con permiso o desactivar el flag.
- **Síntoma:** `UndefinedTable` en tests de integración.
- **Causa probable:** migraciones no aplicadas en la DB de test.
- **Dónde mirar:** `alembic/README.md` y `tests/integration/README.md`.
- **Solución:** aplicar migraciones antes de correr tests.

## 🔎 Ver también
- `./app/README.md`
- `./app/interfaces/api/http/README.md`
- `./app/worker/README.md`
- `./app/infrastructure/db/README.md`
- `./app/infrastructure/repositories/README.md`
- `./alembic/README.md`
- `./scripts/README.md`
- `./tests/README.md`
