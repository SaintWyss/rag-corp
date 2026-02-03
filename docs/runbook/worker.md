# Runbook de worker
Fuente de verdad: `apps/backend/app/worker/README.md` y el código en `apps/backend/app/worker/`.

## Qué es
El worker es un proceso RQ que consume jobs y ejecuta casos de uso de ingesta/procesamiento. Evidencia en `apps/backend/app/worker/worker.py` y `apps/backend/app/worker/jobs.py`.

## Entrypoint
```bash
cd apps/backend
python -m app.worker.worker
```

## Configuración (env)
Evidencia en `apps/backend/app/worker/worker.py` y `apps/backend/app/crosscutting/config.py`:
- `REDIS_URL` (requerido para el worker)
- `DOCUMENT_QUEUE_NAME` (default `documents`)
- `WORKER_HTTP_PORT` (default `8001`)
- `DATABASE_URL` (pool DB)
- `DB_POOL_MIN_SIZE` / `DB_POOL_MAX_SIZE`

## Endpoints operativos
Expuestos por `apps/backend/app/worker/worker_server.py`:
- `GET /healthz`
- `GET /readyz`
- `GET /metrics` (protegido si `METRICS_REQUIRE_AUTH=1`)

## Jobs y colas
- Job handlers → `apps/backend/app/worker/jobs.py`
- Queue adapter (RQ) → `apps/backend/app/infrastructure/queue/rq_queue.py`
- Paths de jobs → `apps/backend/app/infrastructure/queue/job_paths.py`

## Troubleshooting
- **Síntoma:** `REDIS_URL es requerido para ejecutar el worker.`
- **Causa probable:** variable `REDIS_URL` no definida.
- **Dónde mirar:** `apps/backend/app/worker/worker.py`.
- **Solución:** definir `REDIS_URL` y reiniciar.

- **Síntoma:** `/metrics` devuelve 401/403.
- **Causa probable:** `METRICS_REQUIRE_AUTH=1` y falta `X-API-Key` válido.
- **Dónde mirar:** `apps/backend/app/worker/worker_server.py` y `apps/backend/app/identity/rbac.py`.
- **Solución:** enviar API key con scope `metrics` o permiso `admin:metrics`.

- **Síntoma:** errores de pool DB al iniciar.
- **Causa probable:** `DATABASE_URL` inválida o DB apagada.
- **Dónde mirar:** `apps/backend/app/infrastructure/db/pool.py`.
- **Solución:** corregir URL y levantar DB.
