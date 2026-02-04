# Contexto A — Informe de Negocio y Requisitos del Sistema (Entrega Empresarial)

**Producto:** RAG Corp — Gestión y consulta de conocimiento documental por Workspaces

**Tipo de documento:** BRD + SRS (visión de negocio + especificación funcional/no funcional)

**Versión:** Final (Release para despliegue)

**Fecha:** 2026-02-04

**Autor:** Santiago Scacciaferro

---

## Control del documento

### Estado y alcance del documento
Este documento describe **qué es el software**, **qué problema resuelve**, **qué capacidades provee**, **bajo qué restricciones y controles opera**, y **cómo se valida su entrega**. Está orientado a evaluación empresarial (negocio + seguridad + operación) y a aprobación de despliegue.

### Fuente de verdad y consistencia
- El **contrato de interfaz** (endpoints, payloads y errores) está definido por OpenAPI.
- El **modelo de datos** y reglas persistentes están definidos por migraciones y esquema referenciado.
- La **operación** (runbooks, hardening, troubleshooting) está definida por la carpeta de runbooks.

Este documento es la descripción de negocio y requisitos; el contrato de API y la documentación operativa complementan la especificación.

---

## Índice

1. Resumen ejecutivo
2. Contexto y problema
3. Objetivos y beneficios
4. Alcance
5. Stakeholders, usuarios y modelo de responsabilidad
6. Descripción del sistema (visión funcional)
7. Capacidades y módulos
8. Casos de uso (end-to-end)
9. Requerimientos funcionales (RF)
10. Requerimientos no funcionales (RNF)
11. Seguridad y cumplimiento
12. Datos, retención y auditoría
13. Interfaces e integraciones
14. Operación, despliegue y continuidad
15. Calidad, validación y criterios de aceptación
16. Riesgos, supuestos y mitigaciones
17. Anexos

---

## 1. Resumen ejecutivo
RAG Corp es una solución corporativa para **centralizar documentación**, **procesarla** y habilitar **consulta y respuesta con evidencia** sobre la base documental, bajo un modelo de **aislamiento por Workspaces** y **control de acceso**. El sistema combina:

- **Gestión de Workspaces** como unidad de organización y permisos.
- **Gestión de documentos** (subida, estados, reprocesamiento, archivado) por workspace.
- **Consulta y respuesta** con trazabilidad (fuentes/citas) y opción de **respuesta incremental** (streaming) para mejor experiencia operativa.
- **Administración** para gobierno global (usuarios, auditoría y supervisión).
- **Operación y observabilidad**: salud del servicio, métricas y runbooks para despliegue y resolución de incidentes.

### Resultado esperado en la organización
- Reducción del tiempo de búsqueda de información y del costo operativo asociado.
- Disminución de errores por uso de documentación desactualizada o inconsistente.
- Mayor trazabilidad y auditabilidad: se puede verificar “por qué” y “en base a qué” se emitió una respuesta.
- Reducción de riesgo de exposición entre áreas, por separación y autorización por workspace.

---

## 2. Contexto y problema
### 2.1 Situación típica (AS-IS)
En organizaciones medianas y grandes, el conocimiento relevante se dispersa entre múltiples ubicaciones y formatos. Esto genera:

- **Fricción para encontrar información:** búsquedas manuales, falta de indexado semántico, dependencia del conocimiento informal.
- **Inconsistencias:** coexistencia de múltiples versiones, documentos sin dueño claro, y contradicciones.
- **Baja trazabilidad:** respuestas internas sin referencia formal; difícil auditar o justificar decisiones.
- **Riesgo de exposición:** acceso transversal a información de otras áreas, o resultados que mezclan fuentes por falta de aislamiento.

### 2.2 Problema de negocio
La organización necesita un mecanismo para:

1) **Organizar el conocimiento por unidad operativa** (equipo/cliente/área/proyecto).
2) **Recuperar información relevante** con alta precisión.
3) **Emitir respuestas respaldadas por evidencia documental**, sin depender de memoria individual.
4) **Controlar y auditar el acceso** y el uso del conocimiento.

---

## 3. Objetivos y beneficios
### 3.1 Objetivos
- Centralizar conocimiento documental con gobernanza por workspace.
- Habilitar consulta rápida y con evidencia.
- Asegurar aislamiento de datos y control de acceso por roles y ACL.
- Proveer un servicio operable y desplegable en entornos estándar (contenedores y orquestación).

### 3.2 Beneficios esperados
- **Eficiencia operativa:** menor tiempo para resolver dudas internas y casos repetitivos.
- **Calidad de decisiones:** respuestas basadas en documentación, con fuentes verificables.
- **Gobernanza:** ownership del conocimiento, auditoría de acciones críticas.
- **Seguridad:** separación por workspace, controles de acceso y prácticas de hardening.

---

## 4. Alcance
### 4.1 Incluye (In Scope)
1) **Workspaces**
- Crear, listar, consultar, actualizar y archivar workspaces.
- Visibilidad soportada: `PRIVATE`, `ORG_READ`, `SHARED`.
- Compartición y permisos explícitos para visibilidad `SHARED` mediante ACL.

2) **Documentos** (siempre dentro de un workspace)
- Subida de documentos con validación de tipo y tamaño.
- Pipeline de procesamiento asíncrono (estado visible para usuario).
- Listar/consultar/administrar documentos por workspace.
- Reprocesamiento controlado.
- Borrado/archivado con política de soft-delete.

3) **Consulta y respuesta** (siempre acotadas a workspace)
- `ask`: respuesta con evidencia (fuentes/citas).
- `ask/stream`: entrega incremental de respuesta.
- `query`: búsqueda/retrieval de fragmentos.

4) **Administración y auditoría**
- Gestión global de usuarios.
- Endpoints y vistas administrativas.
- Auditoría de eventos críticos (auth/workspace/document).

5) **Operación y observabilidad**
- Endpoints de salud (health y readiness).
- Métricas exportables para monitoreo.
- Runbooks de despliegue, troubleshooting e incidentes.

### 4.2 Excluye (Out of Scope)
- Multi-tenancy por empresa (el sistema se concibe como organización única con workspaces).
- Integración SSO/LDAP corporativa si no está expresamente acordada.
- OCR avanzado obligatorio para documentos escaneados.
- Workflows complejos de aprobación/firma de documentos.

---

## 5. Stakeholders, usuarios y modelo de responsabilidad

### 5.1 Stakeholders
- **Sponsor de negocio:** define objetivos, validación y priorización.
- **Seguridad/Compliance:** valida controles, políticas de acceso, auditoría y hardening.
- **Operaciones/IT:** despliegue, monitoreo, backups, incidentes.
- **Usuarios finales:** consumo de información (consulta y lectura), carga de documentos según permisos.

### 5.2 Roles del sistema
- **Admin:** gestiona usuarios y workspaces; acceso a auditoría; capacidad de override según políticas.
- **Owner:** propietario del workspace; administra documentos y compartición.
- **Viewer/Member:** consume información del workspace; acceso limitado a lectura y consulta.

### 5.3 Responsabilidades operativas (RACI simplificado)
- **Alta de usuarios, roles globales:** Admin (R), Seguridad (A), IT (C)
- **Gestión de permisos por workspace:** Owner (R), Admin (A), Seguridad (C)
- **Carga y mantenimiento de documentos:** Owner (R), Usuarios autorizados (R), Admin (A)
- **Monitoreo e incidentes:** IT/Operaciones (R), Admin (C), Seguridad (C)

---

## 6. Descripción del sistema (visión funcional)

### 6.1 Conceptos clave
- **Workspace:** unidad de organización y aislamiento; contenedor lógico de documentos y chat.
- **Visibilidad:**
  - `PRIVATE`: visible sólo para owner/admin.
  - `ORG_READ`: visible para empleados/autorizados de la organización.
  - `SHARED`: visible sólo para quienes estén en la ACL.
- **ACL (Access Control List):** lista explícita de usuarios/roles con acceso a un workspace.
- **Documento:** archivo subido; pasa por estados de procesamiento (`PENDING`, `PROCESSING`, `READY`, `FAILED`).
- **Chunk/Fragmento:** unidad de texto usada para retrieval (incluye embedding) asociada a un documento.
- **Evidencia/Fuente:** referencia que vincula una respuesta con documento(s) y fragmentos relevantes.

### 6.2 Principios funcionales no negociables
- **Scoping total por workspace:** ningún retrieval/respuesta puede mezclar fragmentos de workspaces distintos.
- **Permisos por defecto restrictivos:** sin permiso explícito → denegación.
- **Evidencia visible:** cuando existen fuentes relevantes, se presentan como parte de la respuesta.
- **Operación verificable:** salud, métricas y auditoría disponibles para operar en producción.

---

## 7. Capacidades y módulos

### 7.1 Gestión de Workspaces
- CRUD completo de workspaces.
- Parámetros: nombre, visibilidad, estado (activo/archivado), owner.
- Compartición: administración de ACL para `SHARED`.
- Reglas de negocio:
  - Unicidad de workspace por owner y nombre.
  - Workspaces archivados no se muestran por defecto.

### 7.2 Gestión de Documentos
- Subida de documentos con validación de formato y tamaño.
- Estados del documento:
  - `PENDING`: registrado, a la espera de procesamiento.
  - `PROCESSING`: en proceso por el worker.
  - `READY`: listo para consultas.
  - `FAILED`: procesado fallido con mensaje de error controlado.
- Operaciones:
  - Listado por workspace, con filtros (tags, status, búsqueda, paginación).
  - Consulta de metadatos.
  - Reprocesamiento.
  - Borrado/archivado (soft delete).

### 7.3 Procesamiento documental (pipeline)
- Extracción de texto según tipo de documento.
- Normalización de contenido.
- Segmentación en fragmentos (chunking).
- Generación de embeddings.
- Persistencia de chunks y metadatos para retrieval.

### 7.4 Consulta y respuesta con evidencia
- **Ask:** recibir pregunta y producir respuesta basada en fragmentos recuperados del workspace.
- **Query:** recuperar fragmentos relevantes para inspección o para soporte a ask.
- **Ask/stream:** modalidad incremental para feedback inmediato al usuario y cancelación segura.
- Resultados:
  - Respuesta textual.
  - Fuentes/citas: lista de documentos/fragmentos relevantes y verificados.

### 7.5 Auditoría
- Registro de eventos críticos:
  - Autenticación (login/logout/me).
  - Operaciones administrativas.
  - Cambios de permisos (ACL).
  - Operaciones sobre documentos (upload, delete, reprocess).
- Los eventos de auditoría incluyen actor, acción, target y metadata relevante (incluye `workspace_id` cuando aplica).

### 7.6 Administración
- Gestión global de usuarios (listado, activación/desactivación, control de acceso).
- Gestión y supervisión de workspaces.
- Consulta administrativa de auditoría (cuando está habilitado).

### 7.7 Observabilidad y operación
- Endpoints de salud y readiness para API y worker.
- Métricas exportables para monitoreo.
- Documentación operativa (runbooks) para:
  - despliegue,
  - troubleshooting,
  - incidentes,
  - rotación de secretos,
  - verificación post-deploy.

---

## 8. Casos de uso (end-to-end)
> Los casos de uso se expresan para validación empresarial y operativa. Los payloads exactos se definen en OpenAPI.

### UC-01 — Autenticación de usuario
**Actor:** Usuario

**Precondiciones:** usuario habilitado.

**Flujo principal:**
1) El usuario ingresa credenciales.
2) El sistema valida autenticación.
3) El sistema crea sesión segura (cookie httpOnly) y retorna identidad.

**Postcondición:** usuario autenticado.

**Excepciones:** credenciales inválidas → error controlado; usuario inactivo → denegación.

### UC-02 — Crear y administrar workspace
**Actor:** Owner o Admin

**Flujo principal:**
1) Solicita creación de workspace con nombre.
2) El sistema valida reglas (nombre/unicidad).
3) Se crea workspace con `PRIVATE` por defecto.
4) El owner puede ajustar visibilidad y metadatos.

**Postcondición:** workspace creado.

### UC-03 — Compartir workspace (ACL)
**Actor:** Owner o Admin

**Flujo principal:**
1) Selecciona workspace.
2) Agrega usuario y rol/permisos a la ACL.
3) El sistema aplica cambios y registra auditoría.

**Postcondición:** usuario comparte acceso conforme ACL.

### UC-04 — Subir documento y procesar
**Actor:** Owner/Admin (o rol con permiso de escritura)

**Flujo principal:**
1) Usuario sube un documento al workspace.
2) El sistema valida tipo y tamaño.
3) Se registra documento como `PENDING`.
4) Se encola job de procesamiento.
5) Worker procesa y transiciona a `READY` o `FAILED`.

**Postcondición:** documento disponible para consulta o estado de falla visible.

### UC-05 — Consultar (ask) con evidencia
**Actor:** Usuario con acceso al workspace

**Flujo principal:**
1) Usuario envía pregunta.
2) El sistema valida acceso al workspace.
3) El sistema recupera fragmentos relevantes sólo del workspace.
4) Genera respuesta y adjunta fuentes/citas.

**Postcondición:** respuesta entregada con evidencia cuando existan fuentes relevantes.

### UC-06 — Consultar (ask/stream) con cancelación
**Actor:** Usuario con acceso

**Flujo principal:**
1) Usuario inicia consulta streaming.
2) El sistema abre canal de eventos.
3) Entrega incremental de respuesta.
4) El cliente puede cancelar; el sistema cierra de forma segura.
5) Se respeta timeout y límites de tamaño/eventos.

**Postcondición:** respuesta completada o error controlado sin recursos colgados.

### UC-07 — Administración de usuarios
**Actor:** Admin

**Flujo principal:**
1) Admin lista usuarios.
2) Admin activa/desactiva usuarios.
3) El sistema registra auditoría.

**Postcondición:** cambios aplicados; efectos inmediatos sobre permisos y acceso.

---

## 9. Requerimientos funcionales (RF)
> La lista a continuación refleja requisitos finales, verificables y alineados a la operación real.

### A. Autenticación y autorización
- **RF-A1 (Must)** Autenticación JWT con login/logout/me.
- **RF-A2 (Must)** Sesión segura mediante cookies httpOnly; no requiere almacenar JWT en localStorage.
- **RF-A3 (Must)** API Keys para integraciones/CI con RBAC.

### B. Workspaces
- **RF-B1 (Must)** CRUD de workspaces, archivado y reglas de unicidad.
- **RF-B2 (Must)** Visibilidad `PRIVATE | ORG_READ | SHARED` con ACL.
- **RF-B3 (Must)** Permisos owner/admin para escritura; viewers sólo lectura y consulta.

### C. Documentos
- **RF-C1 (Must)** Upload de documentos asociado a workspace; validación MIME y tamaño; encolado asíncrono.
- **RF-C2 (Must)** Estados PENDING/PROCESSING/READY/FAILED visibles en UI.
- **RF-C3 (Must)** CRUD de documentos scoped por workspace; sin acceso → denegación.
- **RF-C4 (Should)** Filtros por tags/búsqueda/paginación.

### D. RAG (Query/Ask)
- **RF-D1 (Must)** Ask/query/stream siempre reciben `workspace_id` y validan acceso.
- **RF-D2 (Must)** Retrieval exclusivamente dentro del workspace.

### E. Auditoría
- **RF-E1 (Must)** Auditoría de eventos críticos con actor y target.
- **RF-E2 (Should)** Consulta administrativa de auditoría con filtros y paginación.

### F. UI (Frontend)
- **RF-F1 (Must)** UI por workspace (Sources/Chat) con navegación y selector.
- **RF-F2 (Should)** Selector global y filtros de sources.
- **RF-F3 (Must)** UI aware de permisos: acciones visibles/habilitadas según rol.

---

## 10. Requerimientos no funcionales (RNF)
> Organizados según ISO/IEC 25010. Los valores operativos son configurables, con defaults documentados.

### 10.1 Seguridad
- **RNF-SEC1** En entorno de producción, `JWT_SECRET` obligatorio y no-default; fail-fast al arrancar si no cumple.
- **RNF-SEC2** Autenticación no puede estar deshabilitada en producción; fail-fast.
- **RNF-SEC3** Cookies seguras en prod: `httpOnly`, `Secure`, `SameSite` definido.
- **RNF-SEC4** Content Security Policy (CSP) definida y verificada; sin `unsafe-inline`.
- **RNF-SEC5** API keys no se usan como mecanismo humano en prod; UI opera con sesión segura.
- **RNF-SEC6** `/metrics` protegido en prod; acceso restringido.

### 10.2 Rendimiento y eficiencia
- **RNF-PERF1** Pipeline asíncrono: upload responde rápido y delega al worker.
- **RNF-PERF2** Límite de upload: 10MB (valor definitivo), con respuestas 413/415 según aplique.
- **RNF-PERF3** Streaming con límites de tiempo y tamaño; cancelación segura.

### 10.3 Confiabilidad / Operabilidad
- **RNF-OPS1** Endpoints de salud y readiness disponibles para API y worker.
- **RNF-OPS2** Métricas exportables con formato estándar (Prometheus).
- **RNF-OPS3** Runbooks actualizados para operación y resolución de incidentes.

### 10.4 Mantenibilidad
- **RNF-MAINT1** Respeto estricto de capas (Clean Architecture).
- **RNF-MAINT2** Adaptadores para proveedores (DB, storage, LLM) con puertos.
- **RNF-MAINT3** Suite de tests: unit + integration + e2e + e2e-full para cambios seguros.

---

## 11. Seguridad y cumplimiento

### 11.1 Modelo de seguridad
- Autenticación obligatoria para recursos protegidos.
- Autorización por roles (admin/owner/viewer) y ACL por workspace.
- Scoping total: toda consulta y recuperación se acota al workspace.

### 11.2 Controles técnicos
- Validación de inputs y límites (tamaño de upload, timeouts, límites de streaming).
- Manejo de errores controlado (sin filtrar secretos o detalles internos).
- Protección de endpoints operativos en producción (métricas y administración).
- Políticas de headers de seguridad en frontend (CSP, XFO, nosniff, etc.).

### 11.3 Gestión de secretos
- Secretos fuera del repositorio.
- Rotación documentada para claves críticas.
- Separación por entorno (dev/staging/prod) con prácticas de hardening.

### 11.4 Auditoría y trazabilidad
- Auditoría para acciones críticas.
- La auditoría soporta investigación post-incidente y trazabilidad operativa.

---

## 12. Datos, retención y auditoría

### 12.1 Datos manejados
- Usuarios y atributos de autorización.
- Workspaces, visibilidad y ACL.
- Documentos y metadatos.
- Fragmentos/chunks y embeddings.
- Eventos de auditoría.

### 12.2 Retención y políticas
- Soft-delete y archivado según política.
- Capacidad de respaldos y restauración por prácticas de operación.

### 12.3 Evidencia en respuestas
- Las fuentes/citas exponen relación documento-fragmento.
- La evidencia soporta auditoría de decisiones y justificación de respuestas.

---

## 13. Interfaces e integraciones

### 13.1 API HTTP
- Superficie canónica para auth, workspaces, documentos y consultas.
- Contrato formal en OpenAPI (integración cliente/servidor).

### 13.2 Frontend
- Interfaz web para login, workspaces, documentos (Sources), chat y administración.
- UI centrada en workspace y en permisos.

### 13.3 Procesamiento asíncrono
- Cola de trabajos para procesamiento documental.
- Worker responsable de transformaciones y persistencia.

### 13.4 Almacenamiento de binarios
- Almacenamiento compatible con S3 (S3/MinIO), configurable por entorno.

---

## 14. Operación, despliegue y continuidad

### 14.1 Despliegue
- Despliegue reproducible mediante contenedores.
- Soporte para orquestación (incluye probes de salud para escalado y tolerancia a fallas).

### 14.2 Observabilidad
- Endpoints de health/ready.
- Métricas para monitoreo.
- Dashboards cuando se despliega stack de observabilidad.

### 14.3 Continuidad
- Procedimientos de backup/restore documentados.
- Procedimientos de incidentes y troubleshooting documentados.

---

## 15. Calidad, validación y criterios de aceptación

### 15.1 Estrategia de pruebas
- Unit tests: validación de lógica y contratos internos.
- Integration tests: validación de repositorios, DB, endpoints y seguridad.
- E2E tests: flujos completos (login → workspace → upload → READY → consulta).

### 15.2 Gates de calidad (entrega)
- Tests verdes.
- Lint y checks de calidad.
- Verificación de seguridad operativa (secret scanning y hardening).

### 15.3 Criterios de aceptación finales
Se acepta la entrega cuando:
1) Se valida autenticación y sesión segura.
2) Workspaces operan con visibilidad y ACL.
3) Documentos se suben, procesan y quedan `READY`.
4) Ask/query/stream operan 100% scoped y con evidencia.
5) `/metrics` y endpoints operativos están protegidos en prod.
6) Existen runbooks para deploy, incidentes, troubleshooting y rotación.

---

## 16. Riesgos, supuestos y mitigaciones

### 16.1 Riesgos operativos
- Documentos con mala calidad de texto (escaneos) pueden reducir precisión.
- Errores o latencia del proveedor externo de generación pueden afectar respuestas.

**Mitigaciones:**
- Estados y reprocess para documentos.
- Timeouts, cancelación y degradación segura.
- Observabilidad para detectar y actuar.

### 16.2 Riesgos de seguridad
- Manejo indebido de secretos.
- Exposición accidental por configuración.

**Mitigaciones:**
- Fail-fast en producción si configuración insegura.
- Política de secretos fuera del repositorio.
- Endpoints operativos protegidos.
- Auditoría y logs sanitizados.

---

## 17. Anexos

### 17.1 Glosario
- **Workspace:** unidad de aislamiento y permisos.
- **Owner:** propietario del workspace con permisos de escritura.
- **Viewer:** usuario con acceso de lectura/consulta.
- **ACL:** lista de control de acceso por workspace.
- **Chunk:** fragmento de documento para retrieval.
- **Evidencia/Fuente:** referencia documento-fragmento asociada a una respuesta.

### 17.2 Matriz de trazabilidad (resumen)
| Artefacto | Referencia |
|---|---|
| RF (Funcionales) | Documento de requerimientos funcionales + OpenAPI |
| RNF (No funcionales) | Documento RNF (ISO/IEC 25010) + evidencia operativa |
| Contrato API | OpenAPI |
| Operación | Runbooks |

---

**Fin del documento.**

