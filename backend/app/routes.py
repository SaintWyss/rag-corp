"""
Name: RAG API Controllers

Responsibilities:
  - Expose HTTP endpoints for document ingestion and querying
  - Delegate business logic to application use cases (Clean Architecture)
  - Validate requests and serialize responses using Pydantic models
  - Wire dependencies via FastAPI DI container

Collaborators:
  - application.use_cases: IngestDocumentUseCase, SearchChunksUseCase, AnswerQueryUseCase
  - container: Dependency providers for repositories and services

Constraints:
  - Synchronous endpoints, no streaming response support
  - No authentication or rate limiting (development only)

Notes:
  - This module stays thin (controllers only)
  - Business logic lives in application/use_cases
  - See doc/plan-mejora-arquitectura-2025-12-29.md for roadmap
"""
from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field, field_validator
from uuid import UUID
from .config import get_settings
from .auth import require_scope
from .application.use_cases import (
    AnswerQueryUseCase,
    AnswerQueryInput,
    IngestDocumentUseCase,
    IngestDocumentInput,
    SearchChunksUseCase,
    SearchChunksInput,
)
from .container import (
    get_answer_query_use_case,
    get_ingest_document_use_case,
    get_search_chunks_use_case,
)

# R: Create API router for RAG endpoints
router = APIRouter()

# R: Request model for text ingestion (document metadata + content)
# R: Limits are loaded from Settings at module load time for Pydantic schema
_settings = get_settings()

class IngestTextReq(BaseModel):
    title: str = Field(
        ...,
        min_length=1,
        max_length=_settings.max_title_chars,
        description="Document title (1-200 chars)"
    )
    text: str = Field(
        ...,
        min_length=1,
        max_length=_settings.max_ingest_chars,
        description="Full document text to be chunked (1-100,000 chars)"
    )
    source: str | None = Field(
        default=None,
        max_length=_settings.max_source_chars,
        description="Optional source URL or identifier (max 500 chars)"
    )
    metadata: dict = Field(default_factory=dict, description="Additional custom metadata (JSONB)")

    @field_validator("title", "text")
    @classmethod
    def strip_whitespace(cls, v: str) -> str:
        """Trim leading/trailing whitespace."""
        return v.strip()

# R: Response model for text ingestion (confirmation)
class IngestTextRes(BaseModel):
    document_id: UUID  # R: Unique identifier of stored document
    chunks: int  # R: Number of chunks created from document

# R: Endpoint to ingest documents into the RAG system
@router.post("/ingest/text", response_model=IngestTextRes, tags=["ingest"])
def ingest_text(
    req: IngestTextReq,
    use_case: IngestDocumentUseCase = Depends(get_ingest_document_use_case),
    _auth: None = Depends(require_scope("ingest")),
):
    result = use_case.execute(
        IngestDocumentInput(
            title=req.title,
            text=req.text,
            source=req.source,
            metadata=req.metadata,
        )
    )
    return IngestTextRes(
        document_id=result.document_id,
        chunks=result.chunks_created,
    )

# R: Request model for queries (shared by /query and /ask endpoints)
class QueryReq(BaseModel):
    query: str = Field(
        ...,
        min_length=1,
        max_length=_settings.max_query_chars,
        description="User's natural language question (1-2,000 chars)"
    )
    top_k: int = Field(
        default=5,
        ge=1,
        le=_settings.max_top_k,
        description="Number of similar chunks to retrieve (1-20)"
    )

    @field_validator("query")
    @classmethod
    def strip_query_whitespace(cls, v: str) -> str:
        """Trim leading/trailing whitespace from query."""
        return v.strip()

# R: Match model representing a single similar chunk
class Match(BaseModel):
    chunk_id: UUID  # R: Unique chunk identifier
    document_id: UUID  # R: Parent document identifier
    content: str  # R: Chunk text content
    score: float  # R: Similarity score (0-1, higher is better)

# R: Response model for semantic search (retrieval only)
class QueryRes(BaseModel):
    matches: list[Match]  # R: List of similar chunks ordered by relevance

# R: Endpoint for semantic search (retrieval without generation)
@router.post("/query", response_model=QueryRes, tags=["query"])
def query(
    req: QueryReq,
    use_case: SearchChunksUseCase = Depends(get_search_chunks_use_case),
    _auth: None = Depends(require_scope("ask")),
):
    result = use_case.execute(SearchChunksInput(query=req.query, top_k=req.top_k))
    matches = []
    for chunk in result.matches:
        if chunk.chunk_id is None or chunk.document_id is None:
            raise ValueError("Missing identifiers in search result")
        matches.append(
            Match(
                chunk_id=chunk.chunk_id,
                document_id=chunk.document_id,
                content=chunk.content,
                score=float(chunk.similarity or 0.0),
            )
        )
    return QueryRes(matches=matches)

# R: Response model for RAG (retrieval + generation)
class AskRes(BaseModel):
    answer: str  # R: Generated answer from LLM
    sources: list[str]  # R: Retrieved chunks used as context

# R: Endpoint for complete RAG flow (retrieval + generation) - REFACTORED with Use Case
@router.post("/ask", response_model=AskRes, tags=["query"])
def ask(
    req: QueryReq,
    use_case: AnswerQueryUseCase = Depends(get_answer_query_use_case),
    _auth: None = Depends(require_scope("ask")),
):
    """
    R: RAG endpoint using Clean Architecture (Use Case pattern).
    
    This endpoint demonstrates the architecture improvement:
    - Business logic in use case (testable, framework-independent)
    - Dependency injection via FastAPI Depends
    - Separation of concerns (HTTP ↔ Business Logic)
    
    Uses the same query contract as /query with a generation step.
    """
    # R: Execute use case with input data
    result = use_case.execute(
        AnswerQueryInput(
            query=req.query,
            top_k=req.top_k
        )
    )
    
    # R: Convert domain result to HTTP response
    return AskRes(
        answer=result.answer,
        sources=[chunk.content for chunk in result.chunks]
    )
