"""
===============================================================================
TARJETA CRC — domain/repositories.py
===============================================================================

Módulo:
    Puertos de Persistencia (Repository Protocols)

Responsabilidades:
    - Definir contratos estables para persistencia y queries del dominio.
    - Asegurar inversión de dependencias: application usa interfaces, no DB.
    - Facilitar tests (mocks/stubs) sin infraestructura.

Colaboradores:
    - domain.entities: Document, Chunk, ConversationMessage, Workspace
    - domain.audit: AuditEvent
    - infraestructura: implementaciones concretas (Postgres, in-memory, etc.)

Reglas:
    - SOLO interfaces: nada de SQL, nada de side effects extra.
    - Mantener firmas estables: si agregás métodos, hacelo intencionalmente.
===============================================================================
"""

from __future__ import annotations

from datetime import datetime
from typing import Protocol
from uuid import UUID

from .audit import AuditEvent
from .entities import (
    Chunk,
    ConversationMessage,
    Document,
    Node,
    Workspace,
    WorkspaceVisibility,
)


class DocumentRepository(Protocol):
    """Contrato de persistencia para documentos y chunks."""

    def save_document(self, document: Document) -> None:
        """Persiste metadata del documento."""
        ...

    def save_chunks(
        self,
        document_id: UUID,
        chunks: list[Chunk],
        *,
        workspace_id: UUID | None = None,
    ) -> None:
        """Persiste chunks asociados a un documento."""
        ...

    def save_document_with_chunks(
        self, document: Document, chunks: list[Chunk], nodes: list[Node] | None = None
    ) -> None:
        """Persiste documento + chunks (+ nodos opcionales) de forma atómica."""
        ...

    def find_similar_chunks(
        self,
        embedding: list[float],
        top_k: int,
        *,
        workspace_id: UUID | None = None,
    ) -> list[Chunk]:
        """Búsqueda por similitud (top-k)."""
        ...

    def find_similar_chunks_mmr(
        self,
        embedding: list[float],
        top_k: int,
        fetch_k: int = 20,
        lambda_mult: float = 0.5,
        *,
        workspace_id: UUID | None = None,
    ) -> list[Chunk]:
        """Búsqueda por similitud con MMR (diversidad)."""
        ...

    def find_chunks_full_text(
        self,
        query_text: str,
        top_k: int,
        *,
        workspace_id: UUID | None = None,
    ) -> list[Chunk]:
        """Búsqueda full-text (tsvector + ts_rank_cd) por workspace."""
        ...

    # ------------------------------------------------------------------
    # Nodes (2-tier retrieval)
    # ------------------------------------------------------------------

    def save_nodes(
        self,
        document_id: UUID,
        nodes: list[Node],
        *,
        workspace_id: UUID | None = None,
    ) -> None:
        """Persiste nodos de un documento."""
        ...

    def find_similar_nodes(
        self,
        embedding: list[float],
        top_k: int,
        *,
        workspace_id: UUID | None = None,
    ) -> list[Node]:
        """Búsqueda vectorial sobre nodos (coarse retrieval)."""
        ...

    def find_chunks_by_node_spans(
        self,
        node_spans: list[tuple[UUID, int, int]],
        *,
        workspace_id: UUID | None = None,
    ) -> list[Chunk]:
        """Chunks dentro de spans de nodos (fine retrieval)."""
        ...

    def delete_nodes_for_document(
        self,
        document_id: UUID,
        *,
        workspace_id: UUID | None = None,
    ) -> int:
        """Borrar nodos de un documento."""
        ...

    def list_documents(
        self,
        limit: int = 50,
        offset: int = 0,
        *,
        workspace_id: UUID | None = None,
        query: str | None = None,
        status: str | None = None,
        tag: str | None = None,
        sort: str | None = None,
    ) -> list[Document]:
        """Lista documentos con filtros opcionales."""
        ...

    def get_document(
        self, document_id: UUID, *, workspace_id: UUID | None = None
    ) -> Document | None:
        """Obtiene un documento por ID (opcionalmente scopiado)."""
        ...

    def get_document_by_content_hash(
        self, workspace_id: UUID, content_hash: str
    ) -> Document | None:
        """Busca documento por hash de contenido dentro de un workspace."""
        ...

    def soft_delete_document(
        self, document_id: UUID, *, workspace_id: UUID | None = None
    ) -> bool:
        """Soft delete: setea deleted_at."""
        ...

    def soft_delete_documents_by_workspace(self, workspace_id: UUID) -> int:
        """Soft delete masivo por workspace."""
        ...

    def update_document_file_metadata(
        self,
        document_id: UUID,
        *,
        workspace_id: UUID | None = None,
        file_name: str | None = None,
        mime_type: str | None = None,
        storage_key: str | None = None,
        uploaded_by_user_id: UUID | None = None,
        status: str | None = None,
        error_message: str | None = None,
    ) -> bool:
        """Actualiza metadata de archivo/storage y estado."""
        ...

    def transition_document_status(
        self,
        document_id: UUID,
        *,
        workspace_id: UUID | None = None,
        from_statuses: list[str | None],
        to_status: str,
        error_message: str | None = None,
    ) -> bool:
        """Transición de estado (compare-and-set)."""
        ...

    def delete_chunks_for_document(
        self, document_id: UUID, *, workspace_id: UUID | None = None
    ) -> int:
        """Elimina chunks de un documento."""
        ...

    def restore_document(
        self, document_id: UUID, *, workspace_id: UUID | None = None
    ) -> bool:
        """Restaura un documento soft-deleted."""
        ...

    def ping(self) -> bool:
        """Chequeo de conectividad del repositorio."""
        ...


class WorkspaceRepository(Protocol):
    """Contrato de persistencia para workspaces."""

    def list_workspaces(
        self,
        *,
        owner_user_id: UUID | None = None,
        include_archived: bool = False,
    ) -> list[Workspace]:
        """Lista workspaces (opcionalmente por owner)."""
        ...

    def list_workspaces_by_visibility(
        self,
        visibility: WorkspaceVisibility,
        *,
        include_archived: bool = False,
    ) -> list[Workspace]:
        """Lista workspaces por visibilidad."""
        ...

    def list_workspaces_by_ids(
        self,
        workspace_ids: list[UUID],
        *,
        include_archived: bool = False,
    ) -> list[Workspace]:
        """Lista workspaces por IDs (si falta alguno, se omite)."""
        ...

    def list_workspaces_visible_to_user(
        self,
        user_id: UUID,
        *,
        include_archived: bool = False,
    ) -> list[Workspace]:
        """Lista workspaces visibles para un usuario (optimizado)."""
        ...

    def get_workspace(self, workspace_id: UUID) -> Workspace | None:
        """Obtiene un workspace por ID."""
        ...

    def get_workspace_by_owner_and_name(
        self, owner_user_id: UUID | None, name: str
    ) -> Workspace | None:
        """Obtiene workspace por owner + name (para unicidad)."""
        ...

    def create_workspace(self, workspace: Workspace) -> Workspace:
        """Crea un workspace."""
        ...

    def update_workspace(
        self,
        workspace_id: UUID,
        *,
        name: str | None = None,
        description: str | None = None,
        visibility: WorkspaceVisibility | None = None,
        allowed_roles: list[str] | None = None,
    ) -> Workspace | None:
        """Actualiza atributos de un workspace."""
        ...

    def archive_workspace(self, workspace_id: UUID) -> bool:
        """Archiva un workspace."""
        ...


class WorkspaceAclRepository(Protocol):
    """Contrato para ACL de workspaces (modo SHARED)."""

    def list_workspace_acl(self, workspace_id: UUID) -> list[UUID]:
        """Lista user_ids con acceso."""
        ...

    def replace_workspace_acl(self, workspace_id: UUID, user_ids: list[UUID]) -> None:
        """Reemplaza entradas ACL."""
        ...

    def list_workspaces_for_user(self, user_id: UUID) -> list[UUID]:
        """Reverse lookup: workspaces compartidos a un usuario."""
        ...


class ConversationRepository(Protocol):
    """Contrato para persistencia de historial de conversación."""

    def create_conversation(self) -> str: ...

    def conversation_exists(self, conversation_id: str) -> bool: ...

    def get_message_count(self, conversation_id: str) -> int: ...

    def append_message(
        self, conversation_id: str, message: ConversationMessage
    ) -> None: ...

    def get_messages(
        self, conversation_id: str, limit: int | None = None
    ) -> list[ConversationMessage]: ...

    def clear_messages(self, conversation_id: str) -> None: ...


class AuditEventRepository(Protocol):
    """Contrato para auditoría de eventos del sistema."""

    def record_event(self, event: AuditEvent) -> None: ...

    def list_events(
        self,
        *,
        workspace_id: UUID | None = None,
        actor_id: str | None = None,
        action_prefix: str | None = None,
        start_at: datetime | None = None,
        end_at: datetime | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> list[AuditEvent]: ...


class FeedbackRepository(Protocol):
    """Contrato para feedback de usuario (votos)."""

    def save_vote(
        self,
        *,
        conversation_id: str,
        message_index: int,
        user_id: UUID,
        vote: str,
        comment: str | None = None,
        tags: list[str] | None = None,
        created_at: datetime | None = None,
    ) -> str: ...

    def get_vote(
        self, *, conversation_id: str, message_index: int, user_id: UUID
    ) -> dict | None: ...

    def list_votes_for_conversation(self, conversation_id: str) -> list[dict]: ...

    def count_votes(
        self,
        *,
        workspace_id: UUID | None = None,
        vote_type: str | None = None,
        start_at: datetime | None = None,
        end_at: datetime | None = None,
    ) -> dict: ...


class AnswerAuditRepository(Protocol):
    """Contrato para auditoría de respuestas (cumplimiento / trazabilidad)."""

    def save_audit_record(
        self,
        *,
        record_id: str,
        timestamp: str,
        user_id: UUID,
        workspace_id: UUID,
        query: str,
        answer_preview: str,
        confidence_level: str,
        confidence_value: float,
        requires_verification: bool,
        sources_count: int,
        source_documents: list[str] | None = None,
        user_email: str | None = None,
        suggested_department: str | None = None,
        conversation_id: str | None = None,
        session_id: str | None = None,
        ip_address: str | None = None,
        user_agent: str | None = None,
        response_time_ms: int | None = None,
        metadata: dict | None = None,
    ) -> None: ...

    def get_audit_record(self, record_id: str) -> dict | None: ...

    def list_audit_records(
        self,
        *,
        workspace_id: UUID | None = None,
        user_id: UUID | None = None,
        confidence_level: str | None = None,
        requires_verification: bool | None = None,
        start_at: datetime | None = None,
        end_at: datetime | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> list[dict]: ...

    def list_high_risk_records(
        self,
        *,
        workspace_id: UUID | None = None,
        start_at: datetime | None = None,
        end_at: datetime | None = None,
        limit: int = 50,
    ) -> list[dict]: ...
