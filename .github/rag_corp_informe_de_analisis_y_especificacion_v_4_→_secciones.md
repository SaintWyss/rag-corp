# RAG Corp — Informe de Análisis y Especificación (v4 → “Secciones”)

**Autor:** Santiago Scacciaferro  
**Fecha:** 2026-01-14  
**Versión del documento:** 1.0  

---

## 1. Propósito del documento
Dejar constancia formal (análisis de sistemas) de:
- **Qué está construido hoy** en el proyecto (baseline v4).
- **Qué problema de negocio** queremos resolver con la evolución propuesta.
- **Qué vamos a construir** a continuación: “Secciones” (collections/áreas) + permisos por rol/propietario.
- **Requisitos funcionales y no funcionales**, casos de uso, reglas de negocio, criterios de aceptación y plan.

---

## 2. Contexto y estado actual (baseline)
### 2.1 Stack y componentes (actual)
- **Frontend:** Next.js + React + TypeScript.
- **Backend:** FastAPI + Uvicorn + Pydantic.
- **DB/Vector:** PostgreSQL + pgvector.
- **Autenticación/Autorización:**
  - JWT para usuarios (**admin/employee**).
  - API keys con RBAC (permisos) para “service auth” (sin romper compatibilidad).
  - Flujo unificado de principal (JWT o API key).
- **Carga y procesamiento:**
  - Upload admin-only de PDF/DOCX.
  - Pipeline asíncrono: Redis + RQ + Worker.
  - Estados de documento: PENDING / PROCESSING / READY / FAILED.
- **Storage:** S3/MinIO opcional (binaries fuera; metadata en Postgres).
- **Observabilidad:** métricas Prometheus, logs estructurados, health/ready endpoints.
- **CI/CD:** pipelines unit/fe/e2e/e2e-full, deploy placeholders.

### 2.2 Capacidad actual del producto
- UI tipo “Sources”: listar documentos, ver detalle, upload/reprocess (admin), status chips.
- RAG: ingesta → chunking/embeddings → retrieval → respuesta (incluye streaming SSE).
- Auditoría (eventos) y ACL a nivel documento (incipiente) + roles.

### 2.3 Dolor actual / motivación
Para una empresa, falta el modelo de trabajo real:
- **No existe una “Sección/Área”** (Enero, Ventas, RRHH) como unidad de organización.
- Los permisos requeridos son **por sección** y por owner, no solo “admin vs employee”.
- Se necesita que el chat/retrieval sea **contextual a una sección** (evitar mezclar todo el conocimiento).

---

## 3. Problema de negocio (visión)
### 3.1 Escenario
Una empresa gestiona información en PDFs/DOCX por áreas y periodos.
- Cada empleado puede crear una **sección** (ej. “Enero”, “Ventas Q1”, “RRHH – Altas”).
- La sección tiene un **owner** (el creador) y una visibilidad.
- Cuando es **pública interna**, otros empleados pueden **consultar/chatear** con esos documentos, pero **no modificar**.
- Solo el **owner** (y **admin**) puede **subir** y **borrar** contenido de su sección.
- Admin puede ver/gestionar todo.

### 3.2 Objetivo
Convertir el RAG en una **Knowledge Base empresarial** organizada por secciones con permisos y trazabilidad.

---

## 4. Alcance
### 4.1 En alcance (próxima evolución)
- Secciones (Collections): CRUD mínimo.
- Permisos por rol y owner a nivel sección.
- Documentos asociados a sección.
- Chat/Ask filtrado por sección.
- UI: navegación por secciones + sources por sección.
- Auditoría de acciones clave (ya existe base, se amplía).

### 4.2 Fuera de alcance (por ahora)
- Multi-tenant (múltiples empresas).
- SSO/LDAP.
- Workflows complejos (aprobaciones, firma digital).
- DLP/Clasificación avanzada.
- OCR avanzado (scans) como requisito obligatorio.

---

## 5. Stakeholders y actores
### 5.1 Stakeholders
- **Admin**: dueño del sistema, gestiona usuarios y secciones.
- **Empleado (Employee)**: crea secciones propias, consulta secciones públicas internas.
- **Sistema (Worker/Servicios)**: procesa documentos, genera chunks y embeddings.

### 5.2 Actores (UML informal)
- **A1 Admin**
- **A2 Empleado**
- **A3 Servicio/API Key** (integraciones/CI)
- **A4 Worker**

---

## 6. Reglas de negocio (RB)
**RB-01 Ownership:** cada Sección tiene un `owner_user_id`.

**RB-02 Visibilidad:**
- `PRIVATE`: solo owner y admin.
- `INTERNAL_PUBLIC_READ`: cualquier empleado autenticado puede **ver + chatear**; no puede subir/borrar.

**RB-03 Permisos por acción:**
- Crear sección: employee/admin.
- Editar sección (nombre/visibilidad): owner/admin.
- Eliminar sección: owner/admin (y define comportamiento sobre documentos; ver RB-06).
- Subir documento a sección: owner/admin (y API key con permiso equivalente si se habilita).
- Borrar documento: owner/admin.
- Reprocesar: owner/admin.
- Consultar documentos/chatear: según visibilidad + rol.

**RB-04 Inmutabilidad relativa:** un empleado **no puede** modificar/borrar contenido de secciones que no le pertenecen, incluso si son públicas internas.

**RB-05 Chat por contexto:** toda consulta que use documentos debe recibir `section_id` y filtrar retrieval a esa sección.

**RB-06 Borrado de sección:** política propuesta:
- Opción A (simple): no permitir borrar sección si tiene documentos (requiere vaciar primero).
- Opción B: “soft delete” de sección y documentos asociados.

---

## 7. Casos de uso (UC)
> Formato: **UC-ID — Nombre** (Actor principal)

### 7.1 Gestión de usuarios
- **UC-01 — Iniciar sesión** (Empleado/Admin)
- **UC-02 — Ver perfil /auth/me** (Empleado/Admin)
- **UC-03 — Cerrar sesión** (Empleado/Admin)
- **UC-04 — Administrar usuarios** (Admin)
  - Crear usuario
  - Deshabilitar usuario
  - Resetear contraseña

### 7.2 Secciones
- **UC-10 — Crear sección** (Empleado/Admin)
- **UC-11 — Listar secciones visibles** (Empleado/Admin)
- **UC-12 — Ver detalle de sección** (Empleado/Admin)
- **UC-13 — Editar sección** (Owner/Admin)
- **UC-14 — Eliminar sección** (Owner/Admin)

### 7.3 Documentos (por sección)
- **UC-20 — Subir documento a sección** (Owner/Admin)
- **UC-21 — Ver documentos de sección** (Empleado/Admin según RB)
- **UC-22 — Ver detalle de documento** (Empleado/Admin según RB)
- **UC-23 — Reprocesar documento** (Owner/Admin)
- **UC-24 — Eliminar documento** (Owner/Admin)

### 7.4 Consulta (RAG)
- **UC-30 — Consultar sección (Ask)** (Empleado/Admin según RB)
- **UC-31 — Chat streaming por sección** (Empleado/Admin según RB)

### 7.5 Operación
- **UC-40 — Procesar documento (worker)** (Worker)
- **UC-41 — Monitoreo/health/metrics** (Admin/Ops)

---

## 8. Especificación de casos de uso (detalle)

### UC-10 — Crear sección
**Actor:** Empleado/Admin  
**Precondiciones:** usuario autenticado (JWT).  
**Postcondiciones:** sección creada con `owner_user_id = actor`, visibilidad inicial.  
**Flujo principal:**
1) Actor abre UI de secciones.
2) Ingresa nombre y visibilidad.
3) Sistema valida.
4) Sistema crea sección.
5) Sistema retorna sección creada.

**Reglas:** RB-01, RB-02.

**Excepciones:**
- Nombre vacío → 400 (RFC7807)
- Duplicado (si se decide unique por owner) → 409

**Criterios de aceptación:**
- La sección aparece en la lista del owner.
- El `owner_user_id` coincide con el actor.

---

### UC-20 — Subir documento a sección
**Actor:** Owner/Admin  
**Precondiciones:**
- Sección existe.
- Actor autorizado (RB-03).
- Archivo permitido (PDF/DOCX) y tamaño <= MAX_UPLOAD_BYTES.

**Flujo principal:**
1) Actor selecciona sección y archivo.
2) Sistema valida tipo/tamaño.
3) Sistema guarda binario (S3/MinIO opcional) + metadata en Postgres con estado PENDING.
4) Sistema encola job en Redis.
5) Retorna 202 con document_id.

**Postcondiciones:** documento creado con status PENDING.

**Excepciones:**
- Actor no autorizado → 403.
- Archivo no permitido → 415.
- Tamaño excedido → 413.
- Storage no disponible (si requerido) → 503/500.

**Criterios de aceptación:**
- Documento aparece en UI con status PENDING.
- Worker lo procesa y pasa a READY o FAILED.

---

### UC-30 — Consultar sección (Ask)
**Actor:** Empleado/Admin  
**Precondiciones:**
- Actor tiene acceso de lectura a la sección.
- La sección tiene docs READY (o el sistema responde con “sin fuentes”).

**Flujo principal:**
1) Actor elige sección.
2) Ingresa consulta.
3) Sistema recupera chunks **solo de esa sección**.
4) LLM responde.
5) UI muestra respuesta + fuentes.

**Excepciones:**
- Sin permisos → 403.
- Sección sin docs → respuesta válida con fuentes vacías.

**Criterios de aceptación:**
- Nunca aparecen fuentes de otra sección.

---

## 9. Requisitos funcionales (RF)
### 9.1 Autenticación / autorización
- **RF-01:** Login JWT (admin/employee).
- **RF-02:** /auth/me para sesión.
- **RF-03:** Admin gestiona usuarios.
- **RF-04:** Dual-auth: JWT o API key (sin romper).

### 9.2 Secciones
- **RF-10:** Crear sección con owner y visibilidad.
- **RF-11:** Listar secciones visibles para el usuario.
- **RF-12:** Editar sección (solo owner/admin).
- **RF-13:** Eliminar sección según política RB-06.

### 9.3 Documentos
- **RF-20:** Subir PDF/DOCX a una sección (solo owner/admin).
- **RF-21:** Ver/listar docs de una sección según visibilidad.
- **RF-22:** Reprocesar docs (owner/admin).
- **RF-23:** Borrar docs (owner/admin).
- **RF-24:** Estados PENDING/PROCESSING/READY/FAILED visibles.

### 9.4 RAG por sección
- **RF-30:** Ask filtra retrieval por section_id.
- **RF-31:** Chat streaming filtra por section_id.
- **RF-32:** UI permite seleccionar sección y operar dentro.

### 9.5 Auditoría
- **RF-40:** Registrar eventos: section.create/update/delete, doc.upload/reprocess/delete, auth.login.

---

## 10. Requisitos no funcionales (RNF)
### 10.1 Seguridad
- **RNF-SEC-01:** En producción, **no** permitir JWT secret por defecto; fail-fast.
- **RNF-SEC-02:** Cookies JWT seguras en prod (secure, sameSite adecuado).
- **RNF-SEC-03:** Endurecer CSP (eliminar unsafe-inline si es posible).
- **RNF-SEC-04:** Evitar API key en localStorage para uso real (solo CI/E2E o alternativa cookie).
- **RNF-SEC-05:** /metrics protegido en prod.

### 10.2 Performance y escalabilidad
- **RNF-PERF-01:** Procesamiento asíncrono para uploads.
- **RNF-PERF-02:** No cargar archivos grandes completos en RAM (streaming).
- **RNF-PERF-03:** Rate limit escalable (Redis o gateway) cuando haya múltiples instancias.

### 10.3 Confiabilidad
- **RNF-REL-01:** Worker idempotente (evitar doble procesamiento).
- **RNF-REL-02:** Retries controlados con backoff.
- **RNF-REL-03:** Estados consistentes en DB.

### 10.4 Observabilidad
- **RNF-OBS-01:** Métricas de API y worker (latencia, éxitos, fallos).
- **RNF-OBS-02:** Logs estructurados con correlation id.
- **RNF-OBS-03:** Health/ready endpoints.

### 10.5 Mantenibilidad
- **RNF-MAI-01:** Mantener límites Clean Architecture: domain/app/infra.
- **RNF-MAI-02:** Contratos OpenAPI + cliente generado.

---

## 11. Modelo de datos conceptual (alto nivel)
> No es esquema final; es conceptual para análisis.

### 11.1 Entidades
- **User**(id, email, role, is_active, created_at, password_hash)
- **Section**(id, name, owner_user_id, visibility, created_at, deleted_at?)
- **Document**(id, section_id, title, source, metadata, tags, status, error_message, file_name, mime_type, storage_key, uploaded_by_user_id, created_at, deleted_at)
- **Chunk**(id, document_id, chunk_index, content, embedding, metadata)
- **AuditEvent**(id, event_type, actor, target_type, target_id, metadata, created_at)

### 11.2 Relaciones
- User 1—N Section (owner)
- Section 1—N Document
- Document 1—N Chunk

---

## 12. Matriz de permisos (resumen)
| Acción | Admin | Owner (employee) | Employee (no owner) |
|---|---:|---:|---:|
| Crear sección | ✅ | ✅ | ✅ |
| Editar sección | ✅ | ✅ | ❌ |
| Eliminar sección | ✅ | ✅ | ❌ |
| Ver sección PRIVATE | ✅ | ✅ | ❌ |
| Ver sección INTERNAL_PUBLIC_READ | ✅ | ✅ | ✅ |
| Subir doc a sección | ✅ | ✅ | ❌ |
| Borrar doc | ✅ | ✅ | ❌ |
| Reprocesar doc | ✅ | ✅ | ❌ |
| Chatear/Ask en sección pública | ✅ | ✅ | ✅ |
| Chatear/Ask en sección privada | ✅ | ✅ | ❌ |

---

## 13. Interfaz (API) — propuesta mínima
> Mantener `/v1` como canónica; frontend usa `/api/*` como fachada.

### 13.1 Secciones
- `GET /v1/sections` (lista visible)
- `POST /v1/sections` (crear)
- `GET /v1/sections/{id}` (detalle)
- `PATCH /v1/sections/{id}` (editar)
- `DELETE /v1/sections/{id}` (eliminar)

### 13.2 Documentos por sección
- `GET /v1/sections/{id}/documents` (lista docs)
- `POST /v1/sections/{id}/documents/upload` (upload)
- `POST /v1/documents/{id}/reprocess` (ya existe)
- `DELETE /v1/documents/{id}` (ya existe)

### 13.3 Consulta por sección
- `POST /v1/sections/{id}/ask`
- `POST /v1/sections/{id}/ask/stream`

---

## 14. Interfaz (UI) — propuesta mínima
- **/login** (si no existe en UI, agregar).
- **/sections**: lista + crear + filtros.
- **/sections/{id}**: “Sources” dentro de sección.
- **/sections/{id}/chat**: chat/ask dentro de sección.
- **/admin/users**: ya existe.

---

## 15. Riesgos y mitigaciones
- **R-01**: Complejidad de permisos → mitigación: matriz clara + tests.
- **R-02**: Defaults inseguros en prod → fail-fast.
- **R-03**: Mezcla de conocimiento entre secciones → forzar `section_id` en retrieval.
- **R-04**: Carga masiva de archivos → streaming + límites.

---

## 16. Plan de implementación (roadmap de análisis → delivery)
### Fase A — Diseño y definición
1) Definir entidad Section + visibilidad.
2) Reglas RB y matriz de permisos final.
3) API mínima + UI mínima.

### Fase B — Backend
1) Migración sections + FK en documents.
2) Authz: guards de sección.
3) Endpoints de sections.
4) Ask/chat por sección.
5) Tests unit.

### Fase C — Frontend
1) UI Secciones.
2) Sources por sección.
3) Chat por sección.
4) Tests FE/E2E.

### Fase D — Hardening
1) JWT fail-fast en prod.
2) CSP y key storage.
3) /metrics prod-safe.

---

## 17. Criterios de aceptación globales
- Un employee crea sección PRIVATE: nadie más la ve.
- Un employee crea sección pública interna: otros employees la ven y pueden chatear, pero **no** pueden subir/borrar.
- Retrieval/Ask nunca trae fuentes de otra sección.
- Admin puede hacer todo.
- Errores siguen RFC7807.

---

## 18. Trazabilidad (RF ↔ UC)
| Requisito | Casos de uso |
|---|---|
| RF-10..13 Secciones | UC-10..14 |
| RF-20..24 Documentos por sección | UC-20..24 |
| RF-30..32 RAG por sección | UC-30..31 |
| RF-40 Auditoría | UC-10..14, UC-20..24, UC-01 |

---

## 19. Registro de decisiones
- **D-01:** Mantener `/v1` como API canónica; frontend usa `/api/*`.
- **D-02:** Secciones por tema con owner (no solo por empleado).
- **D-03:** Visibilidad inicial: PRIVATE e INTERNAL_PUBLIC_READ.
- **D-04:** Pipeline asíncrono como estándar para archivos.

---

## 20. Anexos
- A. Lista de endpoints actuales (baseline) — ver OpenAPI generado.
- B. Scorecard de deuda técnica y quick wins (seguridad/config).

---

> **Nota:** Este documento es la base “de analista” (requisitos y casos de uso). A partir de acá, lo siguiente es convertir cada UC/RF en tareas técnicas y tests (sin perder el norte de negocio).

