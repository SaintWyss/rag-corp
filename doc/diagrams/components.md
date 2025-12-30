# Component Diagram

**Project:** RAG Corp  
**Last Updated:** 2025-12-30

This diagram shows the high-level components of RAG Corp and their relationships.

---

## System Components

```mermaid
graph TB
    subgraph "Client Layer"
        User[👤 User]
        Browser[🌐 Browser]
    end
    
    subgraph "Frontend (Next.js)"
        WebApp[Next.js App<br/>Port 3000]
        UI[UI Components]
        APIClient[API Client]
    end
    
    subgraph "Backend (FastAPI)"
        API[FastAPI Server<br/>Port 8000]
        Routes[HTTP Routes]
        Container[DI Container]
        
        subgraph "Application Layer"
            UseCases[Use Cases<br/>- AnswerQuery<br/>- IngestDocument<br/>- SearchChunks]
        end
        
        subgraph "Domain Layer"
            Entities[Entities<br/>- Document<br/>- Chunk<br/>- QueryResult]
            Protocols[Protocols<br/>- DocumentRepository<br/>- EmbeddingService<br/>- LLMService]
        end
        
        subgraph "Infrastructure Layer"
            Repositories[Repositories<br/>PostgresDocumentRepo]
            Services[Services<br/>GoogleEmbedding<br/>GoogleLLM]
            Utils[Utilities<br/>TextChunker]
        end
    end
    
    subgraph "Data Layer"
        DB[(PostgreSQL 16<br/>+ pgvector)]
    end
    
    subgraph "External Services"
        Gemini[Google Gemini API<br/>- text-embedding-004<br/>- gemini-1.5-flash]
    end
    
    %% Client connections
    User --> Browser
    Browser --> WebApp
    
    %% Frontend connections
    WebApp --> UI
    WebApp --> APIClient
    APIClient -->|HTTP REST| API
    
    %% Backend flow
    API --> Routes
    Routes --> Container
    Container --> UseCases
    UseCases --> Protocols
    Protocols -.implements.- Repositories
    Protocols -.implements.- Services
    UseCases --> Entities
    
    %% Infrastructure connections
    Repositories -->|psycopg3| DB
    Services -->|google-generativeai| Gemini
    UseCases --> Utils
    
    %% Styling
    classDef frontend fill:#bbdefb,stroke:#1976d2,stroke-width:2px
    classDef backend fill:#c5e1a5,stroke:#558b2f,stroke-width:2px
    classDef domain fill:#fff9c4,stroke:#f57f17,stroke-width:2px
    classDef infra fill:#ffccbc,stroke:#d84315,stroke-width:2px
    classDef data fill:#b39ddb,stroke:#512da8,stroke-width:2px
    classDef external fill:#f48fb1,stroke:#c2185b,stroke-width:2px
    
    class WebApp,UI,APIClient frontend
    class API,Routes,Container backend
    class UseCases,Entities,Protocols domain
    class Repositories,Services,Utils infra
    class DB data
    class Gemini external
```

---

## Component Descriptions

### Client Layer

| Component | Technology | Description |
|-----------|------------|-------------|
| **User** | - | End user accessing the system via browser |
| **Browser** | Chrome, Firefox, etc. | Web browser rendering the UI |

### Frontend Layer

| Component | Technology | Description |
|-----------|------------|-------------|
| **Next.js App** | Next.js 15, TypeScript | React-based web application with App Router |
| **UI Components** | React, Tailwind CSS | Reusable UI components (forms, results, etc.) |
| **API Client** | fetch API | HTTP client for backend communication |

### Backend Layer

#### API + Routing

| Component | Technology | Description |
|-----------|------------|-------------|
| **FastAPI Server** | FastAPI, Uvicorn | ASGI web server handling HTTP requests |
| **HTTP Routes** | FastAPI Router | Endpoint definitions (`/ask`, `/ingest/text`, etc.) |
| **DI Container** | functools.lru_cache | Dependency injection factory functions |

#### Application Layer (Business Logic)

| Component | Files | Description |
|-----------|-------|-------------|
| **Use Cases** | `application/use_cases/` | Orchestrate business workflows |
| - AnswerQuery | `answer_query.py` | RAG Q&A workflow (embed → retrieve → generate) |
| - IngestDocument | `ingest_document.py` | Document ingestion (chunk → embed → store) |
| - SearchChunks | `search_chunks.py` | Semantic search without LLM generation |

#### Domain Layer (Core Business)

| Component | Files | Description |
|-----------|-------|-------------|
| **Entities** | `domain/entities.py` | Pure business objects (Document, Chunk, QueryResult) |
| **Protocols** | `domain/repositories.py`, `domain/services.py` | Abstract interfaces (contracts) |

#### Infrastructure Layer (Implementations)

| Component | Files | Description |
|-----------|-------|-------------|
| **Repositories** | `infrastructure/repositories/` | Data persistence implementations |
| - PostgresDocumentRepo | `postgres_document_repo.py` | PostgreSQL + pgvector adapter |
| **Services** | `infrastructure/services/` | External service adapters |
| - GoogleEmbedding | `google_embedding_service.py` | Gemini embeddings client |
| - GoogleLLM | `google_llm_service.py` | Gemini text generation client |
| **Utilities** | `infrastructure/text/` | Shared utilities |
| - TextChunker | `chunker.py` | Split text into chunks (900 chars, 120 overlap) |

### Data Layer

| Component | Technology | Description |
|-----------|------------|-------------|
| **PostgreSQL** | PostgreSQL 16 | Relational database with vector extension |
| **pgvector** | pgvector 0.8.1 | Vector similarity search (IVFFlat index) |

### External Services

| Component | API | Description |
|-----------|-----|-------------|
| **Google Gemini** | REST API | LLM and embedding provider |
| - text-embedding-004 | 768D vectors | Convert text to embeddings |
| - gemini-1.5-flash | 1M context | Generate natural language answers |

---

## Data Flow (Simplified)

```mermaid
sequenceDiagram
    participant User
    participant WebApp as Next.js
    participant API as FastAPI
    participant UseCase
    participant Repo as Repository
    participant DB as PostgreSQL
    participant Gemini

    User->>WebApp: Enter query
    WebApp->>API: POST /ask {query}
    API->>UseCase: execute(input)
    UseCase->>Gemini: embed(query)
    Gemini-->>UseCase: embedding[768]
    UseCase->>Repo: search_similar(embedding)
    Repo->>DB: SELECT ... ORDER BY embedding <=> ...
    DB-->>Repo: chunks[]
    Repo-->>UseCase: chunks[]
    UseCase->>Gemini: generate(prompt, context)
    Gemini-->>UseCase: answer_text
    UseCase-->>API: QueryResult
    API-->>WebApp: JSON response
    WebApp-->>User: Display answer
```

---

## Deployment Architecture

```mermaid
graph LR
    subgraph "Development (Docker Compose)"
        DevWeb[Next.js<br/>localhost:3000]
        DevAPI[FastAPI<br/>localhost:8000]
        DevDB[(PostgreSQL<br/>localhost:5432)]
    end
    
    subgraph "Production (Future)"
        LB[Load Balancer]
        ProdWeb1[Next.js Instance 1]
        ProdWeb2[Next.js Instance 2]
        ProdAPI1[FastAPI Instance 1]
        ProdAPI2[FastAPI Instance 2]
        ProdDB[(PostgreSQL<br/>Managed)]
        ProdGemini[Gemini API]
        
        LB --> ProdWeb1
        LB --> ProdWeb2
        ProdWeb1 --> ProdAPI1
        ProdWeb2 --> ProdAPI2
        ProdAPI1 --> ProdDB
        ProdAPI2 --> ProdDB
        ProdAPI1 --> ProdGemini
        ProdAPI2 --> ProdGemini
    end
    
    DevWeb -.migrate.-> LB
    DevAPI -.migrate.-> ProdAPI1
    DevDB -.migrate.-> ProdDB
```

---

## Technology Stack Summary

| Layer | Components | Technologies |
|-------|------------|--------------|
| **Frontend** | Web UI | Next.js 15, React, TypeScript, Tailwind CSS |
| **Backend** | API Server | FastAPI, Python 3.11, Uvicorn (ASGI) |
| **Business Logic** | Use Cases | Pure Python (framework-agnostic) |
| **Data Access** | Repositories | psycopg3, PostgreSQL driver |
| **Database** | Storage | PostgreSQL 16 + pgvector 0.8.1 |
| **AI/ML** | LLM + Embeddings | Google Gemini API |
| **DevOps** | Orchestration | Docker Compose, pnpm, Turborepo |

---

## Integration Points

### 1. Frontend ↔ Backend

**Protocol:** HTTP REST  
**Format:** JSON  
**Authentication:** None (planned: API keys)

```typescript
// Frontend API call
const response = await fetch('http://localhost:8000/ask', {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({ query: 'How does it work?' })
});
const data = await response.json();
```

### 2. Backend ↔ PostgreSQL

**Protocol:** PostgreSQL wire protocol (TCP)  
**Driver:** psycopg3  
**Connection Pool:** Single connection (development)

```python
# Backend DB connection
import psycopg
conn = psycopg.connect("postgresql://postgres:postgres@localhost:5432/rag")
```

### 3. Backend ↔ Gemini API

**Protocol:** HTTPS REST  
**SDK:** google-generativeai  
**Authentication:** API Key

```python
# Backend Gemini integration
import google.generativeai as genai
genai.configure(api_key=settings.GOOGLE_API_KEY)
model = genai.GenerativeModel("gemini-1.5-flash")
```

---

## Component Dependencies

### Direct Dependencies

```
Next.js App
  └─> FastAPI (HTTP)

FastAPI
  ├─> Use Cases (DI)
  └─> DI Container

Use Cases
  ├─> Domain Protocols (interfaces)
  └─> Domain Entities

Infrastructure (Repositories)
  ├─> Domain Protocols (implements)
  └─> PostgreSQL (psycopg3)

Infrastructure (Services)
  ├─> Domain Protocols (implements)
  └─> Gemini API (google-generativeai)
```

### Dependency Inversion

```
High-Level (Use Cases)
      ↑ depends on
Domain Protocols (interfaces)
      ↑ implemented by
Low-Level (Infrastructure)
```

**Key Principle:** High-level modules don't depend on low-level details.

---

## References

- **Architecture Overview:** [overview.md](../architecture/overview.md)
- **Clean Architecture:** [clean-architecture.md](../design/clean-architecture.md)
- **API Documentation:** [http-api.md](../api/http-api.md)

---

**Last Updated:** 2025-12-30  
**Maintainer:** Engineering Team
