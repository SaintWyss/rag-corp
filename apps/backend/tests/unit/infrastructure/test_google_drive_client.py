"""
===============================================================================
CRC — tests/unit/infrastructure/test_google_drive_client.py

Responsibilities:
    - Validar retry con backoff exponencial (429 → retry → éxito).
    - Validar respeto de Retry-After header.
    - Validar error permanente (401/403) no reintenta.
    - Validar streaming download con hashing SHA-256 incremental.
    - Validar max file size guard (ConnectorFileTooLargeError).
    - Validar timeout/connect error → retry.
    - Verificar que logs no contienen tokens.

Collaborators:
    - GoogleDriveClient (SUT)
    - httpx_mock (mock HTTP)
===============================================================================
"""

from __future__ import annotations

import hashlib
from unittest.mock import patch

import httpx
import pytest
from app.infrastructure.services.google_drive_client import (
    ConnectorFileTooLargeError,
    ConnectorPermanentError,
    ConnectorTransientError,
    GoogleDriveClient,
)

pytestmark = pytest.mark.unit

_TOKEN = "test-access-token-secret"
_BASE = "https://www.googleapis.com/drive/v3/files"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_client(**kwargs) -> GoogleDriveClient:
    """Crea un client con settings de test (retries rápidos)."""
    defaults = {
        "max_file_bytes": 1024,  # 1KB para tests
        "retry_max_attempts": 3,
        "retry_base_delay_s": 0.0,  # sin delay real en tests
        "retry_max_delay_s": 0.0,
        "timeout_s": 5.0,
    }
    defaults.update(kwargs)
    return GoogleDriveClient(_TOKEN, **defaults)


def _json_response(data: dict, status: int = 200, headers=None) -> httpx.Response:
    """Crea un httpx.Response simulado."""
    import json

    return httpx.Response(
        status_code=status,
        content=json.dumps(data).encode(),
        headers=headers or {},
    )


# ---------------------------------------------------------------------------
# Retry / Backoff
# ---------------------------------------------------------------------------


class TestRetryBackoff:
    """Tests para retry con backoff exponencial."""

    def test_retry_on_429_then_success(self):
        """429 → retry → 200 debería retornar éxito."""
        responses = [
            httpx.Response(429, headers={"Retry-After": "0"}),
            httpx.Response(200, content=b'{"files":[]}'),
        ]
        call_count = 0

        def mock_request(method, url, **kwargs):
            nonlocal call_count
            resp = responses[call_count]
            call_count += 1
            return resp

        client = _make_client()
        with patch("httpx.request", side_effect=mock_request):
            resp = client._request_with_retry("GET", _BASE, params={"q": "test"})
        assert resp.status_code == 200
        assert call_count == 2

    def test_retry_on_503_then_success(self):
        """503 → retry → 200."""
        responses = [
            httpx.Response(503),
            httpx.Response(200, content=b'{"files":[]}'),
        ]
        idx = 0

        def mock_request(method, url, **kwargs):
            nonlocal idx
            resp = responses[idx]
            idx += 1
            return resp

        client = _make_client()
        with patch("httpx.request", side_effect=mock_request):
            resp = client._request_with_retry("GET", _BASE)
        assert resp.status_code == 200

    def test_retry_respects_retry_after(self):
        """Si viene Retry-After, el delay mínimo debe respetarlo."""
        client = _make_client(retry_base_delay_s=0.001, retry_max_delay_s=60.0)
        # Con retry_after=5 y base=0.001, delay debe ser >= 5
        delay = client._calc_delay(attempt=1, retry_after=5.0)
        assert delay >= 5.0

    def test_retries_exhausted_raises_transient(self):
        """Si todos los reintentos fallan, lanza ConnectorTransientError."""

        def mock_request(method, url, **kwargs):
            return httpx.Response(500)

        client = _make_client(retry_max_attempts=2)
        with (
            patch("httpx.request", side_effect=mock_request),
            pytest.raises(ConnectorTransientError),
        ):
            client._request_with_retry("GET", _BASE)

    def test_timeout_triggers_retry(self):
        """httpx.TimeoutException → retry."""
        call_count = 0

        def mock_request(method, url, **kwargs):
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                raise httpx.ReadTimeout("test timeout")
            return httpx.Response(200, content=b'{"files":[]}')

        client = _make_client()
        with patch("httpx.request", side_effect=mock_request):
            resp = client._request_with_retry("GET", _BASE)
        assert resp.status_code == 200
        assert call_count == 3


# ---------------------------------------------------------------------------
# Permanent Errors
# ---------------------------------------------------------------------------


class TestPermanentErrors:
    """Tests para errores permanentes (no reintenta)."""

    def test_401_raises_permanent(self):
        """401 → ConnectorPermanentError inmediato (sin retry)."""
        call_count = 0

        def mock_request(method, url, **kwargs):
            nonlocal call_count
            call_count += 1
            return httpx.Response(401, content=b"unauthorized")

        client = _make_client()
        with (
            patch("httpx.request", side_effect=mock_request),
            pytest.raises(ConnectorPermanentError) as exc_info,
        ):
            client._request_with_retry("GET", _BASE)

        assert exc_info.value.status_code == 401
        assert call_count == 1  # No retry

    def test_403_raises_permanent(self):
        """403 → ConnectorPermanentError inmediato."""

        def mock_request(method, url, **kwargs):
            return httpx.Response(403, content=b"forbidden")

        client = _make_client()
        with (
            patch("httpx.request", side_effect=mock_request),
            pytest.raises(ConnectorPermanentError) as exc_info,
        ):
            client._request_with_retry("GET", _BASE)
        assert exc_info.value.status_code == 403

    def test_404_raises_permanent(self):
        """404 → ConnectorPermanentError inmediato."""

        def mock_request(method, url, **kwargs):
            return httpx.Response(404, content=b"not found")

        client = _make_client()
        with (
            patch("httpx.request", side_effect=mock_request),
            pytest.raises(ConnectorPermanentError),
        ):
            client._request_with_retry("GET", _BASE)


# ---------------------------------------------------------------------------
# Streaming + Hash + Max Size
# ---------------------------------------------------------------------------


class TestStreamingDownload:
    """Tests para streaming download, hashing y max size guard."""

    def test_fetch_returns_content_and_sha256(self):
        """fetch_file_content retorna (bytes, sha256_hex) correctos."""
        content = b"hello world content"
        expected_hash = hashlib.sha256(content).hexdigest()

        def mock_stream(method, url, **kwargs):
            return httpx.Response(200, content=content)

        client = _make_client(max_file_bytes=1024 * 1024)
        with patch("httpx.stream") as mock_ctx:
            # Simular context manager de httpx.stream
            mock_response = httpx.Response(200, content=content)
            mock_ctx.return_value.__enter__ = lambda self: mock_response
            mock_ctx.return_value.__exit__ = lambda self, *args: None
            data, sha = client.fetch_file_content("file-123", mime_type="text/plain")

        assert data == content
        assert sha == expected_hash

    def test_file_too_large_raises(self):
        """Archivos que exceden max_file_bytes lanzan ConnectorFileTooLargeError."""
        large_content = b"x" * 2048  # 2KB

        client = _make_client(max_file_bytes=1024)  # 1KB limit

        with patch("httpx.stream") as mock_ctx:
            mock_response = httpx.Response(200, content=large_content)
            mock_ctx.return_value.__enter__ = lambda self: mock_response
            mock_ctx.return_value.__exit__ = lambda self, *args: None

            with pytest.raises(ConnectorFileTooLargeError) as exc_info:
                client.fetch_file_content("big-file", mime_type="text/plain")

            assert exc_info.value.file_id == "big-file"
            assert exc_info.value.max_bytes == 1024

    def test_google_docs_export_uses_export_url(self):
        """Google Docs MIME type debe usar la URL de export."""
        content = b"exported text"

        client = _make_client(max_file_bytes=1024 * 1024)
        with patch("httpx.stream") as mock_ctx:
            mock_response = httpx.Response(200, content=content)
            mock_ctx.return_value.__enter__ = lambda self: mock_response
            mock_ctx.return_value.__exit__ = lambda self, *args: None

            client.fetch_file_content(
                "gdoc-123",
                mime_type="application/vnd.google-apps.document",
            )

            call_args = mock_ctx.call_args
            assert "/export" in call_args[0][1]  # URL contiene /export
            assert call_args[1]["params"]["mimeType"] == "text/plain"


# ---------------------------------------------------------------------------
# No token leak
# ---------------------------------------------------------------------------


class TestNoTokenLeak:
    """Verifica que el access_token no se filtra en logs/excepciones."""

    def test_permanent_error_message_excludes_token(self):
        """ConnectorPermanentError no debe contener el access_token."""

        def mock_request(method, url, **kwargs):
            return httpx.Response(401, content=b"bad creds")

        secret_token = "super-secret-access-token-12345"
        client = GoogleDriveClient(
            secret_token,
            retry_max_attempts=1,
            retry_base_delay_s=0,
            retry_max_delay_s=0,
            timeout_s=1,
        )
        with (
            patch("httpx.request", side_effect=mock_request),
            pytest.raises(ConnectorPermanentError) as exc_info,
        ):
            client._request_with_retry("GET", _BASE)

        assert secret_token not in str(exc_info.value)

    def test_transient_error_message_excludes_token(self):
        """ConnectorTransientError no debe contener access_token."""
        secret_token = "another-secret-token-67890"

        def mock_request(method, url, **kwargs):
            raise httpx.ReadTimeout("timeout")

        client = GoogleDriveClient(
            secret_token,
            retry_max_attempts=1,
            retry_base_delay_s=0,
            retry_max_delay_s=0,
            timeout_s=1,
        )
        with (
            patch("httpx.request", side_effect=mock_request),
            pytest.raises(ConnectorTransientError) as exc_info,
        ):
            client._request_with_retry("GET", _BASE)

        assert secret_token not in str(exc_info.value)

    def test_token_not_in_repr(self):
        """El token no debe aparecer en repr/str del client."""
        secret = "my-token-should-not-leak"
        client = GoogleDriveClient(
            secret, retry_max_attempts=1, retry_base_delay_s=0, timeout_s=1
        )
        assert secret not in repr(client)
        assert secret not in str(client)
