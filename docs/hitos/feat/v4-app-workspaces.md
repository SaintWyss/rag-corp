# Hito (HISTORICAL v4): feat/v4-app-workspaces

> HISTORICAL v4: referencia de origen para use cases de workspaces.

## Objetivo

- Implementar use cases (HISTORICAL v4) de Workspaces con policy de acceso.

## Cambios

- Access policy en domain y enum `WorkspaceVisibility` con `PRIVATE/ORG_READ/SHARED`.
- Use cases: create/list/get/update/publish/share/archive con resultados tipados.
- Workspace ACL repository port + repo in-memory.
- Tests unitarios con matriz de permisos.

## Decisiones

- `CreateWorkspace` valida visibilidad y fuerza `PRIVATE` en creacion.
- `ShareWorkspace` requiere ACL no vacia y reemplaza miembros.
- `can_manage_acl` sigue la misma regla que `can_write_workspace`.

## Comandos

- `pnpm test:backend:unit`

## Checklist de validacion

- [ ] `pnpm test:backend:unit`
