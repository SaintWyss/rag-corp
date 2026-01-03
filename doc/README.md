# Documentacion RAG Corp

**Last Updated:** 2026-01-02

Esta carpeta contiene la documentacion viva del proyecto. El quickstart esta en `../README.md`.

## Indice

- `../README.md` - Quickstart y overview
- `architecture/overview.md` - Arquitectura, capas y flujo RAG
- `api/http-api.md` - Endpoints, contratos y ejemplos
- `data/postgres-schema.md` - Schema e indices pgvector
- `runbook/local-dev.md` - Desarrollo local y comandos utiles
- `../backend/tests/README.md` - Tests (unit + integration)
- `../shared/contracts/openapi.json` - OpenAPI (fuente de verdad)
- `../shared/contracts/src/generated.ts` - Cliente TypeScript generado

## Estructura minima

```
doc/
├── README.md
├── architecture/
│   └── overview.md
├── api/
│   └── http-api.md
├── data/
│   └── postgres-schema.md
└── runbook/
    └── local-dev.md
```

## Mantenimiento

- Actualiza `Last Updated` cuando cambien rutas, schema o runbook.
- Contratos: seguir el flujo `pnpm contracts:export` + `pnpm contracts:gen` (ver `api/http-api.md`).
