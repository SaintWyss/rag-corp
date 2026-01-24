# RAG Corp Documentation — v6 Definitive

**Project:** RAG Corp  
**Version:** v6 (Definitivo)  
**Last Updated:** 2026-01-24

---

## 📚 Índice de Documentación

### 🎯 Fuentes de Verdad (Canonical)

| Documento | Descripción | Prioridad |
|-----------|-------------|-----------|
| [System Report](./system/informe_de_sistemas_rag_corp.md) | Contrato v6 completo: alcance, RF, RNF, arquitectura | MÁXIMA |
| [Release Notes](./system/release-notes.md) | Historial de versiones y breaking changes | Alta |
| [API HTTP](./api/http-api.md) | Endpoints, auth, ejemplos curl | Alta |
| [Architecture Overview](./architecture/overview.md) | Arquitectura high-level, flujos, capas | Alta |

---

### 📋 Requerimientos

| Documento | Descripción |
|-----------|-------------|
| [Functional Requirements](./requirements/functional.md) | Matriz RF con IDs, criterios, trazabilidad |
| [Non-Functional Requirements](./requirements/non-functional.md) | Matriz RNF (ISO 25010), seguridad, performance |

---

### 🏗️ Arquitectura

| Documento | Descripción |
|-----------|-------------|
| [Overview](./architecture/overview.md) | Clean Architecture, componentes, flujos |
| [ADR-001: Clean Architecture](./architecture/decisions/ADR-001-clean-architecture.md) | Decisión de estructura |
| [ADR-002: pgvector](./architecture/decisions/ADR-002-pgvector.md) | Vector store |
| [ADR-003: Google Gemini](./architecture/decisions/ADR-003-google-gemini.md) | LLM provider |
| [ADR-004: Naming Workspace](./architecture/decisions/ADR-004-naming-workspace.md) | Terminología |
| [ADR-005: Workspace Uniqueness](./architecture/decisions/ADR-005-workspace-uniqueness.md) | Unicidad |
| [ADR-006: Archive/Soft-Delete](./architecture/decisions/ADR-006-archive-soft-delete.md) | Borrado |
| [ADR-007: Legacy Endpoints](./architecture/decisions/ADR-007-legacy-endpoints.md) | Compatibilidad |

---

### 🎨 Diagramas

| Diagrama | Descripción |
|----------|-------------|
| [Components](./diagrams/components.mmd) | Componentes del sistema |
| [Deployment](./diagrams/deployment.mmd) | Stack Docker Compose |
| [Sequence: Login](./diagrams/sequence-login.mmd) | Flujo de autenticación |
| [Sequence: Upload](./diagrams/sequence-upload-async.mmd) | Flujo de upload asíncrono |
| [Sequence: Ask](./diagrams/sequence-ask-scoped.mmd) | Flujo de consulta RAG |
| [Domain Classes](./diagrams/domain-class.mmd) | Clases del dominio |
| [ER Diagram](./diagrams/data-er.mmd) | Modelo de datos |
| [Document State](./diagrams/document-state.mmd) | Estados del documento |

---

### 💾 Datos

| Documento | Descripción |
|-----------|-------------|
| [PostgreSQL Schema](./data/postgres-schema.md) | Tablas, índices, pgvector, queries |

---

### 🔧 API

| Documento | Descripción |
|-----------|-------------|
| [HTTP API](./api/http-api.md) | Endpoints, auth, ejemplos |
| [RBAC](./api/rbac.md) | Control de acceso basado en roles |

---

### 📖 Runbooks (Operación)

| Documento | Descripción |
|-----------|-------------|
| [Local Development](./runbook/local-dev.md) | Levantar stack, seeds, troubleshooting |
| [Migrations](./runbook/migrations.md) | Alembic upgrade/downgrade |
| [Observability](./runbook/observability.md) | Prometheus, Grafana, métricas |
| [Worker](./runbook/worker.md) | Operación del worker RQ |
| [Incident Response](./runbook/incident.md) | Checklist de incidentes |
| [Troubleshooting](./runbook/troubleshooting.md) | Problemas comunes |
| [Deployment](./runbook/deployment.md) | Deploy a producción |
| [Production Hardening](./runbook/production-hardening.md) | Seguridad en prod |
| [Kubernetes](./runbook/kubernetes.md) | Deploy en k8s |

---

### 🎨 Design

| Documento | Descripción |
|-----------|-------------|
| [Patterns](./design/patterns.md) | Patrones de diseño implementados |

---

### 📊 Quality

| Documento | Descripción |
|-----------|-------------|
| [Testing](./quality/testing.md) | Estrategia de testing |

---

### 📝 Meta

| Documento | Descripción |
|-----------|-------------|
| [Changelog](./meta/CHANGELOG.md) | Cambios por versión |
| [Contributing](./meta/CONTRIBUTING.md) | Guía de contribución |
| [Security](./meta/SECURITY.md) | Política de seguridad |

---

## 🚀 Quick Start

```bash
# 1. Setup
cp .env.example .env
pnpm install

# 2. Start infrastructure
pnpm docker:up
pnpm db:migrate

# 3. Create admin user
pnpm admin:bootstrap -- --email admin@example.com --password secret123

# 4. Start development
pnpm dev
```

**URLs:**
- Frontend: http://localhost:3000
- API: http://localhost:8000
- Swagger: http://localhost:8000/docs

---

## 📐 Estructura de docs/

```
docs/
├── README.md                 # Este archivo (índice)
├── api/                      # Documentación de API
│   ├── http-api.md          # Endpoints y auth
│   └── rbac.md              # Control de acceso
├── architecture/             # Arquitectura
│   ├── overview.md          # Overview high-level
│   └── decisions/           # ADRs
├── data/                     # Modelo de datos
│   └── postgres-schema.md   # Schema y queries
├── design/                   # Diseño
│   └── patterns.md          # Patrones implementados
├── diagrams/                 # Diagramas Mermaid
│   ├── components.mmd
│   ├── deployment.mmd
│   ├── sequence-*.mmd
│   ├── domain-class.mmd
│   ├── data-er.mmd
│   └── document-state.mmd
├── meta/                     # Meta-documentación
│   ├── CHANGELOG.md
│   ├── CONTRIBUTING.md
│   └── SECURITY.md
├── quality/                  # QA
│   └── testing.md
├── requirements/             # Requerimientos
│   ├── functional.md
│   └── non-functional.md
├── runbook/                  # Operación
│   ├── local-dev.md
│   ├── migrations.md
│   ├── observability.md
│   ├── worker.md
│   ├── incident.md
│   └── ...
└── system/                   # Sistema
    ├── informe_de_sistemas_rag_corp.md  # Contrato v6
    └── release-notes.md
```

---

## 🔗 Referencias Externas

- [OpenAPI Spec](../shared/contracts/openapi.json)
- [Alembic Migrations](../apps/backend/alembic/versions/)
- [Compose Config](../compose.yaml)
- [CI Workflow](../.github/workflows/ci.yml)
