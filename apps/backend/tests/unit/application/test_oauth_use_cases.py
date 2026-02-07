"""
===============================================================================
TEST: OAuth + Encryption Use Cases
===============================================================================

Cobertura:
  - FernetTokenEncryption: encrypt/decrypt, clave inválida
  - StartOAuthUseCase: happy path, workspace no existe
  - HandleOAuthCallbackUseCase: happy path, state mismatch, ws no existe,
    exchange falla
===============================================================================
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Dict, Optional
from uuid import UUID, uuid4

import pytest
from app.application.usecases.connectors import ConnectorErrorCode
from app.application.usecases.connectors.handle_oauth_callback import (
    HandleOAuthCallbackInput,
    HandleOAuthCallbackUseCase,
)
from app.application.usecases.connectors.start_oauth import (
    StartOAuthInput,
    StartOAuthUseCase,
)
from app.domain.connectors import (
    ConnectorAccount,
    ConnectorProvider,
    OAuthTokenResponse,
)
from app.infrastructure.services.encryption import FernetTokenEncryption

# ---------------------------------------------------------------------------
# Fakes
# ---------------------------------------------------------------------------

_REDIRECT_TEMPLATE = "https://app.example.com/workspaces/{workspace_id}/oauth/callback"


@dataclass
class _FakeWorkspace:
    id: UUID
    name: str = "test-ws"


class FakeWorkspaceRepository:
    """In-memory workspace repo (solo get_workspace)."""

    def __init__(self, workspaces: list[_FakeWorkspace] | None = None):
        self._data: Dict[UUID, _FakeWorkspace] = {
            ws.id: ws for ws in (workspaces or [])
        }

    def get_workspace(self, workspace_id: UUID):
        return self._data.get(workspace_id)


class FakeOAuthPort:
    """Fake OAuth port con respuestas configurables."""

    def __init__(
        self,
        *,
        auth_url: str = "https://accounts.google.com/o/oauth2/v2/auth?fake=1",
        token_response: OAuthTokenResponse | None = None,
        exchange_error: str | None = None,
    ):
        self._auth_url = auth_url
        self._token_response = token_response or OAuthTokenResponse(
            access_token="at_fake",
            refresh_token="rt_fake",
            email="user@example.com",
            expires_in=3600,
        )
        self._exchange_error = exchange_error
        self.last_state: str | None = None
        self.last_redirect_uri: str | None = None

    def build_authorization_url(self, *, state: str, redirect_uri: str) -> str:
        self.last_state = state
        self.last_redirect_uri = redirect_uri
        return self._auth_url

    def exchange_code(self, *, code: str, redirect_uri: str) -> OAuthTokenResponse:
        if self._exchange_error:
            raise ValueError(self._exchange_error)
        return self._token_response


class FakeTokenEncryption:
    """Fake encryption: prefija con 'ENC:' (para tests sin Fernet real)."""

    def encrypt(self, plaintext: str) -> str:
        return f"ENC:{plaintext}"

    def decrypt(self, ciphertext: str) -> str:
        if not ciphertext.startswith("ENC:"):
            raise ValueError("invalid ciphertext")
        return ciphertext[4:]


class FakeConnectorAccountRepository:
    """In-memory connector account repo."""

    def __init__(self):
        self._data: Dict[tuple[UUID, str], ConnectorAccount] = {}

    def upsert(self, account: ConnectorAccount) -> None:
        key = (account.workspace_id, account.provider.value)
        self._data[key] = account

    def get_by_workspace(
        self, workspace_id: UUID, provider: ConnectorProvider
    ) -> Optional[ConnectorAccount]:
        return self._data.get((workspace_id, provider.value))

    def delete(self, account_id: UUID) -> bool:
        for key, acc in list(self._data.items()):
            if acc.id == account_id:
                del self._data[key]
                return True
        return False


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

_WS_ID = uuid4()


@pytest.fixture()
def ws_repo():
    return FakeWorkspaceRepository([_FakeWorkspace(id=_WS_ID)])


@pytest.fixture()
def oauth_port():
    return FakeOAuthPort()


@pytest.fixture()
def account_repo():
    return FakeConnectorAccountRepository()


@pytest.fixture()
def encryption():
    return FakeTokenEncryption()


# ============================================================================
# FernetTokenEncryption (real)
# ============================================================================


class TestFernetTokenEncryption:
    """Tests del adapter real de cifrado Fernet."""

    def test_encrypt_decrypt_roundtrip(self):
        """Cifrar y descifrar devuelve el texto original."""
        from cryptography.fernet import Fernet

        key = Fernet.generate_key().decode()
        enc = FernetTokenEncryption(key=key)

        plaintext = "my-secret-refresh-token"
        ciphertext = enc.encrypt(plaintext)

        assert ciphertext != plaintext
        assert enc.decrypt(ciphertext) == plaintext

    def test_empty_key_raises(self):
        """Clave vacía produce error inmediato (fail-fast)."""
        with pytest.raises(ValueError, match="CONNECTOR_ENCRYPTION_KEY"):
            FernetTokenEncryption(key="")

    def test_invalid_key_raises(self):
        """Clave con formato inválido produce error."""
        with pytest.raises(ValueError, match="CONNECTOR_ENCRYPTION_KEY"):
            FernetTokenEncryption(key="not-a-valid-fernet-key")

    def test_decrypt_invalid_ciphertext_raises(self):
        """Descifrar texto corrupto produce error."""
        from cryptography.fernet import Fernet

        key = Fernet.generate_key().decode()
        enc = FernetTokenEncryption(key=key)

        with pytest.raises(ValueError, match="decrypt"):
            enc.decrypt("corrupted-ciphertext")


# ============================================================================
# StartOAuthUseCase
# ============================================================================


class TestStartOAuth:
    def test_happy_path(self, ws_repo, oauth_port):
        uc = StartOAuthUseCase(
            oauth_port=oauth_port,
            workspace_repo=ws_repo,
            redirect_uri_template=_REDIRECT_TEMPLATE,
        )
        result = uc.execute(StartOAuthInput(workspace_id=_WS_ID))

        assert result.error is None
        assert result.authorization_url is not None
        assert "fake=1" in result.authorization_url

        # State debe contener workspace_id
        state = json.loads(oauth_port.last_state)
        assert state["workspace_id"] == str(_WS_ID)
        assert state["provider"] == "google_drive"

        # Redirect URI debe tener el workspace_id interpolado
        assert str(_WS_ID) in oauth_port.last_redirect_uri

    def test_workspace_not_found(self, ws_repo, oauth_port):
        uc = StartOAuthUseCase(
            oauth_port=oauth_port,
            workspace_repo=ws_repo,
            redirect_uri_template=_REDIRECT_TEMPLATE,
        )
        result = uc.execute(StartOAuthInput(workspace_id=uuid4()))

        assert result.error is not None
        assert result.error.code == ConnectorErrorCode.NOT_FOUND


# ============================================================================
# HandleOAuthCallbackUseCase
# ============================================================================


def _make_callback_uc(ws_repo, oauth_port, account_repo, encryption):
    return HandleOAuthCallbackUseCase(
        oauth_port=oauth_port,
        account_repo=account_repo,
        workspace_repo=ws_repo,
        encryption=encryption,
        redirect_uri_template=_REDIRECT_TEMPLATE,
    )


def _valid_state(workspace_id: UUID = _WS_ID) -> str:
    return json.dumps(
        {
            "workspace_id": str(workspace_id),
            "provider": "google_drive",
        }
    )


class TestHandleOAuthCallback:
    def test_happy_path(self, ws_repo, oauth_port, account_repo, encryption):
        uc = _make_callback_uc(ws_repo, oauth_port, account_repo, encryption)
        result = uc.execute(
            HandleOAuthCallbackInput(
                workspace_id=_WS_ID,
                code="auth-code-123",
                state=_valid_state(),
            )
        )

        assert result.error is None
        assert result.account_email == "user@example.com"

        # Verificar que se persistió la cuenta
        saved = account_repo.get_by_workspace(_WS_ID, ConnectorProvider.GOOGLE_DRIVE)
        assert saved is not None
        assert saved.account_email == "user@example.com"
        assert saved.encrypted_refresh_token == "ENC:rt_fake"

    def test_state_mismatch(self, ws_repo, oauth_port, account_repo, encryption):
        uc = _make_callback_uc(ws_repo, oauth_port, account_repo, encryption)
        other_ws = uuid4()
        result = uc.execute(
            HandleOAuthCallbackInput(
                workspace_id=_WS_ID,
                code="auth-code-123",
                state=_valid_state(other_ws),
            )
        )

        assert result.error is not None
        assert result.error.code == ConnectorErrorCode.VALIDATION_ERROR
        assert "mismatch" in result.error.message

    def test_invalid_state(self, ws_repo, oauth_port, account_repo, encryption):
        uc = _make_callback_uc(ws_repo, oauth_port, account_repo, encryption)
        result = uc.execute(
            HandleOAuthCallbackInput(
                workspace_id=_WS_ID,
                code="auth-code-123",
                state="not-json",
            )
        )

        assert result.error is not None
        assert result.error.code == ConnectorErrorCode.VALIDATION_ERROR

    def test_workspace_not_found(self, ws_repo, oauth_port, account_repo, encryption):
        uc = _make_callback_uc(ws_repo, oauth_port, account_repo, encryption)
        missing_ws = uuid4()
        result = uc.execute(
            HandleOAuthCallbackInput(
                workspace_id=missing_ws,
                code="auth-code-123",
                state=_valid_state(missing_ws),
            )
        )

        assert result.error is not None
        assert result.error.code == ConnectorErrorCode.NOT_FOUND

    def test_exchange_error(self, ws_repo, account_repo, encryption):
        oauth_port = FakeOAuthPort(exchange_error="token exchange failed")
        uc = _make_callback_uc(ws_repo, oauth_port, account_repo, encryption)
        result = uc.execute(
            HandleOAuthCallbackInput(
                workspace_id=_WS_ID,
                code="bad-code",
                state=_valid_state(),
            )
        )

        assert result.error is not None
        assert result.error.code == ConnectorErrorCode.VALIDATION_ERROR
        assert "token exchange failed" in result.error.message

    def test_upsert_overwrites_existing(self, ws_repo, account_repo, encryption):
        """Segundo callback para mismo workspace actualiza — no duplica."""
        oauth1 = FakeOAuthPort(
            token_response=OAuthTokenResponse(
                access_token="at1",
                refresh_token="rt1",
                email="old@example.com",
            )
        )
        uc1 = _make_callback_uc(ws_repo, oauth1, account_repo, encryption)
        uc1.execute(
            HandleOAuthCallbackInput(
                workspace_id=_WS_ID, code="c1", state=_valid_state()
            )
        )

        oauth2 = FakeOAuthPort(
            token_response=OAuthTokenResponse(
                access_token="at2",
                refresh_token="rt2",
                email="new@example.com",
            )
        )
        uc2 = _make_callback_uc(ws_repo, oauth2, account_repo, encryption)
        uc2.execute(
            HandleOAuthCallbackInput(
                workspace_id=_WS_ID, code="c2", state=_valid_state()
            )
        )

        saved = account_repo.get_by_workspace(_WS_ID, ConnectorProvider.GOOGLE_DRIVE)
        assert saved is not None
        assert saved.account_email == "new@example.com"
        assert saved.encrypted_refresh_token == "ENC:rt2"
