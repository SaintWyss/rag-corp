# apps/backend/app/crosscutting/pagination.py
"""
===============================================================================
MÓDULO: Utilidades de paginación (cursor base64)
===============================================================================

Objetivo
--------
Paginación simple y consistente para endpoints listados:
- cursor basado en offset codificado
- response genérico Page[T]

-------------------------------------------------------------------------------
CRC (Component Card)
-------------------------------------------------------------------------------
Componente:
  paginate + encode/decode_cursor

Responsabilidades:
  - Codificar/decodificar cursor
  - Armar metadata has_next/has_prev y cursors
===============================================================================
"""

from __future__ import annotations

import base64
from typing import Generic, List, Optional, TypeVar

from pydantic import BaseModel, Field

T = TypeVar("T")


class PageInfo(BaseModel):
    has_next: bool = Field(description="Hay más items después de esta página")
    has_prev: bool = Field(description="Hay items antes de esta página")
    next_cursor: Optional[str] = Field(
        None, description="Cursor para la próxima página"
    )
    prev_cursor: Optional[str] = Field(
        None, description="Cursor para la página anterior"
    )
    total: Optional[int] = Field(None, description="Total (si está disponible)")


class Page(BaseModel, Generic[T]):
    items: List[T] = Field(description="Items de la página actual")
    page_info: PageInfo = Field(description="Metadatos de paginación")


def encode_cursor(offset: int) -> str:
    raw = f"offset:{max(0, int(offset))}".encode("utf-8")
    return base64.urlsafe_b64encode(raw).decode("utf-8")


def decode_cursor(cursor: str) -> int:
    try:
        decoded = base64.urlsafe_b64decode(cursor.encode("utf-8")).decode("utf-8")
        if decoded.startswith("offset:"):
            return max(0, int(decoded.split(":", 1)[1]))
    except Exception:
        pass
    return 0


def paginate(
    items: List[T],
    limit: int,
    cursor: Optional[str] = None,
    total: Optional[int] = None,
) -> Page[T]:
    """
    Si `items` viene con “limit+1”, entonces has_next se calcula solo.
    """
    limit = max(1, int(limit))
    offset = decode_cursor(cursor) if cursor else 0

    has_next = len(items) > limit
    page_items = items[:limit]

    return Page(
        items=page_items,
        page_info=PageInfo(
            has_next=has_next,
            has_prev=offset > 0,
            next_cursor=encode_cursor(offset + limit) if has_next else None,
            prev_cursor=encode_cursor(max(0, offset - limit)) if offset > 0 else None,
            total=total,
        ),
    )
