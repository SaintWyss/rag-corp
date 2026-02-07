"""
===============================================================================
USE CASE: Sync Connector Source (Full Implementation)
===============================================================================

Business Goal:
    Sincronizar archivos desde Google Drive hacia el workspace.

Flow:
    1. Validate source exists + belongs to workspace
    2. Get connector account (OAuth tokens)
    3. Decrypt refresh_token → refresh access_token
    4. Build GoogleDriveClient with fresh access_token
    5. Delta sync: get changes since last cursor
    6. For each new/modified file:
       a. Check idempotency (external_source_id)
       b. Download content
       c. Persist document with external_source_id
    7. Update cursor + status
===============================================================================
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from uuid import UUID, uuid4

from app.domain.connectors import (
    ConnectorAccountRepository,
    ConnectorProvider,
    ConnectorSourceRepository,
    ConnectorSourceStatus,
    OAuthPort,
    TokenEncryptionPort,
)
from app.domain.entities import Document
from app.domain.repositories import DocumentRepository

from . import ConnectorError, ConnectorErrorCode

logger = logging.getLogger(__name__)

# Límite de archivos por sync (safety guard)
_MAX_FILES_PER_SYNC = 100


@dataclass(frozen=True)
class SyncStats:
    """Estadísticas de una ejecución de sync."""

    files_found: int = 0
    files_ingested: int = 0
    files_skipped: int = 0
    files_errored: int = 0


@dataclass
class SyncConnectorSourceResult:
    """Resultado de sync con estadísticas."""

    source_id: UUID | None = None
    stats: SyncStats | None = None
    error: ConnectorError | None = None


class SyncConnectorSourceUseCase:
    """Sincroniza archivos desde la fuente externa hacia el workspace."""

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

            client = GoogleDriveClient(access_token)

        # 5) Mark as syncing
        self._connector_repo.update_status(source_id, ConnectorSourceStatus.SYNCING)

        # 6) Delta sync
        try:
            delta = client.get_delta(
                source.folder_id, cursor=source.cursor_json or None
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
        ingested = 0
        skipped = 0
        errored = 0

        for file in files_to_process:
            # Check supported mime
            if not client.is_supported_mime(file.mime_type):
                skipped += 1
                continue

            # Idempotency: external_source_id = gdrive:{file_id}
            external_id = f"gdrive:{file.file_id}"
            existing = self._document_repo.get_by_external_source_id(
                workspace_id, external_id
            )
            if existing is not None:
                skipped += 1
                continue

            # Download content
            try:
                content_bytes = client.fetch_file_content(
                    file.file_id, mime_type=file.mime_type
                )
                text = content_bytes.decode("utf-8", errors="replace")
            except (ValueError, UnicodeDecodeError) as exc:
                logger.warning(
                    "sync: file download failed",
                    extra={
                        "file_id": file.file_id,
                        "name": file.name,
                        "error": str(exc),
                    },
                )
                errored += 1
                continue

            if not text.strip():
                skipped += 1
                continue

            # Persist document with external_source_id
            doc = Document(
                id=uuid4(),
                title=file.name,
                workspace_id=workspace_id,
                source=f"google_drive:{source.folder_id}",
                external_source_id=external_id,
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
            ingested += 1

            logger.info(
                "sync: file ingested",
                extra={
                    "file_id": file.file_id,
                    "name": file.name,
                    "document_id": str(doc.id),
                },
            )

        # 8) Update cursor + status
        if delta.new_cursor:
            self._connector_repo.update_cursor(source_id, delta.new_cursor)

        final_status = (
            ConnectorSourceStatus.ERROR
            if errored > 0 and ingested == 0
            else ConnectorSourceStatus.ACTIVE
        )
        self._connector_repo.update_status(source_id, final_status)

        stats = SyncStats(
            files_found=len(delta.files),
            files_ingested=ingested,
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
                    "ingested": stats.files_ingested,
                    "skipped": stats.files_skipped,
                    "errored": stats.files_errored,
                },
            },
        )

        return SyncConnectorSourceResult(source_id=source_id, stats=stats)
