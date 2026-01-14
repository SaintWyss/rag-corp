"""
Name: RAG API Controllers

Responsibilities:
  - Expose HTTP endpoints for document ingestion and querying
  - Delegate business logic to application use cases (Clean Architecture)
  - Validate requests and serialize responses using Pydantic models
  - Wire dependencies via FastAPI DI container
  - Stream LLM responses via Server-Sent Events

Collaborators:
  - application.use_cases: IngestDocumentUseCase, SearchChunksUseCase, AnswerQueryUseCase
  - container: Dependency providers for repositories and services
  - streaming: SSE streaming handler

Constraints:
  - Synchronous endpoints for ingest/query, async streaming for /ask/stream

Notes:
  - This module stays thin (controllers only)
  - Business logic lives in application/use_cases
  - See doc/plan-mejora-arquitectura-2025-12-29.md for roadmap
"""

from fastapi import APIRouter, Depends, Request, Query, File, Form, UploadFile
from pydantic import BaseModel, Field, field_validator
from uuid import UUID
from datetime import datetime
import json
import os
from uuid import uuid4
from .config import get_settings
from .rbac import Permission
from .dual_auth import (
    require_admin,
    require_employee_or_admin,
    require_principal,
)
from .error_responses import (
    not_found,
    payload_too_large,
    service_unavailable,
    unsupported_media,
    validation_error,
)
from .streaming import stream_answer
from .application.conversations import (
    format_conversation_query,
    resolve_conversation_id,
)
from .application.use_cases import (
    AnswerQueryUseCase,
    AnswerQueryInput,
    DeleteDocumentUseCase,
    GetDocumentUseCase,
    IngestDocumentUseCase,
    IngestDocumentInput,
    ListDocumentsUseCase,
    SearchChunksUseCase,
    SearchChunksInput,
)
from .container import (
    get_answer_query_use_case,
    get_ingest_document_use_case,
    get_search_chunks_use_case,
    get_llm_service,
    get_embedding_service,
    get_document_repository,
    get_conversation_repository,
    get_list_documents_use_case,
    get_get_document_use_case,
    get_delete_document_use_case,
    get_file_storage,
)
from .domain.entities import ConversationMessage, Document
from .domain.repositories import DocumentRepository
from .domain.services import FileStoragePort
from .dual_auth import PrincipalType, Principal

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
        description="Document title (1-200 chars)",
    )
    text: str = Field(
        ...,
        min_length=1,
        max_length=_settings.max_ingest_chars,
        description="Full document text to be chunked (1-100,000 chars)",
    )
    source: str | None = Field(
        default=None,
        max_length=_settings.max_source_chars,
        description="Optional source URL or identifier (max 500 chars)",
    )
    metadata: dict = Field(
        default_factory=dict, description="Additional custom metadata (JSONB)"
    )

    @field_validator("title", "text")
    @classmethod
    def strip_whitespace(cls, v: str) -> str:
        """Trim leading/trailing whitespace."""
        return v.strip()


# R: Response model for text ingestion (confirmation)
class IngestTextRes(BaseModel):
    document_id: UUID  # R: Unique identifier of stored document
    chunks: int  # R: Number of chunks created from document


# R: Response model for batch ingestion
class IngestBatchRes(BaseModel):
    documents: list[IngestTextRes]  # R: List of ingested documents
    total_chunks: int  # R: Total chunks created across all documents


# R: Request model for batch ingestion
class IngestBatchReq(BaseModel):
    documents: list[IngestTextReq] = Field(
        ...,
        min_length=1,
        max_length=10,
        description="List of documents to ingest (1-10)",
    )


class DocumentSummaryRes(BaseModel):
    id: UUID
    title: str
    source: str | None
    metadata: dict
    created_at: datetime | None


class DocumentsListRes(BaseModel):
    documents: list[DocumentSummaryRes]


class DocumentDetailRes(DocumentSummaryRes):
    deleted_at: datetime | None = None


class DeleteDocumentRes(BaseModel):
    deleted: bool


class UploadDocumentRes(BaseModel):
    document_id: UUID
    status: str
    file_name: str
    mime_type: str


_ALLOWED_MIME_TYPES = {
    "application/pdf",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
}


def _parse_metadata(raw: str | None) -> dict:
    if not raw:
        return {}
    try:
        payload = json.loads(raw)
    except json.JSONDecodeError:
        raise validation_error("metadata must be valid JSON.")
    if not isinstance(payload, dict):
        raise validation_error("metadata must be a JSON object.")
    return payload


@router.get("/documents", response_model=DocumentsListRes, tags=["documents"])
def list_documents(
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    use_case: ListDocumentsUseCase = Depends(get_list_documents_use_case),
    _principal: None = Depends(require_principal(Permission.DOCUMENTS_READ)),
    _role: None = Depends(require_employee_or_admin()),
):
    documents = use_case.execute(limit=limit, offset=offset)
    return DocumentsListRes(
        documents=[
            DocumentSummaryRes(
                id=doc.id,
                title=doc.title,
                source=doc.source,
                metadata=doc.metadata,
                created_at=doc.created_at,
            )
            for doc in documents
        ]
    )


@router.get(
    "/documents/{document_id}",
    response_model=DocumentDetailRes,
    tags=["documents"],
)
def get_document(
    document_id: UUID,
    use_case: GetDocumentUseCase = Depends(get_get_document_use_case),
    _principal: None = Depends(require_principal(Permission.DOCUMENTS_READ)),
    _role: None = Depends(require_employee_or_admin()),
):
    document = use_case.execute(document_id)
    if not document:
        raise not_found("Document", str(document_id))
    return DocumentDetailRes(
        id=document.id,
        title=document.title,
        source=document.source,
        metadata=document.metadata,
        created_at=document.created_at,
        deleted_at=document.deleted_at,
    )


@router.delete(
    "/documents/{document_id}",
    response_model=DeleteDocumentRes,
    tags=["documents"],
)
def delete_document(
    document_id: UUID,
    use_case: DeleteDocumentUseCase = Depends(get_delete_document_use_case),
    _principal: None = Depends(require_principal(Permission.DOCUMENTS_DELETE)),
    _role: None = Depends(require_admin()),
):
    deleted = use_case.execute(document_id)
    if not deleted:
        raise not_found("Document", str(document_id))
    return DeleteDocumentRes(deleted=True)


@router.post("/documents/upload", response_model=UploadDocumentRes, tags=["documents"])
async def upload_document(
    request: Request,
    file: UploadFile = File(...),
    title: str | None = Form(None),
    source: str | None = Form(None),
    metadata: str | None = Form(None),
    principal: Principal | None = Depends(
        require_principal(Permission.DOCUMENTS_CREATE)
    ),
    _role: None = Depends(require_admin()),
    repository: DocumentRepository = Depends(get_document_repository),
    storage: FileStoragePort | None = Depends(get_file_storage),
):
    settings = get_settings()
    if storage is None:
        raise service_unavailable("File storage")

    file_name = os.path.basename(file.filename or "").strip()
    if not file_name:
        file_name = "upload"

    mime_type = (file.content_type or "").lower()
    if mime_type not in _ALLOWED_MIME_TYPES:
        raise unsupported_media(f"Unsupported media type: {mime_type or 'unknown'}")

    content = await file.read()
    if settings.max_upload_bytes > 0 and len(content) > settings.max_upload_bytes:
        raise payload_too_large(f"{settings.max_upload_bytes} bytes")

    metadata_payload = _parse_metadata(metadata)

    doc_title = (title or file_name).strip() or file_name
    if len(doc_title) > settings.max_title_chars:
        raise validation_error(
            f"title exceeds maximum size of {settings.max_title_chars} characters"
        )
    if source and len(source) > settings.max_source_chars:
        raise validation_error(
            f"source exceeds maximum size of {settings.max_source_chars} characters"
        )

    document_id = uuid4()
    storage_key = f"documents/{document_id}/{file_name}"
    storage.upload_file(storage_key, content, mime_type)

    repository.save_document(
        Document(
            id=document_id,
            title=doc_title,
            source=source,
            metadata=metadata_payload,
        )
    )

    uploaded_by_user_id = None
    if principal and principal.principal_type == PrincipalType.USER:
        uploaded_by_user_id = principal.user.user_id if principal.user else None

    repository.update_document_file_metadata(
        document_id,
        file_name=file_name,
        mime_type=mime_type,
        storage_key=storage_key,
        uploaded_by_user_id=uploaded_by_user_id,
        status="PENDING",
        error_message=None,
    )

    await file.close()

    return UploadDocumentRes(
        document_id=document_id,
        status="PENDING",
        file_name=file_name,
        mime_type=mime_type,
    )


# R: Endpoint to ingest documents into the RAG system
@router.post("/ingest/text", response_model=IngestTextRes, tags=["ingest"])
def ingest_text(
    req: IngestTextReq,
    use_case: IngestDocumentUseCase = Depends(get_ingest_document_use_case),
    _principal: None = Depends(require_principal(Permission.DOCUMENTS_CREATE)),
    _role: None = Depends(require_admin()),
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


# R: Endpoint for batch document ingestion
@router.post("/ingest/batch", response_model=IngestBatchRes, tags=["ingest"])
def ingest_batch(
    req: IngestBatchReq,
    use_case: IngestDocumentUseCase = Depends(get_ingest_document_use_case),
    _principal: None = Depends(require_principal(Permission.DOCUMENTS_CREATE)),
    _role: None = Depends(require_admin()),
):
    """
    Ingest multiple documents in a single request.

    Processes up to 10 documents sequentially.
    Returns results for all successfully ingested documents.
    """
    results = []
    total_chunks = 0

    for doc in req.documents:
        result = use_case.execute(
            IngestDocumentInput(
                title=doc.title,
                text=doc.text,
                source=doc.source,
                metadata=doc.metadata,
            )
        )
        results.append(
            IngestTextRes(
                document_id=result.document_id,
                chunks=result.chunks_created,
            )
        )
        total_chunks += result.chunks_created

    return IngestBatchRes(documents=results, total_chunks=total_chunks)


# R: Request model for queries (shared by /query and /ask endpoints)
class QueryReq(BaseModel):
    query: str = Field(
        ...,
        min_length=1,
        max_length=_settings.max_query_chars,
        description="User's natural language question (1-2,000 chars)",
    )
    conversation_id: str | None = Field(
        default=None,
        description="Conversation ID for multi-turn chat (optional)",
    )
    top_k: int = Field(
        default=5,
        ge=1,
        le=_settings.max_top_k,
        description="Number of similar chunks to retrieve (1-20)",
    )
    use_mmr: bool = Field(
        default=False,
        description="Use Maximal Marginal Relevance for diverse results (slower but reduces redundancy)",
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
    _principal: None = Depends(require_principal(Permission.QUERY_SEARCH)),
    _role: None = Depends(require_employee_or_admin()),
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
    conversation_id: str | None = None  # R: Conversation ID for multi-turn chat


# R: Endpoint for complete RAG flow (retrieval + generation) - REFACTORED with Use Case
@router.post("/ask", response_model=AskRes, tags=["query"])
def ask(
    req: QueryReq,
    use_case: AnswerQueryUseCase = Depends(get_answer_query_use_case),
    _principal: None = Depends(require_principal(Permission.QUERY_ASK)),
    _role: None = Depends(require_employee_or_admin()),
):
    """
    R: RAG endpoint using Clean Architecture (Use Case pattern).

    This endpoint demonstrates the architecture improvement:
    - Business logic in use case (testable, framework-independent)
    - Dependency injection via FastAPI Depends
    - Separation of concerns (HTTP ↔ Business Logic)

    Uses the same query contract as /query with a generation step.
    Set use_mmr=true for diverse results (reduces redundant chunks).
    """
    conversation_repository = get_conversation_repository()
    conversation_id = resolve_conversation_id(
        conversation_repository, req.conversation_id
    )
    history = conversation_repository.get_messages(
        conversation_id, limit=_settings.max_conversation_messages
    )
    llm_query = format_conversation_query(history, req.query)
    conversation_repository.append_message(
        conversation_id,
        ConversationMessage(role="user", content=req.query),
    )

    # R: Execute use case with input data
    result = use_case.execute(
        AnswerQueryInput(
            query=req.query,
            llm_query=llm_query,
            top_k=req.top_k,
            use_mmr=req.use_mmr,
        )
    )

    # R: Convert domain result to HTTP response
    conversation_repository.append_message(
        conversation_id,
        ConversationMessage(role="assistant", content=result.answer),
    )
    return AskRes(
        answer=result.answer,
        sources=[chunk.content for chunk in result.chunks],
        conversation_id=conversation_id,
    )


# R: Streaming endpoint for complete RAG flow (retrieval + generation) with SSE
@router.post("/ask/stream", tags=["query"])
async def ask_stream(
    req: QueryReq,
    request: Request,
    _principal: None = Depends(require_principal(Permission.QUERY_STREAM)),
    _role: None = Depends(require_employee_or_admin()),
):
    """
    R: Streaming RAG endpoint using Server-Sent Events.

    Returns tokens as they are generated by the LLM for better UX.
    Uses the same query contract as /ask but streams the response.

    SSE Events:
    - sources: Initial event with retrieved chunks
    - token: Individual tokens as generated
    - done: Final event with complete answer
    - error: Error event if generation fails
    """
    # R: Get dependencies
    embedding_service = get_embedding_service()
    repository = get_document_repository()
    llm_service = get_llm_service()
    conversation_repository = get_conversation_repository()

    conversation_id = resolve_conversation_id(
        conversation_repository, req.conversation_id
    )
    history = conversation_repository.get_messages(
        conversation_id, limit=_settings.max_conversation_messages
    )
    llm_query = format_conversation_query(history, req.query)
    conversation_repository.append_message(
        conversation_id,
        ConversationMessage(role="user", content=req.query),
    )

    # R: Embed query and retrieve similar chunks
    query_embedding = embedding_service.embed_query(req.query)
    if req.use_mmr:
        chunks = repository.find_similar_chunks_mmr(
            embedding=query_embedding,
            top_k=req.top_k,
            fetch_k=req.top_k * 4,
            lambda_mult=0.5,
        )
    else:
        chunks = repository.find_similar_chunks(query_embedding, req.top_k)

    # R: Return streaming response
    return await stream_answer(
        llm_query,
        chunks,
        llm_service,
        request,
        conversation_id=conversation_id,
        conversation_repository=conversation_repository,
    )
