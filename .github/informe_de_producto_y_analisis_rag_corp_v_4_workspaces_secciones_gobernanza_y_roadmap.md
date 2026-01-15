# Informe de Producto y Análisis — RAG Corp v4

**Fecha:** 2026-01-14 (America/Argentina/Cordoba)  
**Proyecto:** `rag-corp`  
**Propósito del documento:** dejar constancia **completa, específica y sin ambigüedades** sobre:
- el **estado actual** del repositorio (AS-IS),
- el **propósito de producto** redefinido,
- el **modelo funcional** objetivo (TO-BE) con **Workspaces/Secciones**, visibilidad y permisos,
- el **roadmap** para completar el producto según la visión acordada,
- y las **decisiones técnicas** que deberán guiar a Copilot/Codex para implementar sin drift.

> Este documento está pensado para **subirse al repo** (recomendado: `doc/product/PRODUCT_SPEC_WORKSPACES_v4.md`) y ser tomado como **fuente de verdad**. Si existe un PDF previo, este documento es el “complemento v4” enfocado en la nueva visión de producto.

---

## 1) Resumen ejecutivo (1 página)

### 1.1 Qué es el producto (visión)
RAG Corp v4 evoluciona hacia un sistema interno tipo **NotebookLM empresarial**, orientado a **gestionar fuentes** (PDF/DOCX) por **Workspaces/Secciones** con reglas claras de **gobernanza**:

- Cada **Workspace/Sección** es un “espacio de conocimiento” asociado a un **tema/periodo/área** (ej.: *“Contaduría — Enero”*, *“Ventas — Diario”*, *“RRHH — Legajos”*).
- Los documentos se cargan dentro de una sección y se procesan con un pipeline asíncrono (extract → chunk → embed → pgvector).
- Los usuarios consultan (ask/chat) **siempre en el contexto de una sección**, para evitar mezclar información.
- La seguridad y control de cambios se resuelve con:
  - **Roles globales** (admin/employee),
  - y **permisos por sección** (owner/lectores/compartidos),
  - más auditoría.

### 1.2 Problema que resuelve
En una empresa hay muchos documentos (PDF/DOCX) generados por distintos empleados/áreas. Hoy el problema típico es:
- información fragmentada,
- duplicación y desorden,
- falta de trazabilidad,
- accesos incorrectos,
- y dificultad para **responder preguntas** con fuentes confiables.

RAG Corp v4 busca:
- convertir documentos en “fuentes consultables”,
- con límites y permisos claros,
- permitiendo que otros empleados **consulten** información publicada sin poder modificarla.

### 1.3 Estado actual (AS-IS)
El repo ya implementa gran parte de la base técnica:
- UI Next.js con experiencia “Sources” estilo NotebookLM.
- Backend FastAPI + arquitectura limpia (Domain/Application/Infrastructure).
- DB Postgres + pgvector.
- Upload PDF/DOCX + storage S3/MinIO opcional.
- Pipeline asíncrono con Redis + RQ + worker.
- Auth dual: JWT (users admin/employee) + X-API-Key (RBAC) coexistiendo.
- Observabilidad (métricas/logging/healthchecks) y CI con e2e-full.

**Pero** el repositorio aún no modela formalmente “Secciones/Workspaces” como concepto de producto central. El TO-BE define esa capa.

### 1.4 Decisiones clave (TO-BE)
- El producto se organiza por **Workspaces/Secciones** (con owner) y no por “documentos sueltos” globales.
- Visibilidad profesional (decisión):
  - `PRIVATE` (default)
  - `ORG_READ` (pública interna, lectura + chat)
  - `SHARED` (compartida a usuarios específicos)
- Escritura/borrado:
  - **Solo owner o admin** puede subir/borrar/reprocess.
  - Otros empleados con acceso pueden **ver y chatear** pero **no modificar**.
- Almacenamiento “pro”: S3 compatible (MinIO on-prem o AWS S3 en cloud).

---

## 2) Alcance, objetivos y no-objetivos

### 2.1 Objetivos del producto
1. **Gestión de conocimiento por secciones**: organizar fuentes por tema/periodo/área.
2. **Consulta confiable**: ask/chat con fuentes restringidas a una sección (evita mezclar datos sensibles).
3. **Gobernanza simple y robusta**: owner controla sus secciones; admin puede todo.
4. **Procesamiento asíncrono**: uploads grandes y extracción/embeddings fuera del request.
5. **Trazabilidad**: auditoría de acciones críticas.
6. **Operabilidad real**: health/ready/metrics para API y worker + CI con pipeline completo.

### 2.2 No-objetivos (por ahora)
- Escaneo automático del disco del empleado desde el navegador (no posible por seguridad).
- Agente de escritorio (desktop) para sincronizar carpetas locales.
- OCR avanzado para PDFs escaneados (puede planearse en fase futura).
- Multi-tenant por empresa (este v4 asume una organización).

### 2.3 Principios de diseño
- **Seguridad por defecto** (fail-fast en prod).
- **Contexto explícito** (toda consulta pertenece a una sección).
- **Separación de capas** (Clean Architecture).
- **Ports/adapters** para reemplazar infra (S3/MinIO, LLM, embeddings, queue, repos).
- **Observabilidad** de punta a punta.

---

## 3) Stakeholders y actores

### 3.1 Actores
- **Admin**: administra usuarios, secciones, documentos. Puede ver/modificar todo.
- **Employee (Owner)**: empleado que crea una sección. Puede subir/borrar/reprocess dentro de su sección.
- **Employee (Viewer)**: empleado con acceso a una sección (ORG_READ o SHARED). Puede ver y chatear, no modificar.
- **Service** (API key): integraciones/CI/E2E con RBAC (permiso por scopes/roles en config).

### 3.2 Ejemplos reales (casos de negocio)
- Contador crea **Sección “Enero”**, sube PDFs contables. RRHH consulta esos datos para reportes internos sin modificar fuentes.
- Ventas crea **Sección “Ventas Diario”**, sube planillas/PDFs. Contaduría consume para consolidar. Contaduría no puede editar lo subido por Ventas.

---

## 4) Terminología (glosario mínimo)

- **Workspace/Sección**: contenedor lógico de documentos y chats. Tiene owner, visibilidad, ACL.
- **Fuente / Source**: documento cargado (PDF/DOCX) y su metadata + estado de procesamiento.
- **Chunk**: fragmento de texto del documento con embedding vectorial en pgvector.
- **RAG**: Retrieval-Augmented Generation, búsqueda de chunks + LLM para respuesta.
- **ACL**: Access Control List (control por owner/roles/usuarios).
- **RBAC**: Role-Based Access Control para API keys (permisos/roles).
- **RFC7807**: estándar de error `application/problem+json`.
- **Status documento**: `PENDING | PROCESSING | READY | FAILED`.

---

## 5) Estado actual del repositorio (AS-IS) — descripción técnica verificable

> Esta sección resume el estado actual reportado por auditoría interna de Copilot + evidencia de archivos/endpoints citados.

### 5.1 Stack tecnológico
**Frontend (FE)**
- Next.js + React + TypeScript (en `frontend/`).
- UI “Sources” en ruta `/documents`.
- Cliente FE con contratos OpenAPI (Orval) en `shared/contracts/`.

**Backend (BE)**
- FastAPI + Uvicorn + Pydantic.
- Arquitectura limpia: `backend/app/domain`, `backend/app/application`, `backend/app/infrastructure`.

**Base de datos y vector store**
- Postgres + pgvector.
- Tablas base: `documents`, `chunks`.

**IA**
- SDK `google-genai` (migrado desde paquete deprecated).
- Adapters en `google_embedding_service.py`, `google_llm_service.py`.

**Queue/Cache**
- Redis + RQ.
- Worker (RQ worker) para procesamiento asíncrono.

**Storage**
- S3/MinIO via `boto3`.
- Metadata en Postgres; binarios en object storage.

**Observabilidad**
- Prometheus / Grafana (compose de observability).
- Métricas en `metrics.py`, logging JSON.

**CI/CD**
- Workflows en `.github/workflows/ci.yml` y `deploy.yml`.
- Jobs: backend test/lint, frontend test/lint, contracts, e2e, e2e-full, load-test.

### 5.2 Endpoints principales actuales
- `GET /healthz` público.
- `GET /metrics` condicionado por `METRICS_REQUIRE_AUTH`.

**Auth (JWT)**
- `POST /auth/login`
- `GET /auth/me`
- `POST /auth/logout`
- Administración de usuarios (admin-only):
  - `GET /auth/users`
  - `POST /auth/users`
  - `POST /auth/users/{user_id}/disable`
  - `POST /auth/users/{user_id}/reset-password`

**API v1 (documentos/ingesta/consulta)**
- `GET /v1/documents` (list con filtros/paginación)
- `GET /v1/documents/{id}`
- `DELETE /v1/documents/{id}`
- `POST /v1/documents/upload` (PDF/DOCX, admin-only o permiso)
- `POST /v1/documents/{id}/reprocess` (admin-only o permiso)

**RAG**
- `POST /v1/ask`
- `POST /v1/ask/stream` (SSE)
- `POST /v1/query`
- `POST /v1/ingest/text`
- `POST /v1/ingest/batch`

### 5.3 Auth actual (dual)
- JWT para usuarios humanos con roles `admin|employee`.
- X-API-Key para integraciones/servicios, con permisos RBAC.
- Flujo unificado en un “principal” (dual auth) sin romper compatibilidad.

### 5.4 Pipeline asíncrono actual (uploads)
1. Upload crea documento con status `PENDING` + metadata (incluye `file_name`, `mime_type`, `storage_key`, etc.).
2. Se encola job en Redis (RQ) para procesar.
3. Worker toma job:
   - descarga binario desde storage,
   - extrae texto (PDF/DOCX),
   - chunk + embed,
   - escribe chunks en pgvector,
   - transiciona status a `READY` o `FAILED`.
4. Idempotencia:
   - si `READY`/`PROCESSING` se evita doble procesamiento,
   - retries configurados,
   - errores truncados y persistidos en `error_message`.

### 5.5 UI “Sources” actual
- `/documents` muestra listado de documentos con status chips.
- Acciones admin: upload, reprocess.
- Detalle: muestra error cuando `FAILED`.
- FE incluye soporte a cookies JWT y fallback a API key para CI/E2E.

---

## 6) Problemas identificados (AS-IS) y motivación del rediseño

### 6.1 Dolor funcional
- Falta el concepto central **Workspace/Sección**.
- Sin secciones, “fuentes” quedan globales, lo que complica:
  - permisos por área,
  - responsabilidad de ownership,
  - “no tocar lo de otro”,
  - y consultas acotadas.

### 6.2 Dolor de adopción (UX)
- Para un negocio real, la gente piensa en:
  - “mi carpeta/mi sección de trabajo”,
  - no en “documentos globales sueltos”.

### 6.3 Dolor de seguridad (hardening)
- En producción no puede existir:
  - secrets por defecto,
  - auth accidentalmente deshabilitada,
  - API keys “humanas” en localStorage,
  - métricas abiertas.

---

## 7) Modelo de producto objetivo (TO-BE) — Workspaces/Secciones

### 7.1 Decisión de naming
- En código: **Workspace** (estándar SaaS)
- En UI: puede mostrarse como **Sección** para ser natural en español.

> En este documento se usan como sinónimos. La fuente de verdad técnica es “Workspace”.

### 7.2 Entidad Workspace (definición)
Un Workspace representa un contexto de conocimiento y permisos:

**Atributos mínimos**
- `id` (UUID)
- `name` (string, único por owner o global según decisión)
- `description` (string opcional)
- `visibility` (enum: `PRIVATE | ORG_READ | SHARED`)
- `owner_user_id` (FK users)
- `created_at`
- `updated_at`

**Atributos recomendados (pro)**
- `slug` (para URLs limpias)
- `archived_at` (soft archive)
- `default_tags` (opcional)

### 7.3 Visibilidad (decisión final)
- `PRIVATE` (**default**): solo owner + admin.
- `ORG_READ` (“pública interna”): todos los employees pueden **ver + chatear**, no modificar.
- `SHARED`: lista explícita de usuarios con acceso (ver + chatear), no modificar.

**Regla global:** Admin siempre tiene acceso total.

### 7.4 ACL por Workspace
Se define el acceso de employees no-owner:
- En `ORG_READ`: todos los employees tienen acceso de lectura + chat.
- En `SHARED`: solo los users listados.

**Escritura/borrado/reprocess**:
- Solo `owner` o `admin`.

> Extensión futura: “contributors” por workspace.

---

## 8) Reglas de negocio (TO-BE) — sin ambigüedad

### 8.1 Reglas para documentos
1. Todo documento pertenece a **exactamente 1 workspace**.
2. Un documento tiene un `uploader_user_id` (quién lo subió), pero la autoridad principal es el **workspace owner**.
3. Solo `owner/admin` puede:
   - subir docs,
   - borrar docs,
   - reprocess.
4. Un employee con acceso (viewer) puede:
   - ver listado,
   - ver detalle,
   - chatear/consultar,
   - **no** modificar.

### 8.2 Reglas para consultas (ask/chat/query)
1. Toda consulta debe incluir un `workspace_id`.
2. El retrieval filtra chunks/documentos por `workspace_id`.
3. Si el usuario no tiene acceso al workspace → 403 RFC7807.

### 8.3 Reglas de “publicación”
1. Crear workspace: `PRIVATE` por defecto.
2. Owner/admin puede cambiar a `ORG_READ` o `SHARED`.
3. Cambiar visibilidad genera evento de auditoría.

---

## 9) Casos de uso (TO-BE) — especificación detallada

> Se definen con: Actor, Precondiciones, Flujo principal, Alternativas/errores, Postcondiciones.

### UC-01 — Login
- **Actor:** Employee/Admin
- **Precondiciones:** usuario activo existe
- **Flujo:**
  1) Usuario envía credenciales a `/auth/login`
  2) Sistema valida password (Argon2)
  3) Emite JWT (cookie httpOnly) y/o access token
  4) Usuario queda autenticado
- **Errores:** credenciales inválidas → 401 RFC7807
- **Post:** sesión activa

### UC-02 — Crear Workspace
- **Actor:** Employee/Admin
- **Precondiciones:** autenticado
- **Flujo:**
  1) Usuario solicita crear workspace con `name`, `description`
  2) Sistema crea workspace con `visibility=PRIVATE` y `owner_user_id=user.id`
  3) Devuelve workspace creado
- **Errores:**
  - nombre inválido/duplicado → 400 RFC7807
- **Post:** workspace existe y es visible solo para owner/admin

### UC-03 — Cambiar visibilidad a ORG_READ
- **Actor:** Owner/Admin
- **Precondiciones:** workspace existe
- **Flujo:**
  1) Owner solicita cambiar visibility a ORG_READ
  2) Sistema actualiza workspace
  3) Sistema registra auditoría `workspace.publish`
- **Errores:** no owner y no admin → 403
- **Post:** todos los employees pueden ver y chatear

### UC-04 — Compartir workspace (SHARED)
- **Actor:** Owner/Admin
- **Precondiciones:** workspace existe
- **Flujo:**
  1) Owner elige usuarios con acceso
  2) Sistema guarda ACL
  3) Auditoría `workspace.share`
- **Errores:** usuarios inválidos → 400
- **Post:** solo los seleccionados pueden ver/chatear

### UC-05 — Subir documento (PDF/DOCX) al workspace
- **Actor:** Owner/Admin
- **Precondiciones:** workspace existe y actor tiene permiso de escritura
- **Flujo:**
  1) Usuario sube archivo + metadata (title, tags opcionales)
  2) API valida mime allowlist y MAX_UPLOAD_BYTES
  3) API sube binario a storage (S3/MinIO)
  4) API crea fila document con status `PENDING` y `workspace_id`
  5) API encola job en Redis
  6) Responde 202 con document_id y status
- **Errores:**
  - mime no soportado → 415
  - demasiado grande → 413
  - sin permisos → 403
- **Post:** doc PENDING, en cola

### UC-06 — Procesar documento (worker)
- **Actor:** Sistema
- **Precondiciones:** doc PENDING, storage accesible
- **Flujo:**
  1) Worker toma job
  2) Transiciona doc a PROCESSING
  3) Descarga binario y extrae texto
  4) Chunk + embed
  5) Persist chunks filtrados por workspace
  6) Transiciona a READY
- **Errores:**
  - excepción al extraer/embed/db → FAILED con error_message
  - idempotencia: si READY/PROCESSING se ignora
- **Post:** READY o FAILED

### UC-07 — Consultar/Chatear dentro del workspace
- **Actor:** Employee/Admin
- **Precondiciones:** actor tiene acceso al workspace
- **Flujo:**
  1) Usuario selecciona workspace
  2) UI envía ask/chat incluyendo `workspace_id`
  3) API filtra retrieval por `workspace_id`
  4) Responde con answer + sources
- **Errores:** sin acceso → 403
- **Post:** respuesta generada con fuentes del workspace

### UC-08 — Reprocess documento
- **Actor:** Owner/Admin
- **Precondiciones:** doc existe y pertenece a workspace donde actor puede escribir
- **Flujo:**
  1) Actor pide reprocess
  2) Si doc PROCESSING → 409
  3) Si no: resetea a PENDING + encola job
- **Post:** vuelve a pipeline

### UC-09 — Administración de usuarios
- **Actor:** Admin
- **Acciones:** listar, crear, desactivar, reset-password
- **Post:** auditoría `admin.user.*`

---

## 10) Requisitos funcionales (RF) — lista completa

### RF-A Auth
- RF-A1: login/logout/me con JWT.
- RF-A2: cookies httpOnly para UI.
- RF-A3: API key + RBAC para servicios/CI.

### RF-B Workspaces (nuevo)
- RF-B1: CRUD mínimo (create/list/get/update visibility/archive).
- RF-B2: ACL por workspace (ORG_READ/SHARED).
- RF-B3: owner/admin write; viewers read+chat.

### RF-C Documentos dentro de workspace (extensión)
- RF-C1: upload PDF/DOCX asociado a workspace.
- RF-C2: status PENDING/PROCESSING/READY/FAILED.
- RF-C3: list/get/delete/reprocess filtrado por workspace.
- RF-C4: tags + filtros + paginación.

### RF-D RAG acotado
- RF-D1: ask/query/stream reciben workspace_id.
- RF-D2: retrieval solo de documentos del workspace.

### RF-E Auditoría
- RF-E1: registrar eventos críticos: login, workspace create/publish/share, upload, delete, reprocess.
- RF-E2: consultas de auditoría (admin).

### RF-F UX
- RF-F1: UI tipo “Sources” por workspace.
- RF-F2: selector de workspace + filtros.
- RF-F3: acciones admin/owner visibles solo cuando corresponde.

---

## 11) Requisitos no funcionales (RNF) — lista completa

### RNF-SEC Seguridad
- RNF-SEC1: `JWT_SECRET` **obligatorio** en prod (no aceptar default).
- RNF-SEC2: si auth quedara deshabilitada por config vacía en prod → fail-fast.
- RNF-SEC3: cookies `secure=true` en prod.
- RNF-SEC4: CSP sin `unsafe-inline` (o con nonces/hashes).
- RNF-SEC5: API key no usada como mecanismo “humano” en producción (solo integraciones).
- RNF-SEC6: /metrics protegido en prod.

### RNF-PERF Rendimiento
- RNF-PERF1: pipeline de extracción/embeddings asíncrono.
- RNF-PERF2: límites de tamaño de upload.
- RNF-PERF3 (futuro): streaming upload.

### RNF-OPS Operación
- RNF-OPS1: /healthz y /readyz (API y worker).
- RNF-OPS2: métricas Prometheus API + worker.
- RNF-OPS3: runbook de troubleshooting.

### RNF-MAINT Mantenibilidad
- RNF-MAINT1: respetar Domain/Application/Infrastructure.
- RNF-MAINT2: ports/adapters para storage/queue/LLM.
- RNF-MAINT3: tests unitarios y e2e-full.

---

## 12) Diseño de datos (TO-BE) — cambios requeridos

### 12.1 Tablas existentes relevantes (AS-IS)
- `users` (con roles admin/employee)
- `documents` (con metadata, status, file info, ACL parcial, audit hooks)
- `chunks`
- `audit_events`

### 12.2 Tablas nuevas (TO-BE)
#### `workspaces`
Campos mínimos:
- `id uuid pk`
- `name text not null`
- `description text null`
- `visibility text not null` (PRIVATE/ORG_READ/SHARED)
- `owner_user_id uuid not null fk users(id)`
- `created_at timestamptz not null`
- `updated_at timestamptz not null`
- (opcional) `slug text unique`
- (opcional) `archived_at timestamptz null`

#### `workspace_acl`
Solo necesaria si usamos SHARED o, en el futuro, contributors.
- `workspace_id uuid fk`
- `user_id uuid fk`
- `access text` (READ)
- unique(workspace_id, user_id)

### 12.3 Modificaciones a `documents`
- Agregar `workspace_id uuid not null fk workspaces(id)`
- Índices:
  - (workspace_id, created_at)
  - (workspace_id, status)
  - (workspace_id, tags)

### 12.4 Auditoría por workspace
- En `audit_events`, guardar `workspace_id` cuando aplique.

---

## 13) Diseño de API (TO-BE) — especificación sin drift

### 13.1 Principios
- Canonical API: `/v1/*`.
- FE usa `/api/*` como facade con rewrites.
- Errores: RFC7807.

### 13.2 Endpoints propuestos
#### Workspaces
- `POST /v1/workspaces` — crear (employee/admin)
- `GET /v1/workspaces` — listar visibles
- `GET /v1/workspaces/{id}` — detalle
- `PATCH /v1/workspaces/{id}` — actualizar (owner/admin)
- `POST /v1/workspaces/{id}/publish` — set ORG_READ (owner/admin)
- `POST /v1/workspaces/{id}/share` — set SHARED + ACL (owner/admin)
- `POST /v1/workspaces/{id}/archive` — archivar (owner/admin)

#### Documents (scoped)
- `GET /v1/workspaces/{id}/documents` (o mantener /v1/documents con query workspace_id obligatorio)
- `POST /v1/workspaces/{id}/documents/upload`
- `POST /v1/workspaces/{id}/documents/{doc_id}/reprocess`
- `DELETE /v1/workspaces/{id}/documents/{doc_id}`

#### Ask/Chat (scoped)
- `POST /v1/workspaces/{id}/ask`
- `POST /v1/workspaces/{id}/ask/stream`
- `POST /v1/workspaces/{id}/query`

> Decisión recomendada: **rutas anidadas por workspace** para que sea imposible olvidar el scope.

### 13.3 Modelos de respuesta (mínimos)
- WorkspaceSummary: id, name, visibility, owner, created_at
- DocumentSummary: id, title, status, tags, file_name, mime_type, created_at, error_message?
- RFC7807: type/title/status/detail/instance

---

## 14) UI/UX (TO-BE) — especificación

### 14.1 Navegación
- Sidebar: “Workspaces/Secciones”, “Sources”, “Chat”, “Admin (solo admin)”.
- Selector de workspace en la parte superior de Sources/Chat.

### 14.2 Pantalla Workspaces
- Listado de workspaces visibles.
- Crear workspace.
- Entrar a workspace.
- Owner/admin: cambiar visibilidad, compartir, archivar.

### 14.3 Pantalla Sources (por workspace)
- Lista de documentos del workspace.
- Filtros: q/status/tag/sort.
- Upload (solo owner/admin).
- Reprocess (solo owner/admin).
- Detalle con error cuando FAILED.

### 14.4 Pantalla Chat (por workspace)
- Chat SSE.
- Conversación asociada al workspace.
- Fuentes/sources mostradas como evidencia.

### 14.5 Admin Users
- Gestión de usuarios (ya existe, se mantiene).

---

## 15) Consideraciones técnicas críticas

### 15.1 “Buscar archivos en mi PC” (realidad)
Una web no puede escanear el disco. Alternativas pro:
- Upload manual (file picker/drag drop) — **incluido**.
- Watch folder server/NAS (servicio interno) — **fase futura**.
- Agente desktop — **fase futura**.

### 15.2 Versionado /v1
- Mantener `/v1` como canonical en backend.
- FE usa `/api` como facade.
- Evitar duplicar rutas reales para prevenir drift.

---

## 16) Roadmap recomendado (orden de implementación)

### Fase 0 — Documentación y alineación
- Este documento en repo.
- Diagrama high-level actualizado.

### Fase 1 — Workspaces (núcleo de producto)
1) Modelo y migración `workspaces`.
2) Endpoints CRUD + visibilidad.
3) UI Workspaces + selector.

### Fase 2 — Scope por workspace
1) Documents con `workspace_id`.
2) Listado/upload/reprocess/delete scoped.
3) Ask/chat/query scoped.

### Fase 3 — Auditoría y seguridad final
1) Auditoría por workspace.
2) Fail-fast prod (secrets/config).
3) Remover uso “humano” de API key.

### Fase 4 — Escala real (opcional)
1) Conversaciones persistentes (Redis/Postgres).
2) Rate limiting distribuido.
3) Upload streaming.

---

## 17) Riesgos y mitigaciones

- **Riesgo:** implementación parcial de workspace y consultas sin scope → fuga de contexto.
  - **Mitigación:** rutas anidadas por workspace + validación server-side obligatoria.

- **Riesgo:** defaults inseguros en prod.
  - **Mitigación:** fail-fast en startup si ENV=prod y defaults activos.

- **Riesgo:** storage/queue opcional rompe flujos.
  - **Mitigación:** profiles claros + runbook + healthchecks.

---

## 18) Criterios de “producto completo (100%)”

El proyecto se considera **“100% según visión v4”** cuando:
1) Workspaces completos (CRUD + visibilidad + share).
2) Documentos y consultas 100% scoping por workspace.
3) Permisos: owner/admin write; viewers read+chat.
4) UI: Workspaces + Sources/Chat por workspace.
5) Auditoría por workspace.
6) Hardening prod: secrets/config, métricas protegidas.
7) CI e2e-full cubre flujo: login → crear workspace → upload → READY → chat.

---

## 19) Apéndice — decisiones finales (fuente de verdad)

### Decisión D-01: Workspaces como concepto central
- Aprobado.

### Decisión D-02: Visibilidad
- `PRIVATE` default
- `ORG_READ` lectura + chat para toda la org
- `SHARED` lectura + chat para lista explícita

### Decisión D-03: Escritura
- Solo owner/admin puede subir/borrar/reprocess.

### Decisión D-04: Almacenamiento
- S3 compatible (MinIO on-prem / S3 cloud).

### Decisión D-05: Pipeline
- Asíncrono (cola + worker) como estándar.

---

## 20) Qué se espera de Copilot/Codex al leer este documento

- Entender que el repo ya tiene la base técnica (upload, worker, dual auth, sources UI), pero que el **objetivo de producto** ahora es Workspaces/Secciones.
- Implementar de forma consistente:
  - modelos,
  - endpoints,
  - permisos,
  - y UI,
  sin introducir drift entre `/v1` y `/api`.
- Respetar Clean Architecture, ports/adapters y RFC7807.

---

**Fin del documento.**

