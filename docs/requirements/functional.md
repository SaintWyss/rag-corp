# Requerimientos Funcionales (RF) — RAG Corp

**Project:** RAG Corp  
**Version:** Definitivo  
**Last Updated:** 2026-01-24  
**Source of Truth:** `docs/project/informe_de_sistemas_rag_corp.md` §4.1

---

## TL;DR

Este documento define los **requerimientos funcionales** del sistema RAG Corp. Cada RF tiene un ID único, descripción, prioridad (MoSCoW), y criterios de aceptación verificables.

---

## Matriz de Requerimientos Funcionales

### A. Autenticación y Autorización

| ID    | Nombre           | Descripción                             | Prioridad | Criterios de Aceptación                                                                                 |
| ----- | ---------------- | --------------------------------------- | --------- | ------------------------------------------------------------------------------------------------------- |
| RF-A1 | Auth JWT         | Login/logout/me con JWT                 | Must      | Login correcto crea sesión; credenciales inválidas → 401 RFC7807; `/auth/me` devuelve usuario           |
| RF-A2 | Cookies httpOnly | UI usa cookies httpOnly para auth       | Must      | Cookie httpOnly; logout invalida cookie; no requiere almacenar JWT en localStorage                      |
| RF-A3 | API Keys + RBAC  | API keys para CI/integraciones con RBAC | Must      | Endpoint protegido exige permisos; sin RBAC usa fallback de scopes; actor service queda auditado |

### B. Workspaces

| ID    | Nombre               | Descripción                                 | Prioridad | Criterios de Aceptación                                                             |
| ----- | -------------------- | ------------------------------------------- | --------- | ----------------------------------------------------------------------------------- |
| RF-B1 | CRUD Workspaces      | Crear/listar/ver/editar/archivar workspaces | Must      | `PRIVATE` por default; unicidad `owner+name`; archivados no aparecen por defecto    |
| RF-B2 | Visibilidad + Share  | `ORG_READ` y `SHARED` (ACL)                 | Must      | ORG_READ visible a empleados; SHARED visible solo en ACL; cambios generan auditoría |
| RF-B3 | Permisos owner/admin | Owner/admin write; viewers read+chat        | Must      | Viewer no puede upload/delete/reprocess; 403 RFC7807; admin override funciona       |

### C. Documentos

| ID    | Nombre             | Descripción                                       | Prioridad | Criterios de Aceptación                                            |
| ----- | ------------------ | ------------------------------------------------- | --------- | ------------------------------------------------------------------ |
| RF-C1 | Upload a workspace | Upload PDF/DOCX asociado a workspace              | Must      | Upload crea doc PENDING en workspace; valida MIME/size; encola job |
| RF-C2 | Estados documento  | PENDING/PROCESSING/READY/FAILED                   | Must      | Worker transiciona; FAILED guarda error_message; UI muestra estado |
| RF-C3 | CRUD docs scoped   | list/get/delete/reprocess filtrados por workspace | Must      | Un usuario sin acceso al workspace no puede ver docs ni operar     |
| RF-C4 | Filtros            | tags + búsqueda + paginación                      | Should    | Listado filtra por tag/status/q; paginación estable y testeada     |

### D. RAG (Query/Ask)

| ID    | Nombre           | Descripción                           | Prioridad | Criterios de Aceptación                                           |
| ----- | ---------------- | ------------------------------------- | --------- | ----------------------------------------------------------------- |
| RF-D1 | Ask/query scoped | ask/query/stream reciben workspace_id | Must      | Sin workspace_id → 400; sin acceso → 403; no hay fuentes cruzadas |
| RF-D2 | Retrieval scoped | retrieval solo del workspace          | Must      | Test cross-workspace: WS1 nunca devuelve chunks de WS2            |

### E. Auditoría

| ID    | Nombre             | Descripción                           | Prioridad | Criterios de Aceptación                                                          |
| ----- | ------------------ | ------------------------------------- | --------- | -------------------------------------------------------------------------------- |
| RF-E1 | Auditoría          | eventos críticos (auth/workspace/doc) | Must      | Se registran acciones con actor y target; workspace_id en metadata cuando aplica |
| RF-E2 | Consulta auditoría | admin puede consultar auditoría       | Should    | Endpoint admin-only permite filtrar por workspace/actor/acción y paginar         |

### F. UI (Frontend)

| ID    | Nombre              | Descripción                           | Prioridad | Criterios de Aceptación                                                          |
| ----- | ------------------- | ------------------------------------- | --------- | -------------------------------------------------------------------------------- |
| RF-F1 | UI por workspace    | Sources/Chat por workspace            | Must      | Existe `/workspaces`; selector; navegación al workspace y sus docs/chat          |
| RF-F2 | Selector + filtros  | selector global + filtros de sources  | Should    | Selector persistente; filtros funcionan; estados y permisos visibles             |
| RF-F3 | UI permission-aware | acciones visibles solo si corresponde | Must      | Owner/admin ven upload/delete/reprocess; viewer no ve acciones o quedan disabled |

---

## Trazabilidad RF ↔ Endpoints ↔ Tests

| RF        | Endpoints Canónicos                  | Tests                                    |
| --------- | ------------------------------------ | ---------------------------------------- |
| RF-A1..A3 | `/auth/*`                            | `tests/e2e/tests/*.spec.ts`, unit auth   |
| RF-B1..B3 | `/v1/workspaces*`                    | `tests/e2e/tests/workspace-flow.spec.ts` |
| RF-C1..C3 | `/v1/workspaces/{id}/documents*`     | `tests/e2e/tests/documents.spec.ts`      |
| RF-D1..D2 | `/v1/workspaces/{id}/ask*`, `/v1/workspaces/{id}/query` | `tests/e2e/tests/chat.spec.ts`           |
| RF-E1..E2 | `/v1/admin/audit`                    | unit audit tests                         |

---

## Estado de Implementación (AS-IS)

| RF        | Estado          | Evidencia                                                                          |
| --------- | --------------- | ---------------------------------------------------------------------------------- |
| RF-A1     | ✅ Implementado | `shared/contracts/openapi.json` contiene `/auth/login`, `/auth/me`, `/auth/logout` |
| RF-A2     | ✅ Implementado | Cookie httpOnly en login response                                                  |
| RF-A3     | ✅ Implementado | `X-API-Key` header + `API_KEYS_CONFIG` + `RBAC_CONFIG`                             |
| RF-B1..B3 | ✅ Implementado | Endpoints workspace CRUD en OpenAPI                                                |
| RF-C1..C3 | ✅ Implementado | Endpoints document scoped en OpenAPI                                               |
| RF-D1..D2 | ✅ Implementado | Endpoints ask/query scoped en OpenAPI                                              |
| RF-E1     | ✅ Implementado | `audit_events` table + audit repo                                                  |
| RF-E2     | ✅ Implementado | `/v1/admin/audit` endpoint                                                         |
| RF-F1..F3 | ✅ Implementado | Frontend con workspace selector                                                    |

---

## Glosario

| Término        | Definición                                                           |
| -------------- | -------------------------------------------------------------------- |
| **Workspace**  | Contenedor lógico de documentos y chat; unidad de permisos y scoping |
| **Owner**      | Usuario creador del workspace; controla escritura/borrado            |
| **Visibility** | `PRIVATE`, `ORG_READ`, `SHARED`                                      |
| **ACL**        | Lista explícita (`workspace_acl`) para visibilidad `SHARED`          |
| **Scoped**     | Operación limitada a un workspace específico                         |

---

## Referencias

- Contrato: `docs/project/informe_de_sistemas_rag_corp.md` §4.1
- API HTTP: `docs/reference/api/http-api.md`
- OpenAPI: `shared/contracts/openapi.json`
