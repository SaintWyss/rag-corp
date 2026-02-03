---
applyTo: "backend/**"
---

# Backend (FastAPI) — reglas específicas del repo (v6)

## Estado / Versión (v6)

- La versión vigente del proyecto/documentación es **v6**.
- “v4” solo puede aparecer como **HISTORICAL** (origen/especificación pasada), claramente marcado.

## Modo de trabajo

- Ejecutar cambios directamente (sin pedir confirmación), salvo: ambigüedad bloqueante, cambio destructivo, o riesgo de seguridad.
- No pegar archivos completos: entregar **diff/patch** + **archivos tocados** + **resumen (≤10 bullets)** + **comandos de validación**.

## Source of Truth (anti-drift)

Antes de afirmar algo “como cierto” en backend (endpoints, config, tablas, scripts), verificar en este orden:

1. `shared/contracts/openapi.json`
2. `backend/app/main.py`, `backend/app/routes.py`, `backend/app/auth_routes.py`
3. `backend/alembic/versions/*`
4. `compose*.yaml`, `package.json`, CI workflows

5) Docs vigentes v6 (`docs/project/...`, `docs/reference/api/http-api.md`, `docs/reference/data/postgres-schema.md`)

## Arquitectura (Clean Architecture real en este repo)

- Capas y ubicaciones:
  - Core: `backend/app/domain/**`
  - Use cases: `backend/app/application/**`
  - Adaptadores: `backend/app/infrastructure/**` (DB, Google, chunking, prompts)
  - HTTP/API: `backend/app/routes.py` + `backend/app/main.py` (+ `backend/app/auth_routes.py` si aplica)
  - DI: `backend/app/container.py`
- Reglas de dependencia:
  - `domain/` no importa de `application/`, `infrastructure/` ni de FastAPI.
  - `application/` no depende de FastAPI/HTTP; solo de interfaces del dominio.
  - `infrastructure/` implementa interfaces del dominio (repos/services) y es la única que toca IO.

## Endpoints / prefijos (no inventar)

- Prefijos y routers deben verificarse en `backend/app/main.py`:
  - API v1: router bajo **`/v1`**
  - Auth: rutas **`/auth/*`** (si están montadas)
- Endpoints de soporte (verificar que existan en `backend/app/main.py`):
  - `GET /healthz`
  - `GET /readyz` (si existe en v6)
  - `GET /metrics` (si existe en v6)
- Si tocás versionado, revisar `backend/app/versioning.py` (evitar duplicar rutas).

## Seguridad y hardening (según implementación real del repo)

- Auth principal: header **`X-API-Key`** (si aplica en v6).
- Scopes/roles: verificar en `backend/app/auth.py` / `backend/app/rbac.py` (no inventar).
- Nunca loguear secretos/claves crudas (usar hash/redaction si hace falta).
- Rate limit/hardening: `backend/app/rate_limit.py` y middlewares en `backend/app/main.py`.
- Si v6 exige hardening:
  - fail-fast en prod ante secretos inseguros (verificar en `backend/app/config.py` o startup hooks)
  - /metrics protegido según config real (no asumir)

## DB / schema

- **Source of truth del schema**: `backend/alembic/versions/*` (migraciones).
- `infra/postgres/init.sql` (si existe) es **solo bootstrap** (extensiones como pgvector), no el schema completo.
- Repo Postgres: `backend/app/infrastructure/repositories/postgres_document_repo.py`.
- Si cambiás schema o queries:
  - crear/ajustar migración Alembic,
  - actualizar repositorios,
  - actualizar docs: `docs/data/postgres-schema.md`.

## Contratos (OpenAPI → Orval)

- Export OpenAPI: `backend/scripts/export_openapi.py` (requiere `--out`).
- Fuente de verdad del contrato: `shared/contracts/openapi.json` y `shared/contracts/src/generated.ts`.
- Si tocás request/response del API:
  - regenerar OpenAPI + contracts (si el repo lo exige por CI; verificar workflow `contracts-check`).

## Regla v6 (si aplica): scoping por workspace

- Si un endpoint/use case toca documentos o RAG, verificar que exige/propaga `workspace_id` y aplica policy de acceso.
- Endpoints canónicos (si existen): `/v1/workspaces/{id}/...`
- Endpoints legacy (si existen): **DEPRECATED** y siempre con `workspace_id` explícito (nunca implícito).

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
