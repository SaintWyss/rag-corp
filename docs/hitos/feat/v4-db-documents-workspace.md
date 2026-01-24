# Hito (HISTORICAL v4): feat/v4-db-documents-workspace

> HISTORICAL v4: referencia de origen para la migracion a workspaces.

## Objetivo

- Agregar `documents.workspace_id` con backfill seguro al workspace Legacy.

## Cambios

- Nueva migracion Alembic con columna `workspace_id`, backfill y FK.
- Schema actualizado para reflejar `workspace_id` e indice asociado.

## Decisiones

- Legacy workspace propiedad del primer admin (o primer usuario si no hay admin).
- Si no hay usuarios, la migracion falla y requiere bootstrap previo con `backend/scripts/create_admin.py`.

## Comandos

- `pnpm db:migrate`
- `docker compose exec db psql -U postgres -d rag -c "\\d documents"`

## Checklist de validacion

- [ ] `pnpm db:migrate`
- [ ] Validar con `psql` (`\\d documents`)
