"""
===============================================================================
TARJETA CRC — dependencies.py (Dependencias y helpers comunes)
===============================================================================

Responsabilidades:
  - Centralizar helpers que se repiten en routers:
      * conversión Principal -> WorkspaceActor
      * parseo de metadata JSON
      * validación de filtros (status/sort)
      * validación MIME
      * lectura de UploadFile con límite (anti OOM)
      * helpers de conversación (history -> llm_query)
      * require_active_workspace (helper de guardia)

Patrones aplicados:
  - DRY + Single Responsibility: helpers chicos, reutilizables.
  - Fail-fast: validar temprano y cortar requests peligrosas.
  - Defensive programming: límites y sanitización.

Colaboradores:
  - crosscutting.config.get_settings
  - crosscutting.error_responses (RFC7807 factories)
  - identity.dual_auth.Principal
  - application.conversations (resolve_conversation_id, format_conversation_query)
===============================================================================
"""

from __future__ import annotations

import json
import os
from typing import Any
from uuid import UUID

from app.application.conversations import (
    format_conversation_query,
    resolve_conversation_id,
)
from app.application.usecases import GetWorkspaceUseCase
from app.crosscutting.config import get_settings
from app.crosscutting.error_responses import (
    payload_too_large,
    unsupported_media,
    validation_error,
)
from app.domain.entities import ConversationMessage, Workspace
from app.domain.workspace_policy import WorkspaceActor
from app.identity.dual_auth import Principal, PrincipalType
from app.identity.users import UserRole
from fastapi import UploadFile

# Settings globales (cacheados por lru_cache dentro de get_settings)
_settings = get_settings()

# MIME types permitidos en upload
ALLOWED_MIME_TYPES: set[str] = {
    "application/pdf",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
}

# Filtros válidos para listados de documentos
ALLOWED_DOCUMENT_STATUSES: set[str] = {"PENDING", "PROCESSING", "READY", "FAILED"}
ALLOWED_DOCUMENT_SORTS: set[str] = {
    "created_at_desc",
    "created_at_asc",
    "title_asc",
    "title_desc",
}


def to_workspace_actor(principal: Principal | None) -> WorkspaceActor | None:
    """
    Convierte Principal (auth) -> WorkspaceActor (policy).

    Reglas:
      - SERVICE => ADMIN (sin user_id)
      - USER => user_id + role
      - None => None
    """
    if not principal:
        return None

    if principal.principal_type == PrincipalType.SERVICE:
        return WorkspaceActor(user_id=None, role=UserRole.ADMIN)

    if principal.principal_type != PrincipalType.USER or not principal.user:
        return None

    return WorkspaceActor(user_id=principal.user.user_id, role=principal.user.role)


def parse_metadata(raw: str | None) -> dict[str, Any]:
    """
    Parseo seguro de metadata (form-data).

    Reglas:
      - vacío => {}
      - JSON inválido => 422
      - JSON válido pero no objeto => 422
    """
    if not raw:
        return {}
    try:
        payload = json.loads(raw)
    except json.JSONDecodeError:
        raise validation_error("metadata debe ser JSON válido.")
    if not isinstance(payload, dict):
        raise validation_error("metadata debe ser un objeto JSON.")
    return payload


def validate_mime_type(mime_type: str | None) -> str:
    """Valida y normaliza MIME type del upload."""
    value = (mime_type or "").lower().strip()
    if value not in ALLOWED_MIME_TYPES:
        raise unsupported_media(
            f"Tipo de archivo no soportado: {value or 'desconocido'}"
        )
    return value


def validate_document_filters(
    status: str | None, sort: str | None
) -> tuple[str | None, str]:
    """Valida filtros status/sort en endpoints de listados."""
    status_value = status.upper() if status else None
    sort_value = sort or "created_at_desc"

    if status_value and status_value not in ALLOWED_DOCUMENT_STATUSES:
        raise validation_error("status debe ser PENDING, PROCESSING, READY o FAILED.")
    if sort_value not in ALLOWED_DOCUMENT_SORTS:
        raise validation_error("sort inválido.")
    return status_value, sort_value


def sanitize_filename(filename: str | None) -> str:
    """
    Sanitiza filename para evitar paths raros.
    Nos quedamos con basename.
    """
    if not filename:
        return "upload"
    return os.path.basename(filename)


async def read_upload_bytes(file: UploadFile, *, max_bytes: int | None = None) -> bytes:
    """
    Lee un UploadFile en memoria respetando un límite duro.

    Motivo:
      - Evitar OOM por archivos gigantes.
      - Fail-fast con RFC7807 413.

    Nota:
      - FastAPI/Starlette no garantiza streaming ilimitado seguro si haces file.read()
      - Este helper fuerza lectura por chunks.
    """
    limit = max_bytes if max_bytes is not None else _settings.max_upload_bytes
    if limit <= 0:
        return await file.read()

    chunk_size = 1024 * 1024  # 1MB
    data = bytearray()
    total = 0

    while True:
        piece = await file.read(chunk_size)
        if not piece:
            break
        data.extend(piece)
        total += len(piece)
        if total > limit:
            raise payload_too_large(f"{limit} bytes")

    return bytes(data)


def resolve_workspace_id_required(workspace_id: UUID | None) -> UUID:
    """
    Para endpoints de compatibilidad que aceptan workspace_id por query param.
    """
    if workspace_id:
        return workspace_id
    raise validation_error("workspace_id es obligatorio para este endpoint.")


def require_active_workspace(
    workspace_id: UUID,
    workspace_use_case: GetWorkspaceUseCase,
    actor: WorkspaceActor | None,
) -> Workspace:
    """
    Guardia: workspace debe existir y ser accesible.

    Nota:
      - El mapeo HTTP final lo hacen los routers usando error_mapping.py,
        pero esta función te deja el objeto Workspace listo.
    """
    result = workspace_use_case.execute(workspace_id, actor)
    if result.error:
        # Se eleva como validation_error genérico para no acoplar aquí a error_mapping;
        # el router puede usar error_mapping si prefiere.
        raise validation_error(result.error.message)
    assert result.workspace is not None
    return result.workspace


def prepare_conversation_context(
    conversation_repository,
    conversation_id: str | None,
    user_query: str,
) -> tuple[str, str]:
    """
    Arma contexto conversacional:
      - resuelve/crea conversation_id
      - arma llm_query con historial
      - registra mensaje del usuario en el repo
    """
    conv_id = resolve_conversation_id(conversation_repository, conversation_id)
    history = conversation_repository.get_messages(
        conv_id,
        limit=_settings.max_conversation_messages,
    )
    llm_query = format_conversation_query(history, user_query)

    conversation_repository.append_message(
        conv_id,
        ConversationMessage(role="user", content=user_query),
    )
    return conv_id, llm_query
