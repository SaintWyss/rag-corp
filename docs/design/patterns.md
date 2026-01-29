# Design Patterns — RAG Corp v6

**Project:** RAG Corp  
**Last Updated:** 2026-01-24  
**Status:** Active

---

## TL;DR

Este documento describe los patrones de diseño **actualmente implementados** en RAG Corp. Los patrones están verificados con evidencia del código.

---

## Patrones Arquitectónicos

### Clean Architecture (Ports & Adapters)

**Qué:** Separación en capas con dependencias hacia adentro.

```
┌──────────────────────────────────────────┐
│  API Layer (Presentation)                │
│  FastAPI controllers, middleware, auth   │
├──────────────────────────────────────────┤
│  Application Layer (Use Cases)           │
│  Orchestration, policies, DTOs           │
├──────────────────────────────────────────┤
│  Domain Layer (Core Business)            │
│  Entities, Ports (Protocols)             │
├──────────────────────────────────────────┤
│  Infrastructure Layer (Adapters)         │
│  PostgreSQL, Google APIs, cache          │
└──────────────────────────────────────────┘
```

**Ubicación:**
- Domain: `apps/backend/app/domain/`
- Application: `apps/backend/app/application/`
- Infrastructure: `apps/backend/app/infrastructure/`
- API: `apps/backend/app/` (main.py, routes.py, etc.)

**Evidencia:** 
- `apps/backend/app/domain/entities/` no importa FastAPI ni SQLAlchemy
- `apps/backend/app/domain/repositories.py` define Protocols (interfaces)

**ADR:** [ADR-001-clean-architecture.md](../architecture/decisions/ADR-001-clean-architecture.md)

---

## Patrones de Diseño Implementados

### 1. Port/Adapter (Hexagonal)

**Qué:** Interfaces (Protocols) en domain, implementaciones en infrastructure.

**Ubicación:**
- Ports: `domain/repositories.py`, `domain/services.py`
- Adapters: `infrastructure/repositories/postgres_*.py`
- Adapters: `infrastructure/services/google_*.py`

**Ejemplo:**
```python
# Port (domain/repositories.py)
class DocumentRepository(Protocol):
    def get_by_id(self, doc_id: UUID) -> Optional[Document]: ...

# Adapter (infrastructure/repositories/postgres_document_repo.py)
class PostgresDocumentRepository:
    def get_by_id(self, doc_id: UUID) -> Optional[Document]:
        # Implementación con SQLAlchemy
```

**Beneficio:** Cambiar PostgreSQL por otro storage sin tocar domain/application.

---

### 2. Repository

**Qué:** Abstracción sobre persistencia de datos.

**Ubicación:**
- Interface: `domain/repositories.py` → `DocumentRepository`, `WorkspaceRepository`
- Implementación: `infrastructure/repositories/postgres_document_repo.py`

**Beneficio:** Domain no conoce SQL ni pgvector.

---

### 3. Use Case (Application Service)

**Qué:** Orquestación de un flujo de negocio específico.

**Ubicación:**
- `application/use_cases/answer_query.py` → `AnswerQueryUseCase`
- `application/use_cases/ingest_document.py` → `IngestDocumentUseCase`
- `application/use_cases/search_chunks.py` → `SearchChunksUseCase`
- `application/use_cases/workspace_*.py` → Operaciones de workspace

**Beneficio:** Un punto de entrada claro para cada operación.

---

### 4. Policy (Domain Service)

**Qué:** Lógica de autorización centralizada.

**Ubicación:**
- `domain/policies/workspace_policy.py` → `WorkspacePolicy`

**Ejemplo:**
```python
class WorkspacePolicy:
    def can_read(self, actor: User, workspace: Workspace, acl: List[AclEntry]) -> bool:
        if actor.role == "admin":
            return True
        if workspace.owner_user_id == actor.id:
            return True
        # ...
```

**Beneficio:** Reglas de acceso en un solo lugar, testeable unitariamente.

---

### 5. Decorator (Retry with Backoff)

**Qué:** Agrega retry con backoff exponencial + jitter alrededor de llamadas externas.

**Ubicación:**
- `infrastructure/services/retry.py` → `create_retry_decorator()`
- Usado en `google_embedding_service.py` y `google_llm_service.py`

**Ejemplo:**
```python
@retry(max_attempts=3, backoff_base=1.0, jitter=0.5)
async def embed(self, text: str) -> List[float]:
    return await self._client.embed(text)
```

**Beneficio:** Resiliencia sin acoplar la lógica de retry al negocio.

---

### 6. Facade (Error Envelope)

**Qué:** Interface unificada para manejo de errores HTTP (RFC 7807).

**Ubicación:**
- `crosscutting/exceptions.py` → `ErrorResponse`, `RAGError` y derivados
- `main.py` → exception handlers

**Ejemplo respuesta:**
```json
{
  "type": "https://api.ragcorp.local/errors/not-found",
  "title": "Not Found",
  "status": 404,
  "detail": "Document not found",
  "code": "NOT_FOUND"
}
```

**Beneficio:** Respuestas de error consistentes para clientes y logs.

---

### 7. Strategy (Config-Driven Behavior)

**Qué:** Comportamiento configurable via settings.

**Ubicación:**
- `crosscutting/config.py` → `Settings`
- Settings como `CHUNK_SIZE`, `MAX_CONTEXT_CHARS`, `PROMPT_VERSION`
- `application/context_builder.py` usa `MAX_CONTEXT_CHARS` como policy

**Beneficio:** Cambiar comportamiento sin tocar código.

---

### 8. Singleton (via lru_cache)

**Qué:** Una sola instancia de servicios costosos.

**Ubicación:**
- `crosscutting/config.py` → `@lru_cache def get_settings()`
- `crosscutting/container.py` → `@lru_cache` para repositorios y servicios

**Ejemplo:**
```python
@lru_cache
def get_document_repository() -> DocumentRepository:
    return PostgresDocumentRepository(get_pool())
```

**Beneficio:** Evita recrear conexiones/clientes.

---

### 9. Dependency Injection Container

**Qué:** Wiring centralizado de dependencias.

**Ubicación:**
- `crosscutting/container.py` → Factory functions para dependencias
- FastAPI `Depends()` para inyección en routes

**Ejemplo:**
```python
# container.py
def get_answer_query_use_case() -> AnswerQueryUseCase:
    return AnswerQueryUseCase(
        chunk_repo=get_chunk_repository(),
        embedding_service=get_embedding_service(),
        llm_service=get_llm_service(),
    )

# routes.py
@router.post("/ask")
async def ask(
    use_case: AnswerQueryUseCase = Depends(get_answer_query_use_case)
):
```

**Beneficio:** Componentes desacoplados y testeable con mocks.

---

### 10. Custom Hook (Frontend Facade)

**Qué:** Encapsula lógica de API en un hook React reutilizable.

**Ubicación:**
- `apps/frontend/src/hooks/useRagAsk.ts`
- `apps/frontend/src/hooks/useDocuments.ts`

**Beneficio:** Componentes UI desacoplados de fetch logic.

---

### 11. Error Boundary (React)

**Qué:** Captura errores de render para mostrar fallback UI.

**Ubicación:**
- `apps/frontend/app/error.tsx`

**Beneficio:** App no crashea por errores de componentes.

---

## Anti-Patterns Evitados

| Anti-Pattern | Cómo se evita |
|--------------|---------------|
| God Class | Use cases pequeños y focalizados |
| Leaky Abstraction | Domain no importa psycopg/fastapi |
| Hardcoded Config | Todo en `config.py` via env vars |
| Scattered Error Handling | Centralizado en `exceptions.py` |
| Callback Hell | async/await consistente |
| Anemic Domain | Policies y business rules en Domain |

---

## Patrones NO implementados (Out of Scope v6)

Los siguientes patrones se mencionan a veces pero **NO están en v6**:

| Patrón | Razón |
|--------|-------|
| Observer/PubSub | No hay eventos cross-service |
| CQRS | Mismo modelo para read/write |
| Event Sourcing | Solo auditoría append-only |
| Saga | No hay transacciones distribuidas |

---

## Referencias

- [Clean Architecture - Robert Martin](https://blog.cleancoder.com/uncle-bob/2012/08/13/the-clean-architecture.html)
- [Hexagonal Architecture](https://alistair.cockburn.us/hexagonal-architecture/)
- [RFC 7807 - Problem Details for HTTP APIs](https://tools.ietf.org/html/rfc7807)
- ADR-001: `docs/architecture/decisions/ADR-001-clean-architecture.md`
