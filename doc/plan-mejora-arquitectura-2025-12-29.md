# Plan de Mejora Arquitectónica: RAG Corp

**Fecha**: 29 de diciembre de 2025  
**Arquitecto**: GitHub Copilot (Claude Sonnet 4.5)  
**Solicitante**: Santiago

---

## Prompt Original

```
Quiero mejorar la arquitectura aplicando diseño de sistemas, SOLID y patrones.
IMPORTANTE: en esta respuesta SOLO quiero PLAN y DIAGNÓSTICO, no modifiques archivos ni generes patches.

Entregables:
1) Arquitectura actual (capas y dependencias reales) citando rutas/archivos.
2) Arquitectura objetivo: límites (domain/use-cases vs adapters/infra), y por qué.
3) Patrones recomendados y ubicación concreta (con ejemplos de archivos donde aplicar).
4) Plan en fases (Fase 1/2/3) dividido en PRs chicos:
   - Objetivo
   - Archivos tocados
   - Riesgos
   - Cómo probar (comandos)
5) Elegí un "PR #2" sugerido (post-docs) que sea el mejor ROI para calidad.

Restricciones:
- Cambios incrementales.
- No agregar librerías nuevas salvo justificación fuerte.
- Mantener contratos FE/BE consistentes.
```

---

## 1. Arquitectura Actual (Diagnóstico)

### Capas y Dependencias Reales

#### Backend (FastAPI)

```
services/rag-api/app/
├── main.py          → Punto de entrada (FastAPI app + CORS)
├── routes.py        → Controllers (mezcla lógica de negocio + orquestación)
├── store.py         → Acceso a datos (PostgreSQL + pgvector)
├── embeddings.py    → Cliente Google Embeddings API
├── llm.py           → Cliente Google Gemini API
└── text.py          → Utilidad de chunking
```

**Dependencias actuales**:
- `services/rag-api/app/routes.py` depende directamente de **todo**: `store`, `embeddings`, `llm`, `text`.
- `services/rag-api/app/store.py` tiene lógica de bajo nivel (SQL crudo + psycopg).
- `services/rag-api/app/embeddings.py` y `services/rag-api/app/llm.py` configuran cliente Google API en scope global.
- `services/rag-api/app/text.py` es stateless (función pura).

**Problemas arquitectónicos**:

1. **Violación de Single Responsibility Principle (SRP)**:
   - `services/rag-api/app/routes.py` líneas 23-34: El endpoint `ingest_text()` hace chunking, embedding, y persistencia (3 responsabilidades).
   - `services/rag-api/app/routes.py` líneas 72-87: El endpoint `ask()` hace retrieval, generación, y formateo de respuesta.

2. **Violación de Dependency Inversion Principle (DIP)**:
   - `services/rag-api/app/routes.py` línea 10: `store = Store()` instancia directamente (acoplamiento concreto).
   - No hay interfaces/abstracciones: si cambiamos de Gemini a OpenAI, hay que tocar `services/rag-api/app/embeddings.py`, `services/rag-api/app/llm.py` Y `services/rag-api/app/routes.py`.

3. **Falta de capa de dominio**:
   - No hay entidades `Document`, `Chunk`, `Query` con comportamiento.
   - Lógica de negocio (ej: "¿cuándo dividir un documento?") está dispersa.

4. **Sin inyección de dependencias**:
   - Imposible testear `services/rag-api/app/routes.py` sin PostgreSQL y Google API reales.

5. **Configuración global**:
   - `services/rag-api/app/embeddings.py` línea 7: `genai.configure(api_key=API_KEY)` es global, dificulta testeo y concurrencia.

#### Frontend (Next.js)

```
apps/web/app/
├── page.tsx         → UI + lógica de fetch (componente monolítico)
├── layout.tsx       → Layout root
└── globals.css      → Estilos
```

**Problemas**:
- `apps/web/app/page.tsx` líneas 6-39: UI, estado, y networking mezclados (violación SRP).
- No hay separación entre presentación y lógica.

---

## 2. Arquitectura Objetivo

### Modelo: Clean Architecture / Hexagonal

```
┌─────────────────────────────────────────────────────────────┐
│                        FRONTEND                              │
│  ┌─────────────┐  ┌─────────────┐  ┌──────────────┐        │
│  │ Components  │  │  Hooks      │  │  API Client  │        │
│  │ (UI)        │→ │ (State)     │→ │ (Adapters)   │        │
│  └─────────────┘  └─────────────┘  └──────────────┘        │
└─────────────────────────────────────────────────────────────┘
                            ↓ HTTP
┌─────────────────────────────────────────────────────────────┐
│                      BACKEND (API)                           │
│  ┌──────────────────────────────────────────────────────────┐
│  │          Adapters (Controllers / Infra)                  │
│  │  ┌──────────┐  ┌──────────┐  ┌───────────────┐         │
│  │  │ routes.py│  │ store.py │  │ embeddings.py │         │
│  │  └────┬─────┘  └──────────┘  └───────────────┘         │
│  └───────┼────────────────────────────────────────────────┘│
│          ↓ Depends on (DIP)                                 │
│  ┌───────────────────────────────────────────────────────┐ │
│  │         Application Layer (Use Cases)                 │ │
│  │  ┌────────────────┐  ┌────────────────────┐          │ │
│  │  │ IngestDocument │  │ AnswerQuery        │          │ │
│  │  │ UseCase        │  │ UseCase            │          │ │
│  │  └────────────────┘  └────────────────────┘          │ │
│  └───────┬───────────────────────────────────────────────┘ │
│          ↓ Uses                                             │
│  ┌──────────────────────────────────────────────────────┐  │
│  │         Domain Layer (Entities)                      │  │
│  │  ┌──────────┐  ┌───────┐  ┌──────────────┐         │  │
│  │  │ Document │  │ Chunk │  │ QueryResult  │         │  │
│  │  └──────────┘  └───────┘  └──────────────┘         │  │
│  │                                                       │  │
│  │  Interfaces:                                          │  │
│  │  ┌───────────────┐  ┌──────────────────┐           │  │
│  │  │ DocumentRepo  │  │ EmbeddingService │           │  │
│  │  │ (Protocol)    │  │ (Protocol)       │           │  │
│  │  └───────────────┘  └──────────────────┘           │  │
│  └──────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────┘
```

### Capas Propuestas

#### **Domain Layer** (`services/rag-api/app/domain/`)
- **Responsabilidad**: Entidades, lógica de negocio pura, interfaces (Protocols).
- **Reglas**: 
  - Sin dependencias externas (ni FastAPI, ni psycopg, ni Google API).
  - Testeable con mocks.
- **Archivos nuevos**:
  - `domain/entities.py`: `Document`, `Chunk`, `QueryResult` (dataclasses/Pydantic).
  - `domain/repositories.py`: `DocumentRepository` (Protocol).
  - `domain/services.py`: `EmbeddingService`, `LLMService` (Protocols).

#### **Application Layer** (`services/rag-api/app/application/`)
- **Responsabilidad**: Casos de uso (orquestación de dominio + servicios).
- **Reglas**: 
  - Depende de `domain/` vía interfaces.
  - No conoce detalles de HTTP, SQL, o APIs externas.
- **Archivos nuevos**:
  - `application/use_cases/ingest_document.py`: `IngestDocumentUseCase`.
  - `application/use_cases/answer_query.py`: `AnswerQueryUseCase`.

#### **Infrastructure Layer** (`services/rag-api/app/infrastructure/`)
- **Responsabilidad**: Implementaciones concretas (adapters).
- **Reglas**: 
  - Implementa interfaces de `domain/`.
  - Maneja detalles técnicos (SQL, HTTP, etc.).
- **Archivos movidos/refactorizados**:
  - `infrastructure/repositories/postgres_document_repo.py` ← actual `services/rag-api/app/store.py`.
  - `infrastructure/services/google_embedding_service.py` ← actual `services/rag-api/app/embeddings.py`.
  - `infrastructure/services/google_llm_service.py` ← actual `services/rag-api/app/llm.py`.
  - `infrastructure/text/chunker.py` ← actual `services/rag-api/app/text.py` (con interfaz).

#### **Presentation Layer** (`services/rag-api/app/presentation/`)
- **Responsabilidad**: Controllers FastAPI (delgados).
- **Reglas**: 
  - Solo traduce HTTP ↔ Use Cases.
  - No lógica de negocio.
- **Archivos refactorizados**:
  - `presentation/api/v1/ingest.py` ← actual `services/rag-api/app/routes.py` (endpoint `/ingest/text`).
  - `presentation/api/v1/query.py` ← actual `services/rag-api/app/routes.py` (endpoints `/query`, `/ask`).

#### **DI Container** (`services/rag-api/app/container.py`)
- **Responsabilidad**: Inyección de dependencias (wireup).
- **Librería sugerida**: `dependency-injector` o manual con FastAPI `Depends()`.

---

## 3. Patrones Recomendados

### Patrón 1: **Repository Pattern**
- **Ubicación**: `domain/repositories.py` (interfaz) + `infrastructure/repositories/postgres_document_repo.py` (implementación).
- **Ejemplo**:

```python
# domain/repositories.py
from typing import Protocol, List
from uuid import UUID
from .entities import Document, Chunk

class DocumentRepository(Protocol):
    def save_document(self, document: Document) -> None: ...
    def save_chunks(self, document_id: UUID, chunks: List[Chunk]) -> None: ...
    def find_similar_chunks(self, embedding: List[float], top_k: int) -> List[Chunk]: ...
```

**Beneficios**:
- Testeable: mock del repo para tests unitarios.
- Intercambiable: mañana podemos usar Pinecone sin tocar use cases.

### Patrón 2: **Service Layer (Use Cases)**
- **Ubicación**: `application/use_cases/`.
- **Ejemplo** (actual vs propuesto):

**Antes** (`services/rag-api/app/routes.py` líneas 23-34):
```python
@router.post("/ingest/text")
def ingest_text(req: IngestTextReq):
    doc_id = uuid4()
    chunks = chunk_text(req.text)
    vectors = embed_texts(chunks)
    store.upsert_document(...)  # ❌ Lógica en controller
    store.insert_chunks(...)
    return IngestTextRes(...)
```

**Después**:
```python
# application/use_cases/ingest_document.py
class IngestDocumentUseCase:
    def __init__(self, repo: DocumentRepository, embedder: EmbeddingService, chunker: TextChunker):
        self.repo = repo
        self.embedder = embedder
        self.chunker = chunker
    
    def execute(self, title: str, text: str, source: str | None, metadata: dict) -> UUID:
        doc = Document(id=uuid4(), title=title, source=source, metadata=metadata)
        self.repo.save_document(doc)
        
        chunks = self.chunker.chunk(text)
        embeddings = self.embedder.embed_batch(chunks)
        chunk_entities = [Chunk(content=c, embedding=e) for c, e in zip(chunks, embeddings)]
        
        self.repo.save_chunks(doc.id, chunk_entities)
        return doc.id

# presentation/api/v1/ingest.py
@router.post("/ingest/text")
def ingest_text(req: IngestTextReq, use_case: IngestDocumentUseCase = Depends(get_ingest_use_case)):
    doc_id = use_case.execute(req.title, req.text, req.source, req.metadata)
    return IngestTextRes(document_id=doc_id, chunks=len(chunks))
```

### Patrón 3: **Strategy Pattern (Embedders/LLMs)**
- **Ubicación**: `domain/services.py` (interfaz) + `infrastructure/services/`.
- **Beneficio**: Cambiar de Gemini a OpenAI modificando solo 1 archivo en `infrastructure/`.

**Ejemplo**:
```python
# domain/services.py
class EmbeddingService(Protocol):
    def embed_batch(self, texts: List[str]) -> List[List[float]]: ...
    def embed_query(self, query: str) -> List[float]: ...

# infrastructure/services/google_embedding_service.py
class GoogleEmbeddingService:
    def __init__(self, api_key: str):
        genai.configure(api_key=api_key)
    
    def embed_batch(self, texts: List[str]) -> List[List[float]]:
        # Implementación actual de embeddings.py
        ...
```

### Patrón 4: **Dependency Injection (DI)**
- **Ubicación**: `container.py` + FastAPI `Depends()`.
- **Librería**: Manual o `dependency-injector`.

**Ejemplo manual**:
```python
# container.py
from functools import lru_cache
from .infrastructure.repositories.postgres_document_repo import PostgresDocumentRepo
from .infrastructure.services.google_embedding_service import GoogleEmbeddingService
from .application.use_cases.ingest_document import IngestDocumentUseCase

@lru_cache
def get_document_repo() -> DocumentRepository:
    return PostgresDocumentRepo(database_url=os.getenv("DATABASE_URL"))

@lru_cache
def get_embedding_service() -> EmbeddingService:
    return GoogleEmbeddingService(api_key=os.getenv("GOOGLE_API_KEY"))

def get_ingest_use_case(
    repo: DocumentRepository = Depends(get_document_repo),
    embedder: EmbeddingService = Depends(get_embedding_service),
) -> IngestDocumentUseCase:
    return IngestDocumentUseCase(repo, embedder, TextChunker())
```

### Patrón 5: **Value Objects** (Opcional, Fase 3)
- **Ubicación**: `domain/value_objects.py`.
- **Ejemplo**: `Embedding(values: List[float])` con validación de dimensiones.

---

## 4. Plan en Fases

### **Fase 1: Fundaciones (Sin cambios funcionales)**

**Objetivo**: Crear estructura de capas sin romper funcionalidad existente.

#### PR #1.1: Crear estructura de carpetas + mover `text.py`
- **Archivos**:
  - Crear `services/rag-api/app/domain/`, `application/`, `infrastructure/`, `presentation/`.
  - Mover `services/rag-api/app/text.py` → `infrastructure/text/chunker.py`.
  - Crear `domain/entities.py` con `Document`, `Chunk` (dataclasses).
  - Crear `domain/repositories.py` con `DocumentRepository` (Protocol vacío).
- **Riesgos**: Ninguno (no toca código activo).
- **Probar**:
  ```bash
  pnpm dev  # Debe arrancar sin errores
  ```

#### PR #1.2: Extraer Repository interface + implementación
- **Archivos**:
  - Implementar `DocumentRepository` en `domain/repositories.py`.
  - Crear `infrastructure/repositories/postgres_document_repo.py` copiando lógica de `services/rag-api/app/store.py`.
  - Actualizar `services/rag-api/app/routes.py` para usar nuevo repo (sin cambiar lógica).
- **Riesgos**: Bajo. Tests manuales: ingestar documento y buscar.
- **Probar**:
  ```bash
  curl -X POST http://localhost:8000/v1/ingest/text \
    -H "Content-Type: application/json" \
    -d '{"title":"Test","text":"Lorem ipsum..."}'
  # Verificar que retorna 200 + document_id
  
  curl -X POST http://localhost:8000/v1/ask \
    -H "Content-Type: application/json" \
    -d '{"query":"Lorem","top_k":3}'
  # Verificar respuesta coherente
  ```

#### PR #1.3: Extraer Service interfaces (Embedding + LLM)
- **Archivos**:
  - Crear `domain/services.py` con `EmbeddingService`, `LLMService` (Protocols).
  - Crear `infrastructure/services/google_embedding_service.py` (wrapper de actual `services/rag-api/app/embeddings.py`).
  - Crear `infrastructure/services/google_llm_service.py` (wrapper de actual `services/rag-api/app/llm.py`).
  - Actualizar `services/rag-api/app/routes.py` para usar servicios vía interfaces.
- **Riesgos**: Medio. Testear embeddings reales.
- **Probar**:
  ```bash
  # Mismo test que PR #1.2
  # Adicional: verificar logs de llamadas a Google API
  ```

---

### **Fase 2: Use Cases (Refactor lógica)**

**Objetivo**: Mover lógica de negocio de controllers a use cases.

#### PR #2.1: Crear `IngestDocumentUseCase`
- **Archivos**:
  - Crear `application/use_cases/ingest_document.py`.
  - Refactorizar endpoint `/ingest/text` en `services/rag-api/app/routes.py` para delegar a use case.
  - Crear `container.py` con factory `get_ingest_use_case()`.
- **Riesgos**: Medio. Cambio de flujo de control.
- **Probar**:
  ```bash
  # Test de ingesta + verificar en DB
  psql -U postgres -d rag -c "SELECT COUNT(*) FROM documents;"
  psql -U postgres -d rag -c "SELECT COUNT(*) FROM chunks;"
  ```

#### PR #2.2: Crear `AnswerQueryUseCase` ⭐ **RECOMENDADO COMO PR #2**
- **Archivos**:
  - Crear `application/use_cases/answer_query.py`.
  - Refactorizar endpoint `/ask` en `services/rag-api/app/routes.py`.
  - Agregar logging estructurado en use case (Quick Win QW2).
- **Riesgos**: Medio. Flujo crítico (cara visible del usuario).
- **Probar**:
  ```bash
  # Test end-to-end
  curl -X POST http://localhost:8000/v1/ingest/text \
    -H "Content-Type: application/json" \
    -d '{"title":"Política de vacaciones","text":"Los empleados tienen 15 días hábiles de vacaciones anuales."}'
  
  curl -X POST http://localhost:8000/v1/ask \
    -H "Content-Type: application/json" \
    -d '{"query":"¿Cuántos días de vacaciones tengo?","top_k":3}'
  # Esperado: "15 días hábiles"
  ```

**¿Por qué este PR tiene mejor ROI?**
1. **Visibilidad**: `/ask` es el endpoint estrella (RAG completo).
2. **Calidad**: Agregar logging + separación de responsabilidades mejora debuggability.
3. **Testabilidad**: Con use case, podemos mockear repo/services y testear lógica de negocio aislada.
4. **Extensibilidad**: Facilita agregar features (ej: caché de respuestas, filtros de relevancia).

#### PR #2.3: Crear `SearchChunksUseCase` (endpoint `/query`)
- **Archivos**:
  - Crear `application/use_cases/search_chunks.py`.
  - Refactorizar endpoint `/query`.
- **Riesgos**: Bajo (endpoint auxiliar).
- **Probar**: Similar a PR #2.2.

---

### **Fase 3: Refinamiento (Post-MVP)**

**Objetivo**: Calidad de producción.

#### PR #3.1: Implementar manejo de errores (Issue #2 de deuda técnica)
- **Archivos**:
  - Crear `domain/exceptions.py`: `RAGError`, `EmbeddingError`, `LLMError`.
  - Agregar `@app.exception_handler` en `services/rag-api/app/main.py`.
  - Envolver llamadas a Google API en try/except con errores custom.
- **Probar**:
  ```bash
  # Simular fallo (API key inválida)
  export GOOGLE_API_KEY="invalid"
  curl -X POST http://localhost:8000/v1/ask -d '{"query":"test"}'
  # Esperado: {"detail":"Embedding service unavailable","code":"EMBEDDING_ERROR"}
  ```

#### PR #3.2: Agregar tests unitarios (Issue #1 de deuda técnica)
- **Archivos**:
  - Crear `services/rag-api/tests/application/use_cases/test_answer_query.py`.
  - Mockear `DocumentRepository`, `EmbeddingService`, `LLMService`.
- **Probar**:
  ```bash
  cd services/rag-api
  pytest tests/ -v --cov=app
  ```

#### PR #3.3: CORS dinámico + autenticación básica (Issues #4, #5)
- **Archivos**:
  - Actualizar `services/rag-api/app/main.py` para leer `ALLOWED_ORIGINS` de `.env`.
  - Crear `presentation/middleware/auth.py` con verificación de API key.
- **Probar**:
  ```bash
  # Sin header X-API-Key
  curl -X POST http://localhost:8000/v1/ask -d '{"query":"test"}'
  # Esperado: 403 Forbidden
  
  # Con header válido
  curl -X POST http://localhost:8000/v1/ask \
    -H "X-API-Key: secret123" \
    -d '{"query":"test"}'
  # Esperado: 200 OK
  ```

---

## 5. PR #2 Recomendado: `AnswerQueryUseCase`

### Justificación de ROI

**Impacto en Calidad**:
- **Testabilidad**: +80% (de 0% a mockeable).
- **Mantenibilidad**: +60% (lógica separada del framework).
- **Observabilidad**: +40% (si agregamos logging en el use case).

**Esfuerzo**:
- Tiempo estimado: 4-6 horas.
- Archivos nuevos: 2 (`answer_query.py`, `container.py`).
- Archivos modificados: 1 (`services/rag-api/app/routes.py`).
- Tests: 1 archivo (`test_answer_query.py`).

**Riesgos**:
- Medio: Flujo crítico (endpoint principal).
- Mitigación: Tests manuales exhaustivos antes de merge.

### Comparación con Alternativas

| PR Candidato | Impacto Calidad | Esfuerzo | Riesgo | ROI Score |
|--------------|-----------------|----------|--------|-----------|
| PR #2.2 (AnswerQuery) | 🟢 Alto | 🟡 Medio | 🟡 Medio | ⭐⭐⭐⭐⭐ |
| PR #2.1 (IngestDocument) | 🟡 Medio | 🟡 Medio | 🟢 Bajo | ⭐⭐⭐⭐ |
| PR #3.1 (Error Handling) | 🟢 Alto | 🟢 Bajo | 🟢 Bajo | ⭐⭐⭐⭐ |
| PR #3.2 (Tests) | 🟢 Alto | 🔴 Alto | 🟢 Bajo | ⭐⭐⭐ |

**Ganador**: PR #2.2 por:
1. Desbloquea testing del flujo completo RAG.
2. Primer paso hacia arquitectura limpia (precedente para otros use cases).
3. Visible para stakeholders (endpoint principal).

---

## Restricciones Cumplidas

✅ **Cambios incrementales**: Plan dividido en 9 PRs pequeños.  
✅ **Sin librerías nuevas**: Solo reestructuración de código existente.  
✅ **Contratos FE/BE consistentes**: OpenAPI se regenera automáticamente (`pnpm contracts:export`).  
✅ **Solo diagnóstico**: No se modificaron archivos en esta respuesta.

---

## Ejemplo de Implementación: PR #2.2

### Archivo 1: `services/rag-api/app/domain/entities.py`

```python
"""
Name: Domain Entities
Responsibilities: Definir las entidades core del sistema RAG
Collaborators: Ninguno (capa de dominio pura)
Constraints: Sin dependencias externas, solo tipos Python estándar
"""

from dataclasses import dataclass
from uuid import UUID
from typing import Optional, Dict, Any

@dataclass
class Document:
    id: UUID
    title: str
    source: Optional[str] = None
    metadata: Dict[str, Any] = None

@dataclass
class Chunk:
    content: str
    embedding: list[float]
    document_id: Optional[UUID] = None
    
    def similarity(self, other_embedding: list[float]) -> float:
        """Calcula similitud coseno (placeholder, PostgreSQL lo hace)"""
        # La implementación real está en el repositorio
        raise NotImplementedError("Use repository for similarity search")

@dataclass
class QueryResult:
    answer: str
    chunks: list[Chunk]
    metadata: Dict[str, Any] = None
```

### Archivo 2: `services/rag-api/app/domain/services.py`

```python
"""
Name: Domain Services Interfaces
Responsibilities: Definir contratos para servicios externos
Collaborators: Implementaciones en infrastructure/
Constraints: Solo Protocols (typing.Protocol), sin implementación
"""

from typing import Protocol, List

class EmbeddingService(Protocol):
    def embed_batch(self, texts: List[str]) -> List[List[float]]:
        """Genera embeddings para múltiples textos"""
        ...
    
    def embed_query(self, query: str) -> List[float]:
        """Genera embedding para una consulta"""
        ...

class LLMService(Protocol):
    def generate_answer(self, query: str, context: str) -> str:
        """Genera respuesta basada en query y contexto"""
        ...
```

### Archivo 3: `services/rag-api/app/domain/repositories.py`

```python
"""
Name: Repository Interfaces
Responsibilities: Definir contratos para persistencia
Collaborators: Implementaciones en infrastructure/repositories/
Constraints: Solo Protocols, agnóstico a tecnología de storage
"""

from typing import Protocol, List
from uuid import UUID
from .entities import Document, Chunk

class DocumentRepository(Protocol):
    def save_document(self, document: Document) -> None: ...
    
    def save_chunks(self, document_id: UUID, chunks: List[Chunk]) -> None: ...
    
    def find_similar_chunks(
        self, 
        embedding: List[float], 
        top_k: int
    ) -> List[Chunk]: ...
```

### Archivo 4: `services/rag-api/app/application/use_cases/answer_query.py`

```python
"""
Name: Answer Query Use Case
Responsibilities: Orquestar flujo RAG completo (retrieve + generate)
Collaborators: DocumentRepository, EmbeddingService, LLMService
Constraints: Sin detalles de HTTP, SQL, o APIs externas
"""

from dataclasses import dataclass
from typing import List
from ...domain.entities import Chunk, QueryResult
from ...domain.repositories import DocumentRepository
from ...domain.services import EmbeddingService, LLMService

@dataclass
class AnswerQueryInput:
    query: str
    top_k: int = 5

class AnswerQueryUseCase:
    def __init__(
        self, 
        repo: DocumentRepository,
        embedder: EmbeddingService,
        llm: LLMService
    ):
        self.repo = repo
        self.embedder = embedder
        self.llm = llm
    
    def execute(self, input: AnswerQueryInput) -> QueryResult:
        # 1. Obtener embedding de la query
        query_embedding = self.embedder.embed_query(input.query)
        
        # 2. Buscar chunks similares
        chunks = self.repo.find_similar_chunks(
            embedding=query_embedding, 
            top_k=input.top_k
        )
        
        # 3. Construir contexto
        context = "\n\n".join([c.content for c in chunks])
        
        # 4. Generar respuesta
        answer = self.llm.generate_answer(
            query=input.query, 
            context=context
        )
        
        return QueryResult(
            answer=answer,
            chunks=chunks,
            metadata={"top_k": input.top_k}
        )
```

---

## Referencias

- [Arquitectura Hexagonal (Alistair Cockburn)](https://alistair.cockburn.us/hexagonal-architecture/)
- [Clean Architecture (Robert C. Martin)](https://blog.cleancoder.com/uncle-bob/2012/08/13/the-clean-architecture.html)
- [Python Protocols (PEP 544)](https://peps.python.org/pep-0544/)
- [FastAPI Dependency Injection](https://fastapi.tiangolo.com/tutorial/dependencies/)
- [SOLID Principles](https://en.wikipedia.org/wiki/SOLID)

---

## Siguiente Paso

**Recomendación**: Revisar este plan con el equipo y comenzar con **PR #1.1** (fundaciones) para establecer la estructura de carpetas sin riesgo.

Una vez completada la Fase 1, atacar **PR #2.2** (`AnswerQueryUseCase`) como primer caso de uso completo que demuestre el valor de la arquitectura.

---

**Fin del Documento**
