# Worker Runbook — RAG Corp v6

**Project:** RAG Corp  
**Last Updated:** 2026-01-24  
**Component:** RQ Worker (procesamiento asíncrono)

---

## TL;DR

El worker procesa documentos uploaded de forma asíncrona: extrae texto, genera chunks, crea embeddings, y persiste en PostgreSQL. Corre como servicio separado conectado a Redis (cola) y PostgreSQL.

---

## Arquitectura

```
┌─────────┐       ┌───────────┐       ┌──────────┐
│   API   │──────►│   Redis   │◄──────│  Worker  │
│ (8000)  │ enqueue│   Queue   │dequeue│  (8001)  │
└─────────┘       └───────────┘       └──────────┘
                                            │
                                            ▼
                                   ┌────────────────┐
                                   │  PostgreSQL    │
                                   │  + pgvector    │
                                   └────────────────┘
```

---

## Responsabilidades

1. **Consumir jobs** de la cola Redis
2. **Descargar binario** desde S3/MinIO
3. **Extraer texto** (PDF, DOCX)
4. **Chunking** con solapamiento configurable
5. **Generar embeddings** via Google GenAI (o fake para tests)
6. **Persistir chunks** en PostgreSQL con vectores
7. **Actualizar estado** del documento: `PROCESSING` → `READY` / `FAILED`

---

## Estados de Documento

```
PENDING ──► PROCESSING ──► READY
                │
                └──────────► FAILED (con error_message)
```

**Transiciones:**
- `PENDING` → `PROCESSING`: Worker toma el job
- `PROCESSING` → `READY`: Éxito
- `PROCESSING` → `FAILED`: Error (se guarda en `error_message`)

**Reprocess:**
- `READY` → `PENDING`: Reprocessing manual
- `FAILED` → `PENDING`: Reprocessing manual

---

## Cómo Levantar

### Con Docker Compose

```bash
# Solo worker
pnpm docker:worker

# Stack completo (incluye worker + storage)
pnpm stack:full
```

### Sin Docker (desarrollo)

```bash
cd apps/backend
export DATABASE_URL=postgresql://postgres:postgres@localhost:5432/rag
export REDIS_URL=redis://localhost:6379
export GOOGLE_API_KEY=...  # o FAKE_LLM=1 FAKE_EMBEDDINGS=1

python -m app.worker
```

---

## Endpoints del Worker

El worker expone HTTP propio en `WORKER_HTTP_PORT` (default `8001`):

| Endpoint | Propósito |
|----------|-----------|
| `GET /healthz` | Liveness check |
| `GET /readyz` | Readiness check (cola conectada) |
| `GET /metrics` | Prometheus metrics |

**Validación:**
```bash
curl http://localhost:8001/healthz
curl http://localhost:8001/readyz
```

---

## Configuración

| Variable | Default | Descripción |
|----------|---------|-------------|
| `REDIS_URL` | `redis://redis:6379` | URL de Redis |
| `DATABASE_URL` | — | PostgreSQL connection |
| `GOOGLE_API_KEY` | — | Para embeddings reales |
| `FAKE_LLM` | `0` | Usar LLM fake |
| `FAKE_EMBEDDINGS` | `0` | Usar embeddings fake |
| `WORKER_HTTP_PORT` | `8001` | Puerto HTTP del worker |
| `WORKER_CONCURRENCY` | `2` | Jobs paralelos |

---

## Escalado

### Réplicas en Compose

```yaml
# compose.yaml
worker:
  deploy:
    replicas: 3
```

### Kubernetes

```bash
kubectl -n ragcorp scale deployment ragcorp-worker --replicas=5
```

**Regla de escalado:** 1 worker por cada ~1000 docs/hora esperados.

---

## Monitoreo

### Logs

```bash
# Docker
docker compose logs -f worker

# Kubernetes
kubectl -n ragcorp logs -l app.kubernetes.io/component=worker -f
```

### Métricas clave

| Métrica | Descripción |
|---------|-------------|
| `rag_worker_jobs_processed_total` | Jobs completados |
| `rag_worker_jobs_failed_total` | Jobs fallidos |
| `rag_embed_latency_seconds` | Latencia de embeddings |

### Dashboard Grafana

- `ragcorp-operations.json` tiene panel de worker

---

## Troubleshooting

### Job stuck en PROCESSING

**Síntoma:** Documento en `PROCESSING` por más de 10 minutos.

**Causas:**
1. Worker crasheó mid-job
2. Timeout de embedding service
3. S3/MinIO inalcanzable

**Solución:**
```bash
# Ver logs del worker
docker compose logs worker | grep <document_id>

# Forzar reprocess via API
curl -X POST http://localhost:8000/v1/workspaces/<ws_id>/documents/<doc_id>/reprocess \
  -H "X-API-Key: <key>"
```

### Job en FAILED

**Síntoma:** Documento en `FAILED` con `error_message`.

**Ver error:**
```bash
curl http://localhost:8000/v1/workspaces/<ws_id>/documents/<doc_id> \
  -H "X-API-Key: <key>" | jq .error_message
```

**Causas comunes:**
- Archivo corrupto o no soportado
- Timeout de Google API
- Límite de tamaño excedido

### Worker no consume jobs

**Síntoma:** Jobs en cola pero worker no procesa.

**Verificar:**
```bash
# Redis tiene jobs?
docker compose exec redis redis-cli LLEN rq:queue:default

# Worker conectado?
curl http://localhost:8001/readyz
```

**Solución:** Reiniciar worker.

---

## Failure Modes

| Modo | Detección | Recuperación |
|------|-----------|--------------|
| Worker crash | `/readyz` falla | Auto-restart (Docker) |
| Redis down | Worker logs error | Restore Redis |
| DB down | Jobs fallan | Restore DB, reprocess |
| Google API timeout | Jobs lentos/failed | Retry automático (3x) |
| S3/MinIO down | Jobs failed | Restore storage, reprocess |

---

## Idempotencia

El worker es **idempotente**: reprocessar un documento en `READY` elimina chunks anteriores y crea nuevos. Esto permite:
- Actualizar embeddings si cambia el modelo
- Recuperar de corrupciones

---

## Referencias

- Compose profiles: `compose.yaml` (`worker`, `full`)
- Worker entrypoint: `apps/backend/app/worker.py`
- Job handlers: `apps/backend/app/infrastructure/queue/`
