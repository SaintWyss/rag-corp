"""
===============================================================================
TARJETA CRC — domain/connectors.py
===============================================================================

Módulo:
    Entidades y Puertos del subdominio Connectors

Responsabilidades:
    - Definir ConnectorSource (entidad de dominio).
    - Definir ConnectorProvider (enum de proveedores soportados).
    - Definir ConnectorSourceStatus (estados del ciclo de vida).
    - Definir ConnectorSourceRepository (puerto de persistencia).
    - Definir ConnectorClient (puerto para interacción con proveedores).

Colaboradores:
    - infrastructure/repositories: implementaciones concretas.
    - application/usecases/connectors: orquestación.
    - interfaces/api/http/routers: serialización HTTP.

Principios:
    - Sin dependencias a DB/Redis/FastAPI.
    - Solo interfaces + entidades puras.
===============================================================================
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional, Protocol
from uuid import UUID

# ---------------------------------------------------------------------------
# Value Objects / Enums
# ---------------------------------------------------------------------------


class ConnectorProvider(str, Enum):
    """Proveedores de conectores soportados."""

    GOOGLE_DRIVE = "google_drive"


class ConnectorSourceStatus(str, Enum):
    """Estados del ciclo de vida de un ConnectorSource."""

    PENDING = "pending"
    ACTIVE = "active"
    SYNCING = "syncing"
    ERROR = "error"
    DISABLED = "disabled"


# ---------------------------------------------------------------------------
# Entidad
# ---------------------------------------------------------------------------


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


@dataclass
class ConnectorSource:
    """
    Representa una fuente de datos externa vinculada a un workspace.

    Ejemplo: una carpeta de Google Drive configurada para sincronizar
    documentos hacia un workspace de RAG Corp.
    """

    id: UUID
    workspace_id: UUID
    provider: ConnectorProvider
    folder_id: str
    status: ConnectorSourceStatus = ConnectorSourceStatus.PENDING
    cursor_json: Optional[Dict[str, Any]] = field(default_factory=dict)
    created_at: datetime = field(default_factory=_utcnow)
    updated_at: datetime = field(default_factory=_utcnow)

    def mark_active(self) -> None:
        self.status = ConnectorSourceStatus.ACTIVE
        self.updated_at = _utcnow()

    def mark_syncing(self) -> None:
        self.status = ConnectorSourceStatus.SYNCING
        self.updated_at = _utcnow()

    def mark_error(self) -> None:
        self.status = ConnectorSourceStatus.ERROR
        self.updated_at = _utcnow()

    def update_cursor(self, cursor: Dict[str, Any]) -> None:
        self.cursor_json = cursor
        self.updated_at = _utcnow()


# ---------------------------------------------------------------------------
# Puerto: Persistencia
# ---------------------------------------------------------------------------


class ConnectorSourceRepository(Protocol):
    """Contrato de persistencia para ConnectorSource."""

    def create(self, source: ConnectorSource) -> None:
        """Persiste un nuevo ConnectorSource."""
        ...

    def list_by_workspace(
        self,
        workspace_id: UUID,
        *,
        provider: ConnectorProvider | None = None,
    ) -> List[ConnectorSource]:
        """Lista fuentes de un workspace, opcionalmente filtradas por provider."""
        ...

    def get(self, source_id: UUID) -> Optional[ConnectorSource]:
        """Obtiene un ConnectorSource por ID."""
        ...

    def update_status(self, source_id: UUID, status: ConnectorSourceStatus) -> None:
        """Actualiza el status de un ConnectorSource."""
        ...

    def update_cursor(self, source_id: UUID, cursor_json: Dict[str, Any]) -> None:
        """Actualiza el cursor de sincronización."""
        ...

    def delete(self, source_id: UUID) -> bool:
        """Elimina un ConnectorSource. Devuelve True si existía."""
        ...


# ---------------------------------------------------------------------------
# Puerto: Cliente de conector (interacción con provider externo)
# ---------------------------------------------------------------------------


@dataclass
class ConnectorFile:
    """Metadata mínima de un archivo listado por el conector."""

    file_id: str
    name: str
    mime_type: str
    modified_time: Optional[datetime] = None


@dataclass
class ConnectorDelta:
    """Resultado de un delta-sync: archivos nuevos/modificados + nuevo cursor."""

    files: List[ConnectorFile] = field(default_factory=list)
    new_cursor: Optional[Dict[str, Any]] = None


class ConnectorClient(Protocol):
    """
    Contrato para interactuar con un proveedor externo de archivos.

    Nota: La implementación concreta (Google Drive SDK, etc.) vive en infra.
    """

    def list_files(
        self, folder_id: str, *, page_token: str | None = None
    ) -> List[ConnectorFile]:
        """Lista archivos de una carpeta."""
        ...

    def fetch_file_content(self, file_id: str) -> bytes:
        """Descarga el contenido de un archivo."""
        ...

    def get_delta(
        self, folder_id: str, *, cursor: Dict[str, Any] | None = None
    ) -> ConnectorDelta:
        """Obtiene cambios incrementales desde el último cursor."""
        ...
