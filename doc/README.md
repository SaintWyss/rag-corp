# Documentación RAG Corp

Bienvenido a la documentación técnica de RAG Corp. Esta guía está organizada por áreas de interés.

---

## 🚀 Start Here

**¿Primera vez en el proyecto?**

1. 📖 [README Principal (Quickstart)](../README.md) - Overview y setup rápido
2. 🛠️ [Runbook de Desarrollo Local](runbook/local-dev.md) - Comandos y flujo de trabajo
3. 🏛️ [Arquitectura del Sistema](architecture/overview.md) - Entender capas y responsabilidades
4. 🧪 [Test Suite](../services/rag-api/tests/README.md) - 29 tests implementados ✅

**¿Buscas algo específico?**
- 🔌 [API Endpoints](api/http-api.md)
- 💾 [Schema de PostgreSQL](data/postgres-schema.md)
- 🎨 [Patrones de Diseño](design/patterns.md)
- 📊 [Diagramas](diagrams/README.md) (Mermaid)
- 📝 [ADRs](architecture/decisions/README.md) (Decisiones arquitectónicas)

---

## 📖 Guías por Rol

### Para Desarrolladores
- [Runbook de Desarrollo Local](runbook/local-dev.md) - Cómo correr el proyecto
- [Arquitectura del Sistema](architecture/overview.md) - Entender las capas y flujos
- [Patrones de Diseño](design/patterns.md) - Por qué y dónde aplicamos patrones
- [API HTTP](api/http-api.md) - Endpoints, contratos, ejemplos

### Para DevOps/SRE
- [Base de Datos](data/postgres-schema.md) - Schema, índices, pgvector
- [Docker Compose](../compose.yaml) - Orquestación local
- TODO: [Deployment](deployment/kubernetes.md) - Despliegue en producción

### Para QA
- [Estrategia de Testing](quality/testing.md) - Qué y cómo testear
- TODO: [Test Plans](quality/test-plans.md) - Planes de prueba

---

## 🏗️ Arquitectura

- **[Overview](architecture/overview.md)** - Capas, responsabilidades, flujo de datos
- **[Decisiones de Arquitectura (ADRs)](architecture/decisions/README.md)** - Registro de decisiones clave + template
  - [ADR-001: Elección de Google Gemini como LLM](architecture/decisions/001-gemini-as-llm.md)
  - [ADR-002: Estrategia de Chunking](architecture/decisions/002-chunking-strategy.md)
  - [ADR-003: PostgreSQL + pgvector vs Pinecone](architecture/decisions/003-pgvector-storage.md)

---

## 🔌 API y Contratos

- **[HTTP API](api/http-api.md)** - Endpoints REST, request/response models, errores
- **[Contratos TypeScript](../packages/contracts/src/generated.ts)** - Cliente auto-generado

---

## 💾 Base de Datos

- **[Schema PostgreSQL](data/postgres-schema.md)** - Tablas, relaciones, índices
- **[pgvector Configuration](data/postgres-schema.md#pgvector-configuration)** - IVFFlat, dimensiones, tuning
- TODO: **[Migraciones](data/migrations.md)** - Proceso de cambios de schema

---

## 🎨 Diseño

- **[Patrones de Diseño](design/patterns.md)** - Repository, Use Cases, Strategy, DI
- **[Clean Architecture](design/clean-architecture.md)** - Implementación de capas
- **[CRC Cards](../services/rag-api/app/)** - Responsabilidades de componentes (ver código)

---

## 📊 Diagramas

- **[Diagrams Index](diagrams/README.md)** - Guía y convenciones para diagramas Mermaid
- **[Diagrama de Componentes](diagrams/components.md)** - Visión general del sistema
- **[Secuencia: Flujo RAG Completo](diagrams/sequence-rag-flow.md)** - /ask endpoint
- **[Arquitectura de Capas](diagrams/layers.md)** - Domain/Application/Infrastructure

---

## 🧪 Calidad

- **[Estrategia de Testing](quality/testing.md)** - Unitarios, integración, E2E
- **[Test Suite Documentation](../services/rag-api/tests/README.md)** - 29 tests implementados ✅
- TODO: **[Code Coverage](quality/coverage.md)** - Métricas y objetivos
- TODO: **[Performance](quality/performance.md)** - Benchmarks y optimizaciones

---

## 🚀 Operaciones

- **[Runbook Local](runbook/local-dev.md)** - Desarrollo día a día
- TODO: **[Troubleshooting](runbook/troubleshooting.md)** - Problemas comunes
- TODO: **[Monitoreo](runbook/monitoring.md)** - Logs, métricas, alertas

---

## 🤝 Contribuir a la Documentación

### Agregar un Nuevo Diagrama

1. Crear archivo en `doc/diagrams/nombre-descriptivo.md`
2. Usar sintaxis Mermaid (ver [diagrams/README.md](diagrams/README.md))
3. Agregar metadatos: `**Last Updated:** YYYY-MM-DD`
4. Indexar en [diagrams/README.md](diagrams/README.md)

### Registrar una Decisión Arquitectónica (ADR)

1. Copiar template desde [architecture/decisions/000-template.md](architecture/decisions/000-template.md)
2. Nombrar archivo: `NNN-titulo-decision.md` (ej: `004-redis-caching.md`)
3. Rellenar secciones: Context, Decision, Consequences
4. Listar en [architecture/decisions/README.md](architecture/decisions/README.md)
5. Referenciar desde el código si aplica

### Actualizar Documentación Existente

- **Modificar docs:** Actualizar `Last Updated` al final del archivo
- **Cambios mayores:** Registrar en [CHANGELOG.md](../CHANGELOG.md) si aplica
- **Deprecar secciones:** Marcar con `⚠️ DEPRECATED` y fecha
- **TODOs:** Usar `TODO: [descripción]` para features pendientes

---

## 📝 Referencias Adicionales

- [Plan de Mejora Arquitectónica](plan-mejora-arquitectura-2025-12-29.md) - Roadmap técnico
- [Auditoría del Sistema](auditoria-2025-12-29.md) - Estado inicial y deuda técnica
- [Implementación CRC Cards](crc-documentation-implementation-2025-12-29.md) - Documentación en código
- [FIXES.md](../FIXES.md) - Histórico de fixes críticos
- [README Principal](../README.md) - Quickstart y overview

---

## 🗺️ Navegación Rápida

### Empezar
1. Lee el [README principal](../README.md)
2. Sigue el [Runbook de desarrollo](runbook/local-dev.md)
3. Explora la [Arquitectura](architecture/overview.md)

### Implementar Features
1. Consulta [Patrones de Diseño](design/patterns.md)
2. Revisa [Decisiones Arquitectónicas](architecture/decisions/)
3. Actualiza [API Documentation](api/http-api.md)

### Desplegar
1. TODO: Deployment guides
2. TODO: Monitoring setup
3. TODO: Runbooks de producción

---

## 📦 Estructura de Esta Carpeta

```
doc/
├── README.md                       # Este archivo
├── architecture/
│   ├── overview.md                 # Visión general del sistema
│   └── decisions/                  # ADRs (Architecture Decision Records)
│       ├── 001-gemini-as-llm.md
│       ├── 002-chunking-strategy.md
│       └── 003-pgvector-storage.md
├── api/
│   └── http-api.md                 # Documentación de endpoints REST
├── data/
│   └── postgres-schema.md          # Schema de base de datos
├── design/
│   ├── patterns.md                 # Patrones aplicados
│   └── clean-architecture.md       # Implementación de capas
├── diagrams/
│   ├── components.md               # Diagrama de componentes
│   ├── sequence-rag-flow.md        # Secuencia del flujo RAG
│   └── layers.md                   # Diagrama de capas
├── quality/
│   └── testing.md                  # Estrategia de testing
└── runbook/
    └── local-dev.md                # Guía de desarrollo local
```

---

## 🔄 Actualización de Docs

Al modificar el sistema:
1. **Actualiza ADRs** si cambias decisiones arquitectónicas
2. **Actualiza API docs** si modificas endpoints
3. **Actualiza diagramas** si cambias flujos o componentes
4. **Actualiza schema** si modificas base de datos

---

## 📮 Feedback

¿Encontraste algo confuso o falta documentación? Abre un issue:
- [GitHub Issues](https://github.com/SaintWyss/rag-corp/issues)
- Tag: `documentation`
