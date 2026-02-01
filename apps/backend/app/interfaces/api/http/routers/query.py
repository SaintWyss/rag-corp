"""
===============================================================================
TARJETA CRC — app/interfaces/api/http/routers/query.py
===============================================================================

Name:
    Query Router

Responsibilities:
    - Endpoints HTTP para Search (retrieval) y Ask (RAG).
    - Manejo de conversación (multi-turn) en el borde HTTP.
    - Streaming SSE usando crosscutting.streaming.stream_answer.
    - Traducción de DocumentError / WorkspaceError -> RFC7807.

Collaborators:
    - application.usecases: SearchChunksUseCase, AnswerQueryUseCase
    - domain.repositories: ConversationRepository
    - crosscutting.streaming.stream_answer
    - schemas.query

===============================================================================
"""

from __future__ import annotations

from uuid import UUID

from app.application.conversations import format_conversation_query
from app.application.usecases import (
    AnswerQueryInput,
    AnswerQueryUseCase,
    DocumentError,
    DocumentErrorCode,
    GetWorkspaceUseCase,
    SearchChunksInput,
    SearchChunksUseCase,
    WorkspaceError,
    WorkspaceErrorCode,
)
from app.container import (
    get_answer_query_use_case,
    get_conversation_repository,
    get_get_workspace_use_case,
    get_llm_service,
    get_search_chunks_use_case,
)
from app.crosscutting.config import get_settings
from app.crosscutting.error_responses import (
    conflict,
    forbidden,
    internal_error,
    not_found,
    service_unavailable,
    validation_error,
)
from app.crosscutting.streaming import stream_answer
from app.domain.entities import ConversationMessage
from app.domain.repositories import ConversationRepository
from app.domain.services import LLMService
from app.domain.workspace_policy import WorkspaceActor
from app.identity.dual_auth import (
    Principal,
    require_employee_or_admin,
    require_principal,
)
from app.identity.rbac import Permission
from fastapi import APIRouter, Depends, Request

from ..schemas.query import AskRes, Match, QueryReq, QueryRes

router = APIRouter()
_settings = get_settings()


# =============================================================================
# Helpers
# =============================================================================


def _to_workspace_actor(principal: Principal | None) -> WorkspaceActor | None:
    if principal and principal.user:
        return WorkspaceActor(
            user_id=principal.user.user_id,
            roles=[principal.user.role.value],
        )
    return None


def _raise_document_error(error: DocumentError) -> None:
    if error.code == DocumentErrorCode.VALIDATION_ERROR:
        raise validation_error(error.message)
    if error.code == DocumentErrorCode.NOT_FOUND:
        raise not_found("Document", "-")
    if error.code == DocumentErrorCode.FORBIDDEN:
        raise forbidden("No tenés permisos para acceder a este recurso")
    if error.code == DocumentErrorCode.CONFLICT:
        raise conflict(error.message)
    if error.code == DocumentErrorCode.SERVICE_UNAVAILABLE:
        raise service_unavailable("RAG")
    raise internal_error(error.message)


def _raise_workspace_error(error: WorkspaceError, *, workspace_id: UUID) -> None:
    if error.code == WorkspaceErrorCode.VALIDATION_ERROR:
        raise validation_error(error.message)
    if error.code == WorkspaceErrorCode.NOT_FOUND:
        raise not_found("Workspace", str(workspace_id))
    if error.code == WorkspaceErrorCode.FORBIDDEN:
        raise forbidden("No tenés permisos para acceder a este workspace")
    if error.code == WorkspaceErrorCode.CONFLICT:
        raise conflict(error.message)
    raise internal_error(error.message)


def _require_active_workspace(
    workspace_id: UUID,
    use_case: GetWorkspaceUseCase,
    actor: WorkspaceActor | None,
) -> None:
    result = use_case.execute(workspace_id, actor=actor)
    if result.error is not None:
        _raise_workspace_error(result.error, workspace_id=workspace_id)
    if result.workspace is None:
        raise service_unavailable("Workspace")
    if result.workspace.is_archived:
        raise validation_error("El workspace está archivado")


def _resolve_conversation_id(
    repo: ConversationRepository, conversation_id: str | None
) -> str:
    """
    Garantiza un conversation_id válido usando el contrato real del repo.
    """
    if conversation_id and repo.conversation_exists(conversation_id):
        return conversation_id
    return repo.create_conversation()


# =============================================================================
# Endpoints (compatibilidad)
# =============================================================================


@router.post(
    "/query",
    response_model=QueryRes,
    deprecated=True,
    tags=["query"],
)
def query_compat(
    req: QueryReq,
    workspace_id: UUID,
    use_case: SearchChunksUseCase = Depends(get_search_chunks_use_case),
    workspace_use_case: GetWorkspaceUseCase = Depends(get_get_workspace_use_case),
    principal: Principal | None = Depends(require_principal(Permission.QUERY_SEARCH)),
    _role: None = Depends(require_employee_or_admin()),
):
    actor = _to_workspace_actor(principal)
    _require_active_workspace(workspace_id, workspace_use_case, actor)

    result = use_case.execute(
        SearchChunksInput(
            query=req.query,
            workspace_id=workspace_id,
            actor=actor,
            top_k=req.top_k,
            use_mmr=req.use_mmr,
        )
    )
    if result.error is not None:
        _raise_document_error(result.error)
    if result.matches is None:
        raise service_unavailable("RAG")

    return QueryRes(
        matches=[
            Match(
                chunk_id=c.chunk_id,
                document_id=c.document_id,
                content=c.content,
                score=c.similarity or 0.0,
            )
            for c in result.matches
        ]
    )


@router.post(
    "/ask",
    response_model=AskRes,
    deprecated=True,
    tags=["query"],
)
def ask_compat(
    req: QueryReq,
    workspace_id: UUID,
    use_case: AnswerQueryUseCase = Depends(get_answer_query_use_case),
    workspace_use_case: GetWorkspaceUseCase = Depends(get_get_workspace_use_case),
    conversation_repo: ConversationRepository = Depends(get_conversation_repository),
    principal: Principal | None = Depends(require_principal(Permission.QUERY_ASK)),
    _role: None = Depends(require_employee_or_admin()),
):
    actor = _to_workspace_actor(principal)
    _require_active_workspace(workspace_id, workspace_use_case, actor)

    conv_id = _resolve_conversation_id(conversation_repo, req.conversation_id)
    history = conversation_repo.get_messages(
        conv_id, limit=_settings.max_conversation_messages
    )
    llm_query = format_conversation_query(history, req.query)

    result = use_case.execute(
        AnswerQueryInput(
            query=req.query,
            workspace_id=workspace_id,
            actor=actor,
            llm_query=llm_query,
            top_k=req.top_k,
            use_mmr=req.use_mmr,
        )
    )
    if result.error is not None:
        _raise_document_error(result.error)
    if result.result is None:
        raise service_unavailable("RAG")

    # Best-effort: persistimos conversación
    try:
        conversation_repo.append_message(
            conv_id, ConversationMessage(role="user", content=req.query)
        )
        conversation_repo.append_message(
            conv_id, ConversationMessage(role="assistant", content=result.result.answer)
        )
    except Exception:
        pass

    return AskRes(
        answer=result.result.answer,
        sources=[
            f"{c.document_title or ''}#{c.chunk_index if c.chunk_index is not None else ''}".strip(
                "#"
            )
            for c in result.result.chunks
        ],
        conversation_id=conv_id,
    )


@router.post(
    "/ask/stream",
    deprecated=True,
    tags=["query"],
)
async def ask_stream_compat(
    req: QueryReq,
    workspace_id: UUID,
    request: Request,
    use_case: SearchChunksUseCase = Depends(get_search_chunks_use_case),
    workspace_use_case: GetWorkspaceUseCase = Depends(get_get_workspace_use_case),
    llm_service: LLMService = Depends(get_llm_service),
    principal: Principal | None = Depends(require_principal(Permission.QUERY_STREAM)),
    _role: None = Depends(require_employee_or_admin()),
):
    actor = _to_workspace_actor(principal)
    _require_active_workspace(workspace_id, workspace_use_case, actor)

    search = use_case.execute(
        SearchChunksInput(
            query=req.query,
            workspace_id=workspace_id,
            actor=actor,
            top_k=req.top_k,
            use_mmr=req.use_mmr,
        )
    )
    if search.error is not None:
        _raise_document_error(search.error)
    if search.matches is None:
        raise service_unavailable("RAG")

    return await stream_answer(
        query=req.query,
        chunks=search.matches,
        llm_service=llm_service,
        request=request,
    )


# =============================================================================
# Endpoints workspace-scoped
# =============================================================================


@router.post(
    "/workspaces/{workspace_id}/query",
    response_model=QueryRes,
    tags=["query"],
)
def query_workspace(
    workspace_id: UUID,
    req: QueryReq,
    use_case: SearchChunksUseCase = Depends(get_search_chunks_use_case),
    workspace_use_case: GetWorkspaceUseCase = Depends(get_get_workspace_use_case),
    principal: Principal | None = Depends(require_principal(Permission.QUERY_SEARCH)),
    _role: None = Depends(require_employee_or_admin()),
):
    actor = _to_workspace_actor(principal)
    _require_active_workspace(workspace_id, workspace_use_case, actor)

    result = use_case.execute(
        SearchChunksInput(
            query=req.query,
            workspace_id=workspace_id,
            actor=actor,
            top_k=req.top_k,
            use_mmr=req.use_mmr,
        )
    )
    if result.error is not None:
        _raise_document_error(result.error)
    if result.matches is None:
        raise service_unavailable("RAG")

    return QueryRes(
        matches=[
            Match(
                chunk_id=c.chunk_id,
                document_id=c.document_id,
                content=c.content,
                score=c.similarity or 0.0,
            )
            for c in result.matches
        ]
    )


@router.post(
    "/workspaces/{workspace_id}/ask",
    response_model=AskRes,
    tags=["query"],
)
def ask_workspace(
    workspace_id: UUID,
    req: QueryReq,
    use_case: AnswerQueryUseCase = Depends(get_answer_query_use_case),
    workspace_use_case: GetWorkspaceUseCase = Depends(get_get_workspace_use_case),
    conversation_repo: ConversationRepository = Depends(get_conversation_repository),
    principal: Principal | None = Depends(require_principal(Permission.QUERY_ASK)),
    _role: None = Depends(require_employee_or_admin()),
):
    actor = _to_workspace_actor(principal)
    _require_active_workspace(workspace_id, workspace_use_case, actor)

    conv_id = _resolve_conversation_id(conversation_repo, req.conversation_id)
    history = conversation_repo.get_messages(
        conv_id, limit=_settings.max_conversation_messages
    )
    llm_query = format_conversation_query(history, req.query)

    result = use_case.execute(
        AnswerQueryInput(
            query=req.query,
            workspace_id=workspace_id,
            actor=actor,
            llm_query=llm_query,
            top_k=req.top_k,
            use_mmr=req.use_mmr,
        )
    )
    if result.error is not None:
        _raise_document_error(result.error)
    if result.result is None:
        raise service_unavailable("RAG")

    try:
        conversation_repo.append_message(
            conv_id, ConversationMessage(role="user", content=req.query)
        )
        conversation_repo.append_message(
            conv_id, ConversationMessage(role="assistant", content=result.result.answer)
        )
    except Exception:
        pass

    return AskRes(
        answer=result.result.answer,
        sources=[
            f"{c.document_title or ''}#{c.chunk_index if c.chunk_index is not None else ''}".strip(
                "#"
            )
            for c in result.result.chunks
        ],
        conversation_id=conv_id,
    )


@router.post(
    "/workspaces/{workspace_id}/ask/stream",
    tags=["query"],
)
async def ask_stream_workspace(
    workspace_id: UUID,
    req: QueryReq,
    request: Request,
    use_case: SearchChunksUseCase = Depends(get_search_chunks_use_case),
    workspace_use_case: GetWorkspaceUseCase = Depends(get_get_workspace_use_case),
    llm_service: LLMService = Depends(get_llm_service),
    principal: Principal | None = Depends(require_principal(Permission.QUERY_STREAM)),
    _role: None = Depends(require_employee_or_admin()),
):
    actor = _to_workspace_actor(principal)
    _require_active_workspace(workspace_id, workspace_use_case, actor)

    search = use_case.execute(
        SearchChunksInput(
            query=req.query,
            workspace_id=workspace_id,
            actor=actor,
            top_k=req.top_k,
            use_mmr=req.use_mmr,
        )
    )
    if search.error is not None:
        _raise_document_error(search.error)
    if search.matches is None:
        raise service_unavailable("RAG")

    return await stream_answer(
        query=req.query,
        chunks=search.matches,
        llm_service=llm_service,
        request=request,
    )
