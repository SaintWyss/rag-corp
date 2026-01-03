# Documentacion RAG Corp

**Last Updated:** 2026-01-03

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

### ⚠️ Regla de Oro: Docs + Código en el mismo PR

Para evitar que la documentación se desincronice del código:

1. **Si cambias un endpoint** → actualiza `api/http-api.md`
2. **Si cambias el schema de DB** → actualiza `data/postgres-schema.md`
3. **Si agregas una variable de entorno** → actualiza `.env.example` y `runbook/local-dev.md`
4. **Si cambias la estructura de carpetas** → actualiza `architecture/overview.md`

> 💡 **Tip:** Antes de abrir un PR, preguntate: "¿Qué documentación afecta este cambio?"
