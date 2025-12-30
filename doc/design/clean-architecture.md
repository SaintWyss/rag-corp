# Clean Architecture Implementation

**Project:** RAG Corp  
**Last Updated:** 2025-12-30

This document explains how RAG Corp implements Clean Architecture principles.

---

## Table of Contents

1. [What is Clean Architecture?](#what-is-clean-architecture)
2. [Core Principles](#core-principles)
3. [Layer Structure](#layer-structure)
4. [Dependency Rules](#dependency-rules)
5. [Implementation in RAG Corp](#implementation-in-rag-corp)
6. [Benefits](#benefits)
7. [Migration Strategy](#migration-strategy)

---

## What is Clean Architecture?

Clean Architecture (by Robert C. Martin) is a software design philosophy that emphasizes:

- **Separation of Concerns:** Each layer has a single, well-defined purpose
- **Dependency Inversion:** High-level policy doesn't depend on low-level details
- **Testability:** Business logic can be tested without frameworks
- **Framework Independence:** Core logic doesn't know about FastAPI, PostgreSQL, etc.

### The Dependency Rule

> **Source code dependencies must point inward toward higher-level policies.**

Outer layers (frameworks, databases) depend on inner layers (business logic).  
Inner layers NEVER depend on outer layers.

---

## Core Principles

### 1. Dependency Inversion Principle (DIP)

❌ **Before (Tight Coupling):**
```python
# routes.py directly imports concrete implementation
from app.store import Store  # Concrete class

@router.post("/ask")
async def answer_query(request):
    store = Store()  # Hard dependency
    results = store.search(request.query)
    # ...
```

✅ **After (Loose Coupling via Protocols):**
```python
# Domain layer defines interface
class DocumentRepository(Protocol):
    def search_similar(self, embedding, limit) -> list[Chunk]: ...

# Use case depends on abstraction
class AnswerQueryUseCase:
    def __init__(self, repository: DocumentRepository):  # Protocol, not concrete
        self.repository = repository

# Infrastructure layer implements
class PostgresDocumentRepository:  # Satisfies protocol
    def search_similar(self, embedding, limit):
        # PostgreSQL-specific code
```

### 2. Single Responsibility Principle (SRP)

Each component has ONE reason to change:

| Component | Responsibility | Changes When |
|-----------|----------------|--------------|
| `Document` entity | Represent document data | Business rules change |
| `PostgresDocumentRepository` | Persist to PostgreSQL | Database schema changes |
| `AnswerQueryUseCase` | Orchestrate RAG workflow | Business process changes |
| `/ask` endpoint | Handle HTTP requests | API contract changes |

### 3. Open/Closed Principle (OCP)

Open for extension, closed for modification.

```python
# Adding new LLM provider doesn't modify existing code
class GeminiLLMService: ...  # Existing
class OpenAILLMService: ...  # New (no changes to use case)

# Use case remains unchanged
class AnswerQueryUseCase:
    def __init__(self, llm_service: LLMService):  # Protocol accepts both
        self.llm_service = llm_service
```

---

## Layer Structure

RAG Corp has 4 layers (inside → outside):

```
┌─────────────────────────────────────────┐
│   1. Domain Layer (Entities + Protocols) │  ← Core Business Logic
└─────────────────────────────────────────┘
            ↑
┌─────────────────────────────────────────┐
│   2. Application Layer (Use Cases)       │  ← Business Workflows
└─────────────────────────────────────────┘
            ↑
┌─────────────────────────────────────────┐
│   3. Infrastructure Layer (Adapters)     │  ← Framework Implementations
└─────────────────────────────────────────┘
            ↑
┌─────────────────────────────────────────┐
│   4. API Layer (HTTP Endpoints)          │  ← Entry Points
└─────────────────────────────────────────┘
```

### Layer 1: Domain

**Location:** `services/rag-api/app/domain/`  
**Purpose:** Business entities and contracts  
**Dependencies:** NONE (pure Python)

```
domain/
├── entities.py         # Document, Chunk, QueryResult dataclasses
├── repositories.py     # DocumentRepository Protocol
└── services.py         # EmbeddingService, LLMService Protocols
```

**Key Rule:** Domain layer has ZERO imports from outer layers.

```python
# entities.py
from dataclasses import dataclass

@dataclass
class Document:
    """Pure business entity (no framework coupling)."""
    id: str
    content: str
    chunks: list["Chunk"]
    metadata: dict

# repositories.py
from typing import Protocol

class DocumentRepository(Protocol):
    """Contract for persistence (not implementation)."""
    def save(self, document: Document) -> None: ...
```

### Layer 2: Application

**Location:** `services/rag-api/app/application/use_cases/`  
**Purpose:** Business workflows and orchestration  
**Dependencies:** Domain layer only

```
application/
└── use_cases/
    ├── answer_query.py       # RAG Q&A workflow
    ├── ingest_document.py    # Document ingestion (planned)
    └── search_chunks.py      # Semantic search (planned)
```

**Key Rule:** Use cases depend on protocols, not implementations.

```python
# answer_query.py
from app.domain.repositories import DocumentRepository  # Protocol ✅
from app.domain.services import EmbeddingService, LLMService  # Protocols ✅
# NO imports from infrastructure or API layers ❌

class AnswerQueryUseCase:
    def __init__(
        self,
        repository: DocumentRepository,  # Abstraction
        embedding_service: EmbeddingService,  # Abstraction
        llm_service: LLMService  # Abstraction
    ):
        # Use case doesn't know about PostgreSQL or Gemini
        self.repository = repository
        self.embedding_service = embedding_service
        self.llm_service = llm_service
    
    def execute(self, input: AnswerQueryInput) -> QueryResult:
        # Pure business logic (framework-agnostic)
        query_embedding = self.embedding_service.embed(input.query)
        chunks = self.repository.search_similar(query_embedding, limit=5)
        context = self._build_context(chunks)
        answer = self.llm_service.generate(prompt, context)
        return QueryResult(query=input.query, answer=answer, chunks=chunks)
```

### Layer 3: Infrastructure

**Location:** `services/rag-api/app/infrastructure/`  
**Purpose:** Implement domain protocols with concrete technologies  
**Dependencies:** Domain layer (implements protocols)

```
infrastructure/
├── repositories/
│   ├── postgres_document_repo.py   # DocumentRepository impl
│   └── mongo_document_repo.py      # Alternative impl (future)
├── services/
│   ├── google_embedding_service.py # EmbeddingService impl
│   ├── google_llm_service.py       # LLMService impl
│   └── openai_llm_service.py       # Alternative impl (future)
└── text/
    └── chunker.py                  # Utility (moved from root)
```

**Key Rule:** Infrastructure implements protocols, doesn't modify them.

```python
# google_llm_service.py
import google.generativeai as genai  # External dependency
from app.domain.services import LLMService  # Protocol

class GoogleLLMService:
    """Adapter: Implements LLMService using Gemini API."""
    
    def __init__(self, api_key: str):
        genai.configure(api_key=api_key)
        self.model = genai.GenerativeModel("gemini-1.5-flash")
    
    def generate(self, prompt: str) -> str:
        """Satisfy LLMService protocol."""
        response = self.model.generate_content(prompt)
        return response.text
```

### Layer 4: API

**Location:** `services/rag-api/app/routes.py`, `main.py`  
**Purpose:** HTTP endpoints and framework integration  
**Dependencies:** Application layer (uses use cases)

```python
# routes.py
from fastapi import APIRouter, Depends
from app.application.use_cases.answer_query import AnswerQueryUseCase
from app.container import get_answer_query_use_case

router = APIRouter()

@router.post("/ask")
async def answer_query(
    request: AnswerQueryRequest,
    use_case: AnswerQueryUseCase = Depends(get_answer_query_use_case)
) -> AnswerQueryResponse:
    """
    R: HTTP adapter for AnswerQueryUseCase.
    Converts HTTP request → domain input → domain output → HTTP response.
    """
    # 1. Convert HTTP to domain
    input_dto = AnswerQueryInput(query=request.query)
    
    # 2. Execute business logic (framework-agnostic)
    result = use_case.execute(input_dto)
    
    # 3. Convert domain to HTTP
    return AnswerQueryResponse(
        answer=result.answer,
        sources=[...]
    )
```

---

## Dependency Rules

### Allowed Dependencies

```
Domain Layer
    ↑ (depends on)
Application Layer
    ↑ (depends on)
Infrastructure Layer
    ↑ (depends on)
API Layer
```

✅ **Allowed:**
- Application → Domain
- Infrastructure → Domain
- API → Application
- API → Infrastructure (for DI container)

❌ **Forbidden:**
- Domain → Application
- Domain → Infrastructure
- Domain → API
- Application → Infrastructure
- Application → API

### Dependency Inversion

Infrastructure depends on domain abstractions:

```python
# Domain defines contract
class DocumentRepository(Protocol):
    def save(self, document: Document) -> None: ...

# Infrastructure implements contract (depends inward)
class PostgresDocumentRepository:
    def save(self, document: Document) -> None:
        # Implementation
```

**NOT the other way around:**

```python
# ❌ WRONG: Domain importing infrastructure
from app.infrastructure.repositories.postgres_document_repo import PostgresDocumentRepository

class Document:
    def save_to_postgres(self):  # ❌ Domain knows about PostgreSQL
        repo = PostgresDocumentRepository()
        repo.save(self)
```

---

## Implementation in RAG Corp

### Complete Flow Example

Let's trace a `/ask` request through all layers:

```python
# 4. API Layer: HTTP entry point
@router.post("/ask")
async def answer_query(
    request: AnswerQueryRequest,  # HTTP DTO
    use_case: AnswerQueryUseCase = Depends(get_answer_query_use_case)
):
    # Convert HTTP request to domain input
    input_dto = AnswerQueryInput(query=request.query)
    
    # Delegate to application layer
    result = use_case.execute(input_dto)
    
    # Convert domain output to HTTP response
    return AnswerQueryResponse(answer=result.answer, ...)

# 3. Application Layer: Business workflow
class AnswerQueryUseCase:
    def __init__(
        self,
        repository: DocumentRepository,  # Protocol (domain)
        embedding_service: EmbeddingService,  # Protocol (domain)
        llm_service: LLMService  # Protocol (domain)
    ):
        self.repository = repository
        self.embedding_service = embedding_service
        self.llm_service = llm_service
    
    def execute(self, input: AnswerQueryInput) -> QueryResult:  # Domain entities
        # 3a. Call domain service (via protocol)
        query_embedding = self.embedding_service.embed(input.query)
        
        # 3b. Call domain repository (via protocol)
        chunks = self.repository.search_similar(query_embedding, limit=5)
        
        # 3c. Business logic
        context = self._build_context(chunks)
        
        # 3d. Call domain service (via protocol)
        answer = self.llm_service.generate(prompt, context)
        
        # 3e. Return domain entity
        return QueryResult(query=input.query, answer=answer, chunks=chunks)

# 2. Infrastructure Layer: Concrete implementations
class PostgresDocumentRepository:
    """Implements DocumentRepository protocol."""
    def search_similar(self, embedding, limit):
        # PostgreSQL-specific code (psycopg, SQL)
        ...

class GoogleLLMService:
    """Implements LLMService protocol."""
    def generate(self, prompt):
        # Gemini API-specific code
        ...

# 1. Domain Layer: Entities and protocols
@dataclass
class QueryResult:
    """Business entity (framework-agnostic)."""
    query: str
    answer: str
    chunks: list[Chunk]

class DocumentRepository(Protocol):
    """Contract for persistence (no implementation)."""
    def search_similar(self, embedding, limit) -> list[Chunk]: ...
```

### Dependency Injection Wiring

```python
# container.py
from functools import lru_cache

@lru_cache
def get_document_repository() -> DocumentRepository:
    """Factory: Create infrastructure implementation."""
    return PostgresDocumentRepository(settings.DATABASE_URL)

@lru_cache
def get_embedding_service() -> EmbeddingService:
    """Factory: Create infrastructure implementation."""
    return GoogleEmbeddingService(settings.GEMINI_API_KEY)

@lru_cache
def get_llm_service() -> LLMService:
    """Factory: Create infrastructure implementation."""
    return GoogleLLMService(settings.GEMINI_API_KEY)

def get_answer_query_use_case(
    repository: DocumentRepository = Depends(get_document_repository),
    embedding_service: EmbeddingService = Depends(get_embedding_service),
    llm_service: LLMService = Depends(get_llm_service)
) -> AnswerQueryUseCase:
    """Compose use case with dependencies."""
    return AnswerQueryUseCase(repository, embedding_service, llm_service)
```

---

## Benefits

### 1. Testability

Test business logic WITHOUT starting PostgreSQL or calling Gemini API:

```python
# test_answer_query.py
def test_answer_query_with_no_results():
    # Arrange: Create fake implementations
    fake_repository = FakeDocumentRepository(documents=[])
    fake_embedding = FakeEmbeddingService()
    fake_llm = FakeLLMService()
    
    # Act: Test use case with fakes (no database, no API calls)
    use_case = AnswerQueryUseCase(fake_repository, fake_embedding, fake_llm)
    result = use_case.execute(AnswerQueryInput(query="test"))
    
    # Assert
    assert result.answer == "No relevant documents found."
```

**Result:** Tests run in milliseconds, not seconds.

### 2. Framework Independence

Business logic doesn't know about FastAPI:

```python
# Use case can be called from:
# - FastAPI endpoint
# - CLI script
# - Celery background task
# - Jupyter notebook
# - Unit test

use_case = AnswerQueryUseCase(...)
result = use_case.execute(AnswerQueryInput(query="..."))
```

If we switch from FastAPI to Flask, only API layer changes.

### 3. Database Independence

Swap PostgreSQL for MongoDB without changing use cases:

```python
# Before
repository = PostgresDocumentRepository(...)

# After
repository = MongoDocumentRepository(...)

# Use case remains IDENTICAL
use_case = AnswerQueryUseCase(repository, ...)
```

### 4. Vendor Flexibility

A/B test LLM providers:

```python
# Production: Gemini
llm_service = GoogleLLMService(settings.GEMINI_API_KEY)

# Experiment: OpenAI
llm_service = OpenAILLMService(settings.OPENAI_API_KEY)

# Use case unchanged
use_case = AnswerQueryUseCase(..., llm_service)
```

---

## Migration Strategy

### Phase 1: Foundation (✅ Complete)

- ✅ Create domain layer (entities, protocols)
- ✅ Create infrastructure implementations
- ✅ Create one use case (`AnswerQueryUseCase`)
- ✅ Refactor one endpoint (`/ask`) to use Clean Architecture
- ✅ Keep legacy endpoints for comparison

**Result:** New `/ask` endpoint uses Clean Architecture, old `/query` still works.

### Phase 2: Expand Use Cases (🔄 In Progress)

- [ ] Create `IngestDocumentUseCase`
- [ ] Create `SearchChunksUseCase`
- [ ] Refactor `/ingest/text` endpoint
- [ ] Refactor `/query` endpoint
- [ ] Deprecate legacy `Store` class

**Result:** All endpoints use Clean Architecture.

### Phase 3: Testing & Production (📋 Planned)

- [ ] Add unit tests for all use cases
- [ ] Add integration tests for repositories
- [ ] Add E2E tests for endpoints
- [ ] Deploy to production
- [ ] Monitor performance and quality

---

## Common Questions

### Q: Isn't this overengineered for a small project?

**A:** Clean Architecture scales with complexity. For RAG Corp:
- ✅ Already have 3 external dependencies (PostgreSQL, Gemini embeddings, Gemini LLM)
- ✅ Plan to support multiple LLM providers
- ✅ Need testability for business-critical logic
- ✅ Want flexibility to swap databases/vendors

The overhead is ~3 extra files (entities, protocols, use case) but saves weeks in testing and maintenance.

### Q: Why not use Django or other "all-in-one" frameworks?

**A:** Django couples business logic to framework:
```python
# Django model (violates Clean Architecture)
class Document(models.Model):  # Inherits from Django
    content = models.TextField()  # Database-specific
    
    def search_similar(self, query):
        # Business logic mixed with database queries ❌
```

RAG Corp separates concerns:
```python
# Domain entity (framework-independent)
@dataclass
class Document:  # Pure Python
    content: str
    
# Repository (infrastructure layer)
class PostgresDocumentRepository:
    def search_similar(self, query):
        # Database code isolated ✅
```

### Q: When should I NOT use Clean Architecture?

**A:** Skip Clean Architecture for:
- Prototypes (< 1 week lifespan)
- Single-file scripts
- Projects with 1 developer and no tests

Use Clean Architecture when:
- Multiple developers
- Automated testing required
- Long-term maintenance (> 6 months)
- External dependencies (databases, APIs)

---

## References

- **Clean Architecture Book:** [Robert C. Martin](https://www.amazon.com/Clean-Architecture-Craftsmans-Software-Structure/dp/0134494164)
- **The Clean Architecture Blog Post:** [Uncle Bob](https://blog.cleancoder.com/uncle-bob/2012/08/13/the-clean-architecture.html)
- **Hexagonal Architecture:** [Alistair Cockburn](https://alistair.cockburn.us/hexagonal-architecture/)
- **Python Clean Architecture:** [Cosmic Python](https://www.cosmicpython.com/)

---

**Last Updated:** 2025-12-30  
**Maintainer:** Engineering Team
