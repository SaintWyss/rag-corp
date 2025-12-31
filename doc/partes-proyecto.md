# Partes del Proyecto y Responsabilidades

Objetivo: dividir el repo en partes claras para trabajar por secciones.

## 1) Frontend (UI)
- Ruta: `apps/web`
- Responsabilidad: interfaz de usuario para preguntar y visualizar respuestas.
- Qué hace: renderiza la UI, llama al backend vía `/v1/*` (proxy en `apps/web/next.config.ts`), muestra respuesta y fuentes.
- Archivos clave: `apps/web/app/page.tsx`, `apps/web/app/layout.tsx`, `apps/web/next.config.ts`.

## 2) Backend API (FastAPI)
- Ruta: `services/rag-api`
- Responsabilidad: expone endpoints HTTP para ingesta, búsqueda y RAG.
- Qué hace: recibe requests, valida con Pydantic, coordina casos de uso y servicios.
- Archivos clave: `services/rag-api/app/main.py`, `services/rag-api/app/routes.py`.

## 3) Dominio (Modelos y contratos internos)
- Ruta: `services/rag-api/app/domain`
- Responsabilidad: entidades y contratos (interfaces) del core.
- Qué hace: define `Document`, `Chunk`, `QueryResult` y protocolos para repositorios/servicios.
- Archivos clave: `services/rag-api/app/domain/entities.py`, `services/rag-api/app/domain/repositories.py`, `services/rag-api/app/domain/services.py`.

## 4) Aplicación (Casos de uso)
- Ruta: `services/rag-api/app/application`
- Responsabilidad: orquestar el flujo de negocio.
- Qué hace: ejecuta la lógica RAG: embed → retrieve → generate.
- Archivos clave: `services/rag-api/app/application/use_cases/answer_query.py`.

## 5) Infraestructura (DB + Servicios externos)
- Ruta: `services/rag-api/app/infrastructure`
- Responsabilidad: implementaciones concretas de repositorios y servicios.
- Qué hace: conecta a PostgreSQL + pgvector, llama a Gemini para embeddings/LLM.
- Archivos clave: `services/rag-api/app/infrastructure/repositories/postgres_document_repo.py`, `services/rag-api/app/infrastructure/services/google_embedding_service.py`, `services/rag-api/app/infrastructure/services/google_llm_service.py`.

## 6) Persistencia (DB Schema)
- Ruta: `infra/postgres`
- Responsabilidad: definir el esquema de base de datos.
- Qué hace: crea tablas `documents` y `chunks` + índice vectorial.
- Archivos clave: `infra/postgres/init.sql`.

## 7) Contratos compartidos FE/BE
- Ruta: `packages/contracts`
- Responsabilidad: contratos OpenAPI y cliente TypeScript generado.
- Qué hace: exporta OpenAPI desde backend y genera cliente para frontend.
- Archivos clave: `packages/contracts/openapi.json`, `packages/contracts/src/generated.ts`, `packages/contracts/orval.config.ts`.

## 8) Documentación
- Ruta: `doc`
- Responsabilidad: referencia técnica, arquitectura, runbook y calidad.
- Qué hace: describe flujos, decisiones y guías de ejecución.
- Archivos clave: `doc/README.md`, `doc/architecture/overview.md`, `doc/runbook/local-dev.md`.

## 9) Orquestación/DevOps local
- Ruta: raíz del repo
- Responsabilidad: levantar servicios y tareas monorepo.
- Qué hace: define Docker Compose, scripts y tareas pnpm/turbo.
- Archivos clave: `compose.yaml`, `package.json`, `turbo.json`, `pnpm-workspace.yaml`.

