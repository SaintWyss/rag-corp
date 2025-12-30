# Design Patterns

**Project:** RAG Corp  
**Last Updated:** 2025-12-30

This document describes the key design patterns used in RAG Corp and provides implementation examples.

---

## Table of Contents

1. [Repository Pattern](#repository-pattern)
2. [Use Case Pattern](#use-case-pattern)
3. [Strategy Pattern](#strategy-pattern)
4. [Dependency Injection](#dependency-injection)
5. [Protocol-Based Design](#protocol-based-design)
6. [Factory Pattern](#factory-pattern)

---

## Repository Pattern

### Purpose
Abstract data persistence and retrieval logic from business logic.

### Structure

```python
# Domain layer: Define interface
from typing import Protocol

class DocumentRepository(Protocol):
    """
    Name: DocumentRepository
    Responsibilities:
    - Define contract for document persistence
    - Provide vector similarity search interface
    Collaborators: Document, Chunk entities
    """
    
    def save(self, document: Document) -> None:
        """Persist a document with its chunks and embeddings."""
        ...
    
    def search_similar(
        self, 
        embedding: list[float], 
        limit: int = 5
    ) -> list[Chunk]:
        """Find chunks with embeddings similar to query embedding."""
        ...
    
    def get_by_id(self, doc_id: str) -> Document | None:
        """Retrieve document by ID."""
        ...
```

### Implementation

```python
# Infrastructure layer: Concrete implementation
import psycopg
from psycopg.rows import dict_row

class PostgresDocumentRepository:
    """
    Name: PostgresDocumentRepository
    Responsibilities:
    - Implement DocumentRepository using PostgreSQL + pgvector
    - Manage database connections and transactions
    - Execute vector similarity queries with IVFFlat index
    Collaborators: psycopg, pgvector extension
    """
    
    def __init__(self, connection_string: str):
        self.connection_string = connection_string
    
    def save(self, document: Document) -> None:
        """R: Persist document chunks with embeddings to PostgreSQL."""
        with psycopg.connect(self.connection_string) as conn:
            with conn.cursor() as cur:
                for chunk in document.chunks:
                    cur.execute(
                        """
                        INSERT INTO chunks (doc_id, chunk_index, content, embedding)
                        VALUES (%s, %s, %s, %s)
                        """,
                        (
                            document.id,
                            chunk.index,
                            chunk.content,
                            chunk.embedding
                        )
                    )
                conn.commit()
    
    def search_similar(
        self, 
        embedding: list[float], 
        limit: int = 5
    ) -> list[Chunk]:
        """R: Use pgvector cosine similarity to find top-N chunks."""
        with psycopg.connect(self.connection_string) as conn:
            with conn.cursor(row_factory=dict_row) as cur:
                cur.execute(
                    """
                    SELECT id, doc_id, chunk_index, content, embedding,
                           1 - (embedding <=> %s::vector) AS similarity
                    FROM chunks
                    ORDER BY embedding <=> %s::vector
                    LIMIT %s
                    """,
                    (embedding, embedding, limit)
                )
                rows = cur.fetchall()
                
                return [
                    Chunk(
                        id=row["id"],
                        doc_id=row["doc_id"],
                        index=row["chunk_index"],
                        content=row["content"],
                        embedding=row["embedding"],
                        similarity=row["similarity"]
                    )
                    for row in rows
                ]
```

### Benefits

✅ **Testability:** Easy to mock for unit tests
```python
# Test with fake repository
class FakeDocumentRepository:
    def __init__(self):
        self.documents = {}
    
    def save(self, document: Document) -> None:
        self.documents[document.id] = document
    
    def search_similar(self, embedding, limit=5):
        # Return test fixtures
        return [...]
```

✅ **Flexibility:** Swap implementations without changing business logic
```python
# Switch from PostgreSQL to MongoDB
repository = MongoDocumentRepository(mongo_uri)
use_case = AnswerQueryUseCase(repository, embedding_service, llm_service)
```

✅ **Separation of Concerns:** Domain logic independent of storage details

---

## Use Case Pattern

### Purpose
Encapsulate complete business workflows as single-responsibility classes.

### Structure

```python
from dataclasses import dataclass

# Input DTO
@dataclass(frozen=True)
class AnswerQueryInput:
    """Immutable input for AnswerQuery use case."""
    query: str
    limit: int = 5

# Output is already defined (QueryResult entity)

class AnswerQueryUseCase:
    """
    Name: AnswerQueryUseCase
    Responsibilities:
    - Orchestrate RAG workflow (embed → retrieve → generate)
    - Coordinate between repository and services
    - Return QueryResult with answer and sources
    Collaborators:
    - DocumentRepository (data access)
    - EmbeddingService (query embedding)
    - LLMService (answer generation)
    Notes:
    - Framework-agnostic (no FastAPI coupling)
    - Pure business logic (testable)
    """
    
    def __init__(
        self,
        repository: DocumentRepository,
        embedding_service: EmbeddingService,
        llm_service: LLMService
    ):
        self.repository = repository
        self.embedding_service = embedding_service
        self.llm_service = llm_service
    
    def execute(self, input: AnswerQueryInput) -> QueryResult:
        """Execute RAG workflow."""
        # 1. Embed query
        query_embedding = self.embedding_service.embed(input.query)
        
        # 2. Retrieve similar chunks
        chunks = self.repository.search_similar(
            query_embedding, 
            limit=input.limit
        )
        
        if not chunks:
            return QueryResult(
                query=input.query,
                answer="No relevant documents found.",
                chunks=[]
            )
        
        # 3. Build context from retrieved chunks
        context = "\n\n".join(
            f"[Document {chunk.doc_id}, Part {chunk.index}]\n{chunk.content}"
            for chunk in chunks
        )
        
        # 4. Generate answer with LLM
        prompt = f"""Answer the following question based on the provided context.

Context:
{context}

Question: {input.query}

Answer:"""
        
        answer = self.llm_service.generate(prompt)
        
        return QueryResult(
            query=input.query,
            answer=answer,
            chunks=chunks
        )
```

### Usage in API Layer

```python
# routes.py
from fastapi import APIRouter, Depends

router = APIRouter()

@router.post("/ask")
async def answer_query(
    request: AnswerQueryRequest,
    use_case: AnswerQueryUseCase = Depends(get_answer_query_use_case)
) -> AnswerQueryResponse:
    """
    R: HTTP endpoint adapter for AnswerQueryUseCase.
    Converts HTTP request → Input DTO → Use Case → HTTP response.
    """
    # Convert HTTP request to domain input
    input_dto = AnswerQueryInput(query=request.query)
    
    # Execute business logic
    result = use_case.execute(input_dto)
    
    # Convert domain output to HTTP response
    return AnswerQueryResponse(
        answer=result.answer,
        sources=[
            SourceReference(
                doc_id=chunk.doc_id,
                chunk_index=chunk.index,
                content=chunk.content[:200],
                similarity=chunk.similarity
            )
            for chunk in result.chunks
        ]
    )
```

### Benefits

✅ **Single Responsibility:** One use case = one workflow  
✅ **Testability:** No HTTP/framework coupling  
✅ **Reusability:** Can be called from CLI, Celery tasks, tests  
✅ **Clear Intent:** Use case name describes business goal

---

## Strategy Pattern

### Purpose
Define a family of interchangeable algorithms.

### Example: LLM Providers

```python
# Domain layer: Define interface
from typing import Protocol

class LLMService(Protocol):
    """Strategy interface for LLM providers."""
    
    def generate(self, prompt: str, max_tokens: int = 500) -> str:
        """Generate text from prompt."""
        ...

# Infrastructure layer: Multiple strategies

class GoogleLLMService:
    """Strategy: Google Gemini."""
    
    def __init__(self, api_key: str, model: str = "gemini-1.5-flash"):
        import google.generativeai as genai
        genai.configure(api_key=api_key)
        self.model = genai.GenerativeModel(model)
    
    def generate(self, prompt: str, max_tokens: int = 500) -> str:
        response = self.model.generate_content(
            prompt,
            generation_config={"max_output_tokens": max_tokens}
        )
        return response.text

class OpenAILLMService:
    """Strategy: OpenAI GPT."""
    
    def __init__(self, api_key: str, model: str = "gpt-4-turbo"):
        from openai import OpenAI
        self.client = OpenAI(api_key=api_key)
        self.model = model
    
    def generate(self, prompt: str, max_tokens: int = 500) -> str:
        response = self.client.chat.completions.create(
            model=self.model,
            messages=[{"role": "user", "content": prompt}],
            max_tokens=max_tokens
        )
        return response.choices[0].message.content

class AnthropicLLMService:
    """Strategy: Anthropic Claude."""
    
    def __init__(self, api_key: str, model: str = "claude-3-5-sonnet-20241022"):
        from anthropic import Anthropic
        self.client = Anthropic(api_key=api_key)
        self.model = model
    
    def generate(self, prompt: str, max_tokens: int = 500) -> str:
        response = self.client.messages.create(
            model=self.model,
            max_tokens=max_tokens,
            messages=[{"role": "user", "content": prompt}]
        )
        return response.content[0].text
```

### Strategy Selection

```python
# container.py
from functools import lru_cache

@lru_cache
def get_llm_service() -> LLMService:
    """Factory function: select LLM strategy based on config."""
    provider = settings.LLM_PROVIDER  # "gemini" | "openai" | "anthropic"
    
    if provider == "gemini":
        return GoogleLLMService(settings.GEMINI_API_KEY)
    elif provider == "openai":
        return OpenAILLMService(settings.OPENAI_API_KEY)
    elif provider == "anthropic":
        return AnthropicLLMService(settings.ANTHROPIC_API_KEY)
    else:
        raise ValueError(f"Unknown LLM provider: {provider}")
```

### Benefits

✅ **Vendor Flexibility:** Easy A/B testing and migration  
✅ **Runtime Configuration:** Switch providers via env vars  
✅ **Cost Optimization:** Use cheap model for simple queries  
✅ **Fallback Logic:** Retry with different provider on failure

---

## Dependency Injection

### Purpose
Invert control: components receive dependencies instead of creating them.

### Container Pattern

```python
# container.py
from functools import lru_cache
from app.settings import get_settings

# Singleton instances via @lru_cache

@lru_cache
def get_settings():
    """Load configuration once."""
    return Settings()

@lru_cache
def get_document_repository() -> DocumentRepository:
    """R: Create singleton repository instance."""
    settings = get_settings()
    return PostgresDocumentRepository(settings.DATABASE_URL)

@lru_cache
def get_embedding_service() -> EmbeddingService:
    """R: Create singleton embedding service."""
    settings = get_settings()
    return GoogleEmbeddingService(settings.GEMINI_API_KEY)

@lru_cache
def get_llm_service() -> LLMService:
    """R: Create singleton LLM service."""
    settings = get_settings()
    return GoogleLLMService(settings.GEMINI_API_KEY)

def get_answer_query_use_case(
    repository: DocumentRepository = Depends(get_document_repository),
    embedding_service: EmbeddingService = Depends(get_embedding_service),
    llm_service: LLMService = Depends(get_llm_service)
) -> AnswerQueryUseCase:
    """R: Compose use case with injected dependencies."""
    return AnswerQueryUseCase(repository, embedding_service, llm_service)
```

### Usage with FastAPI Depends

```python
# routes.py
from fastapi import Depends

@router.post("/ask")
async def answer_query(
    request: AnswerQueryRequest,
    use_case: AnswerQueryUseCase = Depends(get_answer_query_use_case)
):
    """FastAPI automatically injects dependencies."""
    result = use_case.execute(AnswerQueryInput(query=request.query))
    return AnswerQueryResponse(answer=result.answer)
```

### Testing with DI

```python
# test_answer_query.py
import pytest
from unittest.mock import Mock

def test_answer_query_use_case():
    # Arrange: Create mocks
    mock_repository = Mock(spec=DocumentRepository)
    mock_repository.search_similar.return_value = [
        Chunk(id=1, doc_id="doc1", index=0, content="Python is great")
    ]
    
    mock_embedding = Mock(spec=EmbeddingService)
    mock_embedding.embed.return_value = [0.1, 0.2, ...]
    
    mock_llm = Mock(spec=LLMService)
    mock_llm.generate.return_value = "Python is a programming language."
    
    # Act: Inject mocks
    use_case = AnswerQueryUseCase(mock_repository, mock_embedding, mock_llm)
    result = use_case.execute(AnswerQueryInput(query="What is Python?"))
    
    # Assert
    assert "Python" in result.answer
    mock_repository.search_similar.assert_called_once()
    mock_llm.generate.assert_called_once()
```

### Benefits

✅ **Testability:** Easy to inject mocks  
✅ **Flexibility:** Swap implementations at runtime  
✅ **Decoupling:** Components don't create dependencies  
✅ **Single Responsibility:** Container handles wiring

---

## Protocol-Based Design

### Purpose
Use Python's `typing.Protocol` for structural subtyping (duck typing with type safety).

### Example

```python
from typing import Protocol

# Define protocol (interface)
class EmbeddingService(Protocol):
    """
    Protocol: Any class with these methods satisfies the interface.
    No inheritance required.
    """
    
    def embed(self, text: str) -> list[float]:
        """Convert text to embedding vector."""
        ...
    
    def embed_batch(self, texts: list[str]) -> list[list[float]]:
        """Batch embedding for efficiency."""
        ...

# Implementation 1: Google Gemini
class GoogleEmbeddingService:
    """Satisfies EmbeddingService protocol."""
    
    def embed(self, text: str) -> list[float]:
        # Implementation
        ...
    
    def embed_batch(self, texts: list[str]) -> list[list[float]]:
        # Implementation
        ...

# Implementation 2: OpenAI
class OpenAIEmbeddingService:
    """Also satisfies EmbeddingService protocol (no inheritance)."""
    
    def embed(self, text: str) -> list[float]:
        # Different implementation
        ...
    
    def embed_batch(self, texts: list[str]) -> list[list[float]]:
        # Different implementation
        ...

# Type checker verifies protocol compatibility
def process_text(text: str, service: EmbeddingService) -> list[float]:
    """Accepts any object with embed() method."""
    return service.embed(text)

# Both work!
google_service = GoogleEmbeddingService(...)
openai_service = OpenAIEmbeddingService(...)

process_text("hello", google_service)  # ✅ Type-safe
process_text("hello", openai_service)  # ✅ Type-safe
```

### Benefits

✅ **No Inheritance Required:** Pythonic duck typing  
✅ **Type Safety:** mypy/pyright verify compatibility  
✅ **Flexibility:** Easy to add new implementations  
✅ **Clear Contracts:** Protocol defines expected behavior

---

## Factory Pattern

### Purpose
Centralize object creation logic.

### Example

```python
# container.py
from functools import lru_cache

class ServiceFactory:
    """
    Name: ServiceFactory
    Responsibilities:
    - Create and configure service instances
    - Manage singleton lifecycle
    - Handle dependency wiring
    """
    
    @staticmethod
    @lru_cache
    def create_embedding_service(provider: str) -> EmbeddingService:
        """Factory method: create embedding service based on provider."""
        if provider == "gemini":
            return GoogleEmbeddingService(
                api_key=settings.GEMINI_API_KEY,
                model="text-embedding-004"
            )
        elif provider == "openai":
            return OpenAIEmbeddingService(
                api_key=settings.OPENAI_API_KEY,
                model="text-embedding-3-small"
            )
        else:
            raise ValueError(f"Unknown embedding provider: {provider}")
    
    @staticmethod
    @lru_cache
    def create_repository(db_type: str) -> DocumentRepository:
        """Factory method: create repository based on database type."""
        if db_type == "postgres":
            return PostgresDocumentRepository(settings.DATABASE_URL)
        elif db_type == "mongodb":
            return MongoDocumentRepository(settings.MONGO_URI)
        else:
            raise ValueError(f"Unknown database type: {db_type}")
```

### Benefits

✅ **Centralized Configuration:** All creation logic in one place  
✅ **Easy Testing:** Mock factory for tests  
✅ **Consistent Initialization:** Ensures proper setup

---

## Pattern Combinations

RAG Corp combines these patterns for maximum flexibility:

```python
# Complete example: All patterns working together

# 1. Protocol defines interface (Protocol Pattern)
class DocumentRepository(Protocol):
    def search_similar(self, embedding, limit) -> list[Chunk]: ...

# 2. Strategy implementations
class PostgresDocumentRepository: ...  # Strategy 1
class MongoDocumentRepository: ...     # Strategy 2

# 3. Factory creates instances
@lru_cache
def get_document_repository() -> DocumentRepository:  # Factory Pattern
    return PostgresDocumentRepository(settings.DATABASE_URL)

# 4. Use case receives dependency
class AnswerQueryUseCase:  # Use Case Pattern
    def __init__(self, repository: DocumentRepository):  # DI
        self.repository = repository  # Repository Pattern

# 5. FastAPI wires everything together
@router.post("/ask")
async def answer_query(
    use_case: AnswerQueryUseCase = Depends(get_answer_query_use_case)  # DI
):
    result = use_case.execute(...)
    return result
```

---

## References

- **Gang of Four Patterns:** [Design Patterns Book](https://en.wikipedia.org/wiki/Design_Patterns)
- **Clean Architecture:** [Uncle Bob Martin](https://blog.cleancoder.com/uncle-bob/2012/08/13/the-clean-architecture.html)
- **Python Protocols:** [PEP 544](https://peps.python.org/pep-0544/)
- **Dependency Injection in Python:** [FastAPI Depends](https://fastapi.tiangolo.com/tutorial/dependencies/)

---

**Last Updated:** 2025-12-30  
**Maintainer:** Engineering Team
