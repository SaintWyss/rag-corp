"""
============================================================
TARJETA CRC — infrastructure/services/google_drive_client.py
============================================================
Class: GoogleDriveClient

Responsibilities:
  - Implementar ConnectorClient para Google Drive API v3.
  - Listar archivos de una carpeta (paginado).
  - Descargar contenido de archivos (export para Google Docs, direct para otros).
  - Delta sync via Changes API.

Collaborators:
  - domain.connectors (ConnectorClient, ConnectorFile, ConnectorDelta)
  - httpx (HTTP client)
============================================================
"""

from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List

import httpx

from ...crosscutting.logger import logger
from ...domain.connectors import ConnectorDelta, ConnectorFile

_DRIVE_FILES_URL = "https://www.googleapis.com/drive/v3/files"
_DRIVE_CHANGES_URL = "https://www.googleapis.com/drive/v3/changes"
_DRIVE_START_PAGE_TOKEN_URL = (
    "https://www.googleapis.com/drive/v3/changes/startPageToken"
)

# Tipos de Google Docs que se pueden exportar a texto plano
_GOOGLE_EXPORT_MIMES: dict[str, str] = {
    "application/vnd.google-apps.document": "text/plain",
    "application/vnd.google-apps.spreadsheet": "text/csv",
    "application/vnd.google-apps.presentation": "text/plain",
}

# Mimes soportados para descarga directa (MVP: solo texto)
_SUPPORTED_DIRECT_MIMES = frozenset(
    {
        "text/plain",
        "text/csv",
        "text/markdown",
        "application/pdf",
    }
)


class GoogleDriveClient:
    """
    Implementación de ConnectorClient para Google Drive API v3.

    Recibe un access_token válido (ya refrescado por la capa de aplicación).
    """

    def __init__(self, access_token: str):
        if not access_token:
            raise ValueError("access_token is required for GoogleDriveClient")
        self._headers = {"Authorization": f"Bearer {access_token}"}
        self._timeout = 30.0

    def list_files(
        self, folder_id: str, *, page_token: str | None = None
    ) -> List[ConnectorFile]:
        """Lista archivos de una carpeta de Google Drive."""
        params: Dict[str, Any] = {
            "q": f"'{folder_id}' in parents and trashed = false",
            "fields": "files(id,name,mimeType,modifiedTime,md5Checksum),nextPageToken",
            "pageSize": 100,
        }
        if page_token:
            params["pageToken"] = page_token

        try:
            resp = httpx.get(
                _DRIVE_FILES_URL,
                params=params,
                headers=self._headers,
                timeout=self._timeout,
            )
            resp.raise_for_status()
            data = resp.json()
        except Exception as exc:
            logger.error(
                "google_drive.list_files failed",
                extra={"folder_id": folder_id, "error": str(exc)},
            )
            raise ValueError(f"Google Drive list_files failed: {exc}") from exc

        files: List[ConnectorFile] = []
        for item in data.get("files", []):
            modified = None
            if item.get("modifiedTime"):
                try:
                    modified = datetime.fromisoformat(
                        item["modifiedTime"].replace("Z", "+00:00")
                    )
                except (ValueError, TypeError):
                    pass

            files.append(
                ConnectorFile(
                    file_id=item["id"],
                    name=item["name"],
                    mime_type=item.get("mimeType", ""),
                    modified_time=modified,
                    etag=item.get("md5Checksum"),  # Usamos md5Checksum como etag
                )
            )
        return files

    def fetch_file_content(self, file_id: str, *, mime_type: str = "") -> bytes:
        """
        Descarga el contenido de un archivo.

        Para Google Docs/Sheets/Slides: exporta a texto plano.
        Para otros archivos: descarga directa.
        """
        try:
            if mime_type in _GOOGLE_EXPORT_MIMES:
                export_mime = _GOOGLE_EXPORT_MIMES[mime_type]
                resp = httpx.get(
                    f"{_DRIVE_FILES_URL}/{file_id}/export",
                    params={"mimeType": export_mime},
                    headers=self._headers,
                    timeout=self._timeout,
                )
            else:
                resp = httpx.get(
                    f"{_DRIVE_FILES_URL}/{file_id}",
                    params={"alt": "media"},
                    headers=self._headers,
                    timeout=self._timeout,
                )
            resp.raise_for_status()
            return resp.content
        except Exception as exc:
            logger.error(
                "google_drive.fetch_file_content failed",
                extra={"file_id": file_id, "error": str(exc)},
            )
            raise ValueError(f"Google Drive fetch_file_content failed: {exc}") from exc

    def get_delta(
        self, folder_id: str, *, cursor: Dict[str, Any] | None = None
    ) -> ConnectorDelta:
        """
        Obtiene cambios incrementales via Changes API.

        Si no hay cursor (first sync), obtiene startPageToken y lista todos los archivos.
        Si hay cursor, usa la Changes API para obtener solo cambios.
        """
        if cursor is None or "page_token" not in cursor:
            # First sync: list all files in folder
            files = self.list_files(folder_id)
            start_token = self._get_start_page_token()
            return ConnectorDelta(
                files=files,
                new_cursor={"page_token": start_token},
            )

        # Incremental: use Changes API
        page_token = cursor["page_token"]
        all_files: List[ConnectorFile] = []

        try:
            while page_token:
                resp = httpx.get(
                    _DRIVE_CHANGES_URL,
                    params={
                        "pageToken": page_token,
                        "fields": "changes(file(id,name,mimeType,modifiedTime,md5Checksum),removed),newStartPageToken,nextPageToken",
                        "spaces": "drive",
                        "includeRemoved": "false",
                    },
                    headers=self._headers,
                    timeout=self._timeout,
                )
                resp.raise_for_status()
                data = resp.json()

                for change in data.get("changes", []):
                    if change.get("removed"):
                        continue
                    file_data = change.get("file", {})
                    if not file_data.get("id"):
                        continue

                    modified = None
                    if file_data.get("modifiedTime"):
                        try:
                            modified = datetime.fromisoformat(
                                file_data["modifiedTime"].replace("Z", "+00:00")
                            )
                        except (ValueError, TypeError):
                            pass

                    all_files.append(
                        ConnectorFile(
                            file_id=file_data["id"],
                            name=file_data.get("name", ""),
                            mime_type=file_data.get("mimeType", ""),
                            modified_time=modified,
                            etag=file_data.get("md5Checksum"),
                        )
                    )

                page_token = data.get("nextPageToken")
                if not page_token:
                    new_start = data.get("newStartPageToken", "")
                    return ConnectorDelta(
                        files=all_files,
                        new_cursor={"page_token": new_start},
                    )

        except Exception as exc:
            logger.error(
                "google_drive.get_delta failed",
                extra={"folder_id": folder_id, "error": str(exc)},
            )
            raise ValueError(f"Google Drive get_delta failed: {exc}") from exc

        return ConnectorDelta(files=all_files, new_cursor=cursor)

    def _get_start_page_token(self) -> str:
        """Obtiene el startPageToken actual (para iniciar tracking de changes)."""
        try:
            resp = httpx.get(
                _DRIVE_START_PAGE_TOKEN_URL,
                headers=self._headers,
                timeout=self._timeout,
            )
            resp.raise_for_status()
            return resp.json().get("startPageToken", "")
        except Exception as exc:
            logger.warning(
                "google_drive.get_start_page_token failed",
                extra={"error": str(exc)},
            )
            return ""

    @staticmethod
    def is_supported_mime(mime_type: str) -> bool:
        """Verifica si el tipo MIME es soportado para ingesta."""
        return mime_type in _GOOGLE_EXPORT_MIMES or mime_type in _SUPPORTED_DIRECT_MIMES
