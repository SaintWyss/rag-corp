# Incident Response Runbook — RAG Corp v6

**Project:** RAG Corp  
**Last Updated:** 2026-01-24  
**Audience:** SRE, DevOps, On-call engineers

---

## TL;DR

Checklist para responder a incidentes en RAG Corp. Objetivo: **restablecer servicio en <15 minutos** para incidentes comunes.

---

## Primeros 5 Minutos

### 1. Verificar estado general

```bash
# API health
curl http://localhost:8000/healthz
curl http://localhost:8000/readyz

# Worker health
curl http://localhost:8001/healthz
curl http://localhost:8001/readyz

# DB connection
docker compose exec db pg_isready -U postgres
```

### 2. Identificar componente afectado

| Síntoma | Componente probable |
|---------|---------------------|
| 5xx en API | Backend o DB |
| Uploads stuck en PENDING | Worker o Redis |
| Timeouts en /ask | LLM (Google API) o DB |
| 403 en todo | Auth config |
| UI no carga | Frontend o network |

### 3. Revisar logs (últimos 5 min)

```bash
# Backend
docker compose logs --since 5m backend | tail -100

# Worker
docker compose logs --since 5m worker | tail -100

# Database
docker compose logs --since 5m db | tail -50
```

---

## Incidentes Comunes

### INC-01: API devuelve 500

**Diagnóstico:**
```bash
docker compose logs backend | grep -i error | tail -20
```

**Causas comunes:**
1. DB inalcanzable → verificar `docker compose ps db`
2. Migración pendiente → `pnpm db:migrate`
3. Variable faltante → verificar `.env`

**Mitigación:**
```bash
docker compose restart backend
```

### INC-02: Documentos stuck en PENDING/PROCESSING

**Diagnóstico:**
```bash
# Ver cola Redis
docker compose exec redis redis-cli LLEN rq:queue:default

# Ver worker logs
docker compose logs worker | tail -50
```

**Causas:**
1. Worker crasheado → reiniciar
2. Redis down → reiniciar Redis
3. S3/MinIO down → verificar storage

**Mitigación:**
```bash
docker compose restart worker
# Si persiste, restart Redis
docker compose restart redis
```

### INC-03: /ask devuelve timeout o lento (>10s)

**Diagnóstico:**
```bash
# Ver métricas de latencia
curl http://localhost:8000/metrics | grep rag_llm_latency

# Ver logs de Google API
docker compose logs backend | grep -i "google\|gemini" | tail -20
```

**Causas:**
1. Google API saturada → esperar o rate limit
2. Contexto muy grande → reducir `top_k`
3. Índice vectorial sin optimizar → ANALYZE

**Mitigación temporal:**
```bash
# Reducir top_k en queries (menos contexto)
# En próximo release: configurar timeout más bajo
```

### INC-04: Auth falla (401/403 en todo)

**Diagnóstico:**
```bash
# Verificar variables de auth
docker compose exec backend env | grep -E "JWT|API_KEYS|RBAC"
```

**Causas:**
1. `JWT_SECRET` vacío/default en prod
2. `API_KEYS_CONFIG` mal formateado
3. Cookie expirada

**Mitigación:**
```bash
# Verificar .env tiene JWT_SECRET configurado
# Reiniciar con config correcta
docker compose up -d --force-recreate backend
```

### INC-05: DB connection refused

**Diagnóstico:**
```bash
docker compose ps db
docker compose logs db | tail -20
```

**Causas:**
1. Container crasheado
2. Volumen corrupto
3. Puerto ocupado

**Mitigación:**
```bash
docker compose restart db
# Esperar 30s y verificar
docker compose exec db pg_isready -U postgres
```

---

## Escalation

### Nivel 1 (On-call)
- Reiniciar servicios
- Verificar configuración
- Aplicar mitigaciones conocidas

### Nivel 2 (Senior/Lead)
- Análisis de logs profundo
- Rollback de despliegue
- Contacto con proveedor (Google API)

### Nivel 3 (Architect)
- Decisiones de arquitectura
- Cambios de emergencia en código
- Post-mortem

---

## Rollback de Despliegue

### Docker Compose

```bash
# Ver imágenes anteriores
docker images | grep ragcorp

# Rebuild con versión anterior
git checkout <commit-anterior>
docker compose build --no-cache
docker compose up -d
```

### Kubernetes

```bash
# Ver historia de rollouts
kubectl -n ragcorp rollout history deployment/ragcorp-backend

# Rollback al anterior
kubectl -n ragcorp rollout undo deployment/ragcorp-backend

# Rollback a versión específica
kubectl -n ragcorp rollout undo deployment/ragcorp-backend --to-revision=3
```

---

## Métricas de Alerta

Ver `infra/prometheus/alerts.yml` para reglas completas.

| Alerta | Threshold | Acción |
|--------|-----------|--------|
| HighErrorRate | >5% errores 5xx | Investigar logs backend |
| HighLatencyP95 | >2s | Ver DB y LLM |
| APIDown | up == 0 | Restart backend |
| PostgreSQLDown | pg_up == 0 | Restart DB |
| HighMemoryUsage | >90% | Scale up o investigate leak |

---

## Comandos Útiles

```bash
# Estado de todos los servicios
docker compose ps

# Logs de todo
docker compose logs -f

# Restart todo
docker compose restart

# Nuclear option (rebuild)
docker compose down
docker compose up -d --build

# Ver eventos Kubernetes
kubectl -n ragcorp get events --sort-by='.lastTimestamp' | tail -20
```

---

## Post-Mortem Template

Después de cada incidente, crear documento con:

1. **Timeline:** Qué pasó, cuándo
2. **Impacto:** Usuarios afectados, duración
3. **Root cause:** Por qué pasó
4. **Mitigación:** Qué se hizo
5. **Prevention:** Qué cambiar para evitar repetición
6. **Action items:** Tareas concretas con owners

---

## Referencias

- Alerting rules: `infra/prometheus/alerts.yml`
- Observability runbook: `docs/runbook/observability.md`
- Troubleshooting general: `docs/runbook/troubleshooting.md`
