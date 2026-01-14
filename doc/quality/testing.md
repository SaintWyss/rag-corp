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
cd backend

# Unit tests (offline)
pytest -m unit

# Integration tests (requieren DB + GOOGLE_API_KEY)
RUN_INTEGRATION=1 GOOGLE_API_KEY=your-key pytest -m integration

# Reporte de cobertura (usa la configuracion de pytest.ini)
pytest
```

### Estructura

```
backend/tests/
├── unit/
│   ├── test_answer_query_use_case.py
│   ├── test_conversation_repository.py
│   ├── test_ingest_document_use_case.py
│   └── test_search_chunks_use_case.py
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
├── documents.page.test.tsx
├── chat.page.test.tsx
└── hooks/
    ├── useRagAsk.test.tsx
    └── useRagChat.test.tsx
```

## E2E (Playwright)

```bash
# Instalar Playwright (primera vez)
cd tests/e2e && pnpm install && pnpm install:browsers

# Ejecutar E2E con backend/frontend locales (usa playwright.config.ts)
pnpm e2e

# Ejecutar con stack Docker Compose
E2E_USE_COMPOSE=1 TEST_API_KEY=e2e-key pnpm e2e
```

Tests principales:
- `tests/e2e/tests/documents.spec.ts`
- `tests/e2e/tests/chat.spec.ts`

Ver `tests/e2e/README.md` para detalles de stack y variables.

## Load Testing (k6)

```bash
# Contra ambiente local
k6 run tests/load/api.k6.js --env BASE_URL=http://localhost:8000
```
