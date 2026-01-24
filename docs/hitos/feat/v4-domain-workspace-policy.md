# Hito (HISTORICAL v4): feat/v4-domain-workspace-policy

> HISTORICAL v4: referencia de origen para politicas de workspace.

## Objetivo

- Definir entidad Workspace y policy de acceso (read/write/ACL) en Domain.

## Cambios

- WorkspaceVisibility con PRIVATE/ORG_READ/SHARED.
- Policy de acceso a workspaces en domain.
- Tests unitarios con matriz de casos.

## Decisiones

- `can_manage_acl` sigue la misma regla que `can_write_workspace` (admin/owner).
- SHARED permite lectura solo si el usuario esta en el ACL.

## Comandos

- `pnpm test:backend:unit`

## Checklist de validacion

- [ ] `pnpm test:backend:unit`
