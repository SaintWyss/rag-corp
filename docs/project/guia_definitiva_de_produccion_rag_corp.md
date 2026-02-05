<!--
===============================================================================
TARJETA CRC - docs/project/guia_definitiva_de_produccion_rag_corp.md
===============================================================================
Responsabilidades:
- Definir el estándar de producción y los gates verificables.
- Servir como fuente de verdad para despliegue, seguridad y calidad.

Colaboradores:
- docs/runbook/*
- infra/k8s/*
- .github/workflows/*

Invariantes:
- No incluir secretos reales.
- Mantener rutas coherentes con el repo.
===============================================================================
-->
# Guía Definitiva de Producción — RAG Corp

> Documento único para llevar el repo **a estado “production‑ready”** y desplegarlo en un entorno empresarial con seguridad, operación y calidad verificables.
>
> **Fuentes prioritarias**
> 1) **Informe de Negocio (BRD/SRS)**: “Contexto A — Informe de Negocio (brd_srs) — Rag Corp” (define alcance, casos de uso, FR/NFR y criterios de aceptación).
> 2) **Playbook Pro‑Senior**: “Playbook Universal Pro‑senior — Rag Corp” (define método, trazabilidad, boundaries y estándares).
> 3) **Repo actual (zip)**: este documento está alineado a la estructura presente (apps/backend, apps/frontend, infra/k8s, docs/, shared/contracts).
>
---

## 0) Tarjeta CRC (para este documento)

**Class (Artefacto):** `docs/project/production-ready.md` (Guía Definitiva de Producción)

**Responsibilities (Responsabilidades):**
- Definir el **estado objetivo final** (production‑ready) para RAG Corp, sin cambios de producto.
- Unificar en un solo lugar: **arquitectura, seguridad, performance, operación, calidad, despliegue y verificación**.
- Establecer **checklists** y comandos verificables (CI/local) para aceptar el release.
- Indicar **decisiones y límites**: canon docs, stubs, source of truth, y política de secretos.

**Collaborators (Colaboradores):**
- `README.md` (entrada principal)
- `docs/README.md` (portal docs)
- `apps/backend/*` (API/worker/migrations)
- `apps/frontend/*` (UI Next.js)
- `shared/contracts/*` (OpenAPI + cliente TS)
- `infra/k8s/*` (manifests + kustomize)
- `.github/workflows/*` (CI/CD)

**Invariantes (Invariantes):**
- **No se cambian endpoints ni contratos** (solo hardening, operación, docs, CI/CD, deploy).
- **No se versionan secretos reales**.
- Todo cambio debe ser **verificable** (tests/checks) y trazable.

---

## 1) Qué es RAG Corp (visión empresarial)

RAG Corp es un sistema empresarial de **gestión y consulta de conocimiento documental**. Centraliza documentación interna por **espacios de trabajo (workspaces)**, ingesta y procesa documentos, habilita **búsqueda semántica** y genera **respuestas con evidencia** (fuentes/citas), preservando **aislamiento** y **control de acceso**.

### 1.1 Problema que resuelve
- Conocimiento distribuido (PDFs, manuales, políticas) → búsqueda lenta y dependiente de “memoria tribal”.
- Versiones contradictorias → errores operativos.
- Respuestas sin trazabilidad → difícil auditar decisiones.
- Riesgo de acceso indebido entre áreas.

### 1.2 Objetivos de negocio (medibles)
- Reducir tiempo medio de búsqueda y “Time To Answer”.
- Mejorar calidad de respuestas internas mediante evidencia.
- Disminuir riesgos de acceso indebido mediante aislamiento/ACL.
- Operación auditable (monitoring, incidentes, registros).

### 1.3 Alcance (scope)
**Incluye:**
- Workspaces: alta/listado/consulta/actualización/archivado.
- Acceso: roles + ACL por workspace.
- Documentos: subir/listar/consultar/borrar‑archivar/reprocesar + estados.
- Procesamiento: extracción/normalización/chunking + representaciones para retrieval.
- Consulta: ask (respuesta) + ask streaming (incremental) + query (chunks).
- Admin global: usuarios y workspaces.
- Operación: health checks, métricas, dashboards cuando desplegado.

**Excluye:**
- Integraciones automáticas (Drive/Confluence/SharePoint) salvo contratación.
- DLP/clasificación avanzada automática más allá de límites y control de acceso.
- Flujos formales multi‑etapa de aprobación para publicación.

---

## 2) Arquitectura del sistema (estado final esperado)

### 2.1 Componentes
- **Frontend (Next.js)**: UI web y proxy por rewrites para `/auth`, `/api`, `/v1`.
- **Backend (FastAPI)**: API HTTP, autenticación, autorización, límites, observabilidad.
- **Worker (RQ/Redis)**: pipeline async (ingesta/procesamiento) cuando se habilita.
- **DB (PostgreSQL + pgvector)**: persistencia de usuarios/workspaces/ACL/documentos/chunks/auditoría.
- **Storage (S3/MinIO)**: almacenamiento de archivos originales.
- **Observabilidad (Prometheus/Grafana)**: métricas + dashboards + alerting.
- **Contratos**: OpenAPI exportado desde backend → cliente TS generado (monorepo).

### 2.2 Principios invariantes (producto + seguridad)
- **Workspace‑first / hard scoping**: toda consulta y resultado pertenece al workspace objetivo.
- **Evidencia por defecto**: la respuesta incluye fuentes cuando existan.
- **Auditable**: acciones críticas registrables.

### 2.3 Entregable de arquitectura
Para producción, el mínimo exigido es:
- Mapa de componentes + boundaries (ya existe en `docs/architecture/diagrams/*`).
- Secuencias clave: login, upload async, ask scoped, ask streaming (ya existen como `.mmd`).
- ADRs que expliquen decisiones clave y tradeoffs.

---

## 3) Estructura del repo (TO‑BE = AS‑IS actual)

> **Objetivo**: que un equipo nuevo entienda *dónde tocar* y *qué no cruzar*.

### 3.1 Raíz
- `README.md`: entrada principal, quickstart, endpoints canónicos, hardening.
- `compose.yaml`: orquestación local por perfiles (core/ui/rag/observability/full).
- `docs/`: portal, referencias canónicas, runbooks, ADRs.
- `.github/`: workflows CI/CD, guidelines.
- `tests/`: e2e, load, helpers (si aplica).

### 3.2 apps/backend
- `apps/backend/app/`: código backend (capas + interfaces HTTP + worker).
- `apps/backend/alembic/`: migraciones.
- `apps/backend/scripts/`: export OpenAPI, bootstrap admin, etc.
- `apps/backend/tests/`: unit/integration/e2e (pytest).
- `apps/backend/Dockerfile`: build multi‑stage + runtime no‑root.

### 3.3 apps/frontend
- `apps/frontend/app/`: routing Next (app router) con layouts.
- `apps/frontend/src/`:
  - `app-shell/`: providers/guards/layout wiring.
  - `features/`: módulos por dominio (auth/chat/documents/rag/workspaces).
  - `shared/`: api/contracts/routes/sse + ui shells/components + lib/config.
  - `test/`: helpers/fixtures/msw.
- `apps/frontend/tests/`: unit + integration.
- `apps/frontend/Dockerfile`: build standalone + runtime no‑root.

### 3.4 shared/contracts
- `shared/contracts/openapi.json`: contrato exportado.
- `shared/contracts/src/generated.ts`: cliente/SDK generado.

### 3.5 infra/
- `infra/k8s/`: manifests + kustomize (namespace/configmap/secret/deploy/services/hpa/pdb/netpol/ingress).
- `infra/prometheus/`, `infra/grafana/`, `infra/postgres/`: stack de observabilidad y bootstrap.

### 3.6 docs/
- `docs/README.md`: portal y política de stubs.
- `docs/reference/*`: canon (config, errors, access-control, limits, api, data, design).
- `docs/runbook/*`: operación (deploy, incidentes, troubleshooting, observability, hardening).
- `docs/architecture/*`: overview, ADRs, diagrams.
- `docs/requirements/*`: FR/NFR.

---

## 4) Requisitos de Producción (traducción directa del BRD/SRS)

> Estos requisitos se convierten en **gates** verificables.

### 4.1 Seguridad (NFR‑S)
- Autenticación obligatoria para recursos protegidos.
- Autorización por rol/ACL en cada request.
- Aislamiento workspace‑scoped en queries/resultados.
- Validación de inputs y sanitización de redirecciones.
- Límites: upload/payload/streaming (eventos/bytes/tiempo).
- Secretos fuera de VCS + rotación documentada.
- Errores/logs sin filtrar datos sensibles.

### 4.2 Performance (NFR‑P)
- Timeouts configurables en requests y streaming.
- Evitar tareas globales innecesarias (todo por workspace).
- Manejo bajo límites definidos.

### 4.3 Resiliencia (NFR‑R)
- Health checks + readiness/liveness.
- Reintentos controlados (backoff) para idempotentes.
- Cancelación segura de streaming.

### 4.4 Operación/Observabilidad (NFR‑O)
- Logs estructurados.
- Métricas (latencia, errores, procesamiento).
- Runbooks mínimos: despliegue, incidentes, troubleshooting, rotación.

### 4.5 Mantenibilidad/Calidad (NFR‑M)
- Contrato HTTP consistente/documentado (OpenAPI).
- Separación por capas/módulos.
- Tests unit + integración para refactor seguro.

---

## 5) Política de configuración y secretos (P0)

### 5.1 Regla de oro
- **Ningún secreto real** se trackea en Git.
- Todo secreto vive en:
  - **Local dev**: `.env` (no trackeado)
  - **CI/CD**: GitHub Secrets / Variables
  - **K8s**: `Secret`/External Secrets/Vault

### 5.2 Verificación automática
Debe existir una verificación que falle el build si:
- se detectan patrones de secretos en archivos trackeados,
- o se intenta commitear `.env` no‑example.

> Resultado esperado: la verificación corre en CI y local (pre‑commit opcional).

### 5.3 Rotación
Mantener un runbook que indique:
- Qué rotar (GOOGLE_API_KEY, JWT_SECRET, API_KEYS_CONFIG si aplica).
- Cómo rotar en local/CI/K8s.
- Cómo invalidar credenciales previas y cómo verificar post‑rotación.

---

## 6) Hardening técnico para producción

### 6.1 Backend (API/Worker)
Checklist:
- **Fail‑fast** en `APP_ENV=production` (no defaults inseguros).
- Cookies/auth:
  - `Secure`, `HttpOnly`, `SameSite` apropiado.
  - Rotación de JWT secret.
- **Rate limiting** activo según NFR y operación.
- **Límites**:
  - upload max
  - payload max
  - streaming: timeout, max events, max chars
- **Errores** RFC7807, sin leaks de stack/secret.
- **/metrics** protegido (auth requerido en prod).
- DB pool y timeouts definidos.

### 6.2 Frontend (Next.js)
Checklist:
- Rewrites/proxy para evitar CORS y mantener cookies same‑origin.
- **Redirecciones seguras** (sanitize next path) para evitar open redirect.
- CSP y headers base:
  - Ajustar CSP para producción (evitar `unsafe-eval`; minimizar `unsafe-inline` si es posible).
  - Confirmar `connect-src` compatible con SSE y/o websockets en dev.
- Streaming SSE robusto:
  - abort/cancel
  - límites de tamaño/tiempo
  - parsing defensivo

### 6.3 Infra / K8s
Checklist:
- Namespace dedicado.
- NetworkPolicy (ingress/egress mínimo).
- PDB para servicios críticos.
- HPA con métricas (CPU y/o custom).
- Ingress con TLS (cert-manager o equivalente).
- Timeouts del ingress compatibles con streaming (SSE suele requerir `proxy-read-timeout` alto).

---

## 7) Observabilidad y operación

### 7.1 Métricas mínimas
- Latencias (p50/p95), errores 4xx/5xx.
- Throughput (RPS), tamaño de payload.
- Pipeline async: jobs en cola, tiempos de procesamiento, ratio de fallos.
- DB: conexiones, slow queries (según tooling), CPU/mem.

### 7.2 Logs
- Estructurados (JSON o key-value consistente).
- Sanitizados (no tokens, no API keys, no PII innecesaria).
- Correlación (request_id/trace_id si existe).

### 7.3 Runbooks obligatorios
- Deploy (paso a paso + rollback)
- Incident response (severidad, triage)
- Troubleshooting (síntomas → diagnóstico → acción)
- Secret rotation
- Migrations (cómo aplicar y cómo recuperar)

---

## 8) Calidad y gates (CI/CD)

### 8.1 Estrategia de pruebas
- **Unit**: lógica pura y helpers (rápidas).
- **Integration**: backend contra DB real (o fixtures), frontend contra mocks.
- **E2E**: flujo user‑journey (login → workspace → upload → ask).
- **Security checks**: secret scan, lint, dependabot.

### 8.2 Gates mínimos antes de release
- `pnpm lint` (repo)
- `pnpm test` (frontend)
- `pytest` (backend unit + integration)
- `contracts:export + contracts:gen` (no drift OpenAPI)
- secret scan (gitleaks + script local)
- build de imágenes Docker (backend + frontend)

---

## 9) Despliegue a producción (K8s) — procedimiento estándar

### 9.1 Preparación
- Definir entorno: **staging** y **production**.
- Definir dominio(s):
  - UI: `ragcorp.<dominio>`
  - API: `api.ragcorp.<dominio>`
- Definir store de secretos: External Secrets / Vault / GitHub Secrets (según organización).

### 9.2 Imagen y versionado
- Publicar imágenes con tags inmutables (ej: `1.2.3`, `sha-<gitsha>`).
- Evitar `latest` en producción.

### 9.3 Kustomize (overlay recomendado)
- Base: `infra/k8s/`.
- Overlays:
  - `infra/k8s/overlays/staging/`
  - `infra/k8s/overlays/prod/`

Cada overlay debe:
- Sobrescribir `images` con `newName` y `newTag`.
- Setear hosts reales en Ingress.
- Ajustar recursos (requests/limits) y HPA.
- Definir Secret source (ExternalSecret o Secret manual).

### 9.4 Migraciones
- Ejecutar migraciones como job controlado antes del rollout (o initContainer).
- Política: “migraciones forward‑only” + rollback por restore/backup (si aplica).

### 9.5 Smoke test post‑deploy
- `/healthz` OK
- login OK
- crear workspace OK
- subir doc (staging) OK
- ask con fuentes OK

---

## 10) Checklist final de aceptación (go‑live)

> Esta lista define el **Definition of Done** para “production‑ready”.

### 10.1 Producto (criterios del BRD/SRS)
- [ ] Crear y administrar workspace según rol.
- [ ] Subir documentos, procesarlos y observar estado.
- [ ] Consultar y obtener respuesta con fuentes.
- [ ] Autorización bloquea accesos fuera del workspace.
- [ ] Límites y timeouts presentes y configurables.
- [ ] Runbooks mínimos disponibles.

### 10.2 Seguridad
- [ ] No hay secretos trackeados + verificación automática activa.
- [ ] JWT secret fuerte + cookies seguras.
- [ ] Rate limiting configurado.
- [ ] Logs sanitizados.
- [ ] Headers/CSP ok.
- [ ] NetworkPolicy aplicada.

### 10.3 Operación
- [ ] Dashboards importados y alertas mínimas.
- [ ] Backups definidos y probados.
- [ ] Procedimiento de rollback definido.

### 10.4 Calidad
- [ ] CI verde (lint/tests/build/contracts/security).
- [ ] Versionado y release notes listos.

---

## 11) Plan ejecutable para automatizar (para Codex en “plan mode”)

### 11.1 Objetivo
Aplicar cualquier ajuste faltante para cumplir **100%** el checklist de go‑live, sin cambiar producto (endpoints/contratos) ni introducir secretos.

### 11.2 Reglas
- **CERO invención**: comandos/endpoints/env/scripts deben venir de fuentes reales del repo.
- No introducir secretos ni ejemplos con valores reales.
- Mantener CRC donde aplique (configs, scripts, workflows, runbooks).
- Cada cambio debe incluir: **archivo → intención → riesgo → verificación**.

### 11.3 Gaps detectados en el repo (repo‑grounded)
> Estos puntos están **verificados** contra el zip actual y deben cerrarse o aceptarse explícitamente.

1) **Deploy workflow referencia un Dockerfile inexistente (backend)**
   - Evidencia: `.github/workflows/deploy.yml` usa `./apps/backend/Dockerfile.prod`.
   - Estado: en el repo existe `apps/backend/Dockerfile` pero **no** `Dockerfile.prod`.
   - Acción: (a) crear `apps/backend/Dockerfile.prod` (wrapper/alias) o (b) ajustar workflow a `apps/backend/Dockerfile`.
   - Verificación: `docker build -f apps/backend/Dockerfile ...` y workflow verde.

2) **K8s usa imágenes `ragcorp/*:latest` vs publish a registry**
   - Evidencia: `infra/k8s/base/kustomization.yaml` define `ragcorp/backend:latest` y `ragcorp/frontend:latest`.
   - Riesgo: drift entre imágenes publicadas (p.ej. GHCR) y lo desplegado.
   - Acción: crear overlays (staging/prod) que reescriban `images.newName/newTag` hacia el registry real (GHCR/ECR/GCR).
   - Verificación: `kubectl kustomize infra/k8s/overlays/prod | grep image:`.

3) **Ingress timeouts pueden cortar SSE**
   - Evidencia: `infra/k8s/base/ingress.yaml` tiene `nginx.ingress.kubernetes.io/proxy-read-timeout: "60"`.
   - Acción: definir timeout de lectura mayor para SSE (p.ej. 10–30 min) o estrategia de keepalive.
   - Verificación: ask streaming prolongado sin cortes (staging) + métricas de duración.

4) **Gates unificados de “release verification”**
   - Estado: existe `pnpm verify` como entrypoint único (local/CI).
   - Acción: mantener orden estable (secrets → contracts → FE → BE → builds → render → e2e).
   - Verificación: `pnpm verify` pasa en limpio.

### 11.4 Tareas típicas que Codex debe cerrar (si faltan)
- Completar overlays Kustomize (staging/prod) y documentar `kubectl apply -k ...`.
- Refinar hardening de ingress (timeouts streaming + headers).
- Asegurar runbooks con comandos reales + smoke tests reproducibles.
- (Opcional enterprise) agregar SCA/containers scan en CI (Trivy/Grype + SBOM) con `--fail-on` controlado.

---

## 12) Apéndice — Comandos de verificación (repo‑grounded)

> Comandos reales (ver `package.json` raíz y `apps/frontend/package.json`).

### 12.1 Verificación rápida (local)
- Instalar dependencias monorepo:
  - `pnpm install`
- Verificación unificada (recomendada):
  - `pnpm verify`
- Lint global (turbo):
  - `pnpm lint`
- Build global (turbo):
  - `pnpm build`

### 12.2 Frontend
- Lint + typecheck + tests (recomendado):
  - `pnpm -C apps/frontend check`
- Alternativas:
  - `pnpm -C apps/frontend lint`
  - `pnpm -C apps/frontend typecheck`
  - `pnpm -C apps/frontend test:ci`

### 12.3 Backend
- Unit tests (Docker, marker unit):
  - `pnpm test:backend:unit`
- Suite completa en repo (si corresponde a tu entorno):
  - `cd apps/backend && pytest`

### 12.4 Contratos
- Export OpenAPI desde backend hacia `shared/contracts/openapi.json`:
  - `pnpm contracts:export`
- Generar cliente TS desde OpenAPI:
  - `pnpm contracts:gen`

### 12.5 Local stack (smoke)
- Levantar core (db+migrate+api):
  - `pnpm stack:core`
  - `pnpm db:migrate`
- Stack completo (incluye worker/minio/redis):
  - `pnpm stack:full`

### 12.6 Secret scan
- Script local:
  - `./scripts/security/verify_no_secrets.sh`

### 12.7 E2E
- Instalación y ejecución:
  - `pnpm e2e`

---

## 13) Apéndice — Entregables para auditoría empresarial

1) **Este documento** (guía de producción).
2) **Guía Definitiva de READMEs** (raíz/padres/hojas).
3) `docs/project/informe_de_sistemas_rag_corp.md` (informe técnico consolidado).
4) `docs/reference/*` (contratos, config, errores, access control, limits).
5) Evidencia CI: pipeline verde + artefactos (imágenes, SBOM si aplica).
