# Migración Estructural - Option A

**Fecha:** 2026-01-02  
**Branch:** `refactor/option-a-structure`  
**Commits:** 6

---

## Índice

1. [Contexto](#1-contexto)
2. [Antes vs Después](#2-antes-vs-después)
3. [Cambios ejecutados](#3-cambios-ejecutados)
4. [Archivos actualizados](#4-archivos-actualizados)
5. [Verificación](#5-verificación)
6. [Riesgos y mitigaciones](#6-riesgos-y-mitigaciones)
7. [Notas y decisiones](#7-notas-y-decisiones)

---

## 1. Contexto

### Por qué se hizo

El monorepo usaba una estructura heredada de templates genéricos:
- `apps/` para frontends
- `services/` para backends
- `packages/` para librerías compartidas

Con un solo frontend y un solo backend, esta estructura agregaba niveles innecesarios de anidamiento y confusión.

### Qué problema resolvía

| Problema | Impacto |
|----------|---------|
| Paths largos (`services/rag-api/app/...`) | Difícil de navegar y recordar |
| Nomenclatura genérica (`web`, `rag-api`) | No comunica propósito |
| Estructura para escala que no existe | Overhead cognitivo innecesario |

### Decisión

**Option A**: Aplanar a `frontend/`, `backend/`, `shared/contracts/`

---

## 2. Antes vs Después

### ANTES

```
rag-corp/
├── apps/
│   └── web/                  # Next.js frontend
│       ├── app/
│       └── package.json
├── services/
│   └── rag-api/              # FastAPI backend
│       ├── app/
│       └── requirements.txt
├── packages/
│   └── contracts/            # OpenAPI → TypeScript
│       └── src/generated.ts
├── pnpm-workspace.yaml       # apps/*, services/*, packages/*
└── compose.yaml              # context: ./services/rag-api
```

### DESPUÉS

```
rag-corp/
├── frontend/                 # Next.js (antes apps/web)
│   ├── app/
│   └── package.json
├── backend/                  # FastAPI (antes services/rag-api)
│   ├── app/
│   └── requirements.txt
├── shared/
│   └── contracts/            # OpenAPI → TypeScript
│       └── src/generated.ts
├── pnpm-workspace.yaml       # frontend, shared/*
└── compose.yaml              # context: ./backend
```

---

## 3. Cambios ejecutados

### Fase 1: Mover estructura (`git mv`)

```bash
git mv apps/web frontend
git mv services/rag-api backend
mkdir -p shared
git mv packages/contracts shared/contracts
rmdir apps services packages
```

**Commit:** `chore(structure): move frontend/backend/contracts`  
**Archivos:** 64 renombrados

---

### Fase 2: Actualizar pnpm-workspace + scripts

**pnpm-workspace.yaml:**
```yaml
# Antes
packages:
  - "apps/*"
  - "services/*"
  - "packages/*"

# Después
packages:
  - "frontend"
  - "shared/*"
```

**package.json (root):**
```diff
- "contracts:export": "... --out /repo/packages/contracts/openapi.json"
+ "contracts:export": "... --out /repo/shared/contracts/openapi.json"
```

**Commit:** `chore(workspace): update pnpm-workspace + root scripts`

---

### Fase 3: Actualizar compose.yaml

```diff
  rag-api:
    build:
-     context: ./services/rag-api
+     context: ./backend
-   working_dir: /repo/services/rag-api
+   working_dir: /repo/backend
```

**Commit:** `chore(compose): update compose paths`

---

### Fase 4: Actualizar contracts pipeline

**backend/scripts/export_openapi.py:**
```diff
- # Output to packages/contracts/openapi.json
+ # Output to shared/contracts/openapi.json
```

**Commit:** `chore(contracts): update export/gen paths`

---

### Fase 5: Actualizar documentación

Archivos modificados:
- `README.md` (8 reemplazos)
- `FIXES.md` (3 reemplazos)
- `doc/README.md`
- `doc/api/http-api.md`
- `doc/architecture/overview.md`
- `doc/runbook/local-dev.md`

**Commit:** `docs: update paths in README/doc`

---

### Fase 6: Actualizar .github

**.github/instructions/backend.instructions.md:**
```diff
- applyTo: "services/rag-api/**"
+ applyTo: "backend/**"
```

**.github/instructions/frontend.instructions.md:**
```diff
- applyTo: "apps/web/**"
+ applyTo: "frontend/**"
```

**Commit:** `chore(github): update .github instruction paths`

---

## 4. Archivos actualizados

### Por categoría

| Categoría | Archivos | Cambios |
|-----------|----------|---------|
| **Estructura** | 64 archivos | `git mv` (rename) |
| **Workspace** | `pnpm-workspace.yaml` | Paths de packages |
| **Scripts root** | `package.json` | `contracts:export` path |
| **Docker** | `compose.yaml` | `build.context`, `working_dir` |
| **Contracts** | `backend/scripts/export_openapi.py` | Comentario de output |
| **Docs** | `README.md`, `FIXES.md`, `doc/*.md` | 6 archivos, paths |
| **GitHub** | `.github/instructions/*.md` | `applyTo` patterns |
| **Lock** | `pnpm-lock.yaml` | Auto-regenerado |

### Total

- **64 archivos renombrados** (sin cambios de contenido)
- **11 archivos modificados** (paths actualizados)
- **3 carpetas eliminadas** (`apps/`, `services/`, `packages/`)

---

## 5. Verificación

### Comandos de verificación

```bash
# 1. Workspaces reconocidos
pnpm install
# Expected: "Scope: all 3 workspace projects"

# 2. Docker build y run
docker compose up -d --build
# Expected: ✔ Container rag-corp-rag-api-1 Started

# 3. Health check
curl http://localhost:8000/healthz
# Expected: {"ok":true,"db":"connected"}

# 4. Contracts pipeline
pnpm contracts:export
pnpm contracts:gen
# Expected: "🎉 rag - Your OpenAPI spec has been converted..."

# 5. Frontend dev
cd frontend && pnpm dev
# Expected: "✓ Ready in Xms" en localhost:3000

# 6. TypeScript check
cd frontend && pnpm exec tsc --noEmit
# Expected: Sin errores
```

### Path Smoke Test

Verificar que NO quedan referencias viejas en código activo:

```bash
# Debe retornar 0 matches (excluyendo _legacy_candidates/)
rg "apps/web|services/rag-api|packages/contracts" \
   --glob '!_legacy_candidates/**' \
   --glob '!node_modules/**' \
   --glob '!pnpm-lock.yaml'
```

**Resultado esperado:** 0 matches

**Excepción aceptada:** `_legacy_candidates/auditoria.md` (documento histórico pre-migración)

---

## 6. Riesgos y mitigaciones

| Riesgo | Detección | Mitigación |
|--------|-----------|------------|
| **Imports rotos (Python)** | `python -c "import ast; ast.parse(...)"` | No hay imports con paths absolutos del repo |
| **Imports rotos (TS)** | `tsc --noEmit` | El alias `@contracts` apunta a `shared/contracts` via workspace |
| **Docker roto** | `docker compose config` | Validar YAML antes de build |
| **Workspace roto** | `pnpm list -r --depth=0` | Debe listar 3 proyectos |
| **Pérdida de historia git** | - | Se usó `git mv` para preservar historial |

### Rollback

Si algo falla crítico:

```bash
git checkout main
git branch -D refactor/option-a-structure
```

---

## 7. Notas y decisiones

### Qué NO se cambió (a propósito)

| Item | Razón |
|------|-------|
| `backend/app/` no se renombró a `src/` | Mantener convención Python existente |
| `frontend/app/` (Next.js App Router) | Es convención de Next.js 13+ |
| Estructura interna de capas (`domain/`, `application/`, `infrastructure/`) | Clean Architecture funciona bien |
| `infra/postgres/` | No forma parte del monorepo de código |
| `_legacy_candidates/auditoria.md` | Documento histórico, referencia válida |

### Qué SÍ se cambió

- Solo **paths de carpetas raíz** (apps→frontend, services→backend, packages→shared)
- Solo **referencias en configs y docs** que apuntaban a paths viejos
- **Cero cambios de lógica de negocio**

### Próximos pasos recomendados

1. **Merge PR** `refactor/option-a-structure` → `main`
2. **Quick wins backend** (del audit previo):
   - Agregar `HEALTHCHECK` al Dockerfile
   - Tests de integración para `/v1/ingest/text`
3. **Quick wins frontend**:
   - Agregar error boundary global
   - Loading states en componentes

---

## Referencias

- **PR:** `refactor/option-a-structure`
- **Auditoría previa:** `_legacy_candidates/auditoria.md`
- **Verificación:** Path Smoke Test (0 referencias viejas)

---

**Autor:** Copilot + Santi  
**Revisado:** 2026-01-02
