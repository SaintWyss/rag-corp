---
applyTo: "backend/**"
---

# Backend (FastAPI) — reglas específicas del repo

## Modo de trabajo
- Ejecutar cambios directamente (sin pedir confirmación), salvo: ambigüedad bloqueante, cambio destructivo, o riesgo de seguridad.
- No pegar archivos completos: entregar **diff/patch** + **archivos tocados** + **resumen (≤10 bullets)** + **comandos de validación**.

## Arquitectura (Clean Architecture real en este repo)
- Capas y ubicaciones:
  - Core: `backend/app/domain/**`
  - Use cases: `backend/app/application/**`
  - Adaptadores: `backend/app/infrastructure/**` (DB, Google, chunking, prompts)
  - HTTP/API: `backend/app/routes.py` + `backend/app/main.py`
  - DI: `backend/app/container.py`
- Reglas de dependencia:
  - `domain/` no importa de `application/`, `infrastructure/` ni de FastAPI.
  - `application/` no depende de FastAPI/HTTP; solo de interfaces del dominio.
  - `infrastructure/` implementa interfaces del dominio (repos/services) y es la única que toca IO.

## Endpoints / prefijos (no inventar)
- Prefijo actual: `backend/app/main.py` monta `routes.router` bajo **`/v1`**.
- Endpoints de soporte:
  - `GET /healthz` (en `backend/app/main.py`)
  - `GET /metrics` (en `backend/app/main.py`)
- Si tocás versionado, revisar `backend/app/versioning.py` (evitar duplicar rutas).

## Seguridad y hardening (ya existe en el repo)
- API key header: **`X-API-Key`**.
- Scopes: `ingest`, `ask`, `metrics` (ver `backend/app/auth.py`).
- Nunca loguear claves crudas (usar hash si hace falta).
- Rate limit/hardening: `backend/app/rate_limit.py` y middlewares en `backend/app/main.py`.

## DB / schema
- Fuente del schema para docker local: `infra/postgres/init.sql` (montado por `compose.yaml`).
- Repo Postgres: `backend/app/infrastructure/repositories/postgres_document_repo.py`.
- Si cambiás schema o queries:
  - actualizar `infra/postgres/init.sql` (o migraciones si se usan),
  - actualizar repositorios,
  - actualizar docs: `doc/data/postgres-schema.md`.

## Contratos (OpenAPI → Orval)
- Export OpenAPI: `backend/scripts/export_openapi.py` (requiere `--out`).
- Fuente de verdad TS client: `shared/contracts/openapi.json` y `shared/contracts/src/generated.ts`.
- Si tocás request/response del API:
  - regenerar OpenAPI + contracts (CI tiene `contracts-check` con `git diff --exit-code shared/contracts/`).

## Calidad (CI)
- Lint/format: CI ejecuta `ruff check .` y `ruff format --check .`.
- Tests: `pytest` (unit + integration; integration usa Postgres).

## Comandos de validación (cuando aplique)
- Lint/format:
  - `cd backend && python -m pip install ruff && ruff check . && ruff format --check .`
- Tests:
  - `cd backend && python -m pip install -r requirements.txt && pytest -q`
- Contracts:
  - `cd backend && python scripts/export_openapi.py --out ../shared/contracts/openapi.json`
  - `pnpm contracts:gen`
