# Backend (apps/backend)

## 🎯 Misión

Este directorio es el **paquete ejecutable** del backend: desde acá se levanta la API, se ejecuta el worker de tareas, se mantienen las migraciones de base de datos y se corre la suite de pruebas.

En otras palabras: si querés **correr** el backend o **entender cómo se opera**, empezás por acá. Si querés **entender la arquitectura interna**, el código vive en `app/`.

Analogía breve: este directorio es el **taller** (procesos y herramientas). La “ingeniería” del producto vive en `app/`.

### Índice rápido (a dónde ir según tu objetivo)

- **Arquitectura interna (capas, contratos, ports/adapters)** → [`app/README.md`](./app/README.md)
- **Endpoints HTTP (routers + DTOs)** → [`app/interfaces/api/http/README.md`](./app/interfaces/api/http/README.md)
- **Worker y cola (jobs asíncronos)** → [`app/worker/README.md`](./app/worker/README.md)
- **Base de datos (pool/sesiones) + repositorios** → [`app/infrastructure/db/README.md`](./app/infrastructure/db/README.md) y [`app/infrastructure/repositories/README.md`](./app/infrastructure/repositories/README.md)
- **Migraciones (historial del esquema)** → [`alembic/README.md`](./alembic/README.md)
- **Scripts operativos (OpenAPI, admin, tooling)** → [`scripts/README.md`](./scripts/README.md)
- **Tests (unit/integration/e2e)** → [`tests/README.md`](./tests/README.md)

**Qué SÍ hace**

- Agrupa el backend como unidad operativa: **código** (`app/`), **migraciones** (`alembic/`), **scripts** (`scripts/`) y **tests** (`tests/`).
- Define puntos de entrada estables para runtime:
  - API (servida por un servidor ASGI como `uvicorn`).
  - Worker (proceso que consume jobs desde Redis).

- Centraliza dependencias Python del backend (`requirements.txt`) y configuración de tests (`pytest.ini`).

**Qué NO hace (y por qué)**

- No describe el despliegue completo (red, servicios, volúmenes) porque eso depende del entorno (local/CI/prod) y se define afuera (por ejemplo en `compose.yaml` / `infra/`).
  - **Consecuencia:** este directorio es “app + tooling”, no “infraestructura como código” completa.

- No contiene lógica de negocio porque esa lógica debe vivir dentro de `app/` y estar separada por capas (Domain/Application/Infrastructure/Interfaces).
  - **Consecuencia:** los cambios funcionales se hacen en `app/`, no en scripts/configs sueltas.

---

## 🗺️ Mapa del territorio

| Recurso               | Tipo       | Responsabilidad (en humano)                                                                   |
| :-------------------- | :--------- | :-------------------------------------------------------------------------------------------- |
| 🧾 `.dockerignore`    | Config     | Define qué archivos NO entran al build de Docker (reduce tamaño y evita leaks de artefactos). |
| 🧾 `Dockerfile`       | Config     | Construye la imagen del backend (instala deps y prepara el runtime).                          |
| 📁 `alembic/`         | 📁 Carpeta | Migraciones versionadas del esquema de base de datos (historial reproducible).                |
| 🧾 `alembic.ini`      | Config     | Configuración de la CLI de Alembic.                                                           |
| 📁 `app/`             | 📁 Carpeta | Código del backend (capas, puertos/adaptadores y entrypoints).                                |
| 🧾 `pytest.ini`       | Config     | Config de Pytest (markers, discovery, plugins, etc.).                                         |
| 📄 `rag-corp.lnk`     | Documento  | Acceso directo local (Windows). No participa del runtime.                                     |
| 🧾 `requirements.txt` | Config     | Dependencias Python del backend.                                                              |
| 📁 `scripts/`         | 📁 Carpeta | Scripts operativos (por ejemplo exportar OpenAPI o tareas admin).                             |
| 📁 `tests/`           | 📁 Carpeta | Tests unitarios/integración/e2e y fixtures.                                                   |
| 📄 `README.md`        | Documento  | Portada + mapa general del backend.                                                           |

---

## ⚙️ ¿Cómo funciona por dentro?

Este backend tiene tres “modos” principales: **API**, **worker** y **tooling**.

### API: HTTP sobre ASGI (FastAPI + Uvicorn)

**ASGI** es un estándar de servidor web en Python: permite que un servidor como `uvicorn` ejecute tu app.

- **Entrada:** requests HTTP.
- **Procesamiento:** routers HTTP → casos de uso (Application) → puertos/adaptadores (Infrastructure) → respuesta.
- **Salida:** JSON / streaming / errores normalizados.

📌 Para profundizar:

- Arquitectura por capas → [`app/README.md`](./app/README.md)
- HTTP (routers y schemas) → [`app/interfaces/api/http/README.md`](./app/interfaces/api/http/README.md)

### Worker: cola de trabajos (RQ + Redis)

Un **worker** es un proceso separado de la API que ejecuta tareas pesadas (ingesta, parsing, tareas batch). En vez de hacerlo durante un request, se encola un trabajo en Redis y el worker lo ejecuta.

- **Entrada:** jobs encolados.
- **Procesamiento:** ejecuta funciones de trabajo y registra resultados (DB / storage).
- **Salida:** efectos (persistencia, archivos procesados, logs/métricas).

📌 Para profundizar:

- Worker → [`app/worker/README.md`](./app/worker/README.md)
- Queue adapter → [`app/infrastructure/queue/README.md`](./app/infrastructure/queue/README.md)

### Base de datos: PostgreSQL + pgvector

**PostgreSQL** almacena datos transaccionales (documentos, metadatos, estados). **pgvector** agrega soporte de vectores (embeddings) para búsquedas semánticas.

📌 Para profundizar:

- DB adapter → [`app/infrastructure/db/README.md`](./app/infrastructure/db/README.md)
- Repositorios → [`app/infrastructure/repositories/README.md`](./app/infrastructure/repositories/README.md)

### Migraciones: Alembic

**Alembic** mantiene el historial de cambios del esquema de la DB. La regla de oro: el esquema se evoluciona con migraciones versionadas para que el proyecto sea reproducible.

📌 Para profundizar:

- Migraciones → [`alembic/README.md`](./alembic/README.md)

### Testing: Pytest (unit / integration / e2e)

- **Unit:** lógica pura, rápida, sin IO real.
- **Integration:** valida integración real con DB/Redis o entornos controlados.
- **E2E:** valida el flujo completo como lo usaría un cliente.

📌 Para profundizar:

- Estrategia de tests → [`tests/README.md`](./tests/README.md)

---

## 🔗 Conexiones y roles

- **Rol arquitectónico:** root operativo del backend (runtime + tooling + pruebas).
- **Recibe órdenes de:**
  - Servidor ASGI (API).
  - Proceso worker (cola).
  - CLI de Alembic (migraciones).
  - Scripts de `scripts/`.

- **Llama a:** `app/` como núcleo del sistema; y a servicios externos (DB/Redis/LLM) según configuración.
- **Contratos y límites (por qué existen):**
  - Mantener el negocio en `app/` evita que scripts/configs se conviertan en “lógica escondida”.
  - Separar API y worker evita bloquear requests con tareas pesadas y mejora resiliencia.

---

## 👩‍💻 Guía de uso (Snippets)

Dos imports útiles para tooling y tests:

```python
# ASGI app (lo que sirve uvicorn)
from app.main import app as asgi_app

# FastAPI app directa (útil para tests/unit)
from app.api.main import fastapi_app

assert callable(asgi_app)
assert hasattr(fastapi_app, "openapi")
```

Comandos típicos (referencia rápida):

```bash
# 1) API local
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

# 2) Migraciones
alembic upgrade head

# 3) Tests
pytest -q
```

Variables de entorno comunes (dependen del entorno/compose):

- `DATABASE_URL`: conexión a PostgreSQL.
- `REDIS_URL`: conexión a Redis.
- `GOOGLE_API_KEY`: habilita el provider LLM (si aplica).

---

## 🧩 Cómo extender sin romper nada

1. Si es comportamiento de negocio, empezá por un caso de uso en `app/application/usecases/`.
2. Si hace IO nuevo, definí el puerto/contrato en `app/domain/` y el adapter en `app/infrastructure/`.
3. Si es un endpoint, agregalo en `app/interfaces/api/http/routers/` + DTOs en `schemas/`.
4. Si es una tarea pesada, movela al worker y encolala desde Application/Interfaces.
5. Si toca DB, creá una migración en `alembic/versions/` y validá en local/CI.
6. Agregá tests en el nivel correcto:
   - unit para lógica sin IO
   - integration para DB/Redis
   - e2e para el flujo completo

---

## 🆘 Troubleshooting

- **Síntoma:** `ModuleNotFoundError: No module named 'app'`
  - **Causa probable:** se está ejecutando desde un directorio incorrecto.
  - **Qué mirar:** ejecutar comandos desde `apps/backend/` o revisar `PYTHONPATH`/WORKDIR.

- **Síntoma:** migraciones fallan por conexión o apuntan a otra DB
  - **Causa probable:** `DATABASE_URL` ausente/incorrecta en el entorno.
  - **Qué mirar:** variables de entorno del entorno/compose y `alembic/env.py` (ver README de Alembic).

- **Síntoma:** worker no consume jobs
  - **Causa probable:** `REDIS_URL` incorrecta o cola distinta a la esperada.
  - **Qué mirar:** settings del worker y adapter de queue (ver READMEs de worker/queue).

---

## 🔎 Ver también

- [Arquitectura del backend (app)](./app/README.md)
- [HTTP (routers + schemas)](./app/interfaces/api/http/README.md)
- [Worker (jobs asíncronos)](./app/worker/README.md)
- [DB (pool/sesiones)](./app/infrastructure/db/README.md)
- [Migraciones (Alembic)](./alembic/README.md)
- [Scripts operativos](./scripts/README.md)
- [Tests](./tests/README.md)