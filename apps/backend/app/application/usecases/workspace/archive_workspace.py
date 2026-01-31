"""
===============================================================================
USE CASE: Archive Workspace (Soft Delete)
===============================================================================

Name:
    Archive Workspace Use Case

Business Goal:
    Archivar (soft-delete) un workspace existente, aplicando política de acceso
    (write permission) y garantizando consistencia funcional al soft-deletar
    también los documentos del workspace.

Why (Context / Intención):
    - Evitar borrado físico: preserva auditoría, trazabilidad y posibilidad de
      restauración futura.
    - Consistencia: si un workspace deja de estar activo, sus documentos deben
      dejar de aparecer en listados/consultas normales.
    - Idempotencia: reintentar el mismo comando no debe romper (importante para
      UI, reintentos HTTP, colas y sistemas distribuidos).

-------------------------------------------------------------------------------
CRC CARD (Class-Responsibility-Collaborator)
-------------------------------------------------------------------------------
Class:
    ArchiveWorkspaceUseCase

Responsibilities:
    - Validar existencia del workspace.
    - Asegurar comportamiento idempotente (si ya está archivado => éxito).
    - Validar autorización (policy: can_write_workspace).
    - Ejecutar archivado en repositorio (soft-delete).
    - Soft-delete de documentos del workspace para consistencia funcional.
    - Devolver un resultado estable y tipado (ArchiveWorkspaceResult).

Collaborators:
    - WorkspaceRepository:
        get_workspace(workspace_id)
        archive_workspace(workspace_id) -> bool
    - DocumentRepository:
        soft_delete_documents_by_workspace(workspace_id)
    - workspace_policy:
        can_write_workspace(workspace, actor) -> bool
    - workspace_results:
        ArchiveWorkspaceResult / WorkspaceError / WorkspaceErrorCode

-------------------------------------------------------------------------------
INPUTS / OUTPUTS (Contrato del caso de uso)
-------------------------------------------------------------------------------
Inputs:
    - workspace_id: UUID
    - actor: WorkspaceActor | None

Outputs:
    - ArchiveWorkspaceResult:
        - archived: bool
        - error: WorkspaceError | None

Error Mapping:
    - NOT_FOUND:
        - workspace no existe
        - o race condition: desaparece/falla el archive al persistir
    - FORBIDDEN:
        - el actor no tiene permisos de escritura sobre el workspace

-------------------------------------------------------------------------------
BUSINESS RULES (Reglas de negocio)
-------------------------------------------------------------------------------
R1) El workspace debe existir.
R2) El actor debe tener permisos de escritura (write access).
R3) Idempotencia: si el workspace ya está archivado, se considera éxito.
R4) Consistencia: al archivar un workspace, se soft-deletean sus documentos.

-------------------------------------------------------------------------------
FLOW (Algoritmo paso a paso)
-------------------------------------------------------------------------------
1) Obtener workspace por ID.
2) Si no existe -> NOT_FOUND.
3) Si está archivado -> SUCCESS (idempotente).
4) Validar permisos (can_write_workspace). Si falla -> FORBIDDEN.
5) Archivar workspace (repository.archive_workspace). Si falla -> NOT_FOUND.
6) Soft-delete documentos del workspace (best-effort, ver nota).
7) Retornar SUCCESS.

-------------------------------------------------------------------------------
SUSTAINABILITY / MANTENIBILIDAD (Notas de diseño)
-------------------------------------------------------------------------------
- Guard clauses: salida temprana para reducir indentación y complejidad.
- Helpers privados para evitar duplicación (mismo error en varios caminos).
- Idempotencia explícita: simplifica clientes y reintentos.
- Mejor naming: _workspaces / _documents deja claro el rol del colaborador.
- Best-effort cleanup: si documentos fallan, el comando principal ya ocurrió.
  Recomendación futura: envolver (5) y (6) en UnitOfWork/transacción atómica.
===============================================================================
"""

from __future__ import annotations

import logging
from uuid import UUID

from ....domain.repositories import DocumentRepository, WorkspaceRepository
from ....domain.workspace_policy import WorkspaceActor, can_write_workspace
from .workspace_results import (
    ArchiveWorkspaceResult,
    WorkspaceError,
    WorkspaceErrorCode,
)

logger = logging.getLogger(__name__)


class ArchiveWorkspaceUseCase:
    """
    Use Case (Application Service / Command):
        Orquesta la operación "Archive Workspace" aplicando reglas de negocio
        y delegando persistencia/autorización a colaboradores.

    Nota:
        Este use case NO debería conocer detalles de infraestructura (SQL, ORM,
        HTTP, etc.). Solo coordina pasos y devuelve resultados de dominio.
    """

    def __init__(
        self,
        workspace_repository: WorkspaceRepository,
        document_repository: DocumentRepository,
    ) -> None:
        # Se usa naming explícito para legibilidad y mantenibilidad.
        self._workspaces = workspace_repository
        self._documents = document_repository

    def execute(
        self,
        workspace_id: UUID,
        actor: WorkspaceActor | None,
    ) -> ArchiveWorkspaceResult:
        """
        Ejecuta el archivado (soft-delete) del workspace.

        Preconditions (precondiciones):
            - workspace_id válido (UUID)
            - actor puede ser None (se trata como no autorizado)

        Postconditions (poscondiciones, si SUCCESS):
            - workspace queda archivado (soft-delete)
            - documentos del workspace quedan soft-deleteados (best-effort)

        Retorna:
            - ArchiveWorkspaceResult con archived=True si éxito
            - ArchiveWorkspaceResult con archived=False + error si falla
        """

        # ---------------------------------------------------------------------
        # 1) Load current state (leer el estado actual desde el repositorio).
        # ---------------------------------------------------------------------
        # Motivo: necesitamos validar existencia, idempotencia y permisos.
        workspace = self._workspaces.get_workspace(workspace_id)

        # ---------------------------------------------------------------------
        # 2) Workspace inexistente -> NOT_FOUND.
        # ---------------------------------------------------------------------
        if workspace is None:
            return self._not_found()

        # ---------------------------------------------------------------------
        # 3) Idempotencia: si ya está archivado, devolvemos SUCCESS.
        # ---------------------------------------------------------------------
        # Motivo: un segundo llamado (reintento) no debería romper.
        if workspace.is_archived:
            return ArchiveWorkspaceResult(archived=True)

        # ---------------------------------------------------------------------
        # 4) Autorización: solo actores con permisos de escritura.
        # ---------------------------------------------------------------------
        # Motivo: la política vive fuera del use case para separar reglas
        # de acceso del flujo del caso de uso (mejor testeo y mantenibilidad).
        if not can_write_workspace(workspace, actor):
            return self._forbidden()

        # ---------------------------------------------------------------------
        # 5) Archivar workspace (soft-delete).
        # ---------------------------------------------------------------------
        # repository.archive_workspace() devuelve bool para representar si
        # efectivamente persistió el cambio (ej: rows affected == 1).
        archived = self._workspaces.archive_workspace(workspace_id)

        if not archived:
            # Race condition: el workspace pudo cambiar/eliminarse entre el get
            # y el archive. La respuesta más coherente es NOT_FOUND.
            return self._not_found()

        # ---------------------------------------------------------------------
        # 6) Consistencia: soft-delete de documentos asociados.
        # ---------------------------------------------------------------------
        # Nota de diseño:
        #   Idealmente esto sería atómico con el paso (5) usando UnitOfWork o
        #   una transacción. Por ahora se hace best-effort:
        #   - si falla, el workspace igual quedó archivado.
        #   - el cleanup se puede reintentar (manual, job, outbox, etc.).
        try:
            self._documents.soft_delete_documents_by_workspace(workspace_id)
        except Exception:
            logger.exception(
                "Workspace archived but failed to soft-delete documents. workspace_id=%s",
                workspace_id,
            )
            # No cambiamos el resultado principal: el workspace ya quedó archivado.

        # ---------------------------------------------------------------------
        # 7) Resultado final de éxito.
        # ---------------------------------------------------------------------
        return ArchiveWorkspaceResult(archived=True)

    # =========================================================================
    # Private helpers: eliminan duplicación y hacen que execute() sea legible.
    # =========================================================================

    @staticmethod
    def _not_found() -> ArchiveWorkspaceResult:
        """Construye un resultado NOT_FOUND consistente para el caso de uso."""
        return ArchiveWorkspaceResult(
            archived=False,
            error=WorkspaceError(
                code=WorkspaceErrorCode.NOT_FOUND,
                message="Workspace not found.",
            ),
        )

    @staticmethod
    def _forbidden() -> ArchiveWorkspaceResult:
        """Construye un resultado FORBIDDEN consistente para el caso de uso."""
        return ArchiveWorkspaceResult(
            archived=False,
            error=WorkspaceError(
                code=WorkspaceErrorCode.FORBIDDEN,
                message="Access denied.",
            ),
        )
