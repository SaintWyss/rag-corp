"""
Name: Custom Exceptions and Error Handling

Responsibilities:
  - Define domain-specific exceptions
  - Provide error response structure
  - Generate unique error IDs for tracking

Collaborators:
  - FastAPI exception handlers (in main.py)
  - All modules that can raise errors

Constraints:
  - Error responses must include: error_code, message, error_id
  - Don't change existing HTTP response schemas

Notes:
  - error_id is UUID for log correlation
  - Use these exceptions instead of generic Exception
"""
from dataclasses import dataclass
from uuid import uuid4


@dataclass
class ErrorResponse:
    """Structured error response for API."""

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
    """Base exception for RAG application."""

    error_code: str = "RAG_ERROR"

    def __init__(self, message: str, error_id: str | None = None):
        self.message = message
        self.error_id = error_id or str(uuid4())
        super().__init__(message)

    def to_response(self) -> ErrorResponse:
        return ErrorResponse(
            error_code=self.error_code,
            message=self.message,
            error_id=self.error_id,
        )


class DatabaseError(RAGError):
    """Database connection or query error."""

    error_code: str = "DATABASE_ERROR"


class EmbeddingError(RAGError):
    """Embedding generation error (Google API)."""

    error_code: str = "EMBEDDING_ERROR"


class LLMError(RAGError):
    """LLM generation error (Gemini API)."""

    error_code: str = "LLM_ERROR"
