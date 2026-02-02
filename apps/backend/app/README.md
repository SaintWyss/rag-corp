# Backend Application (paquete `app`)

## 🎯 Misión
Este paquete contiene todo el código ejecutable del backend. Aquí viven las capas de Clean Architecture (dominio, aplicación, infraestructura e interfaces), el wiring de dependencias y los entrypoints de API/worker.

**Qué SÍ hace**
- Define entidades y contratos centrales del negocio (Domain).
- Orquesta casos de uso y reglas de flujo (Application).
- Implementa adaptadores a DB, colas, storage y LLMs (Infrastructure).
- Expone API HTTP y jobs de worker (Interfaces/Worker).

**Qué NO hace**
- No contiene scripts de desarrollo/CI (eso vive en `../scripts`).
- No contiene pruebas (ver `../tests`).

**Analogía (opcional)**
- Es el motor completo del backend: piezas internas, cableado y puntos de entrada, pero no el “taller” ni el “manual de pruebas”.

## 🗺️ Mapa del territorio
| Recurso | Tipo | Responsabilidad (en humano) |
| :--- | :--- | :--- |
| 📁 `api/` | Carpeta | Composición de FastAPI, rutas auxiliares y versionado. |
| 📁 `application/` | Carpeta | Casos de uso y servicios de aplicación. |
| 🐍 `audit.py` | Archivo Python | Emisión de eventos de auditoría (best-effort). |
| 🐍 `container.py` | Archivo Python | Composition root: factories y singletons de dependencias. |
| 🐍 `context.py` | Archivo Python | Contexto request/job (request_id, tracing, etc.). |
| 📁 `crosscutting/` | Carpeta | Utilidades transversales (config, logging, errores, métricas). |
| 📁 `domain/` | Carpeta | Entidades, value objects y contratos del dominio. |
| 📁 `identity/` | Carpeta | Auth, roles, permisos, RBAC y validaciones de acceso. |
| 📁 `infrastructure/` | Carpeta | Adaptadores salientes: DB, storage, colas, parsers, LLMs. |
| 📁 `interfaces/` | Carpeta | Adaptadores entrantes: API HTTP y mapeo de DTOs. |
| 🐍 `jobs.py` | Archivo Python | Entrypoints estables para jobs RQ. |
| 🐍 `main.py` | Archivo Python | Entrypoint ASGI (`app.main:app`). |
| 📁 `prompts/` | Carpeta | Templates de prompts y políticas (archivos .md). |
| 📄 `README.md` | Documento | Este documento. |
| 📁 `worker/` | Carpeta | Proceso worker RQ + health/metrics. |

## ⚙️ ¿Cómo funciona por dentro?
Input → Proceso → Output:
- **Input**: request HTTP (FastAPI en `api/`) o job RQ (en `worker/`).
- **Proceso**: router → DTO → caso de uso (`application/usecases`) → repos/servicios (`domain` + `infrastructure`).
- **Output**: respuesta HTTP (RFC7807 si hay error) o side-effects (DB, storage, métricas).

Tecnologías/librerías usadas aquí:
- FastAPI (capa API), Pydantic (schemas), psycopg + pgvector (DB), Redis/RQ (worker).

Flujo típico:
- `app.api.main.create_fastapi_app()` crea la app y registra routers.
- `app.container` arma repositorios/servicios y los inyecta en use cases.
- `app.main:app` expone el ASGI para Uvicorn/Gunicorn.

## 🔗 Conexiones y roles
- Rol arquitectónico: Source Root (Composition + capas internas).
- Recibe órdenes de: Uvicorn/Gunicorn (`app.main:app`), worker RQ, scripts de CLI.
- Llama a: Domain, Application, Infrastructure, Interfaces, Crosscutting.
- Contratos y límites: Domain no depende de Infrastructure; Application orquesta vía puertos; Interfaces solo adaptan HTTP.

## 👩‍💻 Guía de uso (Snippets)
```python
from fastapi.testclient import TestClient
from app.api.main import fastapi_app

client = TestClient(fastapi_app)
resp = client.get("/healthz")
assert resp.status_code == 200
```

## 🧩 Cómo extender sin romper nada
- Crea primero el caso de uso en `application/usecases/`.
- Define/actualiza contratos en `domain/` (repos/services) si aplica.
- Implementa adaptadores en `infrastructure/`.
- Registra el cableado en `container.py`.
- Expone el endpoint en `interfaces/api/http/routers/` + schema en `schemas/`.
- Agrega/ajusta tests en `tests/unit` o `tests/integration`.

## 🆘 Troubleshooting
- Síntoma: `ModuleNotFoundError: No module named 'app'` → Causa: ejecutás fuera de `apps/backend` → Mirar `PYTHONPATH` y cwd.
- Síntoma: use cases usan repos in-memory inesperados → Causa: `APP_ENV=test` → Mirar `app/container.py` y env `APP_ENV`.
- Síntoma: `Pool no inicializado` → Causa: no se ejecutó lifespan → Mirar `app/api/main.py` e inicialización del pool.

## 🔎 Ver también
- [Backend root](../README.md)
- [Application](./application/README.md)
- [Domain](./domain/README.md)
- [Infrastructure](./infrastructure/README.md)
- [Interfaces HTTP](./interfaces/api/http/README.md)
- [Worker](./worker/README.md)
