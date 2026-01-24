# tests/load/ — README

> **Navegación:** [← Volver a tests/](../README.md) · [← Volver a raíz](../../README.md)

## TL;DR (30 segundos)

- **Qué es:** Tests de carga usando k6.
- **Para qué sirve:** Medir rendimiento del API bajo múltiples usuarios concurrentes.
- **Quién la usa:** CI en push a main, SRE para baseline de performance.
- **Impacto si se borra:** Sin datos de rendimiento — no sabés cuánto aguanta el sistema.

---

## Para alguien con 0 conocimientos

### ¿Qué problema resuelve?

Tu app funciona con 1 usuario. ¿Pero aguanta 50? ¿100? ¿Cuánto tarda en responder cuando hay carga?

k6 simula muchos usuarios ("Virtual Users" o VUs) haciendo requests al mismo tiempo. Te dice latencia, errores, y throughput.

**Analogía:** Es como abrir las puertas del shopping y ver cuánta gente puede entrar antes de que se forme cuello de botella.

### ¿Qué hay acá adentro?

```
load/
├── README.md       # Documentación (estás acá)
└── api.k6.js       # Script de load test
```

| Archivo | Propósito |
|---------|-----------|
| `api.k6.js` | Define escenario de carga y métricas |

### ¿Cómo se usa paso a paso?

**1. Instalar k6:**
```bash
# macOS
brew install k6

# Ubuntu/Debian
sudo gpg -k && sudo gpg --no-default-keyring \
  --keyring /usr/share/keyrings/k6-archive-keyring.gpg \
  --keyserver hkp://keyserver.ubuntu.com:80 \
  --recv-keys C5AD17C747E3415A3642D57D77C6C491D6AC1D69

echo "deb [signed-by=/usr/share/keyrings/k6-archive-keyring.gpg] \
  https://dl.k6.io/deb stable main" | sudo tee /etc/apt/sources.list.d/k6.list

sudo apt-get update && sudo apt-get install k6
```

**2. Levantar el backend:**
```bash
docker compose up -d backend db
```

**3. Correr test básico:**
```bash
k6 run tests/load/api.k6.js --env BASE_URL=http://localhost:8000
```

**4. Correr con más carga:**
```bash
k6 run tests/load/api.k6.js --vus 50 --duration 5m
```

**Ver resultados:**
k6 muestra un resumen al final con latencias (p95, p99), requests/s, y errores.

---

## Para engineers / seniors

### Responsabilidades (SRP)

Esta carpeta DEBE contener:
- Scripts de k6 para load testing
- Escenarios de carga definidos
- Thresholds de rendimiento

Esta carpeta NO DEBE contener:
- Tests funcionales (eso va en e2e/)
- Scripts de stress testing destructivo (eso va separado)
- Resultados de tests (son generados, no versionados)

### Configuración del script

```javascript
// api.k6.js (estructura básica)
export const options = {
  vus: 10,                    // Virtual Users
  duration: "30s",
  thresholds: {
    http_req_failed: ["rate<0.1"],      // <10% errores
    http_req_duration: ["p(95)<2000"],  // p95 < 2s
    ask_latency: ["p(95)<3000"],        // /ask específico
    health_latency: ["p(95)<100"],      // health check
  }
};

export default function() {
  // Escenario de requests
  http.get(`${BASE_URL}/healthz`);
  http.post(`${BASE_URL}/api/query`, payload);
}
```

### Métricas clave

| Métrica | Threshold | Descripción |
|---------|-----------|-------------|
| `http_req_failed` | <10% | Tasa de errores HTTP |
| `http_req_duration` | p95<2s | Latencia general |
| `ask_latency` | p95<3s | Latencia del endpoint /ask o /query |
| `health_latency` | p95<100ms | Latencia de health check |

### Resultados esperados

Con la configuración default (10 VUs, 30s):
- ~200-400 requests totales
- Throughput: ~3-5 RPS
- Latencia /ask: ~500ms-2s (depende del LLM)
- Health: <50ms

### Colaboradores y dependencias

| Componente | Rol |
|------------|-----|
| Backend (rag-api) | Sistema bajo prueba |
| LLM (Google AI) | Afecta latencia si está habilitado |
| CI | Ejecuta en push a main |

### Flujo de trabajo típico

**"Quiero medir performance después de un cambio":**
1. Asegurar que el backend levanta clean
2. Correr baseline: `k6 run tests/load/api.k6.js`
3. Guardar resultados
4. Hacer el cambio
5. Correr de nuevo y comparar

**"El load test falla con >10% errores":**
1. Ver qué endpoint está fallando
2. Verificar logs del backend
3. Posibles causas: connection pool agotado, DB lenta, rate limiting

**"Quiero exportar resultados para análisis":**
```bash
k6 run tests/load/api.k6.js --out json=results.json
```

### Riesgos y pitfalls

| Riesgo | Causa | Solución |
|--------|-------|----------|
| Resultados inconsistentes | LLM real tiene latencia variable | Usar `FAKE_LLM=1` para tests reproducibles |
| CI falla por recursos | Ambiente limitado | Reducir VUs en CI |
| Skew por warm-up | Primera request lenta | Agregar warm-up stage |
| Medir DB fría | Sin datos en DB | Pre-popular con fixtures |

### CI Configuration

```yaml
# .github/workflows/ci.yml → load-test job
load-test:
  if: github.ref == 'refs/heads/main'  # Solo en push a main
  steps:
    - run: docker compose up -d backend db
    - run: k6 run tests/load/api.k6.js \
        --env BASE_URL=http://localhost:8000 \
        --vus 10 --duration 30s
```

---

## CRC (Component/Folder CRC Card)

**Name:** `tests/load/`

**Responsibilities:**
1. Medir latencia y throughput del API
2. Detectar regresiones de performance
3. Establecer baseline de rendimiento

**Collaborators:**
- k6 (herramienta)
- Backend (sistema bajo prueba)
- CI (ejecución automatizada)
- Grafana Cloud k6 (opcional, para histórico)

**Constraints:**
- Resultados varían con LLM real
- CI tiene recursos limitados
- Mide solo backend, no frontend

---

## Evidencia

- `tests/load/api.k6.js` — script con escenario y thresholds
- `.github/workflows/ci.yml:262-310` — job `load-test`
- `package.json` — (no hay script wrapper, se corre k6 directo)

---

## FAQ rápido

**¿Por qué k6 y no JMeter?**
k6 es moderno, scripteable en JS, y tiene mejor DX. JMeter es más para QA tradicional.

**¿Cuánto debería tardar?**
Con config default: ~30-60 segundos.

**¿Puedo correr contra producción?**
Técnicamente sí, pero cuidado con rate limiting y costos de LLM.

**¿Cómo veo resultados históricos?**
Enviar a Grafana Cloud k6:
```bash
k6 run --out cloud api.k6.js
```

---

## Glosario

| Término | Definición |
|---------|------------|
| **k6** | Herramienta de load testing de Grafana Labs |
| **VU (Virtual User)** | Usuario simulado haciendo requests |
| **Throughput** | Requests por segundo que el sistema puede manejar |
| **Latency** | Tiempo que tarda una request en completarse |
| **p95/p99** | Percentiles — latencia que el 95%/99% de requests no excede |
| **Threshold** | Límite que define si el test pasa o falla |
| **Warm-up** | Período inicial para que el sistema "caliente" caches |

---

## Ejemplos de uso avanzado

**Test de smoke (rápido, verificar que anda):**
```bash
k6 run api.k6.js --vus 1 --duration 10s
```

**Test de stress (encontrar límite):**
```bash
k6 run api.k6.js --vus 100 --duration 10m
```

**Con stages (ramp-up gradual):**
```javascript
// En api.k6.js
export const options = {
  stages: [
    { duration: "30s", target: 10 },  // Subir a 10 VUs
    { duration: "1m", target: 50 },   // Subir a 50 VUs
    { duration: "30s", target: 0 },   // Bajar a 0
  ]
};
```
