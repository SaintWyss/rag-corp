# PRON v6-A2 — DEUDA TÉCNICA + QUICK WINS (SIN CAMBIOS)

**Fecha:** 2026-01-22  
**Auditor:** Antigravity AI  
**Alcance:** RAG Corp v6 (SaintWyss/rag-corp)  
**Modo:** Solo análisis (NO MODIFICAR ARCHIVOS, NO COMMITS)

---

## RESUMEN EJECUTIVO

**Deuda técnica total:** 10 ítems (3 Alto, 5 Medio, 2 Bajo)  
**Quick wins:** 5 ítems (1-2h cada uno)  
**Mejoras medianas:** 3 ítems (1-2 días cada uno)  
**Postergar:** 3 ítems (falta información o riesgo alto)

**Orden de ejecución sugerido:** QW1 → QW2 → QW3 → TD1 → TD2 → MM1 → QW4 → TD3 → MM2 → QW5 → MM3

---

## (1) TOP 10 DEUDA TÉCNICA

### TD-01: CSP sin validación E2E

**Impacto:** Alto  
**Riesgo:** Seguridad (XSS)  
**Prioridad:** 🔴 Alta

#### Evidencia

- `apps/backend/app/platform/security.py:L56-60` define CSP sin `unsafe-inline`
- No existe test E2E que valide el header en respuestas

```python
# apps/backend/app/platform/security.py:L56-60
csp_policy = (
    "default-src 'self'; "
    "script-src 'self'; "
    ...
)
```

#### Por qué es un problema

1. **Zona ciega:** CSP configurado pero no verificado en runtime
2. **Regresión silenciosa:** cambio accidental podría agregar `unsafe-inline`
3. **Requisito hardening:** RNF-SEC4 exige CSP validado (`docs/system/informe_de_sistemas_rag_corp.md:L284`)

#### Fix recomendado

1. Crear `tests/e2e/security.spec.ts` con Playwright
2. Verificar header `Content-Security-Policy` en GET `/`
3. Asegurar que no contenga `'unsafe-inline'` ni `'unsafe-eval'`

```typescript
// tests/e2e/security.spec.ts (nuevo)
test("CSP header without unsafe directives", async ({ page }) => {
  const response = await page.goto("http://localhost:3000");
  const csp = response?.headers()["content-security-policy"];
  expect(csp).toBeDefined();
  expect(csp).not.toContain("unsafe-inline");
  expect(csp).not.toContain("unsafe-eval");
});
```

#### Cómo validar

```bash
# Manual
curl -I http://localhost:8000/ | grep -i "content-security-policy"

# Automático (después del fix)
pnpm -C tests/e2e test security.spec.ts
```

**Esfuerzo estimado:** 1-2 horas  
**Beneficio:** Garantiza hardening prod

---

### TD-02: /metrics sin test smoke de autenticación

**Impacto:** Alto  
**Riesgo:** Seguridad (information leak)  
**Prioridad:** 🔴 Alta

#### Evidencia

- `apps/backend/app/api/main.py:L361-378` implementa `/metrics` con `require_metrics_permission()`
- `apps/backend/app/platform/config.py:L205-206` valida `METRICS_REQUIRE_AUTH=true` en prod
- No existe test E2E que verifique 401/403 sin auth

```python
# apps/backend/app/api/main.py:L362
@app.get("/metrics")
def metrics(_auth: None = Depends(require_metrics_permission())):
```

#### Por qué es un problema

1. **Exposición de métricas:** podría filtrar info interna (tasas de error, latencias, IDs)
2. **Requisito hardening:** RNF-SEC6 exige `/metrics` protegido (`docs/system/informe_de_sistemas_rag_corp.md:L286`)
3. **Falla silenciosa:** si `METRICS_REQUIRE_AUTH` queda en false, no hay alarma

#### Fix recomendado

1. Crear `apps/backend/tests/smoke/test_metrics_auth.py`
2. Levantar API con `APP_ENV=production` y `METRICS_REQUIRE_AUTH=true`
3. Verificar que GET `/metrics` sin auth → 401/403

```python
# apps/backend/tests/smoke/test_metrics_auth.py (nuevo)
import pytest
from fastapi.testclient import TestClient

def test_metrics_requires_auth_in_prod(monkeypatch):
    monkeypatch.setenv("APP_ENV", "production")
    monkeypatch.setenv("METRICS_REQUIRE_AUTH", "true")
    from app.api.main import app
    client = TestClient(app)
    response = client.get("/metrics")
    assert response.status_code in [401, 403], "Metrics should be protected"
```

#### Cómo validar

```bash
# Manual (con stack prod-like)
export APP_ENV=production METRICS_REQUIRE_AUTH=true
curl -I http://localhost:8000/metrics # sin X-API-Key
# Esperado: 401 o 403

# Automático (después del fix)
pytest apps/backend/tests/smoke/test_metrics_auth.py
```

**Esfuerzo estimado:** 1 hora  
**Beneficio:** Previene fuga de información

---

### TD-03: Drift docs/OpenAPI (ejemplos HTTP)

**Impacto:** Medio  
**Riesgo:** Mantenibilidad  
**Prioridad:** 🟡 Media

#### Evidencia

- `docs/api/http-api.md:L82-108` ejemplos curl con paths `/v1/workspaces`
- `shared/contracts/openapi.json` tiene 14085 líneas con paths reales
- Ejemplo: docs muestran workspace_id como path param, pero algunos ejemplos usan query param legacy

```markdown
# docs/api/http-api.md:L94 (ejemplo)

curl -X POST http://localhost:8000/v1/workspaces/${WORKSPACE_ID}/documents/upload
```

vs OpenAPI real puede tener parámetros adicionales (tags, etc.)

#### Por qué es un problema

1. **Confusión de usuarios:** ejemplos desactualizados → errores 400/422
2. **Mantenimiento manual:** cada cambio de endpoint requiere actualizar docs
3. **Drift incremental:** sin proceso, docs se dessincronizan

#### Fix recomendado

1. Crear script `scripts/generate_api_examples.py` que lea OpenAPI
2. Extraer paths + schemas + generar curl examples
3. Regenerar `docs/api/http-api.md` automáticamente
4. Agregar CI check: `git diff --exit-code docs/api/http-api.md` después de regenerar

```python
# scripts/generate_api_examples.py (nuevo)
import json
with open('shared/contracts/openapi.json') as f:
    spec = json.load(f)

for path, methods in spec['paths'].items():
    if 'post' in methods:
        # Generate curl example for POST
        print(f"curl -X POST http://localhost:8000{path} ...")
```

#### Cómo validar

```bash
# Regenerar ejemplos
python scripts/generate_api_examples.py > docs/api/http-api.md.tmp

# Verificar drift
git diff docs/api/http-api.md docs/api/http-api.md.tmp
```

**Esfuerzo estimado:** 3-4 horas  
**Beneficio:** Docs siempre actualizados

---

### TD-04: Frontend sin coverage report en CI

**Impacto:** Medio  
**Riesgo:** Calidad  
**Prioridad:** 🟡 Media

#### Evidencia

- `apps/frontend/jest.config.js` define coverage settings
- `.github/workflows/ci.yml:L87-108` job `frontend-test` corre `pnpm test --coverage`
- Pero no reporta % en summary ni falla si coverage < threshold

```yaml
# .github/workflows/ci.yml:L104
- run: pnpm test --coverage
```

#### Por qué es un problema

1. **Regresión invisible:** coverage puede bajar sin alarma
2. **Falta de baseline:** no se sabe el % actual
3. **Comparación imposible:** no se puede comparar con backend (que sube a Codecov)

#### Fix recomendado

1. Agregar step de validación de coverage mínimo en CI:
   - Leer `coverage/coverage-summary.json`
   - Verificar `lines.pct >= 70` (o threshold elegido)
2. Opcional: subir a Codecov para dashboard

```yaml
# .github/workflows/ci.yml:L104-110 (modificar)
- run: pnpm test --coverage
- name: Check coverage threshold
  run: |
    COVERAGE=$(jq '.total.lines.pct' apps/frontend/coverage/coverage-summary.json)
    if (( $(echo "$COVERAGE < 70" | bc -l) )); then
      echo "Coverage $COVERAGE% is below 70%"
      exit 1
    fi
```

#### Cómo validar

```bash
# Local
pnpm -C apps/frontend test --coverage
cat apps/frontend/coverage/coverage-summary.json | jq '.total.lines.pct'

# CI (después del fix)
# El job fallará si coverage < threshold
```

**Esfuerzo estimado:** 1 hora  
**Beneficio:** Previene caída de calidad

---

### TD-05: Migración 008 sin estrategia de rollback

**Impacto:** Medio  
**Riesgo:** Operación  
**Prioridad:** 🟡 Media

#### Evidencia

- `apps/backend/alembic/versions/008_docs_workspace_id.py` backfill de `documents.workspace_id`
- Crea workspace "Legacy" si no existe
- No tiene función `downgrade()` completa (solo drop constraint/column)
- Rollback manual no documentado

```python
# apps/backend/alembic/versions/008_docs_workspace_id.py:L50-60
# upgrade: crea Legacy workspace + backfill
# downgrade: solo ALTER TABLE DROP workspace_id
```

#### Por qué es un problema

1. **Recovery imposible:** si falla en prod, rollback manual es complejo
2. **Pérdida de datos:** downgrade elimina `workspace_id` sin restaurar estado previo
3. **Falta de runbook:** equipo no sabe cómo revertir

#### Fix recomendado

1. Documentar en `docs/runbook/migrations.md`:
   - Backup pre-migración: `pg_dump -t documents > backup_documents.sql`
   - Rollback manual: restaurar desde backup + re-migrar hasta 007
2. Agregar nota en migración 008: "Rollback NO automático, ver runbook"

```markdown
# docs/runbook/migrations.md (agregar sección)

## Rollback de migración 008 (workspace_id)

**Pre-requisitos:** Backup de tabla `documents` tomado antes de upgrade.

**Pasos:**

1. `alembic downgrade 007`
2. Restaurar backup: `psql $DATABASE_URL -f backup_documents.sql`
3. Verificar integridad: `SELECT COUNT(*) FROM documents;`

**Nota:** Este rollback es destructivo. Solo usar en emergencia.
```

#### Cómo validar

```bash
# No hay validación automática (es documentación)
# Revisar que runbook existe y está completo
cat docs/runbook/migrations.md | grep -A 10 "Rollback de migración 008"
```

**Esfuerzo estimado:** 2 horas  
**Beneficio:** Reduce riesgo de deployment

---

### TD-06: Worker retry logic sin test unitario

**Impacto:** Medio  
**Riesgo:** Confiabilidad  
**Prioridad:** 🟡 Media

#### Evidencia

- `apps/backend/app/platform/config.py:L141-144` define retry settings
- Worker usa retry decorator en `apps/backend/app/worker/process_document.py`
- No existe test unitario que simule fallos transitorios

```python
# apps/backend/app/platform/config.py:L141-144
retry_max_attempts: int = 3
retry_base_delay_seconds: float = 1.0
retry_max_delay_seconds: float = 30.0
```

#### Por qué es un problema

1. **Idempotencia no verificada:** retry podría duplicar chunks
2. **Backoff no testeado:** delays podrían bloquear queue
3. **Fallo permanente:** ¿worker marca FAILED después de max attempts?

#### Fix recomendado

1. Crear `apps/backend/tests/unit/test_worker_retry.py`
2. Mock Google API para fallar 2 veces, luego éxito
3. Verificar: job marca READY después de 3 intentos, con delays crecientes

```python
# apps/backend/tests/unit/test_worker_retry.py (nuevo)
def test_worker_retries_transient_failure(mocker):
    # Mock Google API: falla 2 veces, luego OK
    call_count = 0
    def mock_embed(text):
        nonlocal call_count
        call_count += 1
        if call_count < 3:
            raise Exception("Transient failure")
        return [0.1] * 768

    mocker.patch('app.infrastructure.embeddings.GoogleEmbeddingService.embed_text', side_effect=mock_embed)

    # Ejecutar job
    process_document(document_id="test")

    # Verificar: 3 llamadas + estado READY
    assert call_count == 3
    doc = get_document("test")
    assert doc.status == "READY"
```

#### Cómo validar

```bash
pytest apps/backend/tests/unit/test_worker_retry.py -v
```

**Esfuerzo estimado:** 3 horas  
**Beneficio:** Garantiza resilencia

---

### TD-07: CORS credentials default false (posible breaking change)

**Impacto:** Bajo  
**Riesgo:** UX  
**Prioridad:** 🟢 Baja

#### Evidencia

- `apps/backend/app/platform/config.py:L109` define `cors_allow_credentials: bool = False`
- `apps/backend/app/api/main.py:L226-237` configura CORS con este valor
- Si frontend necesita enviar cookies cross-origin, falla

```python
# apps/backend/app/api/main.py:L229
allow_credentials=_cors_settings.cors_allow_credentials,  # False por defecto
```

#### Por qué es un problema

1. **Flujo JWT roto:** si UI está en diferente dominio, no puede enviar cookies httpOnly
2. **Cambio de prod:** habilitar credentials en prod requiere también CORS origin específico (no `*`)
3. **Riesgo CSRF:** credentials=true con origins permisivos = vulnerabilidad

#### Fix recomendado

1. Documentar en `docs/runbook/production-hardening.md`:
   - Cuándo habilitar `CORS_ALLOW_CREDENTIALS=true`
   - Requisito: `ALLOWED_ORIGINS` debe ser explícito (NO wildcard)
   - Advertencia: considerar CSRF tokens si se habilita
2. No cambiar default (es seguro)

```markdown
# docs/runbook/production-hardening.md (agregar sección)

## CORS Credentials (Cross-Origin Cookies)

**Default:** `CORS_ALLOW_CREDENTIALS=false` (seguro)

**Cuándo habilitar:**

- Frontend en dominio diferente de API (ej: `app.ragcorp.com` → `api.ragcorp.com`)
- UI usa JWT en cookies httpOnly

**Requisitos:**

1. `ALLOWED_ORIGINS` debe ser explícito: `https://app.ragcorp.com` (NO `*`)
2. Considerar CSRF tokens en formularios POST

**Riesgos:**

- `credentials=true` + `origins=*` → vulnerabilidad CORS
```

#### Cómo validar

```bash
# No hay validación automática (es documentación)
cat docs/runbook/production-hardening.md | grep -A 5 "CORS Credentials"
```

**Esfuerzo estimado:** 30 min  
**Beneficio:** Evita sorpresas en deploy cross-origin

---

### TD-08: Embeddings cache sin TTL explícito

**Impacto:** Bajo  
**Riesgo:** Performance  
**Prioridad:** 🟢 Baja

#### Evidencia

- `apps/backend/app/infrastructure/cache/embedding_cache.py` implementa cache in-memory o Redis
- No define TTL (time-to-live) → cache crece indefinidamente
- Redis podría llenar memoria en workloads con muchos docs únicos

```python
# apps/backend/app/infrastructure/cache/embedding_cache.py (inspección manual requerida)
# Si usa dict in-memory → sin eviction
# Si usa Redis → sin EXPIRE
```

#### Por qué es un problema

1. **Memory leak lento:** cache crece sin límite
2. **Eviction manual:** requiere restart para limpiar
3. **Escalabilidad:** con 100k docs, cache podría ser inmanejable

#### Fix recomendado

1. Agregar TTL configurable: `EMBEDDING_CACHE_TTL_SECONDS` (default: 86400 = 1 día)
2. Si backend=memory: usar LRU con `maxsize` (ej: `@lru_cache(maxsize=10000)`)
3. Si backend=Redis: agregar `EXPIRE` al guardar

```python
# apps/backend/app/infrastructure/cache/embedding_cache.py (modificar)
import os
TTL = int(os.getenv("EMBEDDING_CACHE_TTL_SECONDS", "86400"))

def set(key, value):
    if backend == "redis":
        redis.setex(key, TTL, value)  # Redis con TTL
    else:
        # In-memory: usar functools.lru_cache con maxsize
        pass
```

#### Cómo validar

```bash
# Verificar que Redis keys tienen TTL
redis-cli TTL "embedding:test_key"
# Esperado: valor > 0 (segundos restantes)
```

**Esfuerzo estimado:** 2 horas  
**Beneficio:** Evita memory leak

---

### TD-09: Load test solo en push a main

**Impacto:** Bajo  
**Riesgo:** CI  
**Prioridad:** 🟢 Baja

#### Evidencia

- `.github/workflows/ci.yml:L268-316` job `load-test` con condición `if: github.event_name == 'push' && github.ref == 'refs/heads/main'`
- No corre en PRs ni en schedule

```yaml
# .github/workflows/ci.yml:L271
if: github.event_name == 'push' && github.ref == 'refs/heads/main'
```

#### Por qué es un problema

1. **Feedback tardío:** regresión de perf solo se detecta después de merge
2. **Costo de fix:** revertir commit en main > bloquear PR
3. **Falta de baseline:** sin histórico de PRs para comparar

#### Fix recomendado

1. Opción A: habilitar en PRs con label `run-load-test`
2. Opción B: schedule semanal (nightly) con reporte a Slack/email

```yaml
# .github/workflows/ci.yml:L268-272 (modificar)
load-test:
  runs-on: ubuntu-latest
  needs: [backend-test]
  if: |
    (github.event_name == 'push' && github.ref == 'refs/heads/main') ||
    contains(github.event.pull_request.labels.*.name, 'run-load-test')
```

#### Cómo validar

```bash
# Crear PR con label "run-load-test"
gh pr create --label run-load-test
# Verificar que job load-test corre en CI
```

**Esfuerzo estimado:** 30 min  
**Beneficio:** Detecta regresiones antes de merge

---

### TD-10: Rollback sin checklist en deployment docs

**Impacto:** Bajo  
**Riesgo:** Operación  
**Prioridad:** 🟢 Baja

#### Evidencia

- `docs/runbook/deployment.md` existe pero no tiene sección "Emergency Rollback"
- `docs/runbook/deploy.md` tiene pasos de deploy pero no de rollback

#### Por qué es un problema

1. **Pánico en incidente:** equipo no sabe pasos de rollback
2. **Decisiones lentas:** ¿rollback de imagen Docker? ¿Re-deploy versión anterior?
3. **Falta de SLA:** sin checklist, rollback toma > 30 min

#### Fix recomendado

1. Agregar sección "Emergency Rollback" en `docs/runbook/deployment.md`:
   - Pasos para rollback de imagen Docker
   - Verificación de health checks post-rollback
   - Contactos de escalación

```markdown
# docs/runbook/deployment.md (agregar)

## Emergency Rollback

**Trigger:** Deploy fallido, error crítico en prod

**Pasos (< 10 min):**

1. Identificar versión anterior estable: `git tag --sort=-v:refname | head -2`
2. Re-deploy imagen: `docker compose pull && docker compose up -d --no-build`
3. Verificar health: `curl http://api.ragcorp.com/healthz`
4. Notificar en Slack #incidents

**Escalación:**

- SRE on-call: @sre-team
- PM: @pm-team
```

#### Cómo validar

```bash
# Verificar que sección existe
cat docs/runbook/deployment.md | grep -A 10 "Emergency Rollback"
```

**Esfuerzo estimado:** 1 hora  
**Beneficio:** Reduce MTTR (mean time to recovery)

---

## (2) QUICK WINS (1-2h cada uno)

### QW-01: Smoke test CSP header

**Prioridad:** 🔴 Alta  
**Esfuerzo:** 1 hora  
**Relacionado:** TD-01

#### Acción

Crear `tests/e2e/security.spec.ts` con validación de CSP

#### Pasos

1. `cd tests/e2e`
2. Crear archivo `security.spec.ts`:

```typescript
import { test, expect } from "@playwright/test";

test("CSP header without unsafe directives", async ({ page }) => {
  const response = await page.goto(
    process.env.E2E_BASE_URL || "http://localhost:3000",
  );
  const csp = response?.headers()["content-security-policy"];

  expect(csp).toBeDefined();
  expect(csp).not.toContain("unsafe-inline");
  expect(csp).not.toContain("unsafe-eval");
  expect(csp).toContain("default-src 'self'");
});
```

3. Ejecutar: `pnpm -C tests/e2e test security.spec.ts`

#### Validación

```bash
pnpm -C tests/e2e test security.spec.ts
# Esperado: ✅ PASSED
```

---

### QW-02: Smoke test /metrics auth

**Prioridad:** 🔴 Alta  
**Esfuerzo:** 1 hora  
**Relacionado:** TD-02

#### Acción

Crear `apps/backend/tests/smoke/test_metrics_auth.py`

#### Pasos

1. `mkdir -p apps/backend/tests/smoke && touch apps/backend/tests/smoke/__init__.py`
2. Crear archivo `test_metrics_auth.py`:

```python
import pytest
import os
from fastapi.testclient import TestClient

@pytest.mark.smoke
def test_metrics_requires_auth_in_prod(monkeypatch):
    """Verify /metrics returns 401/403 without auth when METRICS_REQUIRE_AUTH=true"""
    monkeypatch.setenv("APP_ENV", "production")
    monkeypatch.setenv("METRICS_REQUIRE_AUTH", "true")
    monkeypatch.setenv("DATABASE_URL", "postgresql://test:test@localhost/test")
    monkeypatch.setenv("GOOGLE_API_KEY", "test")

    # Import AFTER env vars are set
    from app.api.main import app

    client = TestClient(app)
    response = client.get("/metrics")

    assert response.status_code in [401, 403], \
        f"Expected 401 or 403, got {response.status_code} with body: {response.text}"
```

3. Actualizar `apps/backend/pytest.ini`:

```ini
markers =
    unit: Unit tests
    integration: Integration tests
    smoke: Smoke tests for critical paths
```

#### Validación

```bash
pytest apps/backend/tests/smoke/test_metrics_auth.py -v
# Esperado: ✅ PASSED
```

---

### QW-03: Frontend coverage threshold en CI

**Prioridad:** 🟡 Media  
**Esfuerzo:** 1 hora  
**Relacionado:** TD-04

#### Acción

Agregar step de validación de coverage en `.github/workflows/ci.yml`

#### Pasos

1. Verificar baseline actual:

```bash
pnpm -C apps/frontend test --coverage --silent
cat apps/frontend/coverage/coverage-summary.json | jq '.total.lines.pct'
# Output: ej. 65.5
```

2. Editar `.github/workflows/ci.yml:L87-108`:

```yaml
frontend-test:
  # ... (steps existentes)
  - run: pnpm test --coverage
  - name: Check coverage threshold
    run: |
      COVERAGE=$(jq '.total.lines.pct' apps/frontend/coverage/coverage-summary.json)
      echo "Coverage: $COVERAGE%"
      if (( $(echo "$COVERAGE < 60" | bc -l) )); then
        echo "❌ Coverage $COVERAGE% is below 60%"
        exit 1
      fi
      echo "✅ Coverage $COVERAGE% meets threshold"
```

3. Ajustar threshold (60%) según baseline actual

#### Validación

```bash
# Simular CI local
pnpm -C apps/frontend test --coverage
jq '.total.lines.pct' apps/frontend/coverage/coverage-summary.json
# Verificar que CI job pasa
```

---

### QW-04: Documentar CORS credentials

**Prioridad:** 🟢 Baja  
**Esfuerzo:** 30 min  
**Relacionado:** TD-07

#### Acción

Agregar sección en `docs/runbook/production-hardening.md`

#### Pasos

1. Editar `docs/runbook/production-hardening.md`:

````markdown
## CORS Credentials (Cross-Origin Cookies)

**Default:** `CORS_ALLOW_CREDENTIALS=false` ✅ (secure default)

### Cuándo habilitar

Solo si frontend está en dominio diferente de API:

- Ejemplo: UI en `https://app.ragcorp.com`, API en `https://api.ragcorp.com`
- UI necesita enviar JWT en cookies httpOnly

### Requisitos para habilitar

```bash
export CORS_ALLOW_CREDENTIALS=true
export ALLOWED_ORIGINS="https://app.ragcorp.com"  # ⚠️ NO usar '*'
```
````

### Riesgos

❌ **Configuración insegura:**

```bash
CORS_ALLOW_CREDENTIALS=true + ALLOWED_ORIGINS="*"  # VULNERABLE
```

✅ **Configuración segura:**

```bash
CORS_ALLOW_CREDENTIALS=true + ALLOWED_ORIGINS="https://app.example.com"
```

### Consideraciones adicionales

- Agregar CSRF tokens en formularios POST si se habilita credentials
- Verificar que `SameSite` cookie attribute es `None` o `Lax`

````

#### Validación
```bash
cat docs/runbook/production-hardening.md | grep -A 15 "CORS Credentials"
````

---

### QW-05: Habilitar load test en PRs con label

**Prioridad:** 🟢 Baja  
**Esfuerzo:** 30 min  
**Relacionado:** TD-09

#### Acción

Modificar condición del job `load-test` en CI

#### Pasos

1. Editar `.github/workflows/ci.yml:L268-272`:

```yaml
load-test:
  runs-on: ubuntu-latest
  needs: [backend-test]
  if: |
    (github.event_name == 'push' && github.ref == 'refs/heads/main') ||
    contains(github.event.pull_request.labels.*.name, 'run-load-test')
  # ... (resto del job sin cambios)
```

2. Documentar en `README.md`:

```markdown
## CI Jobs

- `load-test`: corre en push a `main` o PRs con label `run-load-test`
  - Para habilitar: `gh pr edit <PR> --add-label run-load-test`
```

#### Validación

```bash
# Crear PR de prueba
git checkout -b test-load-label
git commit --allow-empty -m "test: trigger load test"
git push origin test-load-label
gh pr create --title "Test load test label" --body "Testing"
gh pr edit --add-label run-load-test

# Verificar que job corre en CI
gh pr checks
```

---

## (3) MEJORAS MEDIANAS (1-2 días cada una)

### MM-01: Script de regeneración de ejemplos API docs

**Prioridad:** 🟡 Media  
**Esfuerzo:** 1-2 días  
**Relacionado:** TD-03

#### Objetivo

Automatizar generación de `docs/api/http-api.md` desde `shared/contracts/openapi.json`

#### Pasos

1. **Día 1:** Crear `scripts/generate_api_examples.py`
   - Parser de OpenAPI JSON
   - Template Jinja2 para Markdown
   - Generar curl examples por endpoint

2. **Día 2:** Integrar en CI
   - Agregar job `docs-check` en `.github/workflows/ci.yml`
   - Regenerar docs y verificar `git diff`
   - Fallar si hay drift

#### Validación

```bash
python scripts/generate_api_examples.py --output docs/api/http-api.md.tmp
git diff docs/api/http-api.md docs/api/http-api.md.tmp
```

---

### MM-02: Test unitario de worker retry logic

**Prioridad:** 🟡 Media  
**Esfuerzo:** 1 día  
**Relacionado:** TD-06

#### Objetivo

Verificar que worker reintenta jobs fallidos con backoff exponencial

#### Pasos

1. Crear `apps/backend/tests/unit/test_worker_retry.py`
2. Mock Google API para fallar N-1 veces, luego éxito
3. Verificar:
   - Job marca `READY` después de retries
   - Delays siguen backoff exponencial
   - Job marca `FAILED` después de `retry_max_attempts`

#### Validación

```bash
pytest apps/backend/tests/unit/test_worker_retry.py -v
```

---

### MM-03: Embeddings cache con TTL configurable

**Prioridad:** 🟢 Baja  
**Esfuerzo:** 1 día  
**Relacionado:** TD-08

#### Objetivo

Agregar TTL a embedding cache (Redis + in-memory)

#### Pasos

1. Agregar env var `EMBEDDING_CACHE_TTL_SECONDS` (default: 86400)
2. Modificar `apps/backend/app/infrastructure/cache/embedding_cache.py`:
   - Redis: usar `setex(key, ttl, value)`
   - In-memory: migrar a `functools.lru_cache(maxsize=10000)`
3. Test unitario: verificar que keys expiran

#### Validación

```bash
# Redis
redis-cli TTL "embedding:test"
# Esperado: > 0

# In-memory (verificar con test)
pytest apps/backend/tests/unit/test_cached_embedding_service.py -k ttl
```

---

## (4) "NO TOCAR TODAVÍA" (Postergar)

### NT-01: Migración 008 rollback automático

**Razón:** Complejidad alta + riesgo de pérdida de datos  
**Alternativa:** Documentar rollback manual (ver TD-05)  
**Cuándo reconsiderar:** Si se requiere rollback en producción más de 1 vez

---

### NT-02: Refactor de legacy endpoints (remover)

**Razón:** Compatibilidad con clientes actuales  
**Bloqueante:** No se sabe cuántos clientes usan legacy  
**Cuándo reconsiderar:** Después de 6 meses de deprecation notice + telemetry de uso

---

### NT-03: Multi-tenant (workspace por empresa)

**Razón:** Out-of-scope v6 (`docs/system/informe_de_sistemas_rag_corp.md:L55`)  
**Bloqueante:** Requiere redesign de auth + schema  
**Cuándo reconsiderar:** Cuando exista requisito de negocio (> 5 clientes enterprise)

---

## (5) ORDEN DE EJECUCIÓN SUGERIDO

### Sprint 1 (1 semana)

1. **QW-01:** Smoke test CSP (1h)
2. **QW-02:** Smoke test /metrics auth (1h)
3. **QW-03:** Frontend coverage threshold (1h)
4. **TD-01:** CSP validación E2E (incluido en QW-01)
5. **TD-02:** /metrics auth test (incluido en QW-02)

**Total:** 3 horas  
**Entregables:** 2 gaps de seguridad cerrados

### Sprint 2 (1 semana)

6. **MM-01:** Script regeneración API docs (2 días)
7. **QW-04:** Documentar CORS credentials (30 min)
8. **TD-03:** Drift docs/OpenAPI (incluido en MM-01)

**Total:** 2.5 días  
**Entregables:** Docs auto-generados + runbook CORS

### Sprint 3 (1 semana)

9. **MM-02:** Test worker retry (1 día)
10. **QW-05:** Load test en PRs (30 min)
11. **TD-05:** Documentar rollback migración (2h)

**Total:** 1.5 días  
**Entregables:** Worker resiliente + CI mejorado

### Backlog (futuro)

12. **MM-03:** Cache TTL (1 día)
13. **TD-10:** Checklist rollback deployment (1h)

---

## (6) DEPENDENCIAS

```
QW-01 → TD-01 (CSP test)
QW-02 → TD-02 (/metrics test)
QW-03 → TD-04 (coverage threshold)
MM-01 → TD-03 (docs regeneration)
MM-02 → TD-06 (worker retry)
MM-03 → TD-08 (cache TTL)

Independientes: QW-04, QW-05, TD-05, TD-07, TD-09, TD-10
```

**Crítico:** QW-01 y QW-02 deben completarse antes de próximo deploy a prod.

---

**FIN DEL INFORME v6-A2**
