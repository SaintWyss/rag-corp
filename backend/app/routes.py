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
from typing import Any
import json
import os
from .config import get_settings
from .rbac import Permission
from .dual_auth import (
    require_admin,
    require_employee_or_admin,
    require_principal,
)
from .error_responses import (
    OPENAPI_ERROR_RESPONSES,
    conflict,
    forbidden,
    not_found,
    payload_too_large,
    service_unavailable,
    unsupported_media,
    validation_error,
)
from .access_control import can_access_document, filter_documents
from .audit import emit_audit_event
from .streaming import stream_answer
from .application.conversations import (
    format_conversation_query,
    resolve_conversation_id,
)
from .application.use_cases import (
    AnswerQueryUseCase,
    AnswerQueryInput,
    AnswerQueryResult,
    ArchiveWorkspaceUseCase,
    ArchiveWorkspaceResult,
    CreateWorkspaceUseCase,
    CreateWorkspaceInput,
    DeleteDocumentUseCase,
    DeleteDocumentResult,
    GetDocumentUseCase,
    GetDocumentResult,
    GetWorkspaceUseCase,
    IngestDocumentUseCase,
    IngestDocumentInput,
    IngestDocumentResult,
    ListDocumentsUseCase,
    ListDocumentsResult,
    ListWorkspacesUseCase,
    PublishWorkspaceUseCase,
    ReprocessDocumentUseCase,
    ReprocessDocumentInput,
    SearchChunksUseCase,
    SearchChunksInput,
    SearchChunksResult,
    ShareWorkspaceUseCase,
    UpdateWorkspaceUseCase,
    UploadDocumentUseCase,
    UploadDocumentInput,
    UploadDocumentResult,
)
from .container import (
    get_answer_query_use_case,
    get_archive_workspace_use_case,
    get_create_workspace_use_case,
    get_ingest_document_use_case,
    get_publish_workspace_use_case,
    get_search_chunks_use_case,
    get_share_workspace_use_case,
    get_llm_service,
    get_conversation_repository,
    get_list_documents_use_case,
    get_list_workspaces_use_case,
    get_get_document_use_case,
    get_get_workspace_use_case,
    get_delete_document_use_case,
    get_update_workspace_use_case,
    get_upload_document_use_case,
    get_reprocess_document_use_case,
)
from .domain.audit import AuditEvent
from .domain.entities import ConversationMessage, Workspace, WorkspaceVisibility
from .domain.workspace_policy import WorkspaceActor
from .application.use_cases.document_results import DocumentErrorCode
from .application.use_cases.workspace_results import WorkspaceErrorCode
from .domain.repositories import AuditEventRepository
from .dual_auth import PrincipalType, Principal
from .container import get_audit_repository
from .users import UserRole

# R: Create API router for RAG endpoints
router = APIRouter(responses=OPENAPI_ERROR_RESPONSES)

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
    file_name: str | None = None
    mime_type: str | None = None
    status: str | None = None
    tags: list[str] = Field(default_factory=list)


class DocumentsListRes(BaseModel):
    documents: list[DocumentSummaryRes]
    next_cursor: str | None = None


class DocumentDetailRes(DocumentSummaryRes):
    deleted_at: datetime | None = None
    error_message: str | None = None


class DeleteDocumentRes(BaseModel):
    deleted: bool


class UploadDocumentRes(BaseModel):
    document_id: UUID
    status: str
    file_name: str
    mime_type: str


class ReprocessDocumentRes(BaseModel):
    document_id: UUID
    status: str
    enqueued: bool


class WorkspaceACL(BaseModel):
    allowed_roles: list[str] = Field(default_factory=list)


class WorkspaceRes(BaseModel):
    id: UUID
    name: str
    visibility: WorkspaceVisibility
    owner_user_id: UUID | None = None
    acl: WorkspaceACL
    created_at: datetime | None = None
    updated_at: datetime | None = None
    archived_at: datetime | None = None


class WorkspacesListRes(BaseModel):
    workspaces: list[WorkspaceRes]


class AuditEventRes(BaseModel):
    id: UUID
    actor: str
    action: str
    target_id: UUID | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)
    created_at: datetime | None = None


class AuditEventsRes(BaseModel):
    events: list[AuditEventRes]
    next_offset: int | None = None


class CreateWorkspaceReq(BaseModel):
    name: str = Field(
        ...,
        min_length=1,
        max_length=_settings.max_title_chars,
        description="Workspace name",
    )
    visibility: WorkspaceVisibility = Field(default=WorkspaceVisibility.PRIVATE)
    owner_user_id: UUID | None = None
    acl: WorkspaceACL = Field(default_factory=WorkspaceACL)

    @field_validator("name")
    @classmethod
    def strip_name(cls, v: str) -> str:
        return v.strip()


class ArchiveWorkspaceRes(BaseModel):
    archived: bool


class UpdateWorkspaceReq(BaseModel):
    name: str | None = Field(
        default=None,
        min_length=1,
        max_length=_settings.max_title_chars,
        description="Workspace name",
    )
    description: str | None = Field(
        default=None,
        max_length=_settings.max_source_chars,
        description="Workspace description",
    )

    @field_validator("name")
    @classmethod
    def strip_name(cls, v: str | None) -> str | None:
        return v.strip() if v is not None else None


class ShareWorkspaceReq(BaseModel):
    user_ids: list[UUID] = Field(
        ...,
        description="List of user IDs to grant read access",
    )


_ALLOWED_MIME_TYPES = {
    "application/pdf",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
}
_ALLOWED_DOCUMENT_STATUSES = {"PENDING", "PROCESSING", "READY", "FAILED"}
_ALLOWED_DOCUMENT_SORTS = {
    "created_at_desc",
    "created_at_asc",
    "title_asc",
    "title_desc",
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


def _to_workspace_res(workspace: Workspace) -> WorkspaceRes:
    return WorkspaceRes(
        id=workspace.id,
        name=workspace.name,
        visibility=workspace.visibility,
        owner_user_id=workspace.owner_user_id,
        acl=WorkspaceACL(allowed_roles=list(workspace.allowed_roles or [])),
        created_at=workspace.created_at,
        updated_at=workspace.updated_at,
        archived_at=workspace.archived_at,
    )


def _to_audit_event_res(event: AuditEvent) -> AuditEventRes:
    return AuditEventRes(
        id=event.id,
        actor=event.actor,
        action=event.action,
        target_id=event.target_id,
        metadata=event.metadata or {},
        created_at=event.created_at,
    )


def _to_workspace_actor(principal: Principal | None) -> WorkspaceActor | None:
    if not principal:
        return None
    if principal.principal_type == PrincipalType.SERVICE:
        return WorkspaceActor(user_id=None, role=UserRole.ADMIN)
    if principal.principal_type != PrincipalType.USER or not principal.user:
        return None
    return WorkspaceActor(
        user_id=principal.user.user_id,
        role=principal.user.role,
    )


def _raise_workspace_error(
    error_code: WorkspaceErrorCode, message: str, workspace_id: UUID | None = None
) -> None:
    if error_code == WorkspaceErrorCode.FORBIDDEN:
        raise forbidden(message)
    if error_code == WorkspaceErrorCode.CONFLICT:
        raise conflict(message)
    if error_code == WorkspaceErrorCode.VALIDATION_ERROR:
        raise validation_error(message)
    if error_code == WorkspaceErrorCode.NOT_FOUND:
        raise not_found("Workspace", str(workspace_id or "unknown"))
    raise validation_error(message)


def _raise_document_error(
    error_code: DocumentErrorCode,
    message: str,
    *,
    resource: str | None = None,
    workspace_id: UUID | None = None,
    document_id: UUID | None = None,
) -> None:
    if error_code == DocumentErrorCode.FORBIDDEN:
        raise forbidden(message)
    if error_code == DocumentErrorCode.CONFLICT:
        raise conflict(message)
    if error_code == DocumentErrorCode.VALIDATION_ERROR:
        raise validation_error(message)
    if error_code == DocumentErrorCode.SERVICE_UNAVAILABLE:
        raise service_unavailable(message)
    if error_code == DocumentErrorCode.NOT_FOUND:
        target = resource or "Document"
        target_id = workspace_id if target == "Workspace" else document_id
        raise not_found(target, str(target_id or "unknown"))
    raise validation_error(message)


def _resolve_legacy_workspace_id(workspace_id: UUID | None) -> UUID:
    if workspace_id:
        return workspace_id
    raise validation_error("workspace_id is required for legacy endpoints.")


def _require_active_workspace(
    workspace_id: UUID,
    use_case: GetWorkspaceUseCase,
    actor: WorkspaceActor | None,
) -> Workspace:
    result = use_case.execute(workspace_id, actor)
    if result.error:
        _raise_workspace_error(result.error.code, result.error.message, workspace_id)
    return result.workspace


@router.get("/workspaces", response_model=WorkspacesListRes, tags=["workspaces"])
def list_workspaces(
    owner_user_id: UUID | None = Query(None),
    include_archived: bool = Query(False),
    use_case: ListWorkspacesUseCase = Depends(get_list_workspaces_use_case),
    principal: Principal | None = Depends(require_principal(Permission.DOCUMENTS_READ)),
    _role: None = Depends(require_employee_or_admin()),
):
    actor = _to_workspace_actor(principal)
    output = use_case.execute(
        actor=actor,
        owner_user_id=owner_user_id,
        include_archived=include_archived,
    )
    if output.error:
        _raise_workspace_error(output.error.code, output.error.message)
    return WorkspacesListRes(
        workspaces=[_to_workspace_res(ws) for ws in output.workspaces]
    )


@router.post(
    "/workspaces",
    response_model=WorkspaceRes,
    status_code=201,
    tags=["workspaces"],
)
def create_workspace(
    req: CreateWorkspaceReq,
    use_case: CreateWorkspaceUseCase = Depends(get_create_workspace_use_case),
    principal: Principal | None = Depends(require_principal(Permission.DOCUMENTS_CREATE)),
    _role: None = Depends(require_employee_or_admin()),
    audit_repo: AuditEventRepository | None = Depends(get_audit_repository),
):
    actor = _to_workspace_actor(principal)
    result = use_case.execute(
        CreateWorkspaceInput(
            name=req.name,
            description=None,
            actor=actor,
            visibility=req.visibility,
        )
    )
    if result.error:
        _raise_workspace_error(result.error.code, result.error.message)
    workspace = result.workspace

    emit_audit_event(
        audit_repo,
        action="workspaces.create",
        principal=principal,
        target_id=workspace.id,
        workspace_id=workspace.id,
    )

    return _to_workspace_res(workspace)


@router.get(
    "/workspaces/{workspace_id}",
    response_model=WorkspaceRes,
    tags=["workspaces"],
)
def get_workspace(
    workspace_id: UUID,
    use_case: GetWorkspaceUseCase = Depends(get_get_workspace_use_case),
    principal: Principal | None = Depends(require_principal(Permission.DOCUMENTS_READ)),
    _role: None = Depends(require_employee_or_admin()),
):
    actor = _to_workspace_actor(principal)
    result = use_case.execute(workspace_id, actor)
    if result.error:
        _raise_workspace_error(result.error.code, result.error.message, workspace_id)
    workspace = result.workspace
    return _to_workspace_res(workspace)


@router.patch(
    "/workspaces/{workspace_id}",
    response_model=WorkspaceRes,
    tags=["workspaces"],
)
def update_workspace(
    workspace_id: UUID,
    req: UpdateWorkspaceReq,
    use_case: UpdateWorkspaceUseCase = Depends(get_update_workspace_use_case),
    principal: Principal | None = Depends(require_principal(Permission.DOCUMENTS_CREATE)),
    _role: None = Depends(require_employee_or_admin()),
    audit_repo: AuditEventRepository | None = Depends(get_audit_repository),
):
    actor = _to_workspace_actor(principal)
    result = use_case.execute(
        workspace_id,
        actor,
        name=req.name,
        description=req.description,
    )
    if result.error:
        _raise_workspace_error(result.error.code, result.error.message, workspace_id)

    emit_audit_event(
        audit_repo,
        action="workspaces.update",
        principal=principal,
        target_id=workspace_id,
        workspace_id=workspace_id,
        metadata={"updated_fields": [key for key, value in req.model_dump().items() if value is not None]},
    )

    return _to_workspace_res(result.workspace)


@router.post(
    "/workspaces/{workspace_id}/publish",
    response_model=WorkspaceRes,
    tags=["workspaces"],
)
def publish_workspace(
    workspace_id: UUID,
    use_case: PublishWorkspaceUseCase = Depends(get_publish_workspace_use_case),
    principal: Principal | None = Depends(require_principal(Permission.DOCUMENTS_CREATE)),
    _role: None = Depends(require_employee_or_admin()),
    audit_repo: AuditEventRepository | None = Depends(get_audit_repository),
):
    actor = _to_workspace_actor(principal)
    result = use_case.execute(workspace_id, actor)
    if result.error:
        _raise_workspace_error(result.error.code, result.error.message, workspace_id)

    emit_audit_event(
        audit_repo,
        action="workspaces.publish",
        principal=principal,
        target_id=workspace_id,
        workspace_id=workspace_id,
    )
    return _to_workspace_res(result.workspace)


@router.post(
    "/workspaces/{workspace_id}/share",
    response_model=WorkspaceRes,
    tags=["workspaces"],
)
def share_workspace(
    workspace_id: UUID,
    req: ShareWorkspaceReq,
    use_case: ShareWorkspaceUseCase = Depends(get_share_workspace_use_case),
    principal: Principal | None = Depends(require_principal(Permission.DOCUMENTS_CREATE)),
    _role: None = Depends(require_employee_or_admin()),
    audit_repo: AuditEventRepository | None = Depends(get_audit_repository),
):
    actor = _to_workspace_actor(principal)
    result = use_case.execute(
        workspace_id,
        actor,
        user_ids=req.user_ids,
    )
    if result.error:
        _raise_workspace_error(result.error.code, result.error.message, workspace_id)

    emit_audit_event(
        audit_repo,
        action="workspaces.share",
        principal=principal,
        target_id=workspace_id,
        workspace_id=workspace_id,
        metadata={
            "shared_user_ids": [str(user_id) for user_id in req.user_ids],
        },
    )
    return _to_workspace_res(result.workspace)


@router.post(
    "/workspaces/{workspace_id}/archive",
    response_model=ArchiveWorkspaceRes,
    tags=["workspaces"],
)
def archive_workspace_action(
    workspace_id: UUID,
    use_case: ArchiveWorkspaceUseCase = Depends(get_archive_workspace_use_case),
    principal: Principal | None = Depends(require_principal(Permission.DOCUMENTS_DELETE)),
    _role: None = Depends(require_employee_or_admin()),
    audit_repo: AuditEventRepository | None = Depends(get_audit_repository),
):
    actor = _to_workspace_actor(principal)
    result: ArchiveWorkspaceResult = use_case.execute(workspace_id, actor)
    if result.error:
        _raise_workspace_error(result.error.code, result.error.message, workspace_id)

    emit_audit_event(
        audit_repo,
        action="workspaces.archive",
        principal=principal,
        target_id=workspace_id,
        workspace_id=workspace_id,
    )

    return ArchiveWorkspaceRes(archived=result.archived)


@router.delete(
    "/workspaces/{workspace_id}",
    response_model=ArchiveWorkspaceRes,
    tags=["workspaces"],
)
def archive_workspace(
    workspace_id: UUID,
    use_case: ArchiveWorkspaceUseCase = Depends(get_archive_workspace_use_case),
    principal: Principal | None = Depends(require_principal(Permission.DOCUMENTS_DELETE)),
    _role: None = Depends(require_employee_or_admin()),
    audit_repo: AuditEventRepository | None = Depends(get_audit_repository),
):
    actor = _to_workspace_actor(principal)
    result: ArchiveWorkspaceResult = use_case.execute(workspace_id, actor)
    if result.error:
        _raise_workspace_error(result.error.code, result.error.message, workspace_id)

    emit_audit_event(
        audit_repo,
        action="workspaces.archive",
        principal=principal,
        target_id=workspace_id,
        workspace_id=workspace_id,
    )

    return ArchiveWorkspaceRes(archived=result.archived)


@router.get(
    "/documents",
    response_model=DocumentsListRes,
    tags=["documents"],
    deprecated=True,
)
def list_documents(
    workspace_id: UUID | None = Query(None),
    q: str | None = Query(None, max_length=200),
    status: str | None = Query(None),
    tag: str | None = Query(None, max_length=64),
    sort: str | None = Query("created_at_desc"),
    cursor: str | None = Query(None),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    use_case: ListDocumentsUseCase = Depends(get_list_documents_use_case),
    principal: Principal | None = Depends(require_principal(Permission.DOCUMENTS_READ)),
    _role: None = Depends(require_employee_or_admin()),
):
    resolved_workspace_id = _resolve_legacy_workspace_id(workspace_id)
    actor = _to_workspace_actor(principal)
    query = q.strip() if q else None
    status_value = status.upper() if status else None
    tag_value = tag.strip() if tag else None
    sort_value = sort or "created_at_desc"

    if status_value and status_value not in _ALLOWED_DOCUMENT_STATUSES:
        raise validation_error("status must be PENDING, PROCESSING, READY, or FAILED.")
    if sort_value not in _ALLOWED_DOCUMENT_SORTS:
        raise validation_error(
            "sort must be created_at_desc, created_at_asc, title_asc, or title_desc."
        )

    output: ListDocumentsResult = use_case.execute(
        workspace_id=resolved_workspace_id,
        actor=actor,
        limit=limit,
        offset=offset,
        cursor=cursor,
        query=query,
        status=status_value,
        tag=tag_value,
        sort=sort_value,
    )
    if output.error:
        _raise_document_error(
            output.error.code,
            output.error.message,
            resource=output.error.resource,
            workspace_id=resolved_workspace_id,
        )
    documents = filter_documents(output.documents, principal)
    return DocumentsListRes(
        documents=[
            DocumentSummaryRes(
                id=doc.id,
                title=doc.title,
                source=doc.source,
                metadata=doc.metadata,
                created_at=doc.created_at,
                file_name=doc.file_name,
                mime_type=doc.mime_type,
                status=doc.status,
                tags=doc.tags,
            )
            for doc in documents
        ],
        next_cursor=output.next_cursor,
    )


@router.get(
    "/documents/{document_id}",
    response_model=DocumentDetailRes,
    tags=["documents"],
    deprecated=True,
)
def get_document(
    document_id: UUID,
    workspace_id: UUID | None = Query(None),
    use_case: GetDocumentUseCase = Depends(get_get_document_use_case),
    principal: Principal | None = Depends(require_principal(Permission.DOCUMENTS_READ)),
    _role: None = Depends(require_employee_or_admin()),
):
    resolved_workspace_id = _resolve_legacy_workspace_id(workspace_id)
    actor = _to_workspace_actor(principal)
    result: GetDocumentResult = use_case.execute(
        workspace_id=resolved_workspace_id,
        document_id=document_id,
        actor=actor,
    )
    if result.error:
        _raise_document_error(
            result.error.code,
            result.error.message,
            resource=result.error.resource,
            workspace_id=resolved_workspace_id,
            document_id=document_id,
        )
    document = result.document
    if not document or not can_access_document(document, principal):
        raise forbidden("Access denied.")
    return DocumentDetailRes(
        id=document.id,
        title=document.title,
        source=document.source,
        metadata=document.metadata,
        created_at=document.created_at,
        deleted_at=document.deleted_at,
        file_name=document.file_name,
        mime_type=document.mime_type,
        status=document.status,
        error_message=document.error_message,
        tags=document.tags,
    )


@router.delete(
    "/documents/{document_id}",
    response_model=DeleteDocumentRes,
    tags=["documents"],
    deprecated=True,
)
def delete_document(
    document_id: UUID,
    workspace_id: UUID | None = Query(None),
    use_case: DeleteDocumentUseCase = Depends(get_delete_document_use_case),
    principal: Principal | None = Depends(require_principal(Permission.DOCUMENTS_DELETE)),
    _role: None = Depends(require_admin()),
    audit_repo: AuditEventRepository | None = Depends(get_audit_repository),
):
    resolved_workspace_id = _resolve_legacy_workspace_id(workspace_id)
    actor = _to_workspace_actor(principal)
    result: DeleteDocumentResult = use_case.execute(
        workspace_id=resolved_workspace_id,
        document_id=document_id,
        actor=actor,
    )
    if result.error:
        _raise_document_error(
            result.error.code,
            result.error.message,
            resource=result.error.resource,
            workspace_id=resolved_workspace_id,
            document_id=document_id,
        )
    emit_audit_event(
        audit_repo,
        action="documents.delete",
        principal=principal,
        target_id=document_id,
        workspace_id=resolved_workspace_id,
    )
    return DeleteDocumentRes(deleted=True)


@router.post(
    "/documents/upload",
    response_model=UploadDocumentRes,
    tags=["documents"],
    deprecated=True,
)
async def upload_document(
    request: Request,
    workspace_id: UUID | None = Query(None),
    file: UploadFile = File(...),
    title: str | None = Form(None),
    source: str | None = Form(None),
    metadata: str | None = Form(None),
    use_case: UploadDocumentUseCase = Depends(get_upload_document_use_case),
    principal: Principal | None = Depends(
        require_principal(Permission.DOCUMENTS_CREATE)
    ),
    _role: None = Depends(require_admin()),
    audit_repo: AuditEventRepository | None = Depends(get_audit_repository),
):
    settings = get_settings()
    resolved_workspace_id = _resolve_legacy_workspace_id(workspace_id)
    actor = _to_workspace_actor(principal)

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

    uploaded_by_user_id = None
    if principal and principal.principal_type == PrincipalType.USER:
        uploaded_by_user_id = principal.user.user_id if principal.user else None

    result: UploadDocumentResult = use_case.execute(
        UploadDocumentInput(
            workspace_id=resolved_workspace_id,
            actor=actor,
            title=doc_title,
            source=source,
            metadata=metadata_payload,
            file_name=file_name,
            mime_type=mime_type,
            content=content,
            uploaded_by_user_id=uploaded_by_user_id,
        )
    )
    if result.error:
        _raise_document_error(
            result.error.code,
            result.error.message,
            resource=result.error.resource,
            workspace_id=resolved_workspace_id,
        )

    await file.close()

    emit_audit_event(
        audit_repo,
        action="documents.upload",
        principal=principal,
        target_id=result.document_id,
        workspace_id=resolved_workspace_id,
        metadata={"file_name": file_name, "mime_type": mime_type},
    )

    return UploadDocumentRes(
        document_id=result.document_id,
        status=result.status,
        file_name=result.file_name,
        mime_type=result.mime_type,
    )


@router.post(
    "/documents/{document_id}/reprocess",
    response_model=ReprocessDocumentRes,
    status_code=202,
    tags=["documents"],
    deprecated=True,
)
def reprocess_document(
    document_id: UUID,
    workspace_id: UUID | None = Query(None),
    use_case: ReprocessDocumentUseCase = Depends(get_reprocess_document_use_case),
    principal: Principal | None = Depends(require_principal(Permission.DOCUMENTS_CREATE)),
    _role: None = Depends(require_admin()),
    audit_repo: AuditEventRepository | None = Depends(get_audit_repository),
):
    resolved_workspace_id = _resolve_legacy_workspace_id(workspace_id)
    actor = _to_workspace_actor(principal)
    result: ReprocessDocumentResult = use_case.execute(
        ReprocessDocumentInput(
            workspace_id=resolved_workspace_id,
            document_id=document_id,
            actor=actor,
        )
    )
    if result.error:
        _raise_document_error(
            result.error.code,
            result.error.message,
            resource=result.error.resource,
            workspace_id=resolved_workspace_id,
            document_id=document_id,
        )

    emit_audit_event(
        audit_repo,
        action="documents.reprocess",
        principal=principal,
        target_id=document_id,
        workspace_id=resolved_workspace_id,
    )

    return ReprocessDocumentRes(
        document_id=result.document_id,
        status=result.status,
        enqueued=result.enqueued,
    )


# R: Endpoint to ingest documents into the RAG system
@router.post(
    "/ingest/text",
    response_model=IngestTextRes,
    tags=["ingest"],
    deprecated=True,
)
def ingest_text(
    req: IngestTextReq,
    workspace_id: UUID | None = Query(None),
    use_case: IngestDocumentUseCase = Depends(get_ingest_document_use_case),
    principal: Principal | None = Depends(
        require_principal(Permission.DOCUMENTS_CREATE)
    ),
    _role: None = Depends(require_admin()),
):
    resolved_workspace_id = _resolve_legacy_workspace_id(workspace_id)
    actor = _to_workspace_actor(principal)
    result: IngestDocumentResult = use_case.execute(
        IngestDocumentInput(
            workspace_id=resolved_workspace_id,
            actor=actor,
            title=req.title,
            text=req.text,
            source=req.source,
            metadata=req.metadata,
        )
    )
    if result.error:
        _raise_document_error(
            result.error.code,
            result.error.message,
            resource=result.error.resource,
            workspace_id=resolved_workspace_id,
        )
    return IngestTextRes(
        document_id=result.document_id,
        chunks=result.chunks_created,
    )


# R: Endpoint for batch document ingestion
@router.post(
    "/ingest/batch",
    response_model=IngestBatchRes,
    tags=["ingest"],
    deprecated=True,
)
def ingest_batch(
    req: IngestBatchReq,
    workspace_id: UUID | None = Query(None),
    use_case: IngestDocumentUseCase = Depends(get_ingest_document_use_case),
    principal: Principal | None = Depends(
        require_principal(Permission.DOCUMENTS_CREATE)
    ),
    _role: None = Depends(require_admin()),
):
    """
    Ingest multiple documents in a single request.

    Processes up to 10 documents sequentially.
    Returns results for all successfully ingested documents.
    """
    results = []
    total_chunks = 0
    resolved_workspace_id = _resolve_legacy_workspace_id(workspace_id)
    actor = _to_workspace_actor(principal)

    for doc in req.documents:
        result: IngestDocumentResult = use_case.execute(
            IngestDocumentInput(
                workspace_id=resolved_workspace_id,
                actor=actor,
                title=doc.title,
                text=doc.text,
                source=doc.source,
                metadata=doc.metadata,
            )
        )
        if result.error:
            _raise_document_error(
                result.error.code,
                result.error.message,
                resource=result.error.resource,
                workspace_id=resolved_workspace_id,
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
@router.post(
    "/query",
    response_model=QueryRes,
    tags=["query"],
    deprecated=True,
)
def query(
    req: QueryReq,
    use_case: SearchChunksUseCase = Depends(get_search_chunks_use_case),
    workspace_id: UUID | None = Query(None),
    principal: Principal | None = Depends(require_principal(Permission.QUERY_SEARCH)),
    _role: None = Depends(require_employee_or_admin()),
):
    resolved_workspace_id = _resolve_legacy_workspace_id(workspace_id)
    actor = _to_workspace_actor(principal)
    result: SearchChunksResult = use_case.execute(
        SearchChunksInput(
            query=req.query,
            workspace_id=resolved_workspace_id,
            actor=actor,
            top_k=req.top_k,
            use_mmr=req.use_mmr,
        )
    )
    if result.error:
        _raise_document_error(
            result.error.code,
            result.error.message,
            resource=result.error.resource,
            workspace_id=resolved_workspace_id,
        )
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
@router.post(
    "/ask",
    response_model=AskRes,
    tags=["query"],
    deprecated=True,
)
def ask(
    req: QueryReq,
    workspace_id: UUID | None = Query(None),
    use_case: AnswerQueryUseCase = Depends(get_answer_query_use_case),
    principal: Principal | None = Depends(require_principal(Permission.QUERY_ASK)),
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

    resolved_workspace_id = _resolve_legacy_workspace_id(workspace_id)
    actor = _to_workspace_actor(principal)

    # R: Execute use case with input data
    result: AnswerQueryResult = use_case.execute(
        AnswerQueryInput(
            query=req.query,
            workspace_id=resolved_workspace_id,
            actor=actor,
            llm_query=llm_query,
            top_k=req.top_k,
            use_mmr=req.use_mmr,
        )
    )
    if result.error:
        _raise_document_error(
            result.error.code,
            result.error.message,
            resource=result.error.resource,
            workspace_id=resolved_workspace_id,
        )

    # R: Convert domain result to HTTP response
    conversation_repository.append_message(
        conversation_id,
        ConversationMessage(role="assistant", content=result.result.answer),
    )
    return AskRes(
        answer=result.result.answer,
        sources=[chunk.content for chunk in result.result.chunks],
        conversation_id=conversation_id,
    )


# R: Streaming endpoint for complete RAG flow (retrieval + generation) with SSE
@router.post(
    "/ask/stream",
    tags=["query"],
    deprecated=True,
)
async def ask_stream(
    req: QueryReq,
    request: Request,
    workspace_id: UUID | None = Query(None),
    use_case: SearchChunksUseCase = Depends(get_search_chunks_use_case),
    principal: Principal | None = Depends(require_principal(Permission.QUERY_STREAM)),
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
    resolved_workspace_id = _resolve_legacy_workspace_id(workspace_id)
    actor = _to_workspace_actor(principal)

    # R: Get dependencies
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
    result: SearchChunksResult = use_case.execute(
        SearchChunksInput(
            query=req.query,
            workspace_id=resolved_workspace_id,
            actor=actor,
            top_k=req.top_k,
            use_mmr=req.use_mmr,
        )
    )
    if result.error:
        _raise_document_error(
            result.error.code,
            result.error.message,
            resource=result.error.resource,
            workspace_id=resolved_workspace_id,
        )
    chunks = result.matches

    # R: Return streaming response
    return await stream_answer(
        llm_query,
        chunks,
        llm_service,
        request,
        conversation_id=conversation_id,
        conversation_repository=conversation_repository,
    )


@router.get(
    "/workspaces/{workspace_id}/documents",
    response_model=DocumentsListRes,
    tags=["workspaces"],
)
def list_workspace_documents(
    workspace_id: UUID,
    q: str | None = Query(None, max_length=200),
    status: str | None = Query(None),
    tag: str | None = Query(None, max_length=64),
    sort: str | None = Query("created_at_desc"),
    cursor: str | None = Query(None),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    workspace_use_case: GetWorkspaceUseCase = Depends(get_get_workspace_use_case),
    use_case: ListDocumentsUseCase = Depends(get_list_documents_use_case),
    principal: Principal | None = Depends(require_principal(Permission.DOCUMENTS_READ)),
    _role: None = Depends(require_employee_or_admin()),
):
    actor = _to_workspace_actor(principal)
    _require_active_workspace(workspace_id, workspace_use_case, actor)
    return list_documents(
        workspace_id=workspace_id,
        q=q,
        status=status,
        tag=tag,
        sort=sort,
        cursor=cursor,
        limit=limit,
        offset=offset,
        use_case=use_case,
        principal=principal,
        _role=_role,
    )


@router.get(
    "/workspaces/{workspace_id}/documents/{document_id}",
    response_model=DocumentDetailRes,
    tags=["workspaces"],
)
def get_workspace_document(
    workspace_id: UUID,
    document_id: UUID,
    workspace_use_case: GetWorkspaceUseCase = Depends(get_get_workspace_use_case),
    use_case: GetDocumentUseCase = Depends(get_get_document_use_case),
    principal: Principal | None = Depends(require_principal(Permission.DOCUMENTS_READ)),
    _role: None = Depends(require_employee_or_admin()),
):
    actor = _to_workspace_actor(principal)
    _require_active_workspace(workspace_id, workspace_use_case, actor)
    return get_document(
        document_id=document_id,
        workspace_id=workspace_id,
        use_case=use_case,
        principal=principal,
        _role=_role,
    )


@router.delete(
    "/workspaces/{workspace_id}/documents/{document_id}",
    response_model=DeleteDocumentRes,
    tags=["workspaces"],
)
def delete_workspace_document(
    workspace_id: UUID,
    document_id: UUID,
    workspace_use_case: GetWorkspaceUseCase = Depends(get_get_workspace_use_case),
    use_case: DeleteDocumentUseCase = Depends(get_delete_document_use_case),
    principal: Principal | None = Depends(require_principal(Permission.DOCUMENTS_DELETE)),
    _role: None = Depends(require_admin()),
    audit_repo: AuditEventRepository | None = Depends(get_audit_repository),
):
    actor = _to_workspace_actor(principal)
    _require_active_workspace(workspace_id, workspace_use_case, actor)
    return delete_document(
        document_id=document_id,
        workspace_id=workspace_id,
        use_case=use_case,
        principal=principal,
        _role=_role,
        audit_repo=audit_repo,
    )


@router.post(
    "/workspaces/{workspace_id}/documents/upload",
    response_model=UploadDocumentRes,
    tags=["workspaces"],
)
async def upload_workspace_document(
    workspace_id: UUID,
    request: Request,
    file: UploadFile = File(...),
    title: str | None = Form(None),
    source: str | None = Form(None),
    metadata: str | None = Form(None),
    workspace_use_case: GetWorkspaceUseCase = Depends(get_get_workspace_use_case),
    use_case: UploadDocumentUseCase = Depends(get_upload_document_use_case),
    principal: Principal | None = Depends(
        require_principal(Permission.DOCUMENTS_CREATE)
    ),
    _role: None = Depends(require_admin()),
    audit_repo: AuditEventRepository | None = Depends(get_audit_repository),
):
    actor = _to_workspace_actor(principal)
    _require_active_workspace(workspace_id, workspace_use_case, actor)
    return await upload_document(
        request=request,
        workspace_id=workspace_id,
        file=file,
        title=title,
        source=source,
        metadata=metadata,
        use_case=use_case,
        principal=principal,
        _role=_role,
        audit_repo=audit_repo,
    )


@router.post(
    "/workspaces/{workspace_id}/documents/{document_id}/reprocess",
    response_model=ReprocessDocumentRes,
    status_code=202,
    tags=["workspaces"],
)
def reprocess_workspace_document(
    workspace_id: UUID,
    document_id: UUID,
    workspace_use_case: GetWorkspaceUseCase = Depends(get_get_workspace_use_case),
    use_case: ReprocessDocumentUseCase = Depends(get_reprocess_document_use_case),
    principal: Principal | None = Depends(require_principal(Permission.DOCUMENTS_CREATE)),
    _role: None = Depends(require_admin()),
    audit_repo: AuditEventRepository | None = Depends(get_audit_repository),
):
    actor = _to_workspace_actor(principal)
    _require_active_workspace(workspace_id, workspace_use_case, actor)
    return reprocess_document(
        document_id=document_id,
        workspace_id=workspace_id,
        use_case=use_case,
        principal=principal,
        _role=_role,
        audit_repo=audit_repo,
    )


@router.post(
    "/workspaces/{workspace_id}/ingest/text",
    response_model=IngestTextRes,
    tags=["workspaces"],
)
def ingest_workspace_text(
    workspace_id: UUID,
    req: IngestTextReq,
    workspace_use_case: GetWorkspaceUseCase = Depends(get_get_workspace_use_case),
    use_case: IngestDocumentUseCase = Depends(get_ingest_document_use_case),
    principal: Principal | None = Depends(require_principal(Permission.DOCUMENTS_CREATE)),
    _role: None = Depends(require_admin()),
):
    actor = _to_workspace_actor(principal)
    _require_active_workspace(workspace_id, workspace_use_case, actor)
    return ingest_text(
        req=req,
        use_case=use_case,
        workspace_id=workspace_id,
        principal=principal,
        _role=_role,
    )


@router.post(
    "/workspaces/{workspace_id}/ingest/batch",
    response_model=IngestBatchRes,
    tags=["workspaces"],
)
def ingest_workspace_batch(
    workspace_id: UUID,
    req: IngestBatchReq,
    workspace_use_case: GetWorkspaceUseCase = Depends(get_get_workspace_use_case),
    use_case: IngestDocumentUseCase = Depends(get_ingest_document_use_case),
    principal: Principal | None = Depends(require_principal(Permission.DOCUMENTS_CREATE)),
    _role: None = Depends(require_admin()),
):
    actor = _to_workspace_actor(principal)
    _require_active_workspace(workspace_id, workspace_use_case, actor)
    return ingest_batch(
        req=req,
        use_case=use_case,
        workspace_id=workspace_id,
        principal=principal,
        _role=_role,
    )


@router.post(
    "/workspaces/{workspace_id}/query",
    response_model=QueryRes,
    tags=["workspaces"],
)
def query_workspace(
    workspace_id: UUID,
    req: QueryReq,
    workspace_use_case: GetWorkspaceUseCase = Depends(get_get_workspace_use_case),
    use_case: SearchChunksUseCase = Depends(get_search_chunks_use_case),
    principal: Principal | None = Depends(require_principal(Permission.QUERY_SEARCH)),
    _role: None = Depends(require_employee_or_admin()),
):
    actor = _to_workspace_actor(principal)
    _require_active_workspace(workspace_id, workspace_use_case, actor)
    return query(
        req=req,
        use_case=use_case,
        workspace_id=workspace_id,
        principal=principal,
        _role=_role,
    )


@router.post(
    "/workspaces/{workspace_id}/ask",
    response_model=AskRes,
    tags=["workspaces"],
)
def ask_workspace(
    workspace_id: UUID,
    req: QueryReq,
    workspace_use_case: GetWorkspaceUseCase = Depends(get_get_workspace_use_case),
    use_case: AnswerQueryUseCase = Depends(get_answer_query_use_case),
    principal: Principal | None = Depends(require_principal(Permission.QUERY_ASK)),
    _role: None = Depends(require_employee_or_admin()),
):
    actor = _to_workspace_actor(principal)
    _require_active_workspace(workspace_id, workspace_use_case, actor)
    return ask(
        req=req,
        use_case=use_case,
        workspace_id=workspace_id,
        principal=principal,
        _role=_role,
    )


@router.post("/workspaces/{workspace_id}/ask/stream", tags=["workspaces"])
async def ask_workspace_stream(
    workspace_id: UUID,
    req: QueryReq,
    request: Request,
    workspace_use_case: GetWorkspaceUseCase = Depends(get_get_workspace_use_case),
    use_case: SearchChunksUseCase = Depends(get_search_chunks_use_case),
    principal: Principal | None = Depends(require_principal(Permission.QUERY_STREAM)),
    _role: None = Depends(require_employee_or_admin()),
):
    actor = _to_workspace_actor(principal)
    _require_active_workspace(workspace_id, workspace_use_case, actor)
    return await ask_stream(
        req=req,
        request=request,
        workspace_id=workspace_id,
        use_case=use_case,
        principal=principal,
        _role=_role,
    )


@router.get(
    "/admin/audit",
    response_model=AuditEventsRes,
    tags=["admin"],
)
def list_audit_events(
    workspace_id: UUID | None = Query(None),
    actor_id: str | None = Query(None),
    action_prefix: str | None = Query(None),
    start_at: datetime | None = Query(None),
    end_at: datetime | None = Query(None),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    audit_repo: AuditEventRepository | None = Depends(get_audit_repository),
    principal: Principal | None = Depends(require_principal(Permission.ADMIN_CONFIG)),
    _role: None = Depends(require_admin()),
):
    if audit_repo is None:
        raise service_unavailable("Audit repository")
    if start_at and end_at and start_at > end_at:
        raise validation_error("start_at must be before end_at.")

    events = audit_repo.list_events(
        workspace_id=workspace_id,
        actor_id=actor_id,
        action_prefix=action_prefix,
        start_at=start_at,
        end_at=end_at,
        limit=limit,
        offset=offset,
    )

    next_offset = offset + limit if len(events) == limit else None
    return AuditEventsRes(
        events=[_to_audit_event_res(event) for event in events],
        next_offset=next_offset,
    )
