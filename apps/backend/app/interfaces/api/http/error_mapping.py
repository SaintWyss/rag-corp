"""
===============================================================================
TARJETA CRC — error_mapping.py (UseCase Error -> HTTP RFC7807)
===============================================================================

Responsabilidades:
  - Traducir códigos de error de casos de uso a HTTP Exceptions RFC7807.
  - Centralizar el mapeo para evitar duplicación en routers.
  - Mantener el dominio libre de HTTP.

Reglas:
  - NUNCA se propagan excepciones de infraestructura hacia la API.
  - Los use cases devuelven errores tipados (code + message [+ resource]).
  - La API traduce a RFC7807 (crosscutting.error_responses).

Colaboradores:
  - application.usecases.* (DocumentErrorCode, WorkspaceErrorCode)
  - crosscutting.error_responses (validation_error, forbidden, etc.)
===============================================================================
"""

from __future__ import annotations

from uuid import UUID

from app.application.usecases import DocumentErrorCode, WorkspaceErrorCode
from app.crosscutting.error_responses import (
    conflict,
    forbidden,
    not_found,
    service_unavailable,
    validation_error,
)


def raise_workspace_error(
    error_code: WorkspaceErrorCode,
    message: str,
    workspace_id: UUID | None = None,
) -> None:
    """
    Traduce WorkspaceErrorCode -> HTTP.

    Nota:
      - workspace_id se usa para NOT_FOUND consistente.
    """
    if error_code == WorkspaceErrorCode.FORBIDDEN:
        raise forbidden(message)
    if error_code == WorkspaceErrorCode.CONFLICT:
        raise conflict(message)
    if error_code == WorkspaceErrorCode.VALIDATION_ERROR:
        raise validation_error(message)
    if error_code == WorkspaceErrorCode.NOT_FOUND:
        raise not_found("Workspace", str(workspace_id or "unknown"))
    raise validation_error(message)


def raise_document_error(
    error_code: DocumentErrorCode,
    message: str,
    *,
    resource: str | None = None,
    workspace_id: UUID | None = None,
    document_id: UUID | None = None,
) -> None:
    """
    Traduce DocumentErrorCode -> HTTP.

    Convención:
      - Si error_code == NOT_FOUND y resource == "Workspace" => usa workspace_id
      - Caso contrario => usa document_id
    """
    if error_code == DocumentErrorCode.FORBIDDEN:
        raise forbidden(message)
    if error_code == DocumentErrorCode.CONFLICT:
        raise conflict(message)
    if error_code == DocumentErrorCode.VALIDATION_ERROR:
        raise validation_error(message)
    if error_code == DocumentErrorCode.SERVICE_UNAVAILABLE:
        # 503 (dependencia externa caída / degradada)
        raise service_unavailable(message)

    if error_code == DocumentErrorCode.NOT_FOUND:
        target = resource or "Document"
        target_id = workspace_id if target == "Workspace" else document_id
        raise not_found(target, str(target_id or "unknown"))

    # Fallback seguro: si aparece un código nuevo, lo tratamos como 422
    raise validation_error(message)
