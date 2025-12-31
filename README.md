# RAG Corp

> Sistema RAG (Retrieval-Augmented Generation) empresarial con Google Gemini, PostgreSQL + pgvector, y Next.js.

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python](https://img.shields.io/badge/Python-3.11-blue.svg)](https://www.python.org/)
[![Next.js](https://img.shields.io/badge/Next.js-16.1.1-black.svg)](https://nextjs.org/)

---

## 📚 Documentación Completa

**👉 [Ir a la Documentación Técnica Completa](doc/README.md)**

Arquitectura, API, diagramas, ADRs, testing strategy, runbooks, y más.

---

## 🎯 ¿Qué es RAG Corp?

RAG Corp es un sistema de búsqueda semántica y generación de respuestas que permite:

- **Ingestar documentos** y dividirlos en fragmentos inteligentes (chunks)
- **Buscar por similitud semántica** usando embeddings vectoriales (768D)
- **Generar respuestas contextuales** con Google Gemini basándose en documentos recuperados
- **Evitar alucinaciones** limitando las respuestas al contexto disponible

### Problema que Resuelve

Las organizaciones tienen documentación dispersa (PDFs, Wikis, Confluence). RAG Corp permite:
- Consultar en lenguaje natural ("¿Cuántos días de vacaciones tengo?")
- Obtener respuestas precisas con fuentes citadas
- Mantener el control sobre los datos (sin enviar documentos completos a APIs externas)

---

## ✨ Features

- ✅ **Ingesta de documentos** vía API REST
- ✅ **Embeddings de 768 dimensiones** (Google text-embedding-004)
- ✅ **Búsqueda vectorial** con PostgreSQL + pgvector (IVFFlat index)
- ✅ **Generación RAG** con Gemini 1.5 Flash
- ✅ **UI moderna** en Next.js 16 con Tailwind CSS
- ✅ **Contratos tipados** (OpenAPI → TypeScript vía Orval)
- ✅ **Docker Compose** para desarrollo local
- ✅ **Clean Architecture** parcial (Use Case en `/ask`)
- ✅ **Test Suite** documentada (ver `services/rag-api/tests`)

---

## 🏗️ Stack Tecnológico

### Backend
- **FastAPI** (Python 3.11) - Framework web ASGI
- **PostgreSQL 16** + **pgvector 0.8.1** - Base de datos vectorial
- **Google Generative AI SDK** - Embeddings + LLM (Gemini)
- **psycopg 3.2** - Driver PostgreSQL moderno

### Frontend
- **Next.js 16.1.1** (App Router) - Framework React con SSR
- **Tailwind CSS 4** - Utilidades de estilo
- **TypeScript 5** - Tipado estático
- **Orval** - Generador de cliente HTTP desde OpenAPI

### DevOps
- **pnpm + Turbo** - Monorepo con caché de builds
- **Docker Compose** - Orquestación local
- **OpenAPI 3.0** - Documentación de API

---

## 🚀 Quickstart Local

### Requisitos Previos

- [Node.js 20.9+](https://nodejs.org/) y [pnpm 10+](https://pnpm.io/)
- [Docker](https://www.docker.com/) y [Docker Compose](https://docs.docker.com/compose/)
- Cuenta de [Google Cloud](https://console.cloud.google.com/) con Gemini API habilitada

### Paso 1: Clonar y Configurar

```bash
# Clonar repositorio
git clone https://github.com/SaintWyss/rag-corp.git
cd rag-corp

# Copiar template de variables de entorno
cp .env.example .env

# Editar .env y agregar tu API Key
# GOOGLE_API_KEY=tu_clave_aqui
```

### Paso 2: Instalar Dependencias

```bash
pnpm install
```

### Paso 3: Levantar Infraestructura

```bash
# Inicia PostgreSQL + pgvector + Backend FastAPI
pnpm docker:up

# Verificar que servicios estén healthy
docker compose ps
```

### Paso 4: Generar Contratos TypeScript

```bash
# Exporta OpenAPI desde FastAPI
pnpm contracts:export

# Genera cliente TypeScript con Orval
pnpm contracts:gen
```

### Paso 5: Ejecutar en Modo Desarrollo

```bash
pnpm dev
```

**Accesos:**
- 🌐 Frontend: http://localhost:3000
- 🔌 API: http://localhost:8000
- 📚 Docs interactivas: http://localhost:8000/docs

---

## 📁 Estructura del Repositorio

```
rag-corp/
├── apps/
│   └── web/                    # Frontend Next.js 16
│       ├── app/                # App Router (page.tsx = UI principal)
│       ├── next.config.ts      # Proxy /v1/* → backend
│       └── package.json
├── services/
│   └── rag-api/                # Backend FastAPI
│       ├── app/
│       │   ├── main.py         # Entry point + CORS
│       │   ├── routes.py       # Controllers (endpoints HTTP)
│       │   ├── store.py        # Repository (PostgreSQL + pgvector) [LEGACY]
│       │   ├── embeddings.py   # Google Embeddings Service [LEGACY]
│       │   ├── llm.py          # Google Gemini LLM Service [LEGACY]
│       │   ├── text.py         # Text Chunking Utility [LEGACY]
│       │   ├── domain/         # ✨ Entidades y reglas de negocio
│       │   ├── application/    # ✨ Use Cases (Clean Architecture)
│       │   ├── infrastructure/ # ✨ Adapters (DB, APIs externas)
│       │   └── container.py    # ✨ Dependency Injection
│       ├── scripts/
│       │   └── export_openapi.py
│       ├── Dockerfile
│       └── requirements.txt
├── packages/
│   └── contracts/              # Contratos compartidos FE/BE
│       ├── openapi.json        # Schema exportado desde FastAPI
│       ├── src/generated.ts    # Cliente TypeScript auto-generado
│       └── orval.config.ts
├── infra/
│   └── postgres/
│       └── init.sql            # Schema inicial (documents + chunks + índice)
├── doc/                        # 📖 Documentación detallada
│   ├── README.md               # Índice de documentación
│   ├── architecture/           # Arquitectura y ADRs
│   ├── api/                    # Documentación de API
│   ├── data/                   # Schema y base de datos
│   ├── design/                 # Patrones y decisiones
│   ├── diagrams/               # Diagramas Mermaid
│   ├── quality/                # Testing y calidad
│   └── runbook/                # Guías operacionales
├── compose.yaml                # Docker Compose (db + rag-api)
├── pnpm-workspace.yaml         # Configuración monorepo
├── turbo.json                  # Tareas Turbo (dev, build, lint)
├── .env.example                # Template de variables de entorno
├── FIXES.md                    # Histórico de fixes críticos
└── README.md                   # Este archivo
```

### Carpetas Clave

- **`apps/web`**: Interfaz de usuario React/Next.js que consume la API.
- **`services/rag-api`**: Servidor Python con lógica RAG (ingesta, búsqueda, generación).
- **`packages/contracts`**: Single source of truth de tipos compartidos (OpenAPI → TypeScript).
- **`infra/postgres`**: DDL y configuración de base de datos vectorial.
- **`doc/`**: Documentación técnica detallada (arquitectura, API, runbooks, ADRs).

---

## 📚 Documentación Completa

La documentación está organizada en [`/doc`](doc/README.md):

- **[Arquitectura](doc/architecture/overview.md)**: Capas, flujo de datos, decisiones de diseño
- **[API HTTP](doc/api/http-api.md)**: Endpoints, contratos, ejemplos, errores
- **[Base de Datos](doc/data/postgres-schema.md)**: Schema, índices, pgvector, migraciones
- **[Runbook Local](doc/runbook/local-dev.md)**: Cómo correr, troubleshooting, comandos útiles
- **[Testing](doc/quality/testing.md)**: Estrategia de tests y ejecución
- **[Patrones de Diseño](doc/design/patterns.md)**: Repository, Use Cases, DI
- **[Diagramas](doc/diagrams/)**: Secuencia, componentes, arquitectura

---

## 🛣️ Roadmap

### ✅ Completado (v0.1.0)
- [x] Ingesta de documentos con chunking
- [x] Embeddings con Google text-embedding-004
- [x] Búsqueda vectorial con pgvector
- [x] Generación RAG con Gemini 1.5 Flash
- [x] UI cyberpunk en Next.js
- [x] Contratos tipados (OpenAPI → TypeScript)
- [x] Documentación CRC Cards en código
- [x] Clean Architecture (Fase 1): Domain, Application, Infrastructure layers
- [x] Exception handlers base (Database/Embedding/LLM)
- [x] Logging estructurado en backend

### 🚧 En Progreso
- [ ] **Clean Architecture** (Fase 2): Refactorizar endpoints restantes
- [ ] **Tests Unitarios**: Alinear tests con contratos actuales
- [ ] **Observabilidad**: Métricas y tracing

### 📋 Planificado
- [ ] **Autenticación**: API Keys o JWT
- [ ] **Rate Limiting**: Protección contra abuse
- [ ] **Streaming**: Respuestas en tiempo real (SSE)
- [ ] **Multi-turn Chat**: Historial de conversación
- [ ] **Filtros Avanzados**: Por metadata, fecha, source
- [ ] **Admin UI**: CRUD de documentos
- [ ] **Deployment**: Kubernetes + Helm charts

Ver [Plan de Mejora Arquitectónica](doc/plan-mejora-arquitectura-2025-12-29.md) para detalles.

---

## 🧪 Testing

```bash
# Backend (Python)
cd services/rag-api
pytest tests/ -v --cov=app

# Solo tests unitarios (rápidos, sin DB)
pytest -m unit

# Solo tests de integración (requiere DB)
pytest -m integration

# Con reporte HTML
pytest --cov=app --cov-report=html
open htmlcov/index.html

# Frontend (TypeScript) - TODO: Implementar tests
# (No hay scripts de test en apps/web por ahora)
```

**Estado actual:**
- ✅ Suite de tests backend presente (unit + integration)
- ✅ Cobertura objetivo definida en `services/rag-api/pytest.ini`
- 📖 Ver [Test Suite Documentation](services/rag-api/tests/README.md)

---

## 🤝 Contribuir

1. Fork el repositorio
2. Crea una branch (`git checkout -b feature/amazing-feature`)
3. Commit tus cambios (`git commit -m 'feat: add amazing feature'`)
4. Push a la branch (`git push origin feature/amazing-feature`)
5. Abre un Pull Request

### Guías de Estilo

- **Python**: PEP 8, type hints, docstrings CRC
- **TypeScript**: ESLint + Prettier
- **Commits**: Conventional Commits (`feat:`, `fix:`, `docs:`, `refactor:`)

---

## 📄 Licencia

Este proyecto está bajo la licencia MIT. Ver [LICENSE](LICENSE) para más detalles.

---

## 🙏 Agradecimientos

- [pgvector](https://github.com/pgvector/pgvector) - Extensión PostgreSQL para búsquedas vectoriales
- [FastAPI](https://fastapi.tiangolo.com/) - Framework web moderno para Python
- [Google Gemini](https://ai.google.dev/) - LLM y embeddings de alta calidad
- [Next.js](https://nextjs.org/) - Framework React con SSR

---

## 📞 Soporte

- 📧 Email: santiago@ragcorp.example
- 💬 Discord: TODO
- 🐛 Issues: [GitHub Issues](https://github.com/SaintWyss/rag-corp/issues)
