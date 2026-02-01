# apps/backend/app/crosscutting/error_responses.py
"""
===============================================================================
MÓDULO: Respuestas de error estándar (RFC 7807 / Problem Details)
===============================================================================

Objetivo
--------
Uniformar TODOS los errores HTTP para que:
- El frontend pueda manejar por "code"
- El backend pueda correlacionar por request_id / error_id
- La API sea consistente y auditable

-------------------------------------------------------------------------------
CRC (Component Card)
-------------------------------------------------------------------------------
Componente:
  AppHTTPException + handlers

Responsabilidades:
  - Definir catálogo de códigos de error (ErrorCode)
  - Construir payload RFC7807 (ErrorDetail)
  - Proveer factories de errores frecuentes
  - Proveer handlers (FastAPI) para devolver JSON problem+json

Colaboradores:
  - crosscutting/middleware.py (request_id)
  - api/exception_handlers.py (mapea errores internos)
===============================================================================
"""

from __future__ import annotations

from enum import Enum
from typing import Any

from fastapi import HTTPException, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel


class ErrorCode(str, Enum):
    # 4xx
    VALIDATION_ERROR = "VALIDATION_ERROR"
    UNAUTHORIZED = "UNAUTHORIZED"
    FORBIDDEN = "FORBIDDEN"
    NOT_FOUND = "NOT_FOUND"
    CONFLICT = "CONFLICT"
    UNSUPPORTED_MEDIA = "UNSUPPORTED_MEDIA"
    RATE_LIMITED = "RATE_LIMITED"
    PAYLOAD_TOO_LARGE = "PAYLOAD_TOO_LARGE"

    # 5xx
    INTERNAL_ERROR = "INTERNAL_ERROR"
    SERVICE_UNAVAILABLE = "SERVICE_UNAVAILABLE"
    LLM_ERROR = "LLM_ERROR"
    EMBEDDING_ERROR = "EMBEDDING_ERROR"
    DATABASE_ERROR = "DATABASE_ERROR"


class ErrorDetail(BaseModel):
    """
    Modelo RFC 7807 (Problem Details).

    Campos extra:
    - code: error code estable para clientes
    - errors: lista opcional de detalles (ej: [{"field":"x","msg":"..."}])
    """

    type: str = "about:blank"
    title: str
    status: int
    detail: str
    code: ErrorCode
    instance: str | None = None
    errors: list[dict[str, Any]] | None = None


PROBLEM_JSON_MEDIA_TYPE = "application/problem+json"

_OPENAPI_ERROR_SCHEMA = {"$ref": "#/components/schemas/ErrorDetail"}
_OPENAPI_ERROR_CONTENT = {PROBLEM_JSON_MEDIA_TYPE: {"schema": _OPENAPI_ERROR_SCHEMA}}

OPENAPI_ERROR_RESPONSES = {
    "400": {
        "description": "Bad Request (RFC7807)",
        "model": ErrorDetail,
        "content": _OPENAPI_ERROR_CONTENT,
    },
    "401": {
        "description": "Unauthorized (RFC7807)",
        "model": ErrorDetail,
        "content": _OPENAPI_ERROR_CONTENT,
    },
    "403": {
        "description": "Forbidden (RFC7807)",
        "model": ErrorDetail,
        "content": _OPENAPI_ERROR_CONTENT,
    },
    "404": {
        "description": "Not Found (RFC7807)",
        "model": ErrorDetail,
        "content": _OPENAPI_ERROR_CONTENT,
    },
    "409": {
        "description": "Conflict (RFC7807)",
        "model": ErrorDetail,
        "content": _OPENAPI_ERROR_CONTENT,
    },
    "413": {
        "description": "Payload Too Large (RFC7807)",
        "model": ErrorDetail,
        "content": _OPENAPI_ERROR_CONTENT,
    },
    "415": {
        "description": "Unsupported Media (RFC7807)",
        "model": ErrorDetail,
        "content": _OPENAPI_ERROR_CONTENT,
    },
    "422": {
        "description": "Validation Error (RFC7807)",
        "model": ErrorDetail,
        "content": _OPENAPI_ERROR_CONTENT,
    },
    "default": {
        "description": "Error (RFC7807)",
        "model": ErrorDetail,
        "content": _OPENAPI_ERROR_CONTENT,
    },
}


class AppHTTPException(HTTPException):
    """
    ----------------------------------------------------------------------------
    CRC (Class Card)
    ----------------------------------------------------------------------------
    Clase:
      AppHTTPException

    Responsabilidades:
      - Adjuntar un ErrorCode estable
      - Transportar errores de validación (errors[])
      - Permitir headers custom (Retry-After, RateLimit, etc.)

    Colaboradores:
      - app_exception_handler()
    ----------------------------------------------------------------------------
    """

    def __init__(
        self,
        status_code: int,
        code: ErrorCode,
        detail: str,
        errors: list[dict[str, Any]] | None = None,
    ):
        super().__init__(status_code=status_code, detail=detail)
        self.code = code
        self.errors = errors


# ---------------------------------------------------------------------------
# Factories de error (helpers)
# ---------------------------------------------------------------------------
def validation_error(
    detail: str, errors: list[dict[str, Any]] | None = None
) -> AppHTTPException:
    return AppHTTPException(422, ErrorCode.VALIDATION_ERROR, detail, errors)


def not_found(resource: str, identifier: str) -> AppHTTPException:
    return AppHTTPException(
        404, ErrorCode.NOT_FOUND, f"{resource} '{identifier}' no encontrado"
    )


def conflict(detail: str) -> AppHTTPException:
    return AppHTTPException(409, ErrorCode.CONFLICT, detail)


def unauthorized(detail: str = "Autenticación requerida") -> AppHTTPException:
    return AppHTTPException(401, ErrorCode.UNAUTHORIZED, detail)


def forbidden(detail: str = "Acceso denegado") -> AppHTTPException:
    return AppHTTPException(403, ErrorCode.FORBIDDEN, detail)


def rate_limited(retry_after: int = 60) -> AppHTTPException:
    exc = AppHTTPException(
        429,
        ErrorCode.RATE_LIMITED,
        f"Demasiadas solicitudes. Reintentá en {retry_after}s",
    )
    exc.headers = {"Retry-After": str(retry_after)}
    return exc


def payload_too_large(max_size: str) -> AppHTTPException:
    return AppHTTPException(
        413,
        ErrorCode.PAYLOAD_TOO_LARGE,
        f"El payload excede el máximo permitido ({max_size})",
    )


def unsupported_media(detail: str) -> AppHTTPException:
    return AppHTTPException(415, ErrorCode.UNSUPPORTED_MEDIA, detail)


def internal_error(detail: str = "Ocurrió un error inesperado") -> AppHTTPException:
    return AppHTTPException(500, ErrorCode.INTERNAL_ERROR, detail)


def service_unavailable(service: str) -> AppHTTPException:
    return AppHTTPException(
        503,
        ErrorCode.SERVICE_UNAVAILABLE,
        f"Servicio no disponible temporalmente: {service}",
    )


def llm_error(detail: str) -> AppHTTPException:
    return AppHTTPException(502, ErrorCode.LLM_ERROR, detail)


def embedding_error(detail: str) -> AppHTTPException:
    return AppHTTPException(502, ErrorCode.EMBEDDING_ERROR, detail)


def database_error(
    detail: str = "Falla en operación de base de datos",
) -> AppHTTPException:
    return AppHTTPException(503, ErrorCode.DATABASE_ERROR, detail)


# ---------------------------------------------------------------------------
# Handlers FastAPI
# ---------------------------------------------------------------------------
async def app_exception_handler(
    request: Request, exc: AppHTTPException
) -> JSONResponse:
    """
    Handler para AppHTTPException.

    Incluye instance (URL) y propaga headers opcionales (Retry-After, etc.).
    """
    # Correlación: request_id si existe
    request_id = getattr(getattr(request, "state", None), "request_id", None)

    errors = exc.errors or []
    if request_id:
        errors = [*errors, {"request_id": request_id}]

    error = ErrorDetail(
        type=f"about:blank/{exc.code.value.lower()}",
        title=exc.code.value.replace("_", " ").title(),
        status=exc.status_code,
        detail=str(exc.detail),
        code=exc.code,
        instance=str(request.url),
        errors=errors or None,
    )
    headers = getattr(exc, "headers", None)
    return JSONResponse(
        status_code=exc.status_code,
        content=error.model_dump(exclude_none=True),
        headers=headers,
        media_type=PROBLEM_JSON_MEDIA_TYPE,
    )


async def generic_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """
    Handler de fallback para excepciones no manejadas.
    (No expone detalles internos al cliente.)
    """
    request_id = getattr(getattr(request, "state", None), "request_id", None)
    errors = [{"request_id": request_id}] if request_id else None

    error = ErrorDetail(
        type="about:blank/internal_error",
        title="Internal Server Error",
        status=500,
        detail="Ocurrió un error inesperado",
        code=ErrorCode.INTERNAL_ERROR,
        instance=str(request.url),
        errors=errors,
    )
    return JSONResponse(
        status_code=500,
        content=error.model_dump(exclude_none=True),
        media_type=PROBLEM_JSON_MEDIA_TYPE,
    )
