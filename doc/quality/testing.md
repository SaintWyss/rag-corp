# Estrategia de Testing

## Overview

| Capa | Framework | Cobertura objetivo |
|------|-----------|-------------------|
| Backend | pytest | >=70% |
| Frontend | Jest + Testing Library | >=70% |
| E2E | Playwright | Flujos criticos |
| Load | k6 | Benchmarks |

## Backend (pytest)

### Ejecutar tests

```bash
# Unit tests (Docker, recomendado)
pnpm test:backend:unit

# Unit tests (local)
cd backend
pytest -m unit

# Integration tests (requieren DB + GOOGLE_API_KEY)
RUN_INTEGRATION=1 GOOGLE_API_KEY=<GOOGLE_API_KEY> pytest -m integration

# Reporte de cobertura (usa la configuracion de pytest.ini)
pytest
```

### Estructura

```
backend/tests/
├── unit/
│   ├── test_upload_endpoint.py
│   ├── test_reprocess_endpoint.py
│   ├── test_dual_authz.py
│   ├── test_user_auth.py
│   └── test_jobs.py
├── integration/
│   ├── test_api_endpoints.py
│   └── test_postgres_document_repo.py
└── conftest.py
```

### Configuracion (pytest.ini)

- Cobertura aplica a: `app/domain`, `app/application`, `app/infrastructure/text`.
- Umbral de cobertura: `--cov-fail-under=70`.
- Markers disponibles: `unit`, `integration`, `slow`, `api`.

## Frontend (Jest)

### Ejecutar tests

```bash
# Todos los tests
pnpm --filter web test

# Watch mode
pnpm --filter web test:watch

# Con cobertura
pnpm --filter web test:coverage
```

### Estructura

```
frontend/__tests__/
├── page.test.tsx
├── documents.page.test.tsx
├── chat.page.test.tsx
└── hooks/
    ├── useRagAsk.test.tsx
    └── useRagChat.test.tsx
```

## E2E (Playwright)

```bash
# Instalar Playwright (primera vez)
pnpm e2e:install
pnpm e2e:install:browsers

# Ejecutar E2E con backend/frontend locales (usa playwright.config.ts)
pnpm e2e

# Ejecutar con stack Docker Compose
E2E_USE_COMPOSE=1 TEST_API_KEY=<E2E_API_KEY> pnpm e2e
```

Tests principales:
- `tests/e2e/tests/documents.spec.ts`
- `tests/e2e/tests/chat.spec.ts`
- `tests/e2e/tests/full-pipeline.spec.ts` (upload -> READY -> chat)
- `tests/e2e/tests/workspace-flow.spec.ts` (workspace v4 end-to-end)

Ver `tests/e2e/README.md` para detalles de stack y variables.

## Load Testing (k6)

```bash
# Contra ambiente local
k6 run tests/load/api.k6.js --env BASE_URL=http://localhost:8000
```
