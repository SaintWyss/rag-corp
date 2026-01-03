# Readiness Review — 2026-01-02

**Branch:** work  
**Commit:** b3d17a9

## Resultado final
✅ READY

## Checklist por fases
- Fase 0 (contexto git): ✅ limpio, en rama esperada.
- Fase 1 (checks mecánicos):
  - 🔎 Path smoke test: ✅ sin referencias legacy.
  - 🧰 Workspace/Node: ✅ `pnpm install`, `pnpm -r list` operativos.
  - 📜 Contracts: ⚠️ `pnpm contracts:export` falla porque no hay `docker` en el entorno; `pnpm contracts:gen` ✅.
  - 🐍 Backend tests: ✅ `pytest -m unit` (offline) pasa con 99% coverage.
  - 🐳 Compose sanity: ⚠️ `docker compose config` no disponible por falta de binario `docker` en entorno.
- Fase 2 (revisión arquitectónica): ✅ sin bloqueadores; ver hallazgos.

## Hallazgos
### BLOCKER
- Ninguno.

### MAJOR
- Generación de contratos via `pnpm contracts:export` requiere `docker` (script invoca `docker compose run`). En el entorno actual no está instalado, por lo que la verificación automática falla.
- Comandos de Docker Compose (`docker compose config`) dependen de la presencia del binario; no disponible en este entorno de ejecución.

### MINOR
- Cobertura muestra 1 línea sin cubrir en `app/application/use_cases/answer_query.py` (branch de mensaje de error); no afecta funcionalidad pero podría cubrirse con tests adicionales.
- Prompt del LLM está hardcodeado en español en `GoogleLLMService` y parámetros de generación no son configurables por env; documentado pero limita flexibilidad entre entornos.

## Recomendaciones accionables
- **Contracts** (`package.json` / `scripts/export_openapi.py`): ejecutar `pnpm contracts:export` en un entorno con Docker disponible o sustituir el paso de `docker compose run` por una alternativa sin Docker si se desea validar en CI sin contenedores.
- **Compose** (`compose.yaml`): validar `docker compose config` en una máquina con Docker para confirmar que los contextos actualizados siguen correctos.
- **Tests** (`backend/app/application/use_cases/answer_query.py`): agregar un caso unitario que cubra la rama de `top_k <= 0` para elevar cobertura a 100% si se requiere.
- **LLM Config** (`backend/app/infrastructure/services/google_llm_service.py`): considerar parametrizar prompt/modelo vía variables de entorno para facilitar ajustes por entorno.

## Comandos y salidas relevantes
- `git rev-parse --abbrev-ref HEAD` / `git status` / `git log -1 --oneline`
- `rg -n "apps/web|services/rag-api|packages/contracts" .` (0 matches)
- `rg -n "(^|/)(apps|services|packages)/" .` (0 matches)
- `node -v` / `pnpm -v`
- `pnpm install`
- `pnpm -r list`
- `pnpm contracts:export` (falla por falta de docker)
- `pnpm contracts:gen`
- `cd backend && python --version && pip --version && pip install -r requirements.txt && pytest -m unit`
- `docker compose config` (falla por falta de docker)
