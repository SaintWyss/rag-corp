# apps/backend/app/crosscutting/exceptions.py
"""
===============================================================================
MÓDULO: Excepciones tipadas del backend (errores internos)
===============================================================================

Objetivo
--------
Tener excepciones internas coherentes, con:
- error_code estable
- error_id para correlación con logs
- message “humana” (sin filtrar secretos)

-------------------------------------------------------------------------------
CRC (Component Card)
-------------------------------------------------------------------------------
Componente:
  RAGError + subclases

Responsabilidades:
  - Estandarizar errores internos que luego se mapean a HTTP
  - Generar error_id para rastreo

Colaboradores:
  - api/exception_handlers.py (mapea a AppHTTPException)
  - crosscutting/logger.py
===============================================================================
"""

from __future__ import annotations

from dataclasses import dataclass
from uuid import uuid4


@dataclass(frozen=True)
class ErrorResponse:
    """Estructura mínima para responder errores de forma consistente (si se necesita)."""

    error_code: str
    message: str
    error_id: str

    def to_dict(self) -> dict:
        return {
            "error_code": self.error_code,
            "message": self.message,
            "error_id": self.error_id,
        }


class RAGError(Exception):
    """
    ----------------------------------------------------------------------------
    CRC (Class Card)
    ----------------------------------------------------------------------------
    Clase:
      RAGError

    Responsabilidades:
      - Base para errores internos del sistema
      - Proveer error_code + error_id + message

    Colaboradores:
      - api/exception_handlers.py
    ----------------------------------------------------------------------------
    """

    error_code: str = "RAG_ERROR"

    def __init__(
        self,
        message: str,
        error_id: str | None = None,
        original_error: Exception | None = None,
    ):
        self.message = message
        self.error_id = error_id or str(uuid4())
        self.original_error = original_error
        super().__init__(message)

    def to_response(self) -> ErrorResponse:
        return ErrorResponse(
            error_code=self.error_code, message=self.message, error_id=self.error_id
        )


class DatabaseError(RAGError):
    """Errores de DB (conexión, query, timeout, pool)."""

    error_code: str = "DATABASE_ERROR"


class EmbeddingError(RAGError):
    """Errores de embeddings (provider externo)."""

    error_code: str = "EMBEDDING_ERROR"


class LLMError(RAGError):
    """Errores del LLM (provider externo / quota / invalid request)."""

    error_code: str = "LLM_ERROR"
