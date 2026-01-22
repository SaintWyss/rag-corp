# Observability Runbook (v6)

**Project:** RAG Corp
**Last Updated:** 2026-01-22

---

## Endpoints

- API health: `GET /healthz`
- API readiness: `GET /readyz`
- Metrics: `GET /metrics`
- Worker readiness: `GET http://localhost:8001/readyz` (en contenedor worker)

`/metrics` requiere auth si `METRICS_REQUIRE_AUTH=true`.

---

## Docker Compose perfiles

- `--profile observability` (Prometheus + Grafana + postgres-exporter)
- `--profile full` (stack completo)
- Archivo dedicado: `compose.observability.yaml`

Ejemplos:

```bash
pnpm docker:observability
# o
pnpm stack:full
```

---

## URLs locales

- Prometheus: http://localhost:9090
- Grafana: http://localhost:3001
- Postgres exporter: http://localhost:9187/metrics

---

## Troubleshooting rapido

```bash
curl http://localhost:8000/healthz
curl http://localhost:8000/readyz
curl -H "X-API-Key: <METRICS_KEY>" http://localhost:8000/metrics | head -20
```

