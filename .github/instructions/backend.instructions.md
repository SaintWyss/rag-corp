---
applyTo: "apps/backend/**"
---

# Backend (FastAPI) — reglas específicas del repo

## Estado / Versión

- Baseline actual: `docs/project/informe_de_sistemas_rag_corp.md`.
- No usar etiquetas internas de versión en documentación.

## Modo de trabajo

- Ejecutar cambios directamente (sin pedir confirmación), salvo: ambigüedad bloqueante, cambio destructivo, o riesgo de seguridad.
- No pegar archivos completos: entregar **diff/patch** + **archivos tocados** + **resumen (≤10 bullets)** + **comandos de validación**.

## Source of Truth (anti-drift)

Antes de afirmar algo “como cierto” en backend (endpoints, config, tablas, scripts), verificar en este orden:

1. `shared/contracts/openapi.json`
2. `apps/backend/app/main.py`, `apps/backend/app/api/main.py`, `apps/backend/app/interfaces/api/http/routes.py`, `apps/backend/app/api/auth_routes.py`
3. `apps/backend/alembic/versions/*`
4. `compose*.yaml`, `package.json`, CI workflows
5. Docs vigentes (`docs/project/...`, `docs/reference/api/http-api.md`, `docs/reference/data/postgres-schema.md`)

## Arquitectura (Clean Architecture real en este repo)

- Capas y ubicaciones:
  - Core: `apps/backend/app/domain/**`
  - Use cases: `apps/backend/app/application/**`
  - Adaptadores: `apps/backend/app/infrastructure/**` (DB, Google, chunking, prompts)
  - HTTP/API: `apps/backend/app/api/main.py` + `apps/backend/app/interfaces/api/http/routes.py` (+ `apps/backend/app/api/auth_routes.py` si aplica)
  - DI: `apps/backend/app/container.py`
- Reglas de dependencia:
  - `domain/` no importa de `application/`, `infrastructure/` ni de FastAPI.
  - `application/` no depende de FastAPI/HTTP; solo de interfaces del dominio.
  - `infrastructure/` implementa interfaces del dominio (repos/services) y es la única que toca IO.

## Endpoints / prefijos (no inventar)

- Prefijos y routers deben verificarse en `apps/backend/app/api/main.py`:
  - API v1: router bajo **`/v1`**
  - Auth: rutas **`/auth/*`** (si están montadas)
- Endpoints de soporte (verificar que existan en `apps/backend/app/api/main.py`):
  - `GET /healthz`
  - `GET /readyz` (si existe)
  - `GET /metrics` (si existe)
- Si tocás versionado, revisar `apps/backend/app/api/versioning.py` (evitar duplicar rutas).

## Seguridad y hardening (según implementación real del repo)

- Auth principal: header **`X-API-Key`** (si aplica).
- Scopes/roles: verificar en `apps/backend/app/identity/auth.py` / `apps/backend/app/identity/rbac.py` (no inventar).
- Nunca loguear secretos/claves crudas (usar hash/redaction si hace falta).
- Rate limit/hardening: `apps/backend/app/crosscutting/rate_limit.py` y middlewares en `apps/backend/app/api/main.py`.
- Si aplica hardening:
  - fail-fast en prod ante secretos inseguros (verificar en `apps/backend/app/crosscutting/config.py` o startup hooks)
  - /metrics protegido según config real (no asumir)

## DB / schema

- **Source of truth del schema**: `apps/backend/alembic/versions/*` (migraciones).
- `infra/postgres/init.sql` (si existe) es **solo bootstrap** (extensiones como pgvector), no el schema completo.
- Repo Postgres: `apps/backend/app/infrastructure/repositories/postgres/document.py`.
- Si cambiás schema o queries:
  - crear/ajustar migración Alembic,
  - actualizar repositorios,
  - actualizar docs: `docs/reference/data/postgres-schema.md`.

## Contratos (OpenAPI → Orval)

- Export OpenAPI: `apps/backend/scripts/export_openapi.py` (requiere `--out`).
- Fuente de verdad del contrato: `shared/contracts/openapi.json` y `shared/contracts/src/generated.ts`.
- Si tocás request/response del API:
  - regenerar OpenAPI + contracts (si el repo lo exige por CI; verificar workflow `contracts-check`).

## Regla de scoping por workspace

- Si un endpoint/use case toca documentos o RAG, verificar que exige/propaga `workspace_id` y aplica policy de acceso.
- Endpoints canónicos: `/v1/workspaces/{id}/...`

## Calidad (CI)

- Lint/format: CI ejecuta `ruff check .` y `ruff format --check .`.
- Tests: `pytest` (unit + integration; integration usa Postgres).

## Comandos de validación (cuando aplique)

- Lint/format:
  - `cd apps/backend && python -m pip install ruff && ruff check . && ruff format --check .`
- Tests:
  - `cd apps/backend && python -m pip install -r requirements.txt && pytest -q`
- Contracts:
  - `cd apps/backend && python scripts/export_openapi.py --out ../../shared/contracts/openapi.json`
  - `pnpm contracts:gen`
