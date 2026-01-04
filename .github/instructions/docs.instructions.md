---
applyTo: "doc/**"
---

# Docs — reglas específicas del repo

## Modo de trabajo
- Ejecutar cambios directamente (sin pedir confirmación), salvo: ambigüedad bloqueante, cambio destructivo, o riesgo de seguridad.
- No pegar archivos completos: entregar **diff/patch** + **archivos tocados** + **resumen (≤10 bullets)** + **comandos de validación**.

## Veracidad / No alucinaciones
- No inventar features/endpoints/comandos. Si algo no existe en el repo, marcarlo como **TODO/Planned**.
- Verificar siempre contra:
  - API: `backend/app/routes.py` y `backend/app/main.py` (prefijos y endpoints)
  - Docker: `compose.yaml`, `compose.prod.yaml`, `compose.observability.yaml`
  - Contracts: `shared/contracts/openapi.json`

## Índices y rutas canónicas
- `doc/README.md` es el índice principal (mantener links vivos).
- `README.md` raíz debe apuntar a `doc/README.md` (portal).
- Documentos “fuente”:
  - Arquitectura: `doc/architecture/overview.md`
  - API HTTP: `doc/api/http-api.md`
  - Data/schema: `doc/data/postgres-schema.md`
  - Runbook local: `doc/runbook/local-dev.md`

## Convenciones de comandos (este repo)
- Usar `docker compose` (no `docker-compose`).
- Services actuales en `compose.yaml`: `db` y `rag-api`.
- Si mencionás generación de contratos:
  - `pnpm contracts:export` (usa `docker compose run rag-api ...`)
  - `pnpm contracts:gen`

## Regla de actualización
- Si un cambio toca API, DB o compose:
  - actualizar docs correspondientes en el mismo PR.

## Comandos de validación (cuando aplique)
- Links y rutas: revisar que los paths existan.
- API examples:
  - `curl http://localhost:8000/healthz`
  - `curl -X POST http://localhost:8000/v1/ask -H 'Content-Type: application/json' -d '{"query":"...","top_k":3}'`
