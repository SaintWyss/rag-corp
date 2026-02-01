"""
===============================================================================
TARJETA CRC — schemas/documents.py
===============================================================================

Módulo:
    Schemas HTTP para Documentos (metadata, listados, detalle, acciones)

Responsabilidades:
    - DTOs de request/response para endpoints de documentos.
    - Validar filtros (status/sort) de forma consistente.
    - Mantener responses listas para UI.

Colaboradores:
    - crosscutting.config.get_settings (límites)
===============================================================================
"""

from __future__ import annotations

from datetime import datetime
from typing import Annotated, Any
from uuid import UUID

from app.crosscutting.config import get_settings
from pydantic import BaseModel, Field, field_validator

_settings = get_settings()

ALLOWED_DOCUMENT_STATUSES: set[str] = {"PENDING", "PROCESSING", "READY", "FAILED"}
ALLOWED_DOCUMENT_SORTS: set[str] = {
    "created_at_desc",
    "created_at_asc",
    "title_asc",
    "title_desc",
}


# -----------------------------------------------------------------------------
# Requests
# -----------------------------------------------------------------------------
class IngestTextReq(BaseModel):
    """Crear documento a partir de texto (ingesta directa)."""

    title: Annotated[
        str,
        Field(..., min_length=1, max_length=_settings.max_title_chars),
    ]
    text: Annotated[
        str,
        Field(..., min_length=1, max_length=_settings.max_ingest_chars),
    ]
    source: str | None = Field(default=None, max_length=_settings.max_source_chars)
    metadata: dict[str, Any] = Field(default_factory=dict)

    @field_validator("title", "text")
    @classmethod
    def strip_required(cls, v: str) -> str:
        return v.strip()

    @field_validator("source")
    @classmethod
    def strip_source(cls, v: str | None) -> str | None:
        return v.strip() if v else None


class IngestBatchReq(BaseModel):
    """Batch de documentos (ingesta texto)."""

    documents: list[IngestTextReq] = Field(
        ...,
        min_length=1,
        max_length=10,
        description="Batch limitado para proteger recursos",
    )


class DocumentsListQuery(BaseModel):
    """Query params validados para listado de documentos.

    Nota:
      - Se usa como modelo auxiliar; el router lo parsea con Depends si quiere.
    """

    query: str | None = Field(default=None, max_length=_settings.max_query_chars)
    status: str | None = Field(default=None)
    tag: str | None = Field(default=None, max_length=64)
    sort: str = Field(default="created_at_desc")
    limit: int = Field(default=50, ge=1, le=200)
    offset: int = Field(default=0, ge=0)

    @field_validator("query")
    @classmethod
    def strip_query(cls, v: str | None) -> str | None:
        return v.strip() if v else None

    @field_validator("status")
    @classmethod
    def normalize_status(cls, v: str | None) -> str | None:
        if not v:
            return None
        value = v.strip().upper()
        if value not in ALLOWED_DOCUMENT_STATUSES:
            raise ValueError("status inválido")
        return value

    @field_validator("sort")
    @classmethod
    def validate_sort(cls, v: str) -> str:
        value = (v or "").strip()
        if value not in ALLOWED_DOCUMENT_SORTS:
            raise ValueError("sort inválido")
        return value


# -----------------------------------------------------------------------------
# Responses
# -----------------------------------------------------------------------------
class DocumentSummaryRes(BaseModel):
    """Resumen para listados."""

    id: UUID
    title: str
    source: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)
    created_at: datetime | None = None

    file_name: str | None = None
    mime_type: str | None = None
    status: str | None = None

    tags: list[str] = Field(default_factory=list)


class DocumentDetailRes(DocumentSummaryRes):
    """Detalle extendido."""

    deleted_at: datetime | None = None
    error_message: str | None = None
    storage_key: str | None = None


class DocumentsListRes(BaseModel):
    """Response de listados."""

    documents: list[DocumentSummaryRes]
    next_cursor: str | None = None


class DeleteDocumentRes(BaseModel):
    """Response de delete."""

    deleted: bool


class UploadDocumentRes(BaseModel):
    """Response de upload + encolado."""

    document_id: UUID
    status: str
    file_name: str
    mime_type: str


class ReprocessDocumentRes(BaseModel):
    """Response de reprocess."""

    document_id: UUID
    status: str
    enqueued: bool


class IngestTextRes(BaseModel):
    """Respuesta de ingesta individual."""

    document_id: UUID
    chunks: int


class IngestBatchRes(BaseModel):
    """Respuesta de ingesta batch."""

    documents: list[IngestTextRes]
    total_chunks: int
