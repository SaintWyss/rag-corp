"""
Standardized error response catalog for API consistency.
All HTTP error responses follow the RFC 7807 Problem Details format.
"""

from __future__ import annotations

from enum import Enum
from typing import Any

from fastapi import HTTPException, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel


class ErrorCode(str, Enum):
    """Application error codes for client-side handling."""

    # 4xx Client Errors
    VALIDATION_ERROR = "VALIDATION_ERROR"
    UNAUTHORIZED = "UNAUTHORIZED"
    FORBIDDEN = "FORBIDDEN"
    NOT_FOUND = "NOT_FOUND"
    CONFLICT = "CONFLICT"
    UNSUPPORTED_MEDIA = "UNSUPPORTED_MEDIA"
    RATE_LIMITED = "RATE_LIMITED"
    PAYLOAD_TOO_LARGE = "PAYLOAD_TOO_LARGE"

    # 5xx Server Errors
    INTERNAL_ERROR = "INTERNAL_ERROR"
    SERVICE_UNAVAILABLE = "SERVICE_UNAVAILABLE"
    LLM_ERROR = "LLM_ERROR"
    EMBEDDING_ERROR = "EMBEDDING_ERROR"
    DATABASE_ERROR = "DATABASE_ERROR"


class ErrorDetail(BaseModel):
    """RFC 7807 Problem Details response."""

    type: str = "about:blank"
    title: str
    status: int
    detail: str
    code: ErrorCode
    instance: str | None = None
    errors: list[dict[str, Any]] | None = None


PROBLEM_JSON_MEDIA_TYPE = "application/problem+json"

# R: Reusable OpenAPI response entry for RFC 7807 errors
_OPENAPI_ERROR_SCHEMA = {"$ref": "#/components/schemas/ErrorDetail"}
_OPENAPI_ERROR_CONTENT = {
    PROBLEM_JSON_MEDIA_TYPE: {
        "schema": _OPENAPI_ERROR_SCHEMA,
    }
}

OPENAPI_ERROR_RESPONSES = {
    "400": {
        "description": "Bad Request (RFC 7807 Problem Details)",
        "model": ErrorDetail,
        "content": _OPENAPI_ERROR_CONTENT,
    },
    "401": {
        "description": "Unauthorized (RFC 7807 Problem Details)",
        "model": ErrorDetail,
        "content": _OPENAPI_ERROR_CONTENT,
    },
    "403": {
        "description": "Forbidden (RFC 7807 Problem Details)",
        "model": ErrorDetail,
        "content": _OPENAPI_ERROR_CONTENT,
    },
    "404": {
        "description": "Not Found (RFC 7807 Problem Details)",
        "model": ErrorDetail,
        "content": _OPENAPI_ERROR_CONTENT,
    },
    "409": {
        "description": "Conflict (RFC 7807 Problem Details)",
        "model": ErrorDetail,
        "content": _OPENAPI_ERROR_CONTENT,
    },
    "422": {
        "description": "Validation Error (RFC 7807 Problem Details)",
        "model": ErrorDetail,
        "content": _OPENAPI_ERROR_CONTENT,
    },
    "default": {
        "description": "Error response (RFC 7807 Problem Details)",
        "model": ErrorDetail,
        "content": _OPENAPI_ERROR_CONTENT,
    },
}


class AppHTTPException(HTTPException):
    """Application-specific HTTP exception with error code."""

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


# Pre-defined error factories
def validation_error(
    detail: str, errors: list[dict[str, Any]] | None = None
) -> AppHTTPException:
    return AppHTTPException(422, ErrorCode.VALIDATION_ERROR, detail, errors)


def not_found(resource: str, identifier: str) -> AppHTTPException:
    return AppHTTPException(
        404, ErrorCode.NOT_FOUND, f"{resource} '{identifier}' not found"
    )


def conflict(detail: str) -> AppHTTPException:
    return AppHTTPException(409, ErrorCode.CONFLICT, detail)


def unauthorized(detail: str = "Authentication required") -> AppHTTPException:
    return AppHTTPException(401, ErrorCode.UNAUTHORIZED, detail)


def forbidden(detail: str = "Access denied") -> AppHTTPException:
    return AppHTTPException(403, ErrorCode.FORBIDDEN, detail)


def rate_limited(retry_after: int = 60) -> AppHTTPException:
    exc = AppHTTPException(
        429, ErrorCode.RATE_LIMITED, f"Too many requests. Retry after {retry_after}s"
    )
    exc.headers = {"Retry-After": str(retry_after)}
    return exc


def payload_too_large(max_size: str) -> AppHTTPException:
    return AppHTTPException(
        413, ErrorCode.PAYLOAD_TOO_LARGE, f"Payload exceeds maximum size of {max_size}"
    )


def unsupported_media(detail: str) -> AppHTTPException:
    return AppHTTPException(415, ErrorCode.UNSUPPORTED_MEDIA, detail)


def internal_error(detail: str = "An unexpected error occurred") -> AppHTTPException:
    return AppHTTPException(500, ErrorCode.INTERNAL_ERROR, detail)


def service_unavailable(service: str) -> AppHTTPException:
    return AppHTTPException(
        503, ErrorCode.SERVICE_UNAVAILABLE, f"{service} is temporarily unavailable"
    )


def llm_error(detail: str) -> AppHTTPException:
    return AppHTTPException(502, ErrorCode.LLM_ERROR, detail)


def embedding_error(detail: str) -> AppHTTPException:
    return AppHTTPException(502, ErrorCode.EMBEDDING_ERROR, detail)


def database_error(detail: str = "Database operation failed") -> AppHTTPException:
    return AppHTTPException(503, ErrorCode.DATABASE_ERROR, detail)


# Exception handlers for FastAPI
async def app_exception_handler(
    request: Request, exc: AppHTTPException
) -> JSONResponse:
    """Handler for AppHTTPException."""
    error = ErrorDetail(
        type=f"https://api.ragcorp.local/errors/{exc.code.value.lower()}",
        title=exc.code.value.replace("_", " ").title(),
        status=exc.status_code,
        detail=exc.detail,
        code=exc.code,
        instance=str(request.url),
        errors=exc.errors,
    )
    headers = getattr(exc, "headers", None)
    return JSONResponse(
        status_code=exc.status_code,
        content=error.model_dump(exclude_none=True),
        headers=headers,
        media_type=PROBLEM_JSON_MEDIA_TYPE,
    )


async def generic_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """Fallback handler for unhandled exceptions."""
    error = ErrorDetail(
        type="https://api.ragcorp.local/errors/internal_error",
        title="Internal Server Error",
        status=500,
        detail="An unexpected error occurred",
        code=ErrorCode.INTERNAL_ERROR,
        instance=str(request.url),
    )
    return JSONResponse(
        status_code=500,
        content=error.model_dump(exclude_none=True),
        media_type=PROBLEM_JSON_MEDIA_TYPE,
    )
