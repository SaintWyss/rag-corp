# Troubleshooting Guide

**Project:** RAG Corp  
**Last Updated:** 2026-01-13

---

## Quick Diagnosis

```bash
# Check all services status
docker compose ps

# Check API health
curl http://localhost:8000/healthz?full=true | jq

# Check logs
docker compose logs -f backend
docker compose logs -f db
```

---

## Common Issues

### 1. API Returns 500 Internal Server Error

**Symptoms:**
- All endpoints return 500
- Logs show database connection errors

**Diagnosis:**
```bash
# Check if DB is running
docker compose ps db

# Check DB logs
docker compose logs db --tail=50

# Test DB connection
docker compose exec db psql -U postgres -d rag -c "SELECT 1"
```

**Solutions:**

| Cause | Solution |
|-------|----------|
| DB container not running | `docker compose up -d db` |
| DB not initialized | `docker compose down -v && docker compose up -d` |
| Wrong DATABASE_URL | Check `.env` file |
| Connection pool exhausted | Increase `DB_POOL_MAX_SIZE` or check for leaks |

---

### 2. Google API Errors (Embeddings/LLM)

**Symptoms:**
- `/v1/ask` returns 500 or timeout
- Logs show `google.api_core.exceptions`

**Diagnosis:**
```bash
# Check if API key is set
echo $GOOGLE_API_KEY | head -c 10

# Test API connectivity
curl http://localhost:8000/healthz?full=true | jq '.google'
```

**Solutions:**

| Error | Cause | Solution |
|-------|-------|----------|
| `InvalidArgument` | Invalid API key | Regenerate key in Google Cloud Console |
| `ResourceExhausted` | Quota exceeded | Wait or increase quota |
| `PermissionDenied` | API not enabled | Enable "Generative Language API" |
| `DeadlineExceeded` | Network timeout | Check firewall/proxy settings |

**Rate Limits (Gemini API):**
- text-embedding-004: 1500 RPM
- gemini-1.5-flash: 15 RPM (free), 1000 RPM (paid)

---

### 3. Frontend Cannot Connect to Backend

**Symptoms:**
- Network errors in browser console
- CORS errors

**Diagnosis:**
```bash
# Check if backend is accessible
curl http://localhost:8000/healthz

# Check CORS headers
curl -I -X OPTIONS http://localhost:8000/v1/ask \
  -H "Origin: http://localhost:3000" \
  -H "Access-Control-Request-Method: POST"
```

**Solutions:**

| Error | Cause | Solution |
|-------|-------|----------|
| `CORS error` | Origin not allowed | Add origin to `ALLOWED_ORIGINS` in `.env` |
| `Connection refused` | Backend not running | `docker compose up -d backend` |
| `404 Not Found` | Wrong API URL | Check `NEXT_PUBLIC_API_URL` in frontend `.env` |

---

### 4. Slow Query Performance

**Symptoms:**
- `/v1/ask` takes >5 seconds
- High latency on search

**Diagnosis:**
```bash
# Check pipeline breakdown
curl http://localhost:8000/metrics | grep rag_

# Check DB query performance
docker compose exec db psql -U postgres -d rag -c "
  SELECT query, calls, mean_exec_time 
  FROM pg_stat_statements 
  ORDER BY mean_exec_time DESC 
  LIMIT 5;
"
```

**Breakdown of typical latency:**
| Stage | Expected | High if |
|-------|----------|---------|
| Embedding | 100-300ms | >500ms |
| Retrieval | 10-50ms | >200ms |
| LLM | 500-2000ms | >5000ms |

**Solutions:**

| Cause | Solution |
|-------|----------|
| Cold embedding cache | Enable Redis cache |
| Missing pgvector index | Run `CREATE INDEX` on embedding column |
| Too many chunks retrieved | Reduce `top_k` parameter |
| LLM cold start | Use streaming for perceived performance |

---

### 5. Memory Issues

**Symptoms:**
- Container OOM killed
- Python `MemoryError`

**Diagnosis:**
```bash
# Check container memory usage
docker stats

# Check Python memory
docker compose exec backend python -c "
import psutil
print(f'Memory: {psutil.Process().memory_info().rss / 1024**2:.0f} MB')
"
```

**Solutions:**

| Cause | Solution |
|-------|----------|
| Large documents | Limit document size in config |
| Memory leak | Check for unclosed connections |
| Small container limit | Increase `mem_limit` in compose.yaml |

---

### 6. Migrations Failed

**Symptoms:**
- Alembic migration errors
- Schema mismatch

**Diagnosis:**
```bash
# Check current migration version
cd backend
alembic current

# Check pending migrations
alembic history --verbose
```

**Solutions:**

```bash
# Option A: Apply pending migrations
alembic upgrade head

# Option B: Reset and reapply (DESTRUCTIVE)
alembic downgrade base
alembic upgrade head

# Option C: Stamp current state (if DB is correct)
alembic stamp head
```

---

### 7. Rate Limiting Issues

**Symptoms:**
- 429 Too Many Requests
- `X-RateLimit-Remaining: 0` header

**Diagnosis:**
```bash
# Check rate limit headers
curl -I http://localhost:8000/healthz
```

**Solutions:**

| Scenario | Solution |
|----------|----------|
| Testing locally | Set `RATE_LIMIT_RPS=100` in `.env` |
| Production | Increase limit or add IP allowlist |
| DDoS protection | Rate limit is working as intended |

---

### 8. Authentication Errors

**Symptoms:**
- 401 Unauthorized
- 403 Forbidden

**Diagnosis:**
```bash
# Test with API key
curl -H "X-API-Key: your-key" http://localhost:8000/v1/documents
```

**Solutions:**

| Error | Cause | Solution |
|-------|-------|----------|
| 401 | Missing or invalid key | Check `API_KEYS` env var format |
| 403 | Insufficient scope | Key needs `ingest`, `ask`, or `metrics` scope |

**API Key format:**
```
API_KEYS=key1:ingest,ask;key2:metrics
```

---

## Logs Reference

### Log Levels

| Level | When to use |
|-------|-------------|
| `DEBUG` | Detailed diagnostic info |
| `INFO` | Normal operations |
| `WARNING` | Recoverable issues |
| `ERROR` | Failed operations |

### Key Log Fields

| Field | Description |
|-------|-------------|
| `request_id` | Unique ID for request tracing |
| `embed_ms` | Embedding generation time |
| `retrieve_ms` | Vector search time |
| `llm_ms` | LLM generation time |
| `chunks_found` | Number of relevant chunks |

### Filtering Logs

```bash
# Errors only
docker compose logs backend 2>&1 | jq 'select(.level == "ERROR")'

# Slow requests (>2s)
docker compose logs backend 2>&1 | jq 'select(.total_ms > 2000)'

# Specific request
docker compose logs backend 2>&1 | jq 'select(.request_id == "abc-123")'
```

---

## Health Check Deep Dive

```bash
# Basic health
curl http://localhost:8000/healthz

# Full health (includes Google API check)
curl "http://localhost:8000/healthz?full=true"
```

**Response fields:**

| Field | Values | Meaning |
|-------|--------|---------|
| `ok` | true/false | Overall health |
| `db` | connected/disconnected | PostgreSQL status |
| `google` | available/unavailable/skipped | Gemini API status |

---

## Getting Help

1. Check this guide first
2. Search existing [GitHub Issues](https://github.com/SaintWyss/rag-corp/issues)
3. Check [Architecture docs](../architecture/overview.md) for context
4. Open a new issue with:
   - Error message
   - Steps to reproduce
   - Relevant logs
   - Environment info

---

## Emergency Procedures

### Full Reset (Development Only)

```bash
# Stop everything
docker compose down -v

# Clean Docker artifacts
docker system prune -f

# Restart fresh
docker compose up -d
pnpm dev
```

### Rollback Deployment

See [deployment.md](deployment.md#rollback-procedures) for production rollback steps.
