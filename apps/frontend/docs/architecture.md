# Frontend Architecture

Este documento describe la arquitectura FE actual (capas, boundaries y fuentes de verdad).

## Capas y responsabilidades

- **Interface (Next App Router)**: `app/`
  - Routing, layouts y boundaries (error/loading/not-found).
  - No contiene lógica de producto ni fetch.
- **App Shell**: `src/app-shell/`
  - Providers, guards y layouts reutilizables por `app/`.
- **Application (features)**: `src/features/*`
  - Orquestación de UI por feature (components/hooks/services).
  - No depende de otros features directamente.
- **Infrastructure (API/adapters)**: `src/shared/api/*`
  - Cliente HTTP, helpers SSE y contracts/decoders.
- **Domain FE (tipos/contratos)**: `src/shared/api/contracts/*` + `src/features/*/types`.
- **Shared UI / Lib**: `src/shared/ui/*`, `src/shared/lib/*`, `src/shared/config/*`.

## Reglas de dependencia

- `app/*` solo importa de:
  - `src/app-shell/*`
  - `src/features/*`
  - `src/shared/*`
- `src/features/*` puede importar:
  - `src/shared/*`
  - Nunca otros features (salvo acuerdos explícitos via contracts).
- `src/shared/*` **no** importa desde `src/features/*` ni `app/*`.
- `src/app-shell/*` solo depende de `src/shared/*`.

Estas reglas se enforcean en `eslint.config.mjs`.

## Source of Truth de endpoints

- **Endpoints FE**: `src/shared/api/routes.ts`.
- **Cliente HTTP**: `src/shared/api/api.ts`.
- **Contracts/decoders**: `src/shared/api/contracts/*`.

## Testing

- Tests: `tests/unit/**` y `tests/integration/**`.
- Fixtures/helpers: `src/test/**`.

## Notas

- SSE streaming se centraliza en `src/shared/api/sse.ts`.
- Guards server-side viven en `src/app-shell/guards/`.
