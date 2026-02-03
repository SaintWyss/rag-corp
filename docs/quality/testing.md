# Estrategia de testing
Documento transversal con foco en backend. El detalle vive en `apps/backend/tests/README.md`.

## Backend (pytest)
Evidencia:
- Tests y markers → `apps/backend/tests/README.md`
- Config Pytest → `apps/backend/pytest.ini`
- Script CI/local → `package.json` (`test:backend:unit`)

Comandos típicos:
```bash
# Unit tests (Docker, script oficial)
pnpm test:backend:unit

# Unit tests (local)
cd apps/backend
pytest -m unit tests/unit

# Integration tests (local)
RUN_INTEGRATION=1 pytest -m integration tests/integration
```

## Contratos OpenAPI (anti-drift)
Evidencia:
- Exporter → `apps/backend/scripts/export_openapi.py`
- OpenAPI → `shared/contracts/openapi.json`

```bash
cd apps/backend
python scripts/export_openapi.py --out ../shared/contracts/openapi.json
```

## E2E (Playwright)
Evidencia:
- Tests E2E → `tests/e2e/README.md`
- Scripts en `package.json` (`e2e`, `e2e:install`, `e2e:install:browsers`)

```bash
pnpm e2e:install
pnpm e2e:install:browsers
pnpm e2e
```

## Load (k6)
Evidencia:
- Tests de carga → `tests/load/README.md`

```bash
k6 run tests/load/api.k6.js --env BASE_URL=http://localhost:8000
```
