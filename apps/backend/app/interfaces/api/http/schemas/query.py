"""
===============================================================================
TARJETA CRC — schemas/query.py
===============================================================================

Módulo:
    Schemas HTTP para Query / Ask (búsqueda y respuesta)

Responsabilidades:
    - DTOs request/response para endpoints de retrieval y generación.
    - Validar query, top_k, flags y conversación.

Colaboradores:
    - crosscutting.config.get_settings (límites)
===============================================================================
"""

from __future__ import annotations

from typing import Annotated
from uuid import UUID

from app.crosscutting.config import get_settings
from pydantic import BaseModel, Field, field_validator

_settings = get_settings()


# -----------------------------------------------------------------------------
# Requests
# -----------------------------------------------------------------------------
class QueryReq(BaseModel):
    """Request para retrieval (similarity o MMR)."""

    query: Annotated[
        str,
        Field(..., min_length=1, max_length=_settings.max_query_chars),
    ]
    top_k: int = Field(default=5, ge=1, le=_settings.max_top_k)
    use_mmr: bool = Field(default=False)

    @field_validator("query")
    @classmethod
    def strip_query(cls, v: str) -> str:
        return v.strip()


class AskReq(BaseModel):
    """Request para Answer (RAG)."""

    query: Annotated[
        str,
        Field(..., min_length=1, max_length=_settings.max_query_chars),
    ]
    conversation_id: str | None = Field(default=None)
    top_k: int = Field(default=5, ge=1, le=_settings.max_top_k)
    use_mmr: bool = Field(default=False)

    @field_validator("query")
    @classmethod
    def strip_query(cls, v: str) -> str:
        return v.strip()


# -----------------------------------------------------------------------------
# Responses
# -----------------------------------------------------------------------------
class Match(BaseModel):
    """Match de retrieval."""

    chunk_id: UUID
    document_id: UUID
    content: str
    score: float


class QueryRes(BaseModel):
    """Response retrieval."""

    matches: list[Match]


class AskRes(BaseModel):
    """Response ask."""

    answer: str
    sources: list[str]
    conversation_id: str | None = None
