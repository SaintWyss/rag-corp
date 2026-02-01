"""
===============================================================================
TARJETA CRC — domain/entities.py
===============================================================================

Módulo:
    Entidades del Dominio (Document, Workspace, Chunk, QueryResult, Conversation)

Responsabilidades:
    - Definir estructuras centrales del negocio (sin infraestructura).
    - Brindar helpers mínimos (métodos) para mantener invariantes simples.
    - Mantener tipos claros para casos de uso y repositorios.

Colaboradores:
    - domain.repositories: persisten/recuperan estas entidades.
    - application/usecases: construyen/consumen estas entidades.
    - interfaces/api: serializan/retornan DTOs basados en estas entidades.

Principios:
    - Sin dependencias a DB/Redis/FastAPI.
    - Datos + comportamiento mínimo (no “anemia total”, pero sin lógica pesada).
===============================================================================
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Literal, Optional
from uuid import UUID


def _utcnow() -> datetime:
    """Fecha/hora UTC (helper interno)."""
    return datetime.now(timezone.utc)


# ---------------------------------------------------------------------------
# Document
# ---------------------------------------------------------------------------


@dataclass
class Document:
    """
    Documento del sistema (metadata + estado).

    Importante:
      - El contenido (bytes) vive fuera: storage.
      - Los chunks/embeddings viven fuera: repositorios de chunks.
    """

    id: UUID
    title: str
    workspace_id: Optional[UUID] = None
    source: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    created_at: Optional[datetime] = None
    deleted_at: Optional[datetime] = None

    # Metadatos de archivo
    file_name: Optional[str] = None
    mime_type: Optional[str] = None
    storage_key: Optional[str] = None
    uploaded_by_user_id: Optional[UUID] = None

    # Estado de procesamiento
    status: Optional[str] = None
    error_message: Optional[str] = None

    # Organización / permisos
    tags: List[str] = field(default_factory=list)
    allowed_roles: List[str] = field(default_factory=list)

    @property
    def is_deleted(self) -> bool:
        """True si está soft-deleted."""
        return self.deleted_at is not None

    def mark_deleted(self, *, at: datetime | None = None) -> None:
        """Marca el documento como eliminado (soft delete)."""
        self.deleted_at = at or _utcnow()

    def restore(self) -> None:
        """Restaura un documento soft-deleted."""
        self.deleted_at = None

    def set_processing_status(
        self, status: str, *, error_message: str | None = None
    ) -> None:
        """
        Actualiza estado de procesamiento del documento.

        Nota:
          - No valida el flujo de estados (eso puede vivir en application).
          - Sí centraliza la intención para evitar writes inconsistentes.
        """
        self.status = status
        self.error_message = error_message


# ---------------------------------------------------------------------------
# Workspace
# ---------------------------------------------------------------------------


class WorkspaceVisibility(str, Enum):
    """Visibilidad del workspace."""

    PRIVATE = "PRIVATE"
    ORG_READ = "ORG_READ"
    SHARED = "SHARED"


@dataclass
class Workspace:
    """Workspace: contenedor lógico de documentos."""

    id: UUID
    name: str
    visibility: WorkspaceVisibility = WorkspaceVisibility.PRIVATE
    owner_user_id: Optional[UUID] = None
    description: Optional[str] = None

    # Control de acceso
    allowed_roles: List[str] = field(default_factory=list)
    shared_user_ids: List[UUID] = field(default_factory=list)

    # Auditoría
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    archived_at: Optional[datetime] = None

    @property
    def is_archived(self) -> bool:
        """True si está archivado."""
        return self.archived_at is not None

    def archive(self, *, at: datetime | None = None) -> None:
        """Archiva el workspace (soft)."""
        self.archived_at = at or _utcnow()

    def unarchive(self) -> None:
        """Des-archiva el workspace."""
        self.archived_at = None


# ---------------------------------------------------------------------------
# Chunk
# ---------------------------------------------------------------------------


@dataclass
class Chunk:
    """
    Fragmento de texto con embedding.

    Nota:
      - similarity es un atributo “de resultado” (search).
      - metadata es flexible (ej: page_number, offsets, etc.).
    """

    content: str
    embedding: List[float]
    document_id: Optional[UUID] = None
    document_title: Optional[str] = None
    document_source: Optional[str] = None
    chunk_index: Optional[int] = None
    chunk_id: Optional[UUID] = None
    similarity: Optional[float] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


# ---------------------------------------------------------------------------
# QueryResult
# ---------------------------------------------------------------------------


@dataclass
class QueryResult:
    """
    Resultado estructurado del RAG.

    - answer: texto generado
    - chunks: evidencia usada
    - sources/confidence: value objects (se evita import circular aquí)
    """

    answer: str
    chunks: List[Chunk]
    query: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    sources: Optional[List[Any]] = None
    confidence: Optional[Any] = None


# ---------------------------------------------------------------------------
# Conversation
# ---------------------------------------------------------------------------


@dataclass
class ConversationMessage:
    """Mensaje para historial multi-turn."""

    role: Literal["user", "assistant"]
    content: str
