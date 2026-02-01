"""
===============================================================================
TARJETA CRC — domain/services.py
===============================================================================

Módulo:
    Puertos de Servicios Externos (Protocols)

Responsabilidades:
    - Definir contratos para servicios externos (Embeddings / LLM / Chunking).
    - Proteger a application de detalles del proveedor.
    - Mantener el dominio independiente de SDKs.

Colaboradores:
    - infrastructure/services/*: implementaciones concretas.
    - application/usecases: consumen estos puertos.

Reglas:
    - SOLO interfaces: nada de implementación.
    - Firmas estables y provider-agnostic.
===============================================================================
"""

from __future__ import annotations

from typing import AsyncGenerator, Protocol
from uuid import UUID


class EmbeddingService(Protocol):
    """Contrato para generar embeddings."""

    def embed_batch(self, texts: list[str]) -> list[list[float]]:
        """Embeddings batch (ideal para ingesta)."""
        ...

    def embed_query(self, query: str) -> list[float]:
        """Embedding individual (ideal para búsqueda)."""
        ...


class LLMService(Protocol):
    """Contrato para generación con modelo de lenguaje."""

    def generate_answer(self, query: str, context: str) -> str:
        """Genera respuesta usando contexto (RAG)."""
        ...

    def generate_text(self, prompt: str, max_tokens: int = 200) -> str:
        """Generación auxiliar (resúmenes, reescrituras, etc.)."""
        ...

    async def generate_stream(
        self, query: str, chunks: list["Chunk"]
    ) -> AsyncGenerator[str, None]:
        """Stream de salida (token a token / chunk a chunk)."""
        ...


from .entities import Chunk  # noqa: E402


class TextChunkerService(Protocol):
    """Contrato para partir texto en chunks de forma determinística."""

    def chunk(self, text: str) -> list[str]: ...


class FileStoragePort(Protocol):
    """Contrato de storage de archivos (S3/MinIO/etc.)."""

    def upload_file(
        self, key: str, content: bytes, content_type: str | None
    ) -> None: ...

    def download_file(self, key: str) -> bytes: ...

    def delete_file(self, key: str) -> None: ...

    def generate_presigned_url(
        self,
        key: str,
        *,
        expires_in_seconds: int = 3600,
        filename: str | None = None,
    ) -> str: ...


class DocumentTextExtractor(Protocol):
    """Contrato para extraer texto desde documentos binarios."""

    def extract_text(self, mime_type: str, content: bytes) -> str: ...


class DocumentProcessingQueue(Protocol):
    """Contrato para encolar procesamiento de documentos."""

    def enqueue_document_processing(
        self, document_id: UUID, *, workspace_id: UUID
    ) -> str: ...
