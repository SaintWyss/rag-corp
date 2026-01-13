# Estrategia de Testing

## Overview

| Capa | Framework | Cobertura objetivo |
|------|-----------|-------------------|
| Backend | pytest | >=70% |
| Frontend | Jest + Testing Library | >=70% |
| Load | k6 | Benchmarks |
| E2E | (Planned) Playwright | Flujos criticos |

## Backend (pytest)

### Ejecutar tests

```bash
cd backend

# Unit tests (offline)
pytest -m unit

# Integration tests (requieren DB + GOOGLE_API_KEY)
RUN_INTEGRATION=1 pytest -m integration

# Reporte de cobertura (usa la configuracion de pytest.ini)
pytest
```

### Estructura

```
backend/tests/
├── unit/
│   ├── test_answer_query_use_case.py
│   ├── test_ingest_document_use_case.py
│   ├── test_search_chunks_use_case.py
│   ├── test_chunker.py
│   └── test_config.py
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
cd frontend

# Todos los tests
pnpm test

# Watch mode
pnpm test:watch

# Con cobertura
pnpm test:coverage
```

### Estructura

```
frontend/__tests__/
├── page.test.tsx
├── error.test.tsx
└── hooks/
    └── useRagAsk.test.tsx
```

### Configuracion (jest.config.js)

- `testEnvironment: "jsdom"`
- `setupFilesAfterEnv: ["<rootDir>/jest.setup.ts"]`
- `moduleNameMapper` incluye `^@/(.*)$` y `^@contracts/(.*)$`
- `collectCoverageFrom` en `app/**/*.{ts,tsx}` (excluye `app/layout.tsx`)

## Load Testing (k6)

```bash
# Contra ambiente local
k6 run tests/load/api.k6.js --env BASE_URL=http://localhost:8000
```
