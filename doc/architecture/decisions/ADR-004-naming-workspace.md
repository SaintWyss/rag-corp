# ADR-004: Naming de workspace en API/codigo y "seccion" solo en UI

## Estado

**Aceptado** (2026-01-15)

## Contexto

- El API canonico usa el prefijo `/v1` y expone endpoints de documentos y query (`/v1/documents`, `/v1/ask`, `/v1/ask/stream`) en la documentacion y en el router del backend. (`doc/api/http-api.md`, `backend/app/routes.py`)
- El frontend consume `/api/ask`, `/api/ask/stream` y `/api/documents` como proxy a `/v1/*`. (`frontend/app/hooks/useRagAsk.ts`, `frontend/app/hooks/useRagChat.ts`, `frontend/app/lib/api.ts`, `doc/api/http-api.md`)
- El repo declara Clean Architecture con capas domain/application/infrastructure/API como base. (`doc/architecture/overview.md`, `doc/architecture/decisions/ADR-001-clean-architecture.md`)

## Decision

- Usar **workspace** como termino tecnico en API, contratos, codigo y DB. (`backend/app/domain/`, `backend/app/application/use_cases/`, `backend/app/infrastructure/`, `backend/app/routes.py`, `shared/contracts/openapi.json`, `doc/data/postgres-schema.md`)
- Usar **seccion** solo como etiqueta de UI (copy/labels), sin aparecer en rutas, nombres de entidades o columnas. (`frontend/app/page.tsx`, `frontend/app/chat/page.tsx`, `frontend/app/documents/page.tsx`)
- Si la UI necesita exponer el concepto, el mapping UI -> workspace es solo visual. (`frontend/app/page.tsx`, `frontend/app/chat/page.tsx`, `frontend/app/documents/page.tsx`)

## Alternativas consideradas

1. "Seccion" en todas las capas (descartado por mezclar UI con contratos).
2. "Workspace" tambien en UI (descartado por preferencia de copy en espanol).
3. "Proyecto" como termino unificado (descartado por ambiguedad).

## Consecuencias

- Evita drift FE/BE/DB y reduce traducciones en contratos y nombres de dominio. (`backend/app/domain/`, `backend/app/application/use_cases/`, `backend/app/infrastructure/`, `backend/app/routes.py`, `shared/contracts/openapi.json`, `doc/data/postgres-schema.md`)
- La UI puede mantener copy en espanol sin contaminar API/DB. (`frontend/app/page.tsx`, `frontend/app/chat/page.tsx`, `frontend/app/documents/page.tsx`)

## Impacto en FE/BE/DB

- FE: labels y copy en `frontend/app/page.tsx`, `frontend/app/chat/page.tsx`, `frontend/app/documents/page.tsx`, `frontend/app/components/PageHeader.tsx`.
- BE (domain/application/infrastructure/API): naming de entidades, rutas y DTOs en `backend/app/domain/entities.py`, `backend/app/application/use_cases/`, `backend/app/infrastructure/`, `backend/app/routes.py`.
- DB: naming de tablas/columnas y migraciones en `doc/data/postgres-schema.md`, `backend/alembic/`.

## Como validar

- Tests backend: `pnpm test:backend:unit` (ver `doc/quality/testing.md`).
- Tests frontend: `pnpm --filter web test` (ver `doc/quality/testing.md`).
- E2E: `pnpm e2e` (ver `doc/quality/testing.md`).
- Si se cambia naming en contratos: `pnpm contracts:export` + `pnpm contracts:gen` (ver `doc/README.md`, `doc/api/http-api.md`).

## Referencias

- `doc/api/http-api.md`
- `backend/app/routes.py`
- `frontend/app/hooks/useRagAsk.ts`
- `frontend/app/hooks/useRagChat.ts`
- `frontend/app/lib/api.ts`
- `doc/architecture/overview.md`
- `doc/architecture/decisions/ADR-001-clean-architecture.md`
- `doc/data/postgres-schema.md`
- `backend/alembic/`
- `doc/quality/testing.md`
- `doc/README.md`
