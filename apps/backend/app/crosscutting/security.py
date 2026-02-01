# apps/backend/app/crosscutting/security.py
"""
===============================================================================
MÓDULO: Security headers (OWASP hardening)
===============================================================================

Objetivo
--------
Agregar headers de seguridad a todas las respuestas:
- CSP
- HSTS (solo cuando corresponde)
- Anti-clickjacking, anti-sniffing, etc.

-------------------------------------------------------------------------------
CRC (Component Card)
-------------------------------------------------------------------------------
Componente:
  SecurityHeadersMiddleware

Responsabilidades:
  - Añadir headers de hardening sin romper dev
  - Ajustar CSP según entorno

Colaboradores:
  - crosscutting.config.get_settings
===============================================================================
"""

from __future__ import annotations

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response


def _build_csp(is_production: bool) -> str:
    # CSP defensiva. En dev permitimos inline para docs/swagger.
    if is_production:
        return (
            "default-src 'self'; "
            "script-src 'self'; "
            "style-src 'self'; "
            "img-src 'self' data:; "
            "font-src 'self'; "
            "connect-src 'self'"
        )

    return (
        "default-src 'self'; "
        "script-src 'self' 'unsafe-inline'; "
        "style-src 'self' 'unsafe-inline'; "
        "img-src 'self' data:; "
        "font-src 'self'; "
        "connect-src 'self'"
    )


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """
    ----------------------------------------------------------------------------
    CRC (Class Card)
    ----------------------------------------------------------------------------
    Clase:
      SecurityHeadersMiddleware

    Responsabilidades:
      - Agregar headers de seguridad OWASP
      - HSTS solo si producción y request por HTTPS

    Colaboradores:
      - crosscutting.config
    ----------------------------------------------------------------------------
    """

    def __init__(self, app):
        super().__init__(app)
        from .config import get_settings

        self._is_production = get_settings().is_production()
        self._csp = _build_csp(self._is_production)

    async def dispatch(self, request: Request, call_next) -> Response:
        response = await call_next(request)

        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        response.headers["Permissions-Policy"] = (
            "accelerometer=(), camera=(), geolocation=(), gyroscope=(), "
            "magnetometer=(), microphone=(), payment=(), usb=()"
        )
        response.headers["Content-Security-Policy"] = self._csp

        # HSTS: solo si prod + HTTPS (directo o detrás de proxy)
        if self._is_production:
            proto = (request.headers.get("x-forwarded-proto") or request.url.scheme or "").lower()
            if proto == "https":
                response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"

        return response
