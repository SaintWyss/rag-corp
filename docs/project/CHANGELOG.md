# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
- **Kubernetes manifests** - Production-ready K8s deployment in `infra/k8s/`
  - Deployment, Service, HPA for backend and frontend
  - ConfigMap and Secret management
  - Ingress with TLS support
  - Pod Disruption Budgets for high availability
  - Network Policies (zero-trust)
  - Redis deployment for caching
  - Kustomize configuration
- **Role-Based Access Control (RBAC)** - Fine-grained permissions system
  - Hierarchical roles (admin, user, readonly, ingest-only)
  - Permission-based access control (documents:*, query:*, admin:*)
  - Role inheritance support
  - Configurable via `RBAC_CONFIG` environment variable
- SSE streaming endpoint for LLM responses (`POST /v1/workspaces/{workspace_id}/ask/stream`)
- Redis cache backend for production (auto-detected via `REDIS_URL`)
- Maximal Marginal Relevance (MMR) retrieval for diverse search results
- E2E tests with Playwright
- Configurable Google API health check via `HEALTHCHECK_GOOGLE_ENABLED`
- Database migrations documentation
- Conventional changelog automation

### Changed
- **compose.prod.yaml** - Full observability stack integration
  - Redis always enabled in production
  - Prometheus, Grafana, exporters via `--profile observability`
  - Redis exporter for cache metrics
- Extracted exception handlers from `main.py` to `exception_handlers.py`
- Added coverage threshold (70%) to frontend tests
- Updated documentation index with K8s and RBAC guides

### Fixed
- Health check now respects configuration for Google API verification
- Completed TODO for LLM fallback documentation in ADR-003

## [0.1.0] - 2026-01-01

### Added
- Initial RAG Corp implementation
- Document ingestion with chunking
- Semantic search with pgvector
- Answer generation with Google Gemini
- FastAPI backend with Clean Architecture
- Next.js frontend
- OpenAPI contracts with TypeScript generation
- Prometheus metrics and structured logging
- API key authentication with scopes
- Rate limiting with token bucket algorithm
