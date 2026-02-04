# ADR-002: API Routes as Source of Truth

## Status
Accepted

## Context
Las rutas HTTP estaban hardcodeadas en hooks y componentes, provocando drift con el backend.

## Decision
Definir `src/shared/api/routes.ts` como fuente única de endpoints usados por el frontend.

## Consequences
- Menos duplicación de strings de rutas.
- Cambios de endpoints se hacen en un solo lugar.
- `shared/api/api.ts` y hooks consumen `apiRoutes`.
