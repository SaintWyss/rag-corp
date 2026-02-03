# Panorama de arquitectura
Documento de alto nivel. El detalle técnico vive en los README hoja del backend.

## Fuente de verdad
- ADRs → `docs/architecture/adr/`
- Mapa backend → `apps/backend/app/README.md`
- HTTP (routers + schemas) → `apps/backend/app/interfaces/api/http/README.md`
- Use cases → `apps/backend/app/application/usecases/README.md`
- Infraestructura → `apps/backend/app/infrastructure/README.md`
- Worker → `apps/backend/app/worker/README.md`

## Componentes principales (backend)
| Componente | Evidencia |
| :-- | :-- |
| API HTTP (FastAPI) | `apps/backend/app/api/main.py` |
| Routers v1 (HTTP) | `apps/backend/app/interfaces/api/http/router.py` |
| Worker RQ | `apps/backend/app/worker/worker.py` |
| Cola (RQ + Redis) | `apps/backend/app/infrastructure/queue/rq_queue.py` |
| Pool DB | `apps/backend/app/infrastructure/db/pool.py` |
| Repositorios Postgres | `apps/backend/app/infrastructure/repositories/postgres/README.md` |
| Storage S3-compatible | `apps/backend/app/infrastructure/storage/s3_file_storage.py` |
| Servicios LLM/Embeddings | `apps/backend/app/infrastructure/services/README.md` |
| Prompts versionados | `apps/backend/app/prompts/README.md` |

## Capas (Clean Architecture)
- Domain → `apps/backend/app/domain/README.md`
- Application → `apps/backend/app/application/README.md`
- Infrastructure → `apps/backend/app/infrastructure/README.md`
- Interfaces → `apps/backend/app/interfaces/README.md`

## Flujos principales (puntos de entrada)
- Ingesta de documentos → `apps/backend/app/application/usecases/ingestion/README.md`
- Lectura/actualización de documentos → `apps/backend/app/application/usecases/documents/README.md`
- Chat/RAG → `apps/backend/app/application/usecases/chat/README.md`
- Workspaces → `apps/backend/app/application/usecases/workspace/README.md`

## Versionado de rutas
- Prefijo canónico `/v1` en `apps/backend/app/api/main.py`.
- Alias `/api/v1` en `apps/backend/app/api/versioning.py`.
