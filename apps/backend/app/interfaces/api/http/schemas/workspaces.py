"""
===============================================================================
TARJETA CRC — schemas/workspaces.py
===============================================================================

Módulo:
    Schemas HTTP para Workspaces

Responsabilidades:
    - Definir DTOs de request/response para endpoints de workspaces.
    - Validar campos (name/description/ACL) con límites desde settings.
    - Mantener contratos estables y fáciles de versionar.

Colaboradores:
    - domain.entities.WorkspaceVisibility
    - crosscutting.config.get_settings (límites)
===============================================================================
"""

from __future__ import annotations

from datetime import datetime
from typing import Annotated
from uuid import UUID

from app.crosscutting.config import get_settings
from app.domain.entities import AclRole, WorkspaceVisibility
from pydantic import BaseModel, Field, field_validator

_settings = get_settings()


# -----------------------------------------------------------------------------
# Requests
# -----------------------------------------------------------------------------
class WorkspaceACL(BaseModel):
    """ACL del workspace (por roles)."""

    allowed_roles: list[str] = Field(
        default_factory=list,
        description="Lista de roles permitidos (strings normalizados)",
        max_length=50,
    )

    @field_validator("allowed_roles")
    @classmethod
    def normalize_roles(cls, v: list[str]) -> list[str]:
        roles: list[str] = []
        for role in v or []:
            if not isinstance(role, str):
                continue
            cleaned = role.strip().lower()
            if cleaned and cleaned not in roles:
                roles.append(cleaned)
        return roles


class CreateWorkspaceReq(BaseModel):
    """Request para crear workspace."""

    name: Annotated[
        str,
        Field(
            ...,
            min_length=1,
            max_length=_settings.max_title_chars,
            description="Nombre del workspace",
        ),
    ]
    description: str | None = Field(
        default=None,
        max_length=_settings.max_source_chars,
        description="Descripción del workspace",
    )
    visibility: WorkspaceVisibility = Field(default=WorkspaceVisibility.PRIVATE)
    owner_user_id: UUID | None = Field(
        default=None, description="Owner explícito (si aplica)"
    )
    acl: WorkspaceACL = Field(default_factory=WorkspaceACL)

    @field_validator("name")
    @classmethod
    def strip_name(cls, v: str) -> str:
        return v.strip()

    @field_validator("description")
    @classmethod
    def strip_description(cls, v: str | None) -> str | None:
        return v.strip() if v is not None else None


class UpdateWorkspaceReq(BaseModel):
    """Request para actualizar workspace (patch)."""

    name: str | None = Field(
        default=None,
        min_length=1,
        max_length=_settings.max_title_chars,
        description="Nuevo nombre del workspace",
    )
    description: str | None = Field(
        default=None,
        max_length=_settings.max_source_chars,
        description="Descripción",
    )
    visibility: WorkspaceVisibility | None = Field(default=None)
    acl: WorkspaceACL | None = Field(default=None)

    @field_validator("name")
    @classmethod
    def strip_name(cls, v: str | None) -> str | None:
        return v.strip() if v is not None else None

    @field_validator("description")
    @classmethod
    def strip_description(cls, v: str | None) -> str | None:
        return v.strip() if v is not None else None


class ShareWorkspaceReq(BaseModel):
    """Request para reemplazar ACL de usuarios (shared)."""

    user_ids: list[UUID] = Field(
        ..., description="IDs de usuarios con acceso", min_length=0
    )


# -----------------------------------------------------------------------------
# Responses
# -----------------------------------------------------------------------------
class WorkspaceRes(BaseModel):
    """Response de workspace."""

    id: UUID
    name: str
    visibility: WorkspaceVisibility
    owner_user_id: UUID | None = None
    description: str | None = None
    acl: WorkspaceACL = Field(default_factory=WorkspaceACL)
    created_at: datetime | None = None
    updated_at: datetime | None = None
    archived_at: datetime | None = None


class WorkspacesListRes(BaseModel):
    """Listado de workspaces."""

    workspaces: list[WorkspaceRes]
    next_offset: int | None = None


class ArchiveWorkspaceRes(BaseModel):
    """Resultado de archivado / delete lógico."""

    workspace_id: UUID
    archived: bool


# -----------------------------------------------------------------------------
# ACL Management
# -----------------------------------------------------------------------------
class GrantAclReq(BaseModel):
    """Request para otorgar acceso a un usuario en un workspace."""

    user_id: UUID = Field(..., description="ID del usuario al que se otorga acceso")
    role: AclRole = Field(
        default=AclRole.VIEWER, description="Rol de acceso (VIEWER | EDITOR)"
    )


class AclEntryRes(BaseModel):
    """Respuesta: entrada individual de ACL."""

    user_id: UUID
    role: AclRole
    granted_by: UUID | None = None
    created_at: datetime | None = None


class AclListRes(BaseModel):
    """Respuesta: listado de entradas ACL de un workspace."""

    entries: list[AclEntryRes]


class AclRevokeRes(BaseModel):
    """Respuesta: resultado de revocación de acceso."""

    revoked: bool
