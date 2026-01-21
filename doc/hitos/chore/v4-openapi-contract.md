# Hito: chore/v4-openapi-contract

## Objetivo

- Alinear el contrato OpenAPI v4 con workspaces/ACL y regenerar el cliente FE.

## Cambios

- Actualizar OpenAPI con rutas v4 de workspaces y respuestas RFC 7807.
- Regenerar `shared/contracts/openapi.json` y `shared/contracts/src/generated.ts`.
- Documentar como regenerar contratos en `doc/api/http-api.md`.

## Decisiones

- Mantener `ErrorDetail` como schema RFC 7807 y publicarlo en OpenAPI via responses default del router.
- Mantener compatibilidad con endpoints legacy y versionados existentes.

## Comandos

- `pnpm contracts:export`
- `pnpm contracts:gen`

## Checklist de validacion

- [ ] `pnpm test:backend:unit`
- [ ] `pnpm --filter web test`
- [ ] `pnpm e2e`
