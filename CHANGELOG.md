# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
- SSE streaming endpoint for LLM responses (`POST /v1/ask/stream`)
- Redis cache backend for production (auto-detected via `REDIS_URL`)
- Maximal Marginal Relevance (MMR) retrieval for diverse search results
- E2E tests with Playwright
- Configurable Google API health check via `HEALTHCHECK_GOOGLE_ENABLED`
- Database migrations documentation
- Conventional changelog automation

### Changed
- Extracted exception handlers from `main.py` to `exception_handlers.py`
- Integrated observability stack as Docker Compose profiles
- Added coverage threshold (70%) to frontend tests

### Fixed
- Health check now respects configuration for Google API verification

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
