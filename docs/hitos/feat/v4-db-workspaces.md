# Hito (HISTORICAL v4): feat/v4-db-workspaces

> HISTORICAL v4: referencia de origen para tablas `workspaces` y `workspace_acl`.

## Objetivo

- Agregar tablas `workspaces` y `workspace_acl` con constraints e indices (HISTORICAL v4).

## Cambios

- Nueva migracion Alembic para workspaces y ACL.
- Documentacion de schema actualizada.

## Decisiones

- Unicidad por `(owner_user_id, name)` segun ADR-005.
- `visibility` con valores `PRIVATE/ORG_READ/SHARED` y default `PRIVATE`.

## Comandos

- `pnpm db:migrate`

## Checklist de validacion

- [ ] `pnpm db:migrate`
- [ ] Validar con `psql` (`\\d workspaces`, `\\d workspace_acl`)
