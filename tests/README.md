# tests/ — README

> **Navegación:** [← Volver a raíz del repo](../README.md)

## TL;DR (30 segundos)

- **Qué es:** Tests de integración y rendimiento que viven fuera de las apps.
- **Para qué sirve:** Validar que el sistema completo funciona correctamente.
- **Quién la usa:** CI, QA, y developers antes de mergear.
- **Impacto si se borra:** Sin tests E2E ni load tests — deploys a ciegas.

---

## Para alguien con 0 conocimientos

### ¿Qué problema resuelve?

Los tests unitarios verifican piezas pequeñas. Pero ¿cómo sabés que TODO el sistema funciona junto? ¿Que el frontend puede hablar con el backend? ¿Que el sistema aguanta carga?

Esta carpeta contiene:
- **Tests E2E (End-to-End):** Simulan un usuario real usando la UI
- **Load tests:** Simulan muchos usuarios para medir rendimiento

**Analogía:** Los unit tests son como probar que cada pieza de un auto funciona. Los E2E son como manejar el auto para ver que todo anda junto.

### ¿Qué hay acá adentro?

```
tests/
├── e2e/               # Tests End-to-End con Playwright
│   ├── fixtures/      # Archivos de prueba (sample.pdf)
│   ├── tests/         # Specs de Playwright
│   └── playwright-report/  # Reportes generados
└── load/              # Tests de carga con k6
    └── api.k6.js      # Script de load test
```

| Carpeta | Herramienta | Propósito |
|---------|-------------|-----------|
| `e2e/` | Playwright | Simular usuario en browser |
| `load/` | k6 | Medir rendimiento bajo carga |

### ¿Cómo se usa paso a paso?

**Correr E2E tests:**
```bash
# Instalar Playwright browsers
pnpm e2e:install:browsers

# Levantar stack y correr tests
docker compose --profile e2e up -d --build
pnpm e2e
```

**Correr load tests:**
```bash
# Instalar k6 (ver README de load/)
k6 run tests/load/api.k6.js --env BASE_URL=http://localhost:8000
```

---

## Para engineers / seniors

### Responsabilidades (SRP)

Esta carpeta DEBE contener:
- Tests de integración (E2E)
- Tests de performance (load)
- Fixtures compartidos para tests
- Configuración de herramientas de testing

Esta carpeta NO DEBE contener:
- Unit tests (van dentro de `apps/backend/tests` o `apps/frontend/__tests__`)
- Mocks de servicios (van junto a los unit tests)
- Código de aplicación

### Colaboradores y dependencias

| Test | Requiere |
|------|----------|
| E2E | Docker Compose stack corriendo (backend + frontend + DB) |
| E2E full-pipeline | Stack completo con worker + minio |
| Load | Solo backend corriendo |

### Estructura de CI

```yaml
# .github/workflows/ci.yml
e2e:              # Tests E2E básicos
  needs: [backend-test, frontend-test]
  
e2e-full:         # Tests de pipeline completo
  needs: [backend-test, frontend-test]
  
load-test:        # Solo en push a main
  needs: [backend-test]
```

### Flujo de trabajo típico

**"Agregar un test E2E nuevo":**
1. Crear archivo en `tests/e2e/tests/nombre.spec.ts`
2. Usar helpers de `tests/e2e/tests/helpers.ts`
3. Correr con `pnpm e2e -- --grep "nombre del test"`
4. El CI lo correrá automáticamente

**"Ver por qué falló un E2E en CI":**
1. Descargar artifact `playwright-artifacts` del CI
2. Abrir `playwright-report/index.html`
3. Ver screenshots y traces del fallo

### Riesgos y pitfalls

| Riesgo | Causa | Solución |
|--------|-------|----------|
| Flaky tests | Timing issues | Usar `waitFor`, aumentar timeouts |
| E2E muy lento | Muchos tests | Paralelizar con `--workers` |
| Load test falla en CI | Recursos limitados | Ajustar VUs y duración |
| Tests pasan local, fallan en CI | Diferencias de ambiente | Usar Docker para reproducir |

---

## CRC (Component/Folder CRC Card)

**Name:** `tests/`

**Responsibilities:**
1. Validar flujos E2E del sistema completo
2. Medir rendimiento bajo carga
3. Proveer fixtures de prueba

**Collaborators:**
- Docker Compose (levanta stack para tests)
- CI (ejecuta tests en PRs y pushes)
- Backend/Frontend (sistemas bajo prueba)

**Constraints:**
- E2E requiere stack levantado
- Load tests requieren al menos backend
- Timeouts pueden variar según ambiente

---

## Evidencia

- `pnpm-workspace.yaml:4` — `tests/e2e` incluido como workspace
- `package.json:23-26` — scripts de e2e
- `.github/workflows/ci.yml:129-189` — jobs de e2e
- `.github/workflows/ci.yml:262-310` — job de load-test

---

## FAQ rápido

**¿Por qué los unit tests no están acá?**
Porque van junto al código que testean — más fácil de mantener.

**¿Cuánto tardan los E2E?**
~2-5 minutos localmente, ~10-15 minutos en CI (incluye build).

**¿Debo correr load tests antes de cada PR?**
No, corren solo en push a main. Son para baseline de performance.

---

## Glosario

| Término | Definición |
|---------|------------|
| **E2E (End-to-End)** | Tests que simulan un usuario real |
| **Playwright** | Framework de testing de browsers de Microsoft |
| **k6** | Herramienta de load testing de Grafana Labs |
| **Fixture** | Datos de prueba reutilizables |
| **Flaky test** | Test que a veces pasa y a veces falla |
| **VU (Virtual User)** | Usuario simulado en load testing |

---

## Índice de subcarpetas

- [e2e/](./e2e/README.md) — Tests End-to-End con Playwright
- [load/](./load/README.md) — Tests de carga con k6
