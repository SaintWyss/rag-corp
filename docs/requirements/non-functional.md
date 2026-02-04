# Requerimientos No Funcionales (RNF) — RAG Corp

**Project:** RAG Corp  
**Version:** Definitivo  
**Last Updated:** 2026-01-24  
**Source of Truth:** `docs/project/informe_de_sistemas_rag_corp.md` §4.2  
**Standard:** ISO/IEC 25010

---

## TL;DR

Este documento define los **requerimientos no funcionales** del sistema RAG Corp, organizados según ISO/IEC 25010 (Security, Performance, Reliability, Maintainability).

---

## Matriz de Requerimientos No Funcionales

### Security (Seguridad)

| ID       | Requisito                                | Métrica / Criterio de Aceptación                                               | Estado AS-IS                |
| -------- | ---------------------------------------- | ------------------------------------------------------------------------------ | --------------------------- |
| RNF-SEC1 | JWT_SECRET obligatorio en prod           | En `ENV=prod`, si secret default/vacío → proceso falla al arrancar (fail-fast) | ✅ Implementado             |
| RNF-SEC2 | Auth deshabilitada en prod → fail-fast   | `ENV=prod` + auth off → abort startup                                          | ✅ Implementado             |
| RNF-SEC3 | Cookies secure en prod                   | En prod: `Secure` activo; `SameSite` definido; httpOnly                        | ✅ Implementado             |
| RNF-SEC4 | CSP sin unsafe-inline                    | Header CSP cumple política; test smoke valida header                           | ⚠️ Parcial (falta test E2E) |
| RNF-SEC5 | API key no como mecanismo humano en prod | UI no depende de API key persistida; CI/E2E pueden usar service keys           | ✅ Implementado             |
| RNF-SEC6 | /metrics protegido en prod               | Sin auth → 401/403; con rol/permiso → 200                                      | ✅ Implementado             |

### Performance Efficiency (Rendimiento)

| ID        | Requisito          | Métrica / Criterio de Aceptación                         | Estado AS-IS    |
| --------- | ------------------ | -------------------------------------------------------- | --------------- |
| RNF-PERF1 | Pipeline asíncrono | Upload responde rápido (202) y delega al worker          | ✅ Implementado |
| RNF-PERF2 | Límites de upload  | 413 al exceder; 415 mime inválido; valores configurables | ✅ Implementado |

**Límite de Upload (AS-IS):**

```
# Evidencia: apps/backend/app/crosscutting/config.py
max_body_bytes: int = 10 * 1024 * 1024  # 10MB
```

**TO-BE:** El límite de 10MB es el valor definitivo. Si se requiere aumentar, se ajustará con evidencia y tests.

### Reliability / Operability (Confiabilidad)

| ID       | Requisito                          | Métrica / Criterio de Aceptación           | Estado AS-IS    |
| -------- | ---------------------------------- | ------------------------------------------ | --------------- |
| RNF-OPS1 | /healthz y /readyz en API y worker | health/ready responden; CI smoke verifica  | ✅ Implementado |
| RNF-OPS2 | Métricas Prometheus                | Métricas exportadas; dashboards opcionales | ✅ Implementado |
| RNF-OPS3 | Runbooks y troubleshooting         | Existe `docs/runbook/*` actualizado        | ✅ Implementado |

### Maintainability (Mantenibilidad)

| ID         | Requisito                         | Métrica / Criterio de Aceptación     | Estado AS-IS    |
| ---------- | --------------------------------- | ------------------------------------ | --------------- |
| RNF-MAINT1 | Respetar capas Clean Architecture | Domain no importa FastAPI/SQLAlchemy | ✅ Implementado |
| RNF-MAINT2 | Ports/adapters para infra         | Cambiar provider no rompe use cases  | ✅ Implementado |
| RNF-MAINT3 | Tests unit + e2e-full             | Suite verde: unit + e2e + e2e-full   | ✅ Implementado |

---

## Gaps de Implementación

| ID       | Gap                                    | Impacto | Acción Sugerida          |
| -------- | -------------------------------------- | ------- | ------------------------ |
| RNF-SEC4 | Falta test E2E para validar CSP header | Medio   | Agregar smoke test en CI |

---

## Out-of-Scope

Los siguientes RNF NO están en alcance para el baseline actual:

| ID       | Requisito     | Razón                                 |
| -------- | ------------- | ------------------------------------- |
| RNF-SSO  | SSO/OIDC      | Requiere integración con IdP externo  |
| RNF-LDAP | LDAP binding  | Requiere infraestructura enterprise   |
| RNF-MT   | Multi-tenancy | Arquitectura single-tenant por diseño |

---

## Referencias

- Contrato: `docs/project/informe_de_sistemas_rag_corp.md` §4.2
- ISO/IEC 25010: https://www.iso.org/standard/35733.html
- ADR-001: `docs/architecture/adr/ADR-001-clean-architecture.md`
