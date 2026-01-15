# ADR-007: Compatibilidad de endpoints legacy vs nested workspaces

## Estado

**Aceptado** (2026-01-15)

## Contexto

- El API canonico usa `/v1` y documenta `/v1/documents`, `/v1/ask` y `/v1/ask/stream`. (`doc/api/http-api.md`)
- El router backend define endpoints `/documents`, `/ask` y `/ask/stream` bajo el prefijo del API. (`backend/app/routes.py`)
- El frontend llama `/api/ask`, `/api/ask/stream` y `/api/documents` via proxy. (`frontend/app/hooks/useRagAsk.ts`, `frontend/app/hooks/useRagChat.ts`, `frontend/app/lib/api.ts`, `doc/api/http-api.md`)

## Decision

- Mantener `/v1/documents` y `/v1/ask` como endpoints **legacy estables**. (`doc/api/http-api.md`, `backend/app/routes.py`)
- Cuando se agreguen workspaces, sumar endpoints nested (`/v1/workspaces/{workspace_id}/documents`, `/v1/workspaces/{workspace_id}/ask`) sin romper los legacy. (`backend/app/routes.py`)
- Cuando existan workspaces, los endpoints legacy operaran sobre un workspace implicito para compatibilidad (implementar en `backend/app/application/use_cases/`, `backend/app/routes.py`).

## Alternativas consideradas

1. Deprecar de inmediato `/v1/documents` y `/v1/ask` (descartado por romper FE actual). (`frontend/app/hooks/useRagAsk.ts`, `frontend/app/lib/api.ts`)
2. Solo endpoints legacy sin nested (descartado por falta de aislamiento multi-workspace).
3. Workspace via header en vez de path (descartado por menor claridad en contratos).

## Consecuencias

- Se preserva compatibilidad con FE y clientes existentes.
- Se habilita evolucion hacia endpoints nested sin cambios disruptivos.

## Impacto en FE/BE/DB

- FE: consumo actual en `frontend/app/hooks/useRagAsk.ts`, `frontend/app/hooks/useRagChat.ts`, `frontend/app/lib/api.ts`; futuros selectores de workspace en paginas `frontend/app/page.tsx` y `frontend/app/documents/page.tsx`.
- BE (domain/application/infrastructure/API): nuevos use cases y repos para workspace en `backend/app/domain/`, `backend/app/application/use_cases/`, `backend/app/infrastructure/`, rutas en `backend/app/routes.py`.
- DB: futura tabla workspace y constraints en `backend/alembic/` y `doc/data/postgres-schema.md`.

## Como validar

- Tests backend: `pnpm test:backend:unit` (ver `doc/quality/testing.md`).
- Tests frontend: `pnpm --filter web test` (ver `doc/quality/testing.md`).
- E2E: `pnpm e2e` (ver `doc/quality/testing.md`).

## Referencias

- `doc/api/http-api.md`
- `backend/app/routes.py`
- `frontend/app/hooks/useRagAsk.ts`
- `frontend/app/hooks/useRagChat.ts`
- `frontend/app/lib/api.ts`
- `frontend/app/page.tsx`
- `frontend/app/documents/page.tsx`
- `backend/app/domain/`
- `backend/app/application/use_cases/`
- `backend/app/infrastructure/`
- `backend/alembic/`
- `doc/data/postgres-schema.md`
- `doc/quality/testing.md`
