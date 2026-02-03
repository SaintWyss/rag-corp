# Patrones de diseño
Este documento resume patrones presentes en el backend con evidencia directa en el código.

## Clean Architecture (Ports & Adapters)
- Capas: Domain, Application, Infrastructure, Interfaces → `apps/backend/app/README.md`.
- Domain no depende de frameworks (ver `apps/backend/app/domain/README.md`).
- Ports (Protocols) → `apps/backend/app/domain/repositories.py` y `apps/backend/app/domain/services.py`.
- Adapters → `apps/backend/app/infrastructure/` (repositorios, servicios, storage, queue).
- ADR: `docs/architecture/adr/ADR-001-clean-architecture.md`.

## Use Case (Application Service)
- Casos de uso en `apps/backend/app/application/usecases/`.
- Ejemplos:
- `apps/backend/app/application/usecases/documents/get_document.py`
- `apps/backend/app/application/usecases/ingestion/ingest_document.py`
- `apps/backend/app/application/usecases/chat/answer_query.py`

## Repository
- Protocolos en `apps/backend/app/domain/repositories.py`.
- Implementaciones Postgres en `apps/backend/app/infrastructure/repositories/postgres/`.
- Implementaciones in-memory en `apps/backend/app/infrastructure/repositories/in_memory/`.

## Adapter (external services)
- Embeddings/LLM: `apps/backend/app/infrastructure/services/`.
- Storage S3-compatible: `apps/backend/app/infrastructure/storage/s3_file_storage.py`.
- Cola RQ: `apps/backend/app/infrastructure/queue/rq_queue.py`.

## Policy (reglas de acceso)
- Workspace policy en `apps/backend/app/domain/workspace_policy.py`.
- Acceso a documentos en `apps/backend/app/identity/access_control.py`.

## Decorator / Retry
- Retry con backoff: `apps/backend/app/infrastructure/services/retry.py`.

## Error Envelope (RFC7807)
- Modelo y factories: `apps/backend/app/crosscutting/error_responses.py`.
- Handlers de exceptions: `apps/backend/app/api/exception_handlers.py`.

## Strategy (configurable)
- Settings centralizados: `apps/backend/app/crosscutting/config.py`.
- Context builder: `apps/backend/app/application/context_builder.py`.

## Singleton / Cache de dependencias
- `get_settings()` con `@lru_cache` en `apps/backend/app/crosscutting/config.py`.
- Container con `@lru_cache` en `apps/backend/app/container.py`.
