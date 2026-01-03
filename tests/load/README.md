# Load Testing

## Requisitos

- [k6](https://k6.io/docs/getting-started/installation/) instalado

```bash
# macOS
brew install k6

# Ubuntu/Debian
sudo gpg -k && sudo gpg --no-default-keyring --keyring /usr/share/keyrings/k6-archive-keyring.gpg --keyserver hkp://keyserver.ubuntu.com:80 --recv-keys C5AD17C747E3415A3642D57D77C6C491D6AC1D69
echo "deb [signed-by=/usr/share/keyrings/k6-archive-keyring.gpg] https://dl.k6.io/deb stable main" | sudo tee /etc/apt/sources.list.d/k6.list
sudo apt-get update && sudo apt-get install k6
```

## Ejecución

### Test básico

```bash
# Contra ambiente local
k6 run tests/load/api.k6.js --env BASE_URL=http://localhost:8000

# Con output JSON para análisis
k6 run tests/load/api.k6.js --out json=results.json
```

### Test con más carga

```bash
# 50 VUs por 5 minutos
k6 run tests/load/api.k6.js --vus 50 --duration 5m
```

## Métricas

| Métrica | Umbral | Descripción |
|---------|--------|-------------|
| `http_req_failed` | <10% | Tasa de errores HTTP |
| `http_req_duration` | p95<2s | Latencia general |
| `ask_latency` | p95<3s | Latencia endpoint /ask |
| `health_latency` | p95<100ms | Latencia health check |

## Resultados esperados

Con la configuración actual (10 VUs):
- ~200-400 requests totales
- Throughput ~3-5 RPS
- Latencia ask: ~500ms-2s (depende de LLM)
