# ADR-005: Unicidad de workspace por owner_user_id + name

## Estado

**Aceptado** (2026-01-15)

## Contexto

- El schema documentado incluye tablas `documents`, `users`, `audit_events` y `chunks` y define `uploaded_by_user_id` en `documents` para ownership. (`doc/data/postgres-schema.md`)
- La entidad `Document` expone `uploaded_by_user_id` en el dominio. (`backend/app/domain/entities.py`)
- El API actual no modela workspaces y opera sobre `/v1/documents` y `/v1/ask`. (`doc/api/http-api.md`, `backend/app/routes.py`)

## Decision

- Cuando se agregue la entidad workspace, **la unicidad sera por `(owner_user_id, name)`**. (`backend/app/domain/`, `backend/app/application/use_cases/`, `backend/app/infrastructure/repositories/`, `backend/alembic/`, `doc/data/postgres-schema.md`)
- El nombre puede repetirse entre owners distintos; no se exige unicidad global (documentar en `doc/data/postgres-schema.md`).

## Alternativas consideradas

1. Nombre unico global (descartado por colisiones entre owners).
2. Unicidad por organizacion/tenant (no existe entidad de tenant en el schema actual). (`doc/data/postgres-schema.md`)
3. Sin constraint de unicidad (descartado por UX y conflictos de lookup).

## Consecuencias

- DB: agregar constraint unique compuesto en migraciones. (`backend/alembic/`, `doc/data/postgres-schema.md`)
- API: si hay conflicto, responder 409 usando error factory existente. (`backend/app/error_responses.py`)
- UI: mostrar error de nombre duplicado al usuario (implementar en `frontend/app/components/StatusBanner.tsx`).

## Impacto en FE/BE/DB

- FE: manejo de errores 409 y mensajes de validacion en `frontend/app/components/StatusBanner.tsx` y flujos de creacion en `frontend/app/page.tsx`.
- BE (domain/application/infrastructure/API): entidad y repositorio de workspace en `backend/app/domain/`, validacion en `backend/app/application/use_cases/`, constraint en `backend/app/infrastructure/repositories/`, manejo de conflicto en `backend/app/error_responses.py`, rutas en `backend/app/routes.py`.
- DB: migraciones en `backend/alembic/` y doc de schema en `doc/data/postgres-schema.md`.

## Como validar

- Tests backend: `pnpm test:backend:unit` (ver `doc/quality/testing.md`).
- Integration si hay DB: `RUN_INTEGRATION=1 GOOGLE_API_KEY=your-key pytest -m integration` (ver `doc/quality/testing.md`).
- Tests frontend: `pnpm --filter web test` (ver `doc/quality/testing.md`).

## Referencias

- `doc/data/postgres-schema.md`
- `backend/app/domain/entities.py`
- `doc/api/http-api.md`
- `backend/app/routes.py`
- `backend/app/error_responses.py`
- `frontend/app/components/StatusBanner.tsx`
- `frontend/app/page.tsx`
- `backend/app/domain/`
- `backend/app/application/use_cases/`
- `backend/app/infrastructure/repositories/`
- `backend/alembic/`
- `doc/quality/testing.md`
