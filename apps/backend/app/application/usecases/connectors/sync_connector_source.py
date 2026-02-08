"""
===============================================================================
USE CASE: Sync Connector Source — Update-Aware (v2)
===============================================================================

TARJETA CRC — application/usecases/connectors/sync_connector_source.py
-------------------------------------------------------------------------------
Class: SyncConnectorSourceUseCase

Responsibilities:
  - Sincronizar archivos desde Google Drive hacia el workspace.
  - Detectar cambios usando modified_time/etag (update-aware).
  - Si el archivo no existe: crear nuevo documento.
  - Si el archivo existe pero cambió: actualizar (re-ingestar) sin duplicar.
  - Si el archivo existe y no cambió: skip (idempotente).
  - Mantener workspace-scoped estricto.
  - Registrar métricas de sync (created, updated, skipped).

Collaborators:
  - ConnectorSourceRepository: persistencia de sources.
  - ConnectorAccountRepository: cuentas OAuth.
  - DocumentRepository: documentos + chunks.
  - TokenEncryptionPort: cifrado de tokens.
  - OAuthPort: refresh de access_token.
  - GoogleDriveClient: interacción con Drive API.
  - crosscutting.metrics: métricas de observabilidad.

Flow (Update-Aware):
  1. Validar source existe + pertenece al workspace.
  2. Obtener cuenta OAuth (tokens).
  3. Descifrar refresh_token → refrescar access_token.
  4. Construir GoogleDriveClient con access_token.
  5. Delta sync: obtener cambios desde último cursor.
  6. Para cada archivo:
     a. Si NO existe doc → CREATE (ingestar nuevo).
     b. Si existe doc:
        - Comparar modified_time/etag.
        - Si cambió → UPDATE (re-ingestar + reemplazar chunks).
        - Si no cambió → SKIP (idempotente).
  7. Actualizar cursor + status.
===============================================================================
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from uuid import UUID, uuid4

from app.crosscutting.metrics import (
    record_connector_file_created,
    record_connector_file_skipped_unchanged,
    record_connector_file_updated,
    record_connector_sync_locked,
)
from app.domain.connectors import (
    ConnectorAccountRepository,
    ConnectorFile,
    ConnectorProvider,
    ConnectorSourceRepository,
    ConnectorSourceStatus,
    OAuthPort,
    TokenEncryptionPort,
)
from app.domain.entities import Document
from app.domain.repositories import DocumentRepository
from app.infrastructure.services.google_drive_client import (
    ConnectorFileTooLargeError,
    ConnectorPermanentError,
    ConnectorTransientError,
)

from . import ConnectorError, ConnectorErrorCode

logger = logging.getLogger(__name__)

# Límite de archivos por sync (safety guard)
_MAX_FILES_PER_SYNC = 100


class SyncAction:
    """Acciones posibles durante sync de un archivo."""

    CREATE = "create"
    UPDATE = "update"
    SKIP_UNCHANGED = "skip_unchanged"
    SKIP_UNSUPPORTED = "skip_unsupported"
    SKIP_EMPTY = "skip_empty"
    ERROR = "error"


@dataclass(frozen=True)
class SyncStats:
    """Estadísticas de una ejecución de sync."""

    files_found: int = 0
    files_ingested: int = 0  # Nuevos (CREATE)
    files_updated: int = 0  # Actualizados (UPDATE)
    files_skipped: int = 0  # Sin cambios o no soportados
    files_errored: int = 0


@dataclass
class SyncConnectorSourceResult:
    """Resultado de sync con estadísticas."""

    source_id: UUID | None = None
    stats: SyncStats | None = None
    error: ConnectorError | None = None


def _file_has_changed(existing_doc: Document, drive_file: ConnectorFile) -> bool:
    """
    Determina si un archivo cambió comparando metadata externa.

    Estrategia:
      1. Si tenemos etag en ambos → comparar etag (checksum).
      2. Si no hay etag → comparar modified_time.
      3. Si no hay ninguno → asumir cambio (re-ingestar por seguridad).

    Nota: Google Drive no siempre provee md5Checksum (ej: Google Docs).
    Para esos archivos usamos modified_time como fallback.
    """
    # Comparar por etag si está disponible en ambos
    if existing_doc.external_etag and drive_file.etag:
        return existing_doc.external_etag != drive_file.etag

    # Comparar por modified_time si está disponible
    if existing_doc.external_modified_time and drive_file.modified_time:
        # Comparar timestamps (ignorando microsegundos por posibles diferencias)
        existing_ts = existing_doc.external_modified_time.replace(microsecond=0)
        drive_ts = drive_file.modified_time.replace(microsecond=0)
        return existing_ts != drive_ts

    # Si no hay metadata para comparar, asumir cambio por seguridad
    return True


class SyncConnectorSourceUseCase:
    """
    Sincroniza archivos desde la fuente externa hacia el workspace.

    Implementa sync "update-aware":
      - CREATE: archivos nuevos.
      - UPDATE: archivos existentes que cambiaron.
      - SKIP: archivos sin cambios (idempotente).
    """

    def __init__(
        self,
        connector_repo: ConnectorSourceRepository,
        account_repo: ConnectorAccountRepository,
        document_repo: DocumentRepository,
        encryption: TokenEncryptionPort,
        oauth_port: OAuthPort,
        drive_client_factory=None,
    ):
        self._connector_repo = connector_repo
        self._account_repo = account_repo
        self._document_repo = document_repo
        self._encryption = encryption
        self._oauth = oauth_port
        self._drive_client_factory = drive_client_factory

    def execute(self, workspace_id: UUID, source_id: UUID) -> SyncConnectorSourceResult:
        # 1) Validate source
        source = self._connector_repo.get(source_id)
        if source is None or source.workspace_id != workspace_id:
            return SyncConnectorSourceResult(
                error=ConnectorError(
                    code=ConnectorErrorCode.NOT_FOUND,
                    message=f"Connector source {source_id} not found in workspace {workspace_id}",
                )
            )

        # 2) Get account
        account = self._account_repo.get_by_workspace(
            workspace_id, ConnectorProvider.GOOGLE_DRIVE
        )
        if account is None:
            return SyncConnectorSourceResult(
                error=ConnectorError(
                    code=ConnectorErrorCode.VALIDATION_ERROR,
                    message="No Google Drive account connected for this workspace",
                )
            )

        # 3) Decrypt refresh_token → refresh access_token
        try:
            refresh_token = self._encryption.decrypt(account.encrypted_refresh_token)
            access_token = self._oauth.refresh_access_token(refresh_token)
        except ValueError as exc:
            logger.error(
                "sync: token refresh failed",
                extra={
                    "source_id": str(source_id),
                    "workspace_id": str(workspace_id),
                    "error": str(exc),
                },
            )
            self._connector_repo.update_status(source_id, ConnectorSourceStatus.ERROR)
            return SyncConnectorSourceResult(
                error=ConnectorError(
                    code=ConnectorErrorCode.VALIDATION_ERROR,
                    message=f"Token refresh failed: {exc}",
                )
            )

        # 4) Build drive client
        if self._drive_client_factory:
            client = self._drive_client_factory(access_token)
        else:
            from app.infrastructure.services.google_drive_client import (
                GoogleDriveClient,
            )

            client = GoogleDriveClient(access_token)  # defaults de Settings

        # 5) Acquire per-source sync lock (CAS)
        locked = self._connector_repo.try_set_syncing(source_id)
        if not locked:
            record_connector_sync_locked()
            logger.info(
                "sync: skipped (already syncing)",
                extra={
                    "source_id": str(source_id),
                    "workspace_id": str(workspace_id),
                },
            )
            return SyncConnectorSourceResult(
                source_id=source_id,
                stats=SyncStats(),  # empty — nothing processed
            )

        # 6) Delta sync
        try:
            delta = client.get_delta(
                source.folder_id, cursor=source.cursor_json or None
            )
        except (ConnectorPermanentError, ConnectorTransientError) as exc:
            logger.error(
                "sync: get_delta failed",
                extra={"source_id": str(source_id), "error": str(exc)},
            )
            self._connector_repo.update_status(source_id, ConnectorSourceStatus.ERROR)
            return SyncConnectorSourceResult(
                error=ConnectorError(
                    code=ConnectorErrorCode.VALIDATION_ERROR,
                    message=f"Drive delta failed: {exc}",
                )
            )
        except ValueError as exc:
            logger.error(
                "sync: get_delta failed",
                extra={"source_id": str(source_id), "error": str(exc)},
            )
            self._connector_repo.update_status(source_id, ConnectorSourceStatus.ERROR)
            return SyncConnectorSourceResult(
                error=ConnectorError(
                    code=ConnectorErrorCode.VALIDATION_ERROR,
                    message=f"Drive delta failed: {exc}",
                )
            )

        # 7) Process files
        files_to_process = delta.files[:_MAX_FILES_PER_SYNC]
        created = 0
        updated = 0
        skipped = 0
        errored = 0

        for file in files_to_process:
            action = self._process_file(
                workspace_id=workspace_id,
                source_id=source_id,
                file=file,
                client=client,
            )

            if action == SyncAction.CREATE:
                created += 1
                record_connector_file_created()
            elif action == SyncAction.UPDATE:
                updated += 1
                record_connector_file_updated()
            elif action in (
                SyncAction.SKIP_UNCHANGED,
                SyncAction.SKIP_UNSUPPORTED,
                SyncAction.SKIP_EMPTY,
            ):
                skipped += 1
                if action == SyncAction.SKIP_UNCHANGED:
                    record_connector_file_skipped_unchanged()
            elif action == SyncAction.ERROR:
                errored += 1

        # 8) Update cursor + status
        if delta.new_cursor:
            self._connector_repo.update_cursor(source_id, delta.new_cursor)

        final_status = (
            ConnectorSourceStatus.ERROR
            if errored > 0 and created == 0 and updated == 0
            else ConnectorSourceStatus.ACTIVE
        )
        self._connector_repo.update_status(source_id, final_status)

        stats = SyncStats(
            files_found=len(delta.files),
            files_ingested=created,
            files_updated=updated,
            files_skipped=skipped,
            files_errored=errored,
        )

        logger.info(
            "sync: completed",
            extra={
                "source_id": str(source_id),
                "workspace_id": str(workspace_id),
                "stats": {
                    "found": stats.files_found,
                    "created": stats.files_ingested,
                    "updated": stats.files_updated,
                    "skipped": stats.files_skipped,
                    "errored": stats.files_errored,
                },
            },
        )

        return SyncConnectorSourceResult(source_id=source_id, stats=stats)

    def _process_file(
        self,
        workspace_id: UUID,
        source_id: UUID,
        file: ConnectorFile,
        client,
    ) -> str:
        """
        Procesa un archivo individual.

        Retorna la acción tomada (SyncAction).
        """
        # Check supported mime
        if not client.is_supported_mime(file.mime_type):
            logger.debug(
                "sync: unsupported mime",
                extra={"file_id": file.file_id, "mime_type": file.mime_type},
            )
            return SyncAction.SKIP_UNSUPPORTED

        # Idempotency: external_source_id = gdrive:{file_id}
        external_id = f"gdrive:{file.file_id}"
        existing = self._document_repo.get_by_external_source_id(
            workspace_id, external_id
        )

        if existing is None:
            # CREATE: archivo nuevo
            return self._create_document(
                workspace_id=workspace_id,
                source_id=source_id,
                file=file,
                external_id=external_id,
                client=client,
            )
        else:
            # Verificar si cambió
            if _file_has_changed(existing, file):
                # UPDATE: archivo modificado
                return self._update_document(
                    workspace_id=workspace_id,
                    existing_doc=existing,
                    file=file,
                    client=client,
                )
            else:
                # SKIP: sin cambios
                logger.debug(
                    "sync: file unchanged, skipping",
                    extra={
                        "file_id": file.file_id,
                        "document_id": str(existing.id),
                    },
                )
                return SyncAction.SKIP_UNCHANGED

    def _create_document(
        self,
        workspace_id: UUID,
        source_id: UUID,
        file: ConnectorFile,
        external_id: str,
        client,
    ) -> str:
        """Crea un nuevo documento (primera ingesta)."""
        # Download content
        try:
            content_bytes, content_hash = client.fetch_file_content(
                file.file_id, mime_type=file.mime_type
            )
            text = content_bytes.decode("utf-8", errors="replace")
        except ConnectorFileTooLargeError as exc:
            logger.warning(
                "sync: file too large, skipping",
                extra={
                    "file_id": file.file_id,
                    "file_name": file.name,
                    "size_bytes": exc.size_bytes,
                    "max_bytes": exc.max_bytes,
                },
            )
            return SyncAction.SKIP_UNSUPPORTED
        except (
            ConnectorPermanentError,
            ConnectorTransientError,
            ValueError,
            UnicodeDecodeError,
        ) as exc:
            logger.warning(
                "sync: file download failed",
                extra={
                    "file_id": file.file_id,
                    "file_name": file.name,
                    "error": str(exc),
                },
            )
            return SyncAction.ERROR

        if not text.strip():
            logger.debug(
                "sync: empty file, skipping",
                extra={"file_id": file.file_id, "file_name": file.name},
            )
            return SyncAction.SKIP_EMPTY

        # Persist document with external metadata
        doc = Document(
            id=uuid4(),
            title=file.name,
            workspace_id=workspace_id,
            source=f"google_drive:{source_id}",
            external_source_id=external_id,
            external_source_provider="google_drive",
            external_modified_time=file.modified_time,
            external_etag=file.etag,
            external_mime_type=file.mime_type,
            content_hash=content_hash,
            metadata={
                "connector_source_id": str(source_id),
                "drive_file_id": file.file_id,
                "drive_mime_type": file.mime_type,
                "drive_modified_time": (
                    file.modified_time.isoformat() if file.modified_time else None
                ),
            },
        )
        self._document_repo.save_document(doc)

        logger.info(
            "sync: file created",
            extra={
                "file_id": file.file_id,
                "file_name": file.name,
                "document_id": str(doc.id),
                "action": SyncAction.CREATE,
            },
        )

        return SyncAction.CREATE

    def _update_document(
        self,
        workspace_id: UUID,
        existing_doc: Document,
        file: ConnectorFile,
        client,
    ) -> str:
        """
        Actualiza un documento existente (re-ingesta).

        Estrategia MVP:
          1. Descargar contenido nuevo.
          2. Borrar chunks (y nodos si aplica) anteriores.
          3. La re-ingesta de chunks se delega al pipeline de procesamiento.
          4. Actualizar metadata externa (modified_time, etag).
          5. El documento mantiene el mismo ID (no duplicar).
        """
        document_id = existing_doc.id

        # Download content
        try:
            content_bytes, content_hash = client.fetch_file_content(
                file.file_id, mime_type=file.mime_type
            )
            text = content_bytes.decode("utf-8", errors="replace")
        except ConnectorFileTooLargeError as exc:
            logger.warning(
                "sync: file too large during update, skipping",
                extra={
                    "file_id": file.file_id,
                    "document_id": str(document_id),
                    "size_bytes": exc.size_bytes,
                    "max_bytes": exc.max_bytes,
                },
            )
            return SyncAction.SKIP_UNSUPPORTED
        except (
            ConnectorPermanentError,
            ConnectorTransientError,
            ValueError,
            UnicodeDecodeError,
        ) as exc:
            logger.warning(
                "sync: file download failed during update",
                extra={
                    "file_id": file.file_id,
                    "document_id": str(document_id),
                    "error": str(exc),
                },
            )
            return SyncAction.ERROR

        if not text.strip():
            logger.debug(
                "sync: empty file during update, skipping",
                extra={
                    "file_id": file.file_id,
                    "document_id": str(document_id),
                },
            )
            return SyncAction.SKIP_EMPTY

        # Borrar chunks anteriores (y nodos si aplica)
        try:
            self._document_repo.delete_chunks_for_document(
                document_id, workspace_id=workspace_id
            )
            # Intentar borrar nodos (puede no existir el método en todos los repos)
            if hasattr(self._document_repo, "delete_nodes_for_document"):
                self._document_repo.delete_nodes_for_document(
                    document_id, workspace_id=workspace_id
                )
        except Exception as exc:
            logger.warning(
                "sync: delete chunks/nodes failed during update",
                extra={
                    "document_id": str(document_id),
                    "error": str(exc),
                },
            )
            # Continuamos de todos modos

        # Actualizar metadata del documento (título puede haber cambiado)
        existing_doc.title = file.name
        existing_doc.external_modified_time = file.modified_time
        existing_doc.external_etag = file.etag
        existing_doc.external_mime_type = file.mime_type
        existing_doc.content_hash = content_hash
        if file.modified_time:
            existing_doc.metadata["drive_modified_time"] = (
                file.modified_time.isoformat()
            )
        self._document_repo.save_document(existing_doc)

        # Actualizar metadata externa explícitamente
        self._document_repo.update_external_source_metadata(
            document_id,
            workspace_id=workspace_id,
            external_source_provider="google_drive",
            external_modified_time=file.modified_time,
            external_etag=file.etag,
            external_mime_type=file.mime_type,
        )

        logger.info(
            "sync: file updated",
            extra={
                "file_id": file.file_id,
                "file_name": file.name,
                "document_id": str(document_id),
                "action": SyncAction.UPDATE,
            },
        )

        return SyncAction.UPDATE
