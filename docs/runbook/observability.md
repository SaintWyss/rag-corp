# Observability Runbook — RAG Corp v6

**Project:** RAG Corp  
**Last Updated:** 2026-01-24  
**Audience:** SRE, DevOps, Developers

---

## TL;DR

RAG Corp expone métricas Prometheus, health checks, y dashboards Grafana para monitoreo. Este runbook explica cómo levantar, acceder, y usar la observabilidad.

---

## Arquitectura de Observabilidad

```
┌─────────────┐     ┌─────────────┐     ┌──────────────┐
│  Backend    │────►│ Prometheus  │────►│   Grafana    │
│  /metrics   │     │   :9090     │     │    :3001     │
└─────────────┘     └─────────────┘     └──────────────┘
       ▲                   ▲
       │                   │
┌──────┴──────┐     ┌──────┴──────┐
│   Worker    │     │  postgres-  │
│  :8001      │     │  exporter   │
└─────────────┘     └─────────────┘
```

---

## Endpoints de Health/Metrics

### Backend API (puerto 8000)

| Endpoint | Propósito | Auth |
|----------|-----------|------|
| `GET /healthz` | Liveness (siempre 200 si proceso vivo) | No |
| `GET /readyz` | Readiness (DB conectada) | No |
| `GET /metrics` | Prometheus metrics | Condicional* |

*`/metrics` requiere auth si `METRICS_REQUIRE_AUTH=true`:
```bash
curl -H "X-API-Key: <key_con_scope_metrics>" http://localhost:8000/metrics
```

### Worker (puerto 8001)

| Endpoint | Propósito | Auth |
|----------|-----------|------|
| `GET /healthz` | Liveness | No |
| `GET /readyz` | Readiness (Redis conectado) | No |
| `GET /metrics` | Prometheus metrics | Condicional* |

**Verificación rápida:**
```bash
curl http://localhost:8000/healthz
curl http://localhost:8000/readyz
curl http://localhost:8001/healthz
curl http://localhost:8001/readyz
```

---

## Levantar Observabilidad (Docker Compose)

### Profile `observability`

```bash
# Solo observabilidad + servicios base
docker compose --profile observability up -d

# Stack completo (incluye worker, storage, observability)
pnpm stack:full
```

### Servicios incluidos

| Servicio | Puerto | Propósito |
|----------|--------|-----------|
| Prometheus | 9090 | Recolección de métricas |
| Grafana | 3001 | Visualización y dashboards |
| postgres-exporter | 9187 | Métricas de PostgreSQL |

---

## URLs Locales

| Servicio | URL |
|----------|-----|
| Prometheus UI | http://localhost:9090 |
| Grafana | http://localhost:3001 |
| Grafana login | `admin` / `admin` (o `GRAFANA_PASSWORD`) |
| postgres-exporter | http://localhost:9187/metrics |

---

## Grafana Dashboards

Los dashboards se provisionan automáticamente desde `infra/grafana/dashboards/`:

| Dashboard | Contenido |
|-----------|-----------|
| RAG Corp - Overview | Estado general del sistema |
| RAG Corp - API Performance | Latencia, throughput, errores |
| RAG Corp - Operations | Documentos, queries, worker |
| RAG Corp - PostgreSQL | Conexiones, cache, transacciones |

### Acceder a dashboards

1. Ir a http://localhost:3001
2. Login: `admin` / `admin`
3. Menu izquierdo → Dashboards → RAG Corp

---

## Métricas Clave

### API Metrics

| Métrica | Tipo | Descripción |
|---------|------|-------------|
| `rag_requests_total` | Counter | Total de requests por endpoint/status |
| `rag_request_latency_seconds` | Histogram | Latencia de requests |
| `rag_llm_latency_seconds` | Histogram | Latencia de llamadas a LLM |
| `rag_embed_latency_seconds` | Histogram | Latencia de embeddings |

### Worker Metrics

| Métrica | Tipo | Descripción |
|---------|------|-------------|
| `rag_worker_jobs_processed_total` | Counter | Jobs procesados |
| `rag_worker_jobs_failed_total` | Counter | Jobs fallidos |
| `rag_worker_job_duration_seconds` | Histogram | Duración de jobs |

### PostgreSQL Metrics (via exporter)

| Métrica | Descripción |
|---------|-------------|
| `pg_stat_database_tup_fetched` | Tuplas leídas |
| `pg_stat_database_tup_inserted` | Tuplas insertadas |
| `pg_stat_user_tables_n_live_tup` | Filas por tabla |

---

## Queries PromQL Útiles

### Requests por segundo
```promql
rate(rag_requests_total[5m])
```

### Latencia p95
```promql
histogram_quantile(0.95, rate(rag_request_latency_seconds_bucket[5m]))
```

### Tasa de errores (5xx)
```promql
sum(rate(rag_requests_total{status=~"5.."}[5m])) 
/ 
sum(rate(rag_requests_total[5m]))
```

### Jobs de worker por minuto
```promql
rate(rag_worker_jobs_processed_total[1m]) * 60
```

---

## Alertas

Las alertas están definidas en `infra/prometheus/alerts.yml`:

| Alerta | Condición | Severidad |
|--------|-----------|-----------|
| HighErrorRate | >5% errores 5xx por 5m | critical |
| HighLatencyP95 | p95 > 2s por 5m | warning |
| APIDown | up == 0 por 1m | critical |
| PostgreSQLDown | pg_up == 0 por 1m | critical |
| HighMemoryUsage | >90% por 5m | warning |

**Nota:** Alertmanager no está desplegado por defecto. Para recibir notificaciones, configurar Alertmanager.

---

## Troubleshooting

### Prometheus no scrapea un target

**Síntoma:** Target aparece como "down" en http://localhost:9090/targets

**Verificar:**
```bash
# Target accesible?
curl http://localhost:8000/metrics

# Prometheus config correcta?
docker compose exec prometheus cat /etc/prometheus/prometheus.yml
```

**Causas comunes:**
1. Hostname incorrecto (usar nombre del service: `backend`, no `localhost`)
2. Puerto incorrecto
3. `METRICS_REQUIRE_AUTH=true` sin credenciales en Prometheus

### Grafana no muestra datos

**Verificar:**
1. Prometheus está corriendo: http://localhost:9090/-/healthy
2. Datasource configurado: Grafana → Configuration → Data Sources
3. Query funciona en Prometheus UI

### Métricas vacías después de restart

**Causa:** Prometheus reinicia desde cero (sin persistencia por defecto en dev)

**Solución en dev:** Esperar a que se acumulen datos (5-10 min)

---

## Configuración Avanzada

### Variables de entorno relevantes

| Variable | Default | Descripción |
|----------|---------|-------------|
| `METRICS_REQUIRE_AUTH` | `false` | Proteger /metrics |
| `OTEL_ENABLED` | `0` | Habilitar OpenTelemetry |
| `OTEL_EXPORTER_OTLP_ENDPOINT` | — | Endpoint OTLP |
| `GRAFANA_PASSWORD` | `admin` | Password de Grafana |

### Agregar métricas custom

```python
# En apps/backend/app/
from prometheus_client import Counter, Histogram

my_counter = Counter('my_custom_metric', 'Description')
my_counter.inc()
```

---

## Qué Mirar Primero en un Incidente

1. **¿Servicios vivos?**
   ```bash
   curl http://localhost:8000/healthz
   curl http://localhost:8001/healthz
   ```

2. **¿Hay errores recientes?**
   - Grafana → API Performance → Error Rate

3. **¿Latencia alta?**
   - Grafana → API Performance → p95 Latency

4. **¿DB saturada?**
   - Grafana → PostgreSQL → Connections

5. **¿Worker procesando?**
   - Grafana → Operations → Worker Jobs/min

---

## Referencias

- Prometheus config: `infra/prometheus/prometheus.yml`
- Alertas: `infra/prometheus/alerts.yml`
- Dashboards: `infra/grafana/dashboards/`
- Incident runbook: `docs/runbook/incident.md`
