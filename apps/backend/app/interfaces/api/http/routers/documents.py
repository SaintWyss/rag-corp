"""
===============================================================================
TARJETA CRC — app/interfaces/api/http/routers/documents.py
===============================================================================

Name:
    Documents Router

Responsibilities:
    - Endpoints HTTP para documentos (list/get/delete/upload/reprocess/ingest).
    - Validaciones de borde (MIME, límites de tamaño, metadata JSON).
    - Mapeo de DocumentError -> RFC7807.
    - Enforce de workspace activo antes de operar.
    - Auditoría best-effort.

Collaborators:
    - application.usecases: List/Get/Delete/Upload/Reprocess/Ingest
    - identity.access_control: can_access_document, filter_documents
    - schemas.documents
    - container factories
===============================================================================
"""

from __future__ import annotations

import json
from typing import Any
from uuid import UUID

from app.application.usecases import (
    DeleteDocumentUseCase,
    DocumentError,
    DocumentErrorCode,
    GetDocumentUseCase,
    GetWorkspaceUseCase,
    IngestDocumentInput,
    IngestDocumentUseCase,
    ListDocumentsUseCase,
    ReprocessDocumentInput,
    ReprocessDocumentUseCase,
    UploadDocumentInput,
    UploadDocumentUseCase,
    WorkspaceError,
    WorkspaceErrorCode,
)
from app.audit import emit_audit_event
from app.container import (
    get_audit_repository,
    get_delete_document_use_case,
    get_get_document_use_case,
    get_get_workspace_use_case,
    get_ingest_document_use_case,
    get_list_documents_use_case,
    get_reprocess_document_use_case,
    get_upload_document_use_case,
)
from app.crosscutting.config import get_settings
from app.crosscutting.error_responses import (
    conflict,
    forbidden,
    internal_error,
    not_found,
    payload_too_large,
    service_unavailable,
    unsupported_media,
    validation_error,
)
from app.domain.entities import Document
from app.domain.repositories import AuditEventRepository
from app.domain.workspace_policy import WorkspaceActor
from app.identity.access_control import can_access_document, filter_documents
from app.identity.dual_auth import (
    Principal,
    require_admin,
    require_employee_or_admin,
    require_principal,
)
from app.identity.rbac import Permission
from fastapi import APIRouter, Depends, File, Form, UploadFile

from ..schemas.documents import (
    DeleteDocumentRes,
    DocumentDetailRes,
    DocumentsListRes,
    DocumentSummaryRes,
    IngestBatchReq,
    IngestBatchRes,
    IngestTextReq,
    IngestTextRes,
    ReprocessDocumentRes,
    UploadDocumentRes,
)

router = APIRouter()
_settings = get_settings()

_ALLOWED_MIME_TYPES = {
    "application/pdf",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
}


# =============================================================================
# Helpers
# =============================================================================


def _to_workspace_actor(principal: Principal | None) -> WorkspaceActor | None:
    if principal and principal.user:
        return WorkspaceActor(
            user_id=principal.user.user_id,
            role=principal.user.role,
        )
    return None


def _parse_metadata(raw: str | None) -> dict[str, Any] | None:
    """
    Metadata llega como string JSON desde FormData.
    """
    if not raw:
        return None
    try:
        data = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise validation_error(f"metadata debe ser JSON válido: {exc}")

    if data is None:
        return None
    if not isinstance(data, dict):
        raise validation_error("metadata debe ser un objeto JSON")
    return data


def _raise_document_error(
    error: DocumentError, *, document_id: UUID | None = None
) -> None:
    if error.code == DocumentErrorCode.VALIDATION_ERROR:
        raise validation_error(error.message)
    if error.code == DocumentErrorCode.NOT_FOUND:
        raise not_found("Document", str(document_id or "-"))
    if error.code == DocumentErrorCode.FORBIDDEN:
        raise forbidden("No tenés permisos para acceder a este documento")
    if error.code == DocumentErrorCode.CONFLICT:
        raise conflict(error.message)
    if error.code == DocumentErrorCode.SERVICE_UNAVAILABLE:
        raise service_unavailable("Document")
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


def _to_document_summary(doc: Document) -> DocumentSummaryRes:
    return DocumentSummaryRes(
        id=doc.id,
        title=doc.title,
        status=doc.status,
        mime_type=doc.mime_type,
        file_name=doc.file_name,
        source=doc.source,
        tags=list(doc.tags or []),
        created_at=doc.created_at,
        updated_at=doc.updated_at,
    )


def _to_document_detail(doc: Document) -> DocumentDetailRes:
    return DocumentDetailRes(
        id=doc.id,
        workspace_id=doc.workspace_id,
        title=doc.title,
        status=doc.status,
        mime_type=doc.mime_type,
        file_name=doc.file_name,
        source=doc.source,
        storage_key=doc.storage_key,
        content_hash=doc.content_hash,
        metadata=doc.metadata or {},
        tags=list(doc.tags or []),
        allowed_roles=list(doc.allowed_roles or []),
        created_at=doc.created_at,
        updated_at=doc.updated_at,
        deleted_at=doc.deleted_at,
        archived_at=doc.archived_at,
    )


def _require_active_workspace(
    workspace_id: UUID,
    use_case: GetWorkspaceUseCase,
    actor: WorkspaceActor | None,
) -> None:
    """
    Enforce: existe y no está archivado.
    """
    result = use_case.execute(workspace_id, actor=actor)
    if result.error is not None:
        _raise_workspace_error(result.error, workspace_id=workspace_id)
    if result.workspace is None:
        raise service_unavailable("Workspace")
    if result.workspace.is_archived:
        raise validation_error("El workspace está archivado")


async def _read_upload_bytes(file: UploadFile) -> bytes:
    content = await file.read()
    if len(content) > _settings.max_upload_bytes:
        raise payload_too_large(max_size=f"{_settings.max_upload_bytes} bytes")
    return content


# =============================================================================
# Endpoints (globales - marcados deprecated para compatibilidad)
# =============================================================================


@router.get(
    "/documents",
    response_model=DocumentsListRes,
    deprecated=True,
    tags=["documents"],
)
def list_documents(
    workspace_id: UUID | None = None,
    status: str | None = None,
    limit: int = 50,
    offset: int = 0,
    use_case: ListDocumentsUseCase = Depends(get_list_documents_use_case),
    principal: Principal | None = Depends(require_principal(Permission.DOCUMENTS_READ)),
    _role: None = Depends(require_employee_or_admin()),
):
    if workspace_id is None:
        raise validation_error("workspace_id es requerido")

    actor = _to_workspace_actor(principal)
    result = use_case.execute(
        workspace_id=workspace_id,
        actor=actor,
        status=status,
        limit=limit,
        offset=offset,
    )

    if result.error is not None:
        _raise_document_error(result.error)

    docs = filter_documents(result.documents or [], principal)
    next_offset = offset + limit if len(result.documents or []) == limit else None

    return DocumentsListRes(
        documents=[_to_document_summary(d) for d in docs],
        next_offset=next_offset,
    )


@router.get(
    "/documents/{document_id}",
    response_model=DocumentDetailRes,
    deprecated=True,
    tags=["documents"],
)
def get_document(
    document_id: UUID,
    workspace_id: UUID,
    use_case: GetDocumentUseCase = Depends(get_get_document_use_case),
    principal: Principal | None = Depends(require_principal(Permission.DOCUMENTS_READ)),
    _role: None = Depends(require_employee_or_admin()),
):
    actor = _to_workspace_actor(principal)
    result = use_case.execute(
        workspace_id=workspace_id,
        document_id=document_id,
        actor=actor,
    )
    if result.error is not None:
        if isinstance(result.error, WorkspaceError):
            _raise_workspace_error(result.error, workspace_id=workspace_id)
        _raise_document_error(result.error, document_id=document_id)
    if result.document is None:
        raise not_found("Document", str(document_id))

    if not can_access_document(result.document, principal):
        raise forbidden("No tenés permisos para acceder a este documento")

    return _to_document_detail(result.document)


@router.delete(
    "/documents/{document_id}",
    response_model=DeleteDocumentRes,
    deprecated=True,
    tags=["documents"],
)
def delete_document(
    document_id: UUID,
    workspace_id: UUID,
    use_case: DeleteDocumentUseCase = Depends(get_delete_document_use_case),
    principal: Principal | None = Depends(
        require_principal(Permission.DOCUMENTS_DELETE)
    ),
    _role: None = Depends(require_admin()),
    audit_repo: AuditEventRepository | None = Depends(get_audit_repository),
):
    actor = _to_workspace_actor(principal)
    result = use_case.execute(
        workspace_id=workspace_id,
        document_id=document_id,
        actor=actor,
    )
    if result.error is not None:
        if isinstance(result.error, WorkspaceError):
            _raise_workspace_error(result.error, workspace_id=workspace_id)
        _raise_document_error(result.error, document_id=document_id)

    emit_audit_event(
        audit_repo,
        action="document.delete",
        principal=principal,
        target_id=document_id,
        metadata={"deprecated_endpoint": True},
    )
    return DeleteDocumentRes(document_id=document_id, deleted=True)


@router.post(
    "/documents/upload",
    response_model=UploadDocumentRes,
    deprecated=True,
    tags=["documents"],
)
async def upload_document(
    file: UploadFile = File(...),
    workspace_id: UUID = Form(...),
    title: str = Form(...),
    source: str | None = Form(None),
    metadata: str | None = Form(None),
    use_case: UploadDocumentUseCase = Depends(get_upload_document_use_case),
    workspace_use_case: GetWorkspaceUseCase = Depends(get_get_workspace_use_case),
    principal: Principal | None = Depends(
        require_principal(Permission.DOCUMENTS_CREATE)
    ),
    _role: None = Depends(require_employee_or_admin()),
    audit_repo: AuditEventRepository | None = Depends(get_audit_repository),
):
    if file.content_type not in _ALLOWED_MIME_TYPES:
        raise unsupported_media(f"Tipo de archivo no soportado: {file.content_type}")

    actor = _to_workspace_actor(principal)
    _require_active_workspace(workspace_id, workspace_use_case, actor)

    content = await _read_upload_bytes(file)
    md = _parse_metadata(metadata)

    doc_title = (title or "").strip() or (file.filename or "documento")
    if len(doc_title) > _settings.max_title_chars:
        doc_title = doc_title[: _settings.max_title_chars]

    input_data = UploadDocumentInput(
        workspace_id=workspace_id,
        actor=actor,
        title=doc_title,
        file_name=file.filename or "",
        mime_type=file.content_type,
        content=content,
        source=source,
        metadata=md,
        uploaded_by_user_id=(
            principal.user.user_id if principal and principal.user else None
        ),
    )

    result = use_case.execute(input_data)
    if result.error is not None:
        _raise_document_error(result.error)

    emit_audit_event(
        audit_repo,
        action="document.upload",
        principal=principal,
        workspace_id=workspace_id,
        target_id=result.document_id,
        metadata={"mime_type": file.content_type, "file_name": file.filename or ""},
    )

    return UploadDocumentRes(
        document_id=result.document_id,
        status=result.status,
        file_name=file.filename or "",
        mime_type=file.content_type,
    )


@router.post(
    "/workspaces/{workspace_id}/documents/{document_id}/reprocess",
    response_model=ReprocessDocumentRes,
    status_code=202,
    tags=["documents"],
)
def reprocess_workspace_document(
    workspace_id: UUID,
    document_id: UUID,
    use_case: ReprocessDocumentUseCase = Depends(get_reprocess_document_use_case),
    principal: Principal | None = Depends(
        require_principal(Permission.DOCUMENTS_CREATE)
    ),
    _role: None = Depends(require_employee_or_admin()),
):
    actor = _to_workspace_actor(principal)
    input_data = ReprocessDocumentInput(
        workspace_id=workspace_id,
        document_id=document_id,
        actor=actor,
    )
    result = use_case.execute(input_data)

    if result.error is not None:
        if isinstance(result.error, WorkspaceError):
            _raise_workspace_error(result.error, workspace_id=workspace_id)
        _raise_document_error(result.error, document_id=document_id)

    return ReprocessDocumentRes(
        document_id=document_id,
        status=result.status,
        enqueued=result.enqueued,
    )


@router.post(
    "/documents/{document_id}/reprocess",
    response_model=ReprocessDocumentRes,
    status_code=202,
    deprecated=True,
    tags=["documents"],
)
def reprocess_document(
    document_id: UUID,
    workspace_id: UUID,
    use_case: ReprocessDocumentUseCase = Depends(get_reprocess_document_use_case),
    principal: Principal | None = Depends(
        require_principal(Permission.DOCUMENTS_CREATE)
    ),
    _role: None = Depends(require_employee_or_admin()),
):
    actor = _to_workspace_actor(principal)
    input_data = ReprocessDocumentInput(
        workspace_id=workspace_id,
        document_id=document_id,
        actor=actor,
    )
    result = use_case.execute(input_data)

    if result.error is not None:
        if isinstance(result.error, WorkspaceError):
            _raise_workspace_error(result.error, workspace_id=workspace_id)
        _raise_document_error(result.error, document_id=document_id)

    return ReprocessDocumentRes(
        document_id=document_id,
        status=result.status,
        enqueued=result.enqueued,
    )


@router.post(
    "/ingest/text",
    response_model=IngestTextRes,
    deprecated=True,
    tags=["ingest"],
)
def ingest_text(
    req: IngestTextReq,
    workspace_id: UUID,
    use_case: IngestDocumentUseCase = Depends(get_ingest_document_use_case),
    workspace_use_case: GetWorkspaceUseCase = Depends(get_get_workspace_use_case),
    principal: Principal | None = Depends(
        require_principal(Permission.DOCUMENTS_CREATE)
    ),
    _role: None = Depends(require_employee_or_admin()),
):
    actor = _to_workspace_actor(principal)
    _require_active_workspace(workspace_id, workspace_use_case, actor)

    input_data = IngestDocumentInput(
        workspace_id=workspace_id,
        actor=actor,
        title=req.title,
        text=req.text,
        source=req.source,
        metadata=req.metadata,
    )

    result = use_case.execute(input_data)
    if result.error is not None:
        _raise_document_error(result.error)

    return IngestTextRes(document_id=result.document_id, chunks=result.chunks)


@router.post(
    "/ingest/batch",
    response_model=IngestBatchRes,
    deprecated=True,
    tags=["ingest"],
)
def ingest_batch(
    req: IngestBatchReq,
    workspace_id: UUID,
    use_case: IngestDocumentUseCase = Depends(get_ingest_document_use_case),
    workspace_use_case: GetWorkspaceUseCase = Depends(get_get_workspace_use_case),
    principal: Principal | None = Depends(
        require_principal(Permission.DOCUMENTS_CREATE)
    ),
    _role: None = Depends(require_employee_or_admin()),
):
    actor = _to_workspace_actor(principal)
    _require_active_workspace(workspace_id, workspace_use_case, actor)

    results: list[IngestTextRes] = []
    total_chunks = 0

    for doc in req.documents:
        r = use_case.execute(
            IngestDocumentInput(
                workspace_id=workspace_id,
                actor=actor,
                title=doc.title,
                text=doc.text,
                source=doc.source,
                metadata=doc.metadata,
            )
        )
        if r.error is not None:
            _raise_document_error(r.error)
        results.append(IngestTextRes(document_id=r.document_id, chunks=r.chunks))
        total_chunks += r.chunks

    return IngestBatchRes(documents=results, total_chunks=total_chunks)


# =============================================================================
# Endpoints workspace-scoped (recomendados)
# =============================================================================


@router.get(
    "/workspaces/{workspace_id}/documents",
    response_model=DocumentsListRes,
    tags=["documents"],
)
def list_workspace_documents(
    workspace_id: UUID,
    status: str | None = None,
    limit: int = 50,
    offset: int = 0,
    use_case: ListDocumentsUseCase = Depends(get_list_documents_use_case),
    workspace_use_case: GetWorkspaceUseCase = Depends(get_get_workspace_use_case),
    principal: Principal | None = Depends(require_principal(Permission.DOCUMENTS_READ)),
    _role: None = Depends(require_employee_or_admin()),
):
    actor = _to_workspace_actor(principal)
    _require_active_workspace(workspace_id, workspace_use_case, actor)

    result = use_case.execute(
        workspace_id=workspace_id,
        actor=actor,
        status=status,
        limit=limit,
        offset=offset,
    )
    if result.error is not None:
        _raise_document_error(result.error)

    docs = filter_documents(result.documents or [], principal)
    next_offset = offset + limit if len(result.documents or []) == limit else None

    return DocumentsListRes(
        documents=[_to_document_summary(d) for d in docs],
        next_offset=next_offset,
    )


@router.get(
    "/workspaces/{workspace_id}/documents/{document_id}",
    response_model=DocumentDetailRes,
    tags=["documents"],
)
def get_workspace_document(
    workspace_id: UUID,
    document_id: UUID,
    use_case: GetDocumentUseCase = Depends(get_get_document_use_case),
    workspace_use_case: GetWorkspaceUseCase = Depends(get_get_workspace_use_case),
    principal: Principal | None = Depends(require_principal(Permission.DOCUMENTS_READ)),
    _role: None = Depends(require_employee_or_admin()),
):
    actor = _to_workspace_actor(principal)
    _require_active_workspace(workspace_id, workspace_use_case, actor)

    result = use_case.execute(
        workspace_id=workspace_id,
        document_id=document_id,
        actor=actor,
    )
    if result.error is not None:
        if isinstance(result.error, WorkspaceError):
            _raise_workspace_error(result.error, workspace_id=workspace_id)
        _raise_document_error(result.error, document_id=document_id)
    if result.document is None:
        raise not_found("Document", str(document_id))

    if not can_access_document(result.document, principal):
        raise forbidden("No tenés permisos para acceder a este documento")

    return _to_document_detail(result.document)


@router.delete(
    "/workspaces/{workspace_id}/documents/{document_id}",
    response_model=DeleteDocumentRes,
    tags=["documents"],
)
def delete_workspace_document(
    workspace_id: UUID,
    document_id: UUID,
    use_case: DeleteDocumentUseCase = Depends(get_delete_document_use_case),
    workspace_use_case: GetWorkspaceUseCase = Depends(get_get_workspace_use_case),
    principal: Principal | None = Depends(
        require_principal(Permission.DOCUMENTS_DELETE)
    ),
    _role: None = Depends(require_employee_or_admin()),
    audit_repo: AuditEventRepository | None = Depends(get_audit_repository),
):
    actor = _to_workspace_actor(principal)
    _require_active_workspace(workspace_id, workspace_use_case, actor)

    result = use_case.execute(
        workspace_id=workspace_id,
        document_id=document_id,
        actor=actor,
    )
    if result.error is not None:
        if isinstance(result.error, WorkspaceError):
            _raise_workspace_error(result.error, workspace_id=workspace_id)
        _raise_document_error(result.error, document_id=document_id)

    emit_audit_event(
        audit_repo,
        action="document.delete",
        principal=principal,
        workspace_id=workspace_id,
        target_id=document_id,
    )

    return DeleteDocumentRes(document_id=document_id, deleted=True)


@router.post(
    "/workspaces/{workspace_id}/documents/upload",
    response_model=UploadDocumentRes,
    status_code=202,
    tags=["documents"],
)
async def upload_workspace_document(
    workspace_id: UUID,
    file: UploadFile = File(...),
    title: str = Form(...),
    source: str | None = Form(None),
    metadata: str | None = Form(None),
    use_case: UploadDocumentUseCase = Depends(get_upload_document_use_case),
    workspace_use_case: GetWorkspaceUseCase = Depends(get_get_workspace_use_case),
    principal: Principal | None = Depends(
        require_principal(Permission.DOCUMENTS_CREATE)
    ),
    _role: None = Depends(require_employee_or_admin()),
    audit_repo: AuditEventRepository | None = Depends(get_audit_repository),
):
    if file.content_type not in _ALLOWED_MIME_TYPES:
        raise unsupported_media(f"Tipo de archivo no soportado: {file.content_type}")

    actor = _to_workspace_actor(principal)
    _require_active_workspace(workspace_id, workspace_use_case, actor)

    content = await _read_upload_bytes(file)
    md = _parse_metadata(metadata)

    doc_title = (title or "").strip() or (file.filename or "documento")
    if len(doc_title) > _settings.max_title_chars:
        doc_title = doc_title[: _settings.max_title_chars]

    result = use_case.execute(
        UploadDocumentInput(
            workspace_id=workspace_id,
            actor=actor,
            title=doc_title,
            file_name=file.filename or "",
            mime_type=file.content_type,
            content=content,
            source=source,
            metadata=md,
            uploaded_by_user_id=(
                principal.user.user_id if principal and principal.user else None
            ),
        )
    )
    if result.error is not None:
        _raise_document_error(result.error)

    emit_audit_event(
        audit_repo,
        action="document.upload",
        principal=principal,
        workspace_id=workspace_id,
        target_id=result.document_id,
        metadata={"mime_type": file.content_type, "file_name": file.filename or ""},
    )

    return UploadDocumentRes(
        document_id=result.document_id,
        status=result.status,
        file_name=file.filename or "",
        mime_type=file.content_type,
    )
