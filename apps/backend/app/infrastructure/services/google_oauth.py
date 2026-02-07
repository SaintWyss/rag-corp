"""
============================================================
TARJETA CRC — infrastructure/services/google_oauth.py
============================================================
Class: GoogleOAuthAdapter

Responsibilities:
  - Implementar OAuthPort para Google OAuth 2.0.
  - Construir authorization URL con scopes de Google Drive.
  - Intercambiar authorization code por tokens (via Google token endpoint).
  - Obtener email del usuario desde Google userinfo.

Collaborators:
  - domain.connectors.OAuthPort, OAuthTokenResponse
  - httpx (HTTP client)
============================================================
"""

from __future__ import annotations

import httpx

from ...crosscutting.logger import logger
from ...domain.connectors import OAuthTokenResponse

# Google OAuth endpoints
_GOOGLE_AUTH_URL = "https://accounts.google.com/o/oauth2/v2/auth"
_GOOGLE_TOKEN_URL = "https://oauth2.googleapis.com/token"
_GOOGLE_USERINFO_URL = "https://www.googleapis.com/oauth2/v2/userinfo"

# Scopes necesarios para lectura de archivos en Drive
_DRIVE_SCOPES = [
    "https://www.googleapis.com/auth/drive.readonly",
    "https://www.googleapis.com/auth/userinfo.email",
]


class GoogleOAuthAdapter:
    """Implementación de OAuthPort para Google OAuth 2.0."""

    def __init__(self, *, client_id: str, client_secret: str):
        if not client_id or not client_secret:
            raise ValueError(
                "GOOGLE_OAUTH_CLIENT_ID and GOOGLE_OAUTH_CLIENT_SECRET are required"
            )
        self._client_id = client_id
        self._client_secret = client_secret

    def build_authorization_url(self, *, state: str, redirect_uri: str) -> str:
        """Construye la URL de autorización de Google."""
        from urllib.parse import urlencode

        params = {
            "client_id": self._client_id,
            "redirect_uri": redirect_uri,
            "response_type": "code",
            "scope": " ".join(_DRIVE_SCOPES),
            "access_type": "offline",
            "prompt": "consent",
            "state": state,
        }
        return f"{_GOOGLE_AUTH_URL}?{urlencode(params)}"

    def exchange_code(self, *, code: str, redirect_uri: str) -> OAuthTokenResponse:
        """Intercambia authorization code por tokens."""
        try:
            # 1) Token exchange
            token_resp = httpx.post(
                _GOOGLE_TOKEN_URL,
                data={
                    "client_id": self._client_id,
                    "client_secret": self._client_secret,
                    "code": code,
                    "grant_type": "authorization_code",
                    "redirect_uri": redirect_uri,
                },
                timeout=10.0,
            )
            token_resp.raise_for_status()
            token_data = token_resp.json()

            access_token = token_data["access_token"]
            refresh_token = token_data.get("refresh_token", "")
            expires_in = token_data.get("expires_in", 3600)

            if not refresh_token:
                raise ValueError(
                    "No refresh_token in response (ensure access_type=offline and prompt=consent)"
                )

            # 2) Fetch email from userinfo
            userinfo_resp = httpx.get(
                _GOOGLE_USERINFO_URL,
                headers={"Authorization": f"Bearer {access_token}"},
                timeout=10.0,
            )
            userinfo_resp.raise_for_status()
            email = userinfo_resp.json().get("email", "unknown")

            return OAuthTokenResponse(
                access_token=access_token,
                refresh_token=refresh_token,
                email=email,
                expires_in=expires_in,
            )

        except httpx.HTTPStatusError as exc:
            logger.error(
                "google oauth token exchange failed",
                extra={"status": exc.response.status_code},
            )
            raise ValueError(f"Google OAuth token exchange failed: {exc}") from exc
        except Exception as exc:
            logger.error(
                "google oauth exchange error",
                extra={"error": str(exc)},
            )
            raise ValueError(f"Google OAuth error: {exc}") from exc
