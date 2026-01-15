# ADR-006: Politica de archive/soft-delete para workspaces y documents

## Estado

**Aceptado** (2026-01-15)

## Contexto

- `Document` incluye `deleted_at` y `is_deleted` en el dominio. (`backend/app/domain/entities.py`)
- El caso de uso de delete es soft delete. (`backend/app/application/use_cases/delete_document.py`)
- El repositorio filtra `deleted_at IS NULL` en list/get y setea `deleted_at` en soft delete. (`backend/app/infrastructure/repositories/postgres_document_repo.py`)
- El schema documentado incluye `documents.deleted_at`. (`doc/data/postgres-schema.md`)
- La API expone `deleted_at` en el detalle de documento y tiene `DELETE /documents/{id}`. (`backend/app/routes.py`)
- El frontend modela `deleted_at` en `DocumentDetail`. (`frontend/app/lib/api.ts`)
- La busqueda de chunks usa solo la tabla `chunks` sin join a `documents`. (`backend/app/infrastructure/repositories/postgres_document_repo.py`)

## Decision

- **Archive == soft-delete**: un recurso archivado se marca con `deleted_at` (timestamp) y permanece en DB. (`backend/app/domain/entities.py`, `doc/data/postgres-schema.md`)
- **Documents**:
  - Listados y detalle excluyen archivados por defecto. (`backend/app/infrastructure/repositories/postgres_document_repo.py`, `backend/app/routes.py`)
  - Retrieval (`/v1/query`, `/v1/ask`, `/v1/ask/stream`) no debe devolver chunks de documentos archivados. (`backend/app/routes.py`, `backend/app/infrastructure/repositories/postgres_document_repo.py`)
- **Workspaces (cuando existan)**:
  - `deleted_at` define archivado. (`doc/data/postgres-schema.md`)
  - Comportamiento esperado: quedan fuera de listados y no permiten ingest/ask (implementar en `backend/app/routes.py`, `backend/app/application/use_cases/`).

## Alternativas consideradas

1. Hard delete (descartado por perdida de trazabilidad y audit).
2. Flag boolean `archived` (descartado por inconsistencia con `deleted_at` ya existente).
3. Mantener retrieval sin filtro (descartado por leakage de contenido archivado).

## Consecuencias

- Se alinea el comportamiento actual de list/get con el significado de archivado. (`backend/app/infrastructure/repositories/postgres_document_repo.py`, `backend/app/routes.py`)
- Requiere ajustar la busqueda de chunks para filtrar documentos archivados. (`backend/app/infrastructure/repositories/postgres_document_repo.py`)

## Impacto en FE/BE/DB

- FE: filtros y estados en listados de documentos en `frontend/app/documents/page.tsx` y tipos en `frontend/app/lib/api.ts`.
- BE (domain/application/infrastructure/API): reglas en `backend/app/domain/entities.py`, uso en `backend/app/application/use_cases/`, filtro en `backend/app/infrastructure/repositories/postgres_document_repo.py`, endpoints en `backend/app/routes.py`.
- DB: mantener `deleted_at` y documentar en `doc/data/postgres-schema.md`; futuras migraciones en `backend/alembic/`.

## Como validar

- Unit tests backend: `pnpm test:backend:unit` (ver `doc/quality/testing.md`).
- Integration tests repo: `RUN_INTEGRATION=1 GOOGLE_API_KEY=your-key pytest -m integration` (ver `doc/quality/testing.md`).
- E2E si se modifica flujo de documentos: `pnpm e2e` (ver `doc/quality/testing.md`).

## Referencias

- `backend/app/domain/entities.py`
- `backend/app/application/use_cases/delete_document.py`
- `backend/app/infrastructure/repositories/postgres_document_repo.py`
- `doc/data/postgres-schema.md`
- `backend/app/routes.py`
- `frontend/app/lib/api.ts`
- `frontend/app/documents/page.tsx`
- `backend/alembic/`
- `doc/quality/testing.md`
