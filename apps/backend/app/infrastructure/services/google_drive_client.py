"""
============================================================
TARJETA CRC — infrastructure/services/google_drive_client.py
============================================================
Class: GoogleDriveClient

Responsibilities:
  - Implementar ConnectorClient para Google Drive API v3.
  - Listar archivos de una carpeta (paginado).
  - Descargar contenido en streaming con límite anti-OOM.
  - Delta sync via Changes API.
  - Retry con backoff exponencial + jitter para errores transitorios.
  - Diferenciar errores permanentes (401/403 invalid_grant) vs transitorios (429/5xx).
  - Hashing incremental SHA-256 durante descarga (sin cargar todo en RAM).
  - Registrar métricas de resiliencia (retries, failures).

Collaborators:
  - domain.connectors (ConnectorClient, ConnectorFile, ConnectorDelta)
  - crosscutting.config (Settings — límites y retry config)
  - crosscutting.metrics (record_connector_api_retry, record_connector_api_failure)
  - httpx (HTTP client)
============================================================
"""

from __future__ import annotations

import hashlib
import random
import time
from datetime import datetime
from typing import Any, Dict, List, Tuple

import httpx

from ...crosscutting.logger import logger
from ...crosscutting.metrics import (
    record_connector_api_failure,
    record_connector_api_retry,
)
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

# Códigos HTTP considerados errores permanentes (no reintentar)
_PERMANENT_STATUS_CODES = frozenset({400, 401, 403, 404})

_PROVIDER = "google_drive"


class ConnectorPermanentError(Exception):
    """Error permanente del proveedor (credenciales inválidas, recurso no encontrado)."""

    def __init__(self, message: str, status_code: int = 0):
        super().__init__(message)
        self.status_code = status_code


class ConnectorTransientError(Exception):
    """Error transitorio del proveedor (rate limit, servidor caído)."""

    def __init__(self, message: str, status_code: int = 0, retry_after: float = 0.0):
        super().__init__(message)
        self.status_code = status_code
        self.retry_after = retry_after


class ConnectorFileTooLargeError(Exception):
    """Archivo excede el límite de tamaño configurado."""

    def __init__(self, file_id: str, size_bytes: int, max_bytes: int):
        super().__init__(
            f"File {file_id} size {size_bytes} exceeds max {max_bytes} bytes"
        )
        self.file_id = file_id
        self.size_bytes = size_bytes
        self.max_bytes = max_bytes


class GoogleDriveClient:
    """
    Implementación de ConnectorClient para Google Drive API v3.

    Recibe un access_token válido (ya refrescado por la capa de aplicación).
    Incluye retry con backoff exponencial + jitter para errores transitorios,
    descarga en streaming con límite anti-OOM y hashing incremental SHA-256.
    """

    def __init__(
        self,
        access_token: str,
        *,
        max_file_bytes: int = 25 * 1024 * 1024,
        retry_max_attempts: int = 4,
        retry_base_delay_s: float = 1.0,
        retry_max_delay_s: float = 30.0,
        timeout_s: float = 60.0,
    ):
        if not access_token:
            raise ValueError("access_token is required for GoogleDriveClient")
        self._headers = {"Authorization": f"Bearer {access_token}"}
        self._timeout = timeout_s
        self._max_file_bytes = max_file_bytes
        self._retry_max = retry_max_attempts
        self._retry_base = retry_base_delay_s
        self._retry_max_delay = retry_max_delay_s

    # ------------------------------------------------------------------
    # Retry helper (interno)
    # ------------------------------------------------------------------

    def _request_with_retry(
        self,
        method: str,
        url: str,
        *,
        params: dict | None = None,
        stream: bool = False,
    ) -> httpx.Response:
        """
        Ejecuta request HTTP con retry/backoff para errores transitorios.

        Respeta Retry-After si viene en la respuesta.
        Diferencia errores permanentes (401/403/404) vs transitorios (429/5xx).
        """
        last_exc: Exception | None = None

        for attempt in range(1, self._retry_max + 1):
            try:
                if stream:
                    # Para streaming usamos httpx.stream como context manager externo
                    # Aquí retornamos el response del request normal con stream
                    resp = httpx.request(
                        method,
                        url,
                        params=params,
                        headers=self._headers,
                        timeout=self._timeout,
                    )
                else:
                    resp = httpx.request(
                        method,
                        url,
                        params=params,
                        headers=self._headers,
                        timeout=self._timeout,
                    )

                # Éxito
                if resp.status_code < 400:
                    return resp

                # Error permanente: no reintentar
                if resp.status_code in _PERMANENT_STATUS_CODES:
                    reason = _classify_error_reason(resp.status_code)
                    record_connector_api_failure(_PROVIDER, reason)
                    raise ConnectorPermanentError(
                        f"HTTP {resp.status_code}: {resp.text[:200]}",
                        status_code=resp.status_code,
                    )

                # Error transitorio: reintentar
                retry_after = _parse_retry_after(resp)
                reason = _classify_error_reason(resp.status_code)

                if attempt < self._retry_max:
                    record_connector_api_retry(_PROVIDER, reason)
                    delay = self._calc_delay(attempt, retry_after)
                    logger.warning(
                        "google_drive: transitorio, reintentando",
                        extra={
                            "status": resp.status_code,
                            "attempt": attempt,
                            "delay_s": round(delay, 2),
                            "reason": reason,
                        },
                    )
                    time.sleep(delay)
                    continue

                # Último intento agotado
                record_connector_api_failure(_PROVIDER, reason)
                raise ConnectorTransientError(
                    f"HTTP {resp.status_code} after {self._retry_max} attempts",
                    status_code=resp.status_code,
                )

            except (httpx.TimeoutException, httpx.ConnectError) as exc:
                last_exc = exc
                reason = (
                    "timeout" if isinstance(exc, httpx.TimeoutException) else "connect"
                )

                if attempt < self._retry_max:
                    record_connector_api_retry(_PROVIDER, reason)
                    delay = self._calc_delay(attempt)
                    logger.warning(
                        "google_drive: error de red, reintentando",
                        extra={
                            "attempt": attempt,
                            "delay_s": round(delay, 2),
                            "reason": reason,
                        },
                    )
                    time.sleep(delay)
                    continue

                record_connector_api_failure(_PROVIDER, reason)
                raise ConnectorTransientError(
                    f"Network error after {self._retry_max} attempts: {exc}",
                ) from exc

        # Fallback (no debería llegar aquí)
        raise ConnectorTransientError(
            f"Retries exhausted: {last_exc}",
        )

    def _calc_delay(self, attempt: int, retry_after: float = 0.0) -> float:
        """Backoff exponencial con jitter, respetando Retry-After."""
        exp_delay = self._retry_base * (2 ** (attempt - 1))
        jittered = exp_delay * (0.5 + random.random() * 0.5)  # noqa: S311
        base = max(jittered, retry_after)
        return min(base, self._retry_max_delay)

    # ------------------------------------------------------------------
    # API pública
    # ------------------------------------------------------------------

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
            resp = self._request_with_retry("GET", _DRIVE_FILES_URL, params=params)
            data = resp.json()
        except (ConnectorPermanentError, ConnectorTransientError):
            raise
        except Exception as exc:
            logger.error(
                "google_drive.list_files failed",
                extra={"folder_id": folder_id, "error": str(exc)},
            )
            raise ValueError(f"Google Drive list_files failed: {exc}") from exc

        files: List[ConnectorFile] = []
        for item in data.get("files", []):
            modified = _parse_iso_datetime(item.get("modifiedTime"))
            files.append(
                ConnectorFile(
                    file_id=item["id"],
                    name=item["name"],
                    mime_type=item.get("mimeType", ""),
                    modified_time=modified,
                    etag=item.get("md5Checksum"),
                )
            )
        return files

    def fetch_file_content(
        self, file_id: str, *, mime_type: str = ""
    ) -> Tuple[bytes, str]:
        """
        Descarga el contenido de un archivo en streaming con límite anti-OOM.

        Retorna (contenido_bytes, sha256_hex).
        Para Google Docs/Sheets/Slides: exporta a texto plano.
        Para otros archivos: descarga directa.
        Aborta si el tamaño excede max_connector_file_mb.
        Calcula SHA-256 incremental durante la descarga.
        """
        if mime_type in _GOOGLE_EXPORT_MIMES:
            export_mime = _GOOGLE_EXPORT_MIMES[mime_type]
            url = f"{_DRIVE_FILES_URL}/{file_id}/export"
            params: dict[str, Any] = {"mimeType": export_mime}
        else:
            url = f"{_DRIVE_FILES_URL}/{file_id}"
            params = {"alt": "media"}

        try:
            # Streaming con límite anti-OOM y hashing incremental
            return self._stream_download(url, params=params, file_id=file_id)
        except (
            ConnectorPermanentError,
            ConnectorTransientError,
            ConnectorFileTooLargeError,
        ):
            raise
        except Exception as exc:
            logger.error(
                "google_drive.fetch_file_content failed",
                extra={"file_id": file_id, "error": str(exc)},
            )
            raise ValueError(f"Google Drive fetch_file_content failed: {exc}") from exc

    def _stream_download(
        self,
        url: str,
        *,
        params: dict[str, Any],
        file_id: str,
    ) -> Tuple[bytes, str]:
        """
        Descarga en streaming con:
        - Límite anti-OOM (max_file_bytes).
        - Hashing SHA-256 incremental (sin cargar todo en RAM de golpe).
        - Retry con backoff (a nivel de request completo).
        """
        last_exc: Exception | None = None

        for attempt in range(1, self._retry_max + 1):
            try:
                with httpx.stream(
                    "GET",
                    url,
                    params=params,
                    headers=self._headers,
                    timeout=self._timeout,
                ) as resp:
                    if resp.status_code in _PERMANENT_STATUS_CODES:
                        reason = _classify_error_reason(resp.status_code)
                        record_connector_api_failure(_PROVIDER, reason)
                        raise ConnectorPermanentError(
                            f"HTTP {resp.status_code} downloading {file_id}",
                            status_code=resp.status_code,
                        )

                    if resp.status_code >= 400:
                        retry_after = _parse_retry_after(resp)
                        reason = _classify_error_reason(resp.status_code)

                        if attempt < self._retry_max:
                            record_connector_api_retry(_PROVIDER, reason)
                            delay = self._calc_delay(attempt, retry_after)
                            time.sleep(delay)
                            continue

                        record_connector_api_failure(_PROVIDER, reason)
                        raise ConnectorTransientError(
                            f"HTTP {resp.status_code} after {self._retry_max} attempts",
                            status_code=resp.status_code,
                        )

                    # Streaming OK — leer chunks con límite
                    hasher = hashlib.sha256()
                    chunks: list[bytes] = []
                    total = 0

                    for chunk in resp.iter_bytes(chunk_size=64 * 1024):
                        total += len(chunk)
                        if total > self._max_file_bytes:
                            raise ConnectorFileTooLargeError(
                                file_id=file_id,
                                size_bytes=total,
                                max_bytes=self._max_file_bytes,
                            )
                        chunks.append(chunk)
                        hasher.update(chunk)

                    return b"".join(chunks), hasher.hexdigest()

            except (ConnectorPermanentError, ConnectorFileTooLargeError):
                raise
            except ConnectorTransientError:
                raise
            except (httpx.TimeoutException, httpx.ConnectError) as exc:
                last_exc = exc
                reason = (
                    "timeout" if isinstance(exc, httpx.TimeoutException) else "connect"
                )
                if attempt < self._retry_max:
                    record_connector_api_retry(_PROVIDER, reason)
                    delay = self._calc_delay(attempt)
                    time.sleep(delay)
                    continue
                record_connector_api_failure(_PROVIDER, reason)
                raise ConnectorTransientError(
                    f"Download network error after {self._retry_max} attempts",
                ) from exc

        raise ConnectorTransientError(f"Download retries exhausted: {last_exc}")

    def get_delta(
        self, folder_id: str, *, cursor: Dict[str, Any] | None = None
    ) -> ConnectorDelta:
        """
        Obtiene cambios incrementales via Changes API.

        Si no hay cursor (first sync), obtiene startPageToken y lista todos los archivos.
        Si hay cursor, usa la Changes API para obtener solo cambios.
        """
        if cursor is None or "page_token" not in cursor:
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
                resp = self._request_with_retry(
                    "GET",
                    _DRIVE_CHANGES_URL,
                    params={
                        "pageToken": page_token,
                        "fields": "changes(file(id,name,mimeType,modifiedTime,md5Checksum),removed),newStartPageToken,nextPageToken",
                        "spaces": "drive",
                        "includeRemoved": "false",
                    },
                )
                data = resp.json()

                for change in data.get("changes", []):
                    if change.get("removed"):
                        continue
                    file_data = change.get("file", {})
                    if not file_data.get("id"):
                        continue

                    modified = _parse_iso_datetime(file_data.get("modifiedTime"))
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

        except (ConnectorPermanentError, ConnectorTransientError):
            raise
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
            resp = self._request_with_retry("GET", _DRIVE_START_PAGE_TOKEN_URL)
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


# ---------------------------------------------------------------------------
# Helpers (módulo)
# ---------------------------------------------------------------------------


def _parse_retry_after(resp: httpx.Response) -> float:
    """Parsea el header Retry-After (segundos). 0 si no viene o es inválido."""
    raw = resp.headers.get("Retry-After", "")
    if not raw:
        return 0.0
    try:
        return float(raw)
    except (ValueError, TypeError):
        return 0.0


def _classify_error_reason(status_code: int) -> str:
    """Clasifica HTTP status en reason de baja cardinalidad para métricas."""
    if status_code == 429:
        return "rate_limit"
    if status_code == 401:
        return "unauthorized"
    if status_code == 403:
        return "forbidden"
    if status_code == 404:
        return "not_found"
    if 500 <= status_code < 600:
        return "server_error"
    return "other"


def _parse_iso_datetime(value: str | None) -> datetime | None:
    """Parsea un datetime ISO de Google Drive. None si falla o es None."""
    if not value:
        return None
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except (ValueError, TypeError):
        return None
