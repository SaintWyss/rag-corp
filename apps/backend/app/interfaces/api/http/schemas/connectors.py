"""
===============================================================================
TARJETA CRC — schemas/connectors.py
===============================================================================

Módulo:
    Schemas HTTP para Connector Sources

Responsabilidades:
    - Definir DTOs de request/response para endpoints de connectores.
    - Validar campos de entrada (folder_id).

Colaboradores:
    - domain.connectors (ConnectorProvider, ConnectorSourceStatus)
===============================================================================
"""

from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List, Optional
from uuid import UUID

from pydantic import BaseModel, Field

# ---------------------------------------------------------------------------
# Requests
# ---------------------------------------------------------------------------


class CreateConnectorSourceReq(BaseModel):
    """Request para crear una fuente Google Drive."""

    folder_id: str = Field(
        ...,
        min_length=1,
        max_length=500,
        description="ID de la carpeta de Google Drive",
    )


# ---------------------------------------------------------------------------
# Responses
# ---------------------------------------------------------------------------


class ConnectorSourceRes(BaseModel):
    """Representación HTTP de un ConnectorSource."""

    id: UUID
    workspace_id: UUID
    provider: str
    folder_id: str
    status: str
    cursor_json: Optional[Dict[str, Any]] = None
    created_at: datetime
    updated_at: datetime


class ConnectorSourceListRes(BaseModel):
    """Respuesta de listado de fuentes."""

    sources: List[ConnectorSourceRes]
    count: int


class ConnectorDeleteRes(BaseModel):
    """Respuesta de eliminación de fuente."""

    deleted: bool
