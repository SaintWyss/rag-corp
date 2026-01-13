# Design Patterns - RAG Corp

**Última actualización**: 2026-01-12

Este documento describe los patrones de diseño aplicados en el proyecto y dónde encontrarlos.

---

## Patrones Arquitectónicos

### Clean Architecture (Ports & Adapters)

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

**Ubicación**:
- Domain: `backend/app/domain/`
- Application: `backend/app/application/`
- Infrastructure: `backend/app/infrastructure/`
- API: `backend/app/` (main.py, routes.py, etc.)

---

## Patrones de Diseño

### 1. Port/Adapter (Hexagonal)

**Qué**: Interfaces (Protocols) en domain, implementaciones en infrastructure.

**Dónde**:
- Ports: `domain/repositories.py`, `domain/services.py`
- Adapters: `infrastructure/repositories/postgres_document_repo.py`
- Adapters: `infrastructure/services/google_*.py`

**Beneficio**: Permite cambiar PostgreSQL por otro storage sin tocar domain/application.

---

### 2. Repository

**Qué**: Abstracción sobre persistencia de datos.

**Dónde**:
- Interface: `domain/repositories.py` → `DocumentRepository(Protocol)`
- Implementación: `infrastructure/repositories/postgres_document_repo.py`

**Beneficio**: Domain no conoce SQL ni pgvector.

---

### 3. Use Case (Application Service)

**Qué**: Orquestación de un flujo de negocio específico.

**Dónde**:
- `application/use_cases/answer_query.py` → `AnswerQueryUseCase`
- `application/use_cases/ingest_document.py` → `IngestDocumentUseCase`
- `application/use_cases/search_chunks.py` → `SearchChunksUseCase`

**Beneficio**: Un punto de entrada claro para cada operación.

---

### 4. Decorator (Retry)

**Qué**: Agrega retry con backoff + jitter alrededor de llamadas externas.

**Dónde**:
- `infrastructure/services/retry.py` → `create_retry_decorator()`
- Usado en `google_embedding_service.py` y `google_llm_service.py`

**Beneficio**: Resiliencia sin acoplar la logica de retry al negocio.

---

### 5. Facade (Error Envelope)

**Qué**: Interface unificada para manejo de errores HTTP.

**Dónde**:
- `exceptions.py` → `ErrorResponse`, `RAGError` y derivados
- `main.py` → exception handlers para responder en un formato consistente

**Beneficio**: Respuestas de error consistentes para clientes y logs.

---

### 6. Strategy (implícito en Config)

**Qué**: Comportamiento configurable via settings.

**Dónde**:
- `config.py` → `Settings` con `CHUNK_SIZE`, `MAX_CONTEXT_CHARS`, `PROMPT_VERSION`
- `context_builder.py` usa `MAX_CONTEXT_CHARS` como policy

**Beneficio**: Cambiar comportamiento sin tocar código.

---

### 7. Singleton (via lru_cache)

**Qué**: Una sola instancia de servicios costosos.

**Dónde**:
- `config.py` → `@lru_cache def get_settings()`
- `container.py` → `@lru_cache` para repositorios y servicios

**Beneficio**: Evita recrear conexiones/clientes.

---

### 8. Custom Hook (Frontend Facade)

**Qué**: Encapsula lógica de API en un hook reutilizable.

**Dónde**:
- `frontend/app/hooks/useRagAsk.ts`

**Beneficio**: Componentes UI desacoplados de fetch logic.

---

### 9. Error Boundary (React)

**Qué**: Captura errores de render para mostrar fallback UI.

**Dónde**:
- `frontend/app/error.tsx`

**Beneficio**: App no crashea por errores de componentes.

---

## Anti-Patterns Evitados

| Anti-Pattern | Cómo se evita |
|--------------|---------------|
| God Class | Use cases pequeños y focalizados |
| Leaky Abstraction | Domain no importa psycopg/fastapi |
| Hardcoded Config | Todo en `config.py` via env vars |
| Scattered Error Handling | Centralizado en `error_responses.py` |
| Callback Hell | async/await consistente |

---

## Referencias

- [Clean Architecture - Robert Martin](https://blog.cleancoder.com/uncle-bob/2012/08/13/the-clean-architecture.html)
- [Hexagonal Architecture](https://alistair.cockburn.us/hexagonal-architecture/)
- [RFC 7807 - Problem Details for HTTP APIs](https://tools.ietf.org/html/rfc7807)

---

**Generado desde**: `doc/reviews/PATTERN_MAP_2026-01-03_2059_-0300.md`
