"""
Name: FastAPI Exception Handlers

Responsibilities:
  - Handle domain exceptions and convert to HTTP responses
  - Structured error responses (RFC 7807 style)
  - Centralized logging of errors with correlation IDs

Collaborators:
  - main.py: Registers these handlers
  - exceptions.py: RAGError, DatabaseError, EmbeddingError, LLMError

Constraints:
  - All responses use RFC 7807 Problem Details format
  - HTTP status codes: 503 for service errors, 500 for generic errors

Notes:
  - Extracted from main.py for better maintainability
  - Handlers are stateless functions
"""

from fastapi import Request
from fastapi.responses import JSONResponse

from .exceptions import RAGError, DatabaseError, EmbeddingError, LLMError
from .error_responses import AppHTTPException, ErrorCode, app_exception_handler
from .logger import logger


async def database_error_handler(request: Request, exc: DatabaseError) -> JSONResponse:
    """Handle database errors with structured response."""
    logger.error(
        "Database error", extra={"error_id": exc.error_id, "error_message": exc.message}
    )
    app_exc = AppHTTPException(
        status_code=503,
        code=ErrorCode.DATABASE_ERROR,
        detail=exc.message,
        errors=[{"error_id": exc.error_id}],
    )
    return await app_exception_handler(request, app_exc)


async def embedding_error_handler(
    request: Request, exc: EmbeddingError
) -> JSONResponse:
    """Handle embedding service errors."""
    logger.error(
        "Embedding error",
        extra={"error_id": exc.error_id, "error_message": exc.message},
    )
    app_exc = AppHTTPException(
        status_code=503,
        code=ErrorCode.EMBEDDING_ERROR,
        detail=exc.message,
        errors=[{"error_id": exc.error_id}],
    )
    return await app_exception_handler(request, app_exc)


async def llm_error_handler(request: Request, exc: LLMError) -> JSONResponse:
    """Handle LLM service errors."""
    logger.error(
        "LLM error", extra={"error_id": exc.error_id, "error_message": exc.message}
    )
    app_exc = AppHTTPException(
        status_code=503,
        code=ErrorCode.LLM_ERROR,
        detail=exc.message,
        errors=[{"error_id": exc.error_id}],
    )
    return await app_exception_handler(request, app_exc)


async def rag_error_handler(request: Request, exc: RAGError) -> JSONResponse:
    """Handle generic RAG errors."""
    logger.error(
        "RAG error", extra={"error_id": exc.error_id, "error_message": exc.message}
    )
    app_exc = AppHTTPException(
        status_code=500,
        code=ErrorCode.INTERNAL_ERROR,
        detail=exc.message,
        errors=[{"error_id": exc.error_id}],
    )
    return await app_exception_handler(request, app_exc)


def register_exception_handlers(app) -> None:
    """
    Register all exception handlers on the FastAPI app.

    Usage:
        from .exception_handlers import register_exception_handlers
        register_exception_handlers(app)
    """
    app.add_exception_handler(DatabaseError, database_error_handler)
    app.add_exception_handler(EmbeddingError, embedding_error_handler)
    app.add_exception_handler(LLMError, llm_error_handler)
    app.add_exception_handler(RAGError, rag_error_handler)
    app.add_exception_handler(AppHTTPException, app_exception_handler)
