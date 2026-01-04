# Índice de Documentación

Portal central de documentación técnica de RAG Corp.

## Arquitectura

| Documento | Descripción |
|-----------|-------------|
| [overview.md](architecture/overview.md) | Visión general de capas y componentes |
| [ADR-001: Clean Architecture](architecture/decisions/ADR-001-clean-architecture.md) | Decisión de adoptar Clean Architecture |
| [ADR-002: pgvector](architecture/decisions/ADR-002-pgvector.md) | Elección de PostgreSQL + pgvector |
| [ADR-003: Google Gemini](architecture/decisions/ADR-003-google-gemini.md) | Selección de proveedor LLM |

## Diseño

| Documento | Descripción |
|-----------|-------------|
| [patterns.md](design/patterns.md) | Patrones implementados (retry, error envelope, etc.) |

## API

| Documento | Descripción |
|-----------|-------------|
| [http-api.md](api/http-api.md) | Referencia de endpoints HTTP |

## Datos

| Documento | Descripción |
|-----------|-------------|
| [postgres-schema.md](data/postgres-schema.md) | Esquema de PostgreSQL + pgvector |

## Runbook

| Documento | Descripción |
|-----------|-------------|
| [local-dev.md](runbook/local-dev.md) | Guía de desarrollo local |
| [testing.md](quality/testing.md) | Estrategia y ejecución de tests |

## Diagramas

| Archivo | Descripción |
|---------|-------------|
| [components.mmd](diagrams/components.mmd) | Diagrama de componentes (Mermaid) |
| [sequence_ingest_ask.mmd](diagrams/sequence_ingest_ask.mmd) | Flujo de ingesta y consulta |
| [boundaries_clean_arch.mmd](diagrams/boundaries_clean_arch.mmd) | Límites de Clean Architecture |

## Auditorías

| Documento | Descripción |
|-----------|-------------|
| [audits/](audits/) | Auditorías de código y arquitectura |
| [reviews/](reviews/) | Pattern maps y revisiones |
