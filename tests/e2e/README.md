# tests/e2e/ — README

> **Navegación:** [← Volver a tests/](../README.md) · [← Volver a raíz](../../README.md)

## TL;DR (30 segundos)

- **Qué es:** Tests End-to-End usando Playwright.
- **Para qué sirve:** Simular usuarios reales interactuando con la UI y verificar flujos completos.
- **Quién la usa:** CI en cada PR, developers para validar features.
- **Impacto si se borra:** No hay validación de que los flujos de usuario funcionan.

---

## Para alguien con 0 conocimientos

### ¿Qué problema resuelve?

Imaginate que alguien abre la app, hace login, sube un documento, y hace una pregunta. ¿Cómo sabés que todo eso funciona? 

Playwright abre un browser real (Chrome, Firefox, etc.), hace clicks, escribe texto, y verifica que las cosas aparezcan como deben. Es como tener un tester robot 24/7.

### ¿Qué hay acá adentro?

```
e2e/
├── playwright.config.ts    # Configuración de Playwright
├── package.json            # Dependencias
├── fixtures/               # Archivos para tests
│   └── sample.pdf          # PDF de prueba para upload
├── tests/                  # Los tests en sí
│   ├── helpers.ts          # Funciones reutilizables
│   ├── documents.spec.ts   # Tests de documentos
│   ├── chat.spec.ts        # Tests de chat
│   ├── workspace-flow.spec.ts  # Tests de workspaces
│   └── full-pipeline.spec.ts   # Test de flujo completo
├── playwright-report/      # Reportes HTML generados
└── test-results/           # Screenshots y traces de fallos
```

| Archivo | Propósito |
|---------|-----------|
| `documents.spec.ts` | Ingesta, listado, detalle, delete de docs |
| `chat.spec.ts` | Chat streaming multi-turn |
| `workspace-flow.spec.ts` | Crear workspace → upload → chat |
| `full-pipeline.spec.ts` | Flujo completo (requiere worker + minio) |

### ¿Cómo se usa paso a paso?

**Requisitos:**
- Node.js 20 + pnpm
- Docker + Docker Compose
- `GOOGLE_API_KEY` (o usar `FAKE_LLM=1`)

**Instalación:**
```bash
pnpm e2e:install
pnpm e2e:install:browsers
```

**Correr tests (modo simple):**
```bash
# Levantar stack
docker compose --profile e2e up -d --build

# Correr tests
pnpm e2e

# Cleanup
docker compose --profile e2e down -v
```

**Correr tests full-pipeline (requiere worker + minio):**
```bash
# Levantar stack completo
FAKE_LLM=1 FAKE_EMBEDDINGS=1 \
S3_ENDPOINT_URL=http://minio:9000 \
S3_BUCKET=rag-documents \
S3_ACCESS_KEY=minioadmin \
S3_SECRET_KEY=minioadmin \
docker compose --profile e2e --profile worker --profile storage up -d --build

# Bootstrap admin
pnpm admin:bootstrap -- --email admin@test.com --password testpass123

# Correr tests
E2E_ADMIN_EMAIL=admin@test.com \
E2E_ADMIN_PASSWORD=testpass123 \
pnpm e2e -- --project=chromium
```

---

## Para engineers / seniors

### Responsabilidades (SRP)

Esta carpeta DEBE contener:
- Specs de Playwright (archivos `.spec.ts`)
- Fixtures de prueba (PDFs, etc.)
- Configuración de Playwright
- Helpers/utilities para tests

Esta carpeta NO DEBE contener:
- Unit tests del frontend
- Mocks de API (los E2E usan el backend real)
- Código de aplicación

### Variables de entorno

| Variable | Default | Descripción |
|----------|---------|-------------|
| `TEST_API_KEY` | — | API key inyectada en sessionStorage |
| `E2E_USE_COMPOSE` | — | Si está set, no levanta webServer |
| `E2E_BASE_URL` | `http://localhost:3000` | URL del frontend |
| `E2E_API_URL` | `http://localhost:8000` | URL del backend |
| `E2E_ADMIN_EMAIL` | — | Email del admin para login JWT |
| `E2E_ADMIN_PASSWORD` | — | Password del admin para login JWT |

### Colaboradores y dependencias

| Componente | Rol |
|------------|-----|
| Docker Compose | Levanta el stack |
| Backend (rag-api) | API bajo prueba |
| Frontend (web) | UI bajo prueba |
| Worker + Minio | Para tests de full-pipeline |

### Estructura de un test

```typescript
// tests/ejemplo.spec.ts
import { test, expect } from "@playwright/test";
import { login, waitForReady } from "./helpers";

test.describe("Feature X", () => {
  test.beforeEach(async ({ page }) => {
    await login(page, "admin@test.com", "testpass123");
  });

  test("should do something", async ({ page }) => {
    await page.goto("/some-page");
    await expect(page.locator("h1")).toHaveText("Expected Title");
  });
});
```

### Flujo de trabajo típico

**"Agregar test para feature nueva":**
1. Identificar el flujo a testear
2. Crear `tests/nueva-feature.spec.ts`
3. Usar helpers existentes de `helpers.ts`
4. Correr localmente: `pnpm e2e -- --grep "nombre del test"`
5. Commit

**"Test falla en CI pero pasa local":**
1. Descargar artifact `playwright-artifacts`
2. Abrir `playwright-report/index.html`
3. Ver screenshot del momento del fallo
4. Ver trace para interacción paso a paso
5. Generalmente es timing — agregar `waitFor` explícitos

**"Actualizar helpers después de cambio de UI":**
1. Editar `tests/helpers.ts`
2. Actualizar selectores/lógica
3. Correr todos los tests para verificar
4. Commit

### Riesgos y pitfalls

| Riesgo | Causa | Solución |
|--------|-------|----------|
| Flaky tests | Race conditions | Usar `waitFor`, `toBeVisible` |
| Tests muy lentos | Muchas operaciones | Paralelizar con workers |
| Selectores frágiles | IDs genéricos | Usar `data-testid` |
| Timeout en CI | Recursos limitados | Aumentar timeout en config |

### CI Configuration

```yaml
# .github/workflows/ci.yml
e2e:
  timeout-minutes: 35
  steps:
    - run: docker compose --profile e2e up -d --build
    # Wait for backend
    - run: curl -sf http://localhost:8000/healthz
    # Wait for frontend
    - run: curl -sf http://localhost:3000
    - run: pnpm -C tests/e2e test
    # Upload artifacts on failure
    - uses: actions/upload-artifact@v4
      if: failure()
      with:
        name: playwright-artifacts
        path: |
          tests/e2e/playwright-report
          tests/e2e/test-results
```

---

## CRC (Component/Folder CRC Card)

**Name:** `tests/e2e/`

**Responsibilities:**
1. Validar flujos de usuario end-to-end
2. Detectar regressions en integración
3. Generar reportes de fallos

**Collaborators:**
- Playwright (framework)
- Docker Compose (stack)
- CI (ejecución automatizada)
- Backend + Frontend (sistemas bajo prueba)

**Constraints:**
- Requiere stack Docker corriendo
- Timeouts pueden variar entre local y CI
- Tests deben ser idempotentes (no depender de estado previo)

---

## Evidencia

- `tests/e2e/playwright.config.ts` — configuración con timeouts y proyectos
- `tests/e2e/tests/helpers.ts` — funciones `login`, `waitForReady`, etc.
- `.github/workflows/ci.yml:129-189` — job `e2e`
- `package.json:23-26` — scripts e2e

---

## FAQ rápido

**¿Por qué usar Playwright y no Cypress?**
Playwright tiene mejor soporte multi-browser, es más rápido, y es mantenido por Microsoft.

**¿Cuánto tardan los tests?**
~2-5 minutos localmente, ~10-15 en CI (incluye build de imágenes).

**¿Cómo debuggeo un test?**
```bash
pnpm -C tests/e2e exec playwright test --debug
```

**¿Puedo ver el browser mientras corre?**
```bash
pnpm -C tests/e2e exec playwright test --headed
```

---

## Glosario

| Término | Definición |
|---------|------------|
| **E2E** | End-to-End — test que simula usuario completo |
| **Playwright** | Framework de testing de Microsoft |
| **Spec** | Archivo de especificación de tests |
| **Fixture** | Datos de prueba reutilizables |
| **Selector** | Forma de identificar elementos en la página |
| **Trace** | Grabación paso a paso de la interacción |
| **Flaky test** | Test que a veces pasa y a veces falla |

---

## Tests disponibles

| Test | Descripción | Requiere |
|------|-------------|----------|
| `documents.spec.ts` | Ingesta, listado, detalle, delete | Stack básico |
| `chat.spec.ts` | Chat streaming multi-turn | Stack básico |
| `workspace-flow.spec.ts` | Workspace create → upload → chat | Stack básico |
| `full-pipeline.spec.ts` | Upload → READY → chat (requiere procesamiento real) | Stack completo (worker + minio) |
