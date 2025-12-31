"""
Name: RAG API Controllers

Responsibilities:
  - Expose HTTP endpoints for document ingestion and querying
  - Orchestrate complete RAG flow (chunking → embedding → storage → retrieval → generation)
  - Validate requests and serialize responses using Pydantic models
  - Coordinate dependencies between Store, Embeddings, LLM, and Text modules

Collaborators:
  - Store: Persistence in PostgreSQL + pgvector
  - embed_texts/embed_query: Generate embeddings with Google API
  - generate_rag_answer: Generate responses with Gemini
  - chunk_text: Split documents into fragments

Constraints:
  - No structured error handling (TODO: add exception handlers)
  - Direct instantiation of Store (violates DIP, refactor to DI in Phase 1)
  - Synchronous endpoints, no streaming response support
  - No authentication or rate limiting (development only)

Notes:
  - This module is a candidate for refactoring in Architecture Improvement Plan
  - Should be split into: presentation layer (controllers) + application layer (use cases)
  - See doc/plan-mejora-arquitectura-2025-12-29.md for roadmap
"""
from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field
from uuid import UUID
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
class IngestTextReq(BaseModel):
    title: str  # R: Document title
    text: str  # R: Full document text to be chunked
    source: str | None = None  # R: Optional source URL or identifier
    metadata: dict = Field(default_factory=dict)  # R: Additional custom metadata (JSONB)

# R: Response model for text ingestion (confirmation)
class IngestTextRes(BaseModel):
    document_id: UUID  # R: Unique identifier of stored document
    chunks: int  # R: Number of chunks created from document

# R: Endpoint to ingest documents into the RAG system
@router.post("/ingest/text", response_model=IngestTextRes)
def ingest_text(
    req: IngestTextReq,
    use_case: IngestDocumentUseCase = Depends(get_ingest_document_use_case),
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
    query: str  # R: User's natural language question
    top_k: int = 5  # R: Number of similar chunks to retrieve

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
@router.post("/query", response_model=QueryRes)
def query(
    req: QueryReq,
    use_case: SearchChunksUseCase = Depends(get_search_chunks_use_case),
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
@router.post("/ask", response_model=AskRes)
def ask(
    req: QueryReq,
    use_case: AnswerQueryUseCase = Depends(get_answer_query_use_case)
):
    """
    R: RAG endpoint using Clean Architecture (Use Case pattern).
    
    This endpoint demonstrates the architecture improvement:
    - Business logic in use case (testable, framework-independent)
    - Dependency injection via FastAPI Depends
    - Separation of concerns (HTTP ↔ Business Logic)
    
    Compare with /query endpoint (legacy) to see the difference.
    """
    # R: Execute use case with input data
    result = use_case.execute(
        AnswerQueryInput(
            query=req.query,
            top_k=3  # R: Fixed to 3 for RAG (vs configurable top_k in /query)
        )
    )
    
    # R: Convert domain result to HTTP response
    return AskRes(
        answer=result.answer,
        sources=[chunk.content for chunk in result.chunks]
    )
