"""
===============================================================================
TARJETA CRC — app/api/exception_handlers.py (Manejo Centralizado de Excepciones)
===============================================================================

Responsabilidades:
  - Traducir excepciones de la aplicación a respuestas HTTP RFC7807.
  - Centralizar logging de errores con request_id + error_id.
  - Evitar filtrar detalles internos en errores no controlados.

Patrones aplicados:
  - Exception Mapping (Presentation Layer).
  - Fail-safe: cualquier excepción no tipada -> INTERNAL_ERROR (con logging).
  - Observabilidad: correlación por request_id y error_id.

Colaboradores:
  - crosscutting.error_responses: AppHTTPException, ErrorCode, app_exception_handler
  - crosscutting.exceptions: RAGError y derivadas (Database/Embedding/LLM)
  - crosscutting.config.get_settings (para decidir nivel de detalle)
===============================================================================
"""

from __future__ import annotations

from fastapi import Request
from fastapi.responses import JSONResponse

from ..crosscutting.config import get_settings
from ..crosscutting.error_responses import (
    AppHTTPException,
    ErrorCode,
    app_exception_handler,
)
from ..crosscutting.exceptions import DatabaseError, EmbeddingError, LLMError, RAGError
from ..crosscutting.logger import logger


def _request_id_from(request: Request) -> str | None:
    return getattr(getattr(request, "state", None), "request_id", None)


async def _handle_service_error(
    request: Request,
    *,
    exc: RAGError,
    code: ErrorCode,
    status_code: int,
) -> JSONResponse:
    """Helper común para errores tipados de servicios."""
    request_id = _request_id_from(request)

    logger.error(
        "Error de servicio",
        extra={
            "code": code.value,
            "error_id": getattr(exc, "error_id", None),
            "message": getattr(exc, "message", str(exc)),
            "request_id": request_id,
        },
    )

    app_exc = AppHTTPException(
        status_code=status_code,
        code=code,
        detail=exc.message,
        errors=[{"error_id": exc.error_id, "request_id": request_id}],
    )
    return await app_exception_handler(request, app_exc)


async def database_error_handler(request: Request, exc: DatabaseError) -> JSONResponse:
    return await _handle_service_error(
        request, exc=exc, code=ErrorCode.DATABASE_ERROR, status_code=503
    )


async def embedding_error_handler(
    request: Request, exc: EmbeddingError
) -> JSONResponse:
    return await _handle_service_error(
        request, exc=exc, code=ErrorCode.EMBEDDING_ERROR, status_code=503
    )


async def llm_error_handler(request: Request, exc: LLMError) -> JSONResponse:
    return await _handle_service_error(
        request, exc=exc, code=ErrorCode.LLM_ERROR, status_code=503
    )


async def rag_error_handler(request: Request, exc: RAGError) -> JSONResponse:
    # R: Errores base: tratamos como INTERNAL_ERROR por defecto.
    return await _handle_service_error(
        request, exc=exc, code=ErrorCode.INTERNAL_ERROR, status_code=500
    )


async def unhandled_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """
    Handler defensivo para excepciones no tipadas.

    - Log completo (stacktrace).
    - Respuesta genérica (evita filtrar internos).
    """
    request_id = _request_id_from(request)
    settings = get_settings()

    logger.error(
        "Excepción no controlada",
        exc_info=True,
        extra={"request_id": request_id, "error": str(exc)},
    )

    # R: En desarrollo ayudamos un poco más; en producción evitamos filtrar detalles.
    detail = str(exc) if not settings.is_production() else "Error interno."

    app_exc = AppHTTPException(
        status_code=500,
        code=ErrorCode.INTERNAL_ERROR,
        detail=detail,
        errors=[{"request_id": request_id}],
    )
    return await app_exception_handler(request, app_exc)


def register_exception_handlers(app) -> None:
    """
    Registra handlers en la app FastAPI.

    Importante:
      - AppHTTPException debe registrarse para respetar RFC7807.
      - Exception genérica se registra al final como fallback.
    """
    app.add_exception_handler(DatabaseError, database_error_handler)
    app.add_exception_handler(EmbeddingError, embedding_error_handler)
    app.add_exception_handler(LLMError, llm_error_handler)
    app.add_exception_handler(RAGError, rag_error_handler)
    app.add_exception_handler(AppHTTPException, app_exception_handler)
    app.add_exception_handler(Exception, unhandled_exception_handler)


__all__ = ["register_exception_handlers"]
