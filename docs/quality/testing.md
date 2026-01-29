# Estrategia de Testing (v6)

## Overview

| Capa | Framework | Objetivo |
|------|-----------|----------|
| Backend | pytest | Unit + integration |
| Frontend | Jest | UI + hooks |
| E2E | Playwright | Flujos workspace-first |
| Load | k6 | Benchmarks (CI main) |

Tooling: el repo fija `pnpm@10.0.0` en `package.json` (usar Corepack o instalar esa version).

---

## Backend (pytest)

```bash
# Unit tests (Docker, recomendado)
pnpm test:backend:unit

# Unit tests (local)
cd apps/backend
pytest -m unit

# Integration tests (requiere DB)
RUN_INTEGRATION=1 GOOGLE_API_KEY=<GOOGLE_API_KEY> pytest -m integration
```

---

## Contracts (OpenAPI) — anti-drift

OpenAPI es la fuente de verdad. En CI corre el job `contracts-check` que:
1) Exporta el schema desde el backend.
2) Genera cliente TS (Orval).
3) Falla si `shared/contracts/` difiere.

```bash
# Export + check local
cd apps/backend
python3 scripts/export_openapi.py --out ../shared/contracts/openapi.json
cd ../..
pnpm contracts:gen
git diff --exit-code shared/contracts/
```

---

## Frontend (Jest)

```bash
pnpm -C apps/frontend test
pnpm -C apps/frontend test:watch
pnpm -C apps/frontend test:coverage
```

**CI typecheck:**
```bash
pnpm --filter web exec tsc --noEmit
```

---

## E2E (Playwright)

```bash
pnpm e2e:install
pnpm e2e:install:browsers
pnpm e2e
```

### E2E full pipeline (upload -> READY -> chat)

Requiere worker + storage:

```bash
docker compose --profile e2e --profile worker --profile storage up -d --build
pnpm -C tests/e2e test --grep "Full pipeline"
docker compose --profile e2e --profile worker --profile storage down -v
```

Ver `tests/e2e/README.md` para variables (`TEST_API_KEY`, `E2E_ADMIN_EMAIL`, etc.).

---

## Load testing (k6)

```bash
k6 run tests/load/api.k6.js --env BASE_URL=http://localhost:8000
```
