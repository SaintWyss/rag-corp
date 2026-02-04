# Troubleshooting Guide

**Project:** RAG Corp
**Last Updated:** 2026-01-22

---

## Quick Diagnosis

```bash
docker compose ps
curl http://localhost:8000/healthz
curl http://localhost:8000/readyz
```

---

## Common Issues

### 1) API retorna 500

**Diagnostico:**

```bash
docker compose ps db
docker compose logs db --tail=50
docker compose exec db psql -U postgres -d rag -c "SELECT 1"
```

**Causas tipicas:**
- DB no inicializada
- `DATABASE_URL` invalida
- Pool agotado (`DB_POOL_MAX_SIZE`)

---

### 2) Errores Google GenAI

**Diagnostico:**

```bash
curl http://localhost:8000/healthz?full=true
```

**Soluciones:**
- Verificar `GOOGLE_API_KEY`
- Usar `FAKE_LLM=1` y `FAKE_EMBEDDINGS=1` para desarrollo

---

### 3) Frontend no conecta a backend

**Diagnostico:**

```bash
curl http://localhost:8000/healthz
```

**Soluciones:**
- Ver `RAG_BACKEND_URL`
- Verificar CORS (`ALLOWED_ORIGINS`)

---

### 4) Documentos quedan en PROCESSING

**Diagnostico:**

```bash
docker compose logs -f worker
docker compose exec redis redis-cli llen rq:queue:documents
```

**Soluciones:**
- Verificar `REDIS_URL`
- Levantar worker con `--profile worker`
- Validar credenciales S3/MinIO

---

### 5) /metrics devuelve 403

**Causa:** `METRICS_REQUIRE_AUTH=true` sin API key con scope `metrics`.

**Solucion:**

```bash
curl -H "X-API-Key: <METRICS_KEY>" http://localhost:8000/metrics
```

---

### 6) Requests sin workspace_id

Todos los endpoints de documentos y RAG son scoped por workspace.
Usar rutas canonicas `/v1/workspaces/{workspace_id}/...`.

---

## Logs

```bash
docker compose logs -f rag-api
docker compose logs -f worker
```
