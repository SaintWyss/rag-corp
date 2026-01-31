"""
===============================================================================
DOCUMENT USE CASES PACKAGE (Public API / Exports)
===============================================================================

Name:
    Document Use Cases (package exports)

Business Goal:
    Exponer una API pública, clara y estable para la capa application respecto
    a casos de uso de Documentos y sus DTOs/resultados/errores asociados.

Why (Context / Intención):
    - Centraliza imports en un único módulo: evita dependencias “desparramadas”.
    - Permite refactors internos sin romper consumidores (API estable).
    - Deja explícito qué partes del paquete son “públicas” y cuáles internas.
    - Facilita onboarding: un analista/ingeniero ve el catálogo de capacidades
      del subdominio Document de un vistazo.

-------------------------------------------------------------------------------
CRC CARD (Module-Responsibility-Collaborator)
-------------------------------------------------------------------------------
Component:
    document usecases package (__init__.py)

Responsibilities:
    - Re-exportar los casos de uso principales de Document.
    - Re-exportar resultados/DTOs compartidos utilizados por Document + RAG flows.
    - Re-exportar tipos de error (DocumentError, DocumentErrorCode).
    - Definir __all__ como contrato de API pública del paquete.

Collaborators:
    - Módulos internos del paquete:
        delete_document, download_document, get_document, list_documents,
        update_document_metadata, document_results
===============================================================================
"""

from __future__ import annotations

# -----------------------------------------------------------------------------
# Use Cases
# -----------------------------------------------------------------------------
from .delete_document import DeleteDocumentUseCase

# -----------------------------------------------------------------------------
# DTOs / Result models (shared across document & RAG-related flows)
# -----------------------------------------------------------------------------
from .document_results import (
    AnswerQueryResult,
    DeleteDocumentResult,
    DocumentError,
    DocumentErrorCode,
    DownloadDocumentResult,
    GetDocumentResult,
    IngestDocumentResult,
    ListDocumentsResult,
    ReprocessDocumentResult,
    SearchChunksResult,
    UpdateDocumentMetadataResult,
    UploadDocumentResult,
)
from .download_document import DownloadDocumentUseCase
from .get_document import GetDocumentUseCase
from .list_documents import ListDocumentsUseCase
from .update_document_metadata import UpdateDocumentMetadataUseCase

# -----------------------------------------------------------------------------
# Public API (explicit exports)
# -----------------------------------------------------------------------------
__all__ = [
    # Use Cases
    "GetDocumentUseCase",
    "ListDocumentsUseCase",
    "DeleteDocumentUseCase",
    "UpdateDocumentMetadataUseCase",
    "DownloadDocumentUseCase",
    # Results
    "GetDocumentResult",
    "ListDocumentsResult",
    "DeleteDocumentResult",
    "UpdateDocumentMetadataResult",
    "DownloadDocumentResult",
    "UploadDocumentResult",
    "ReprocessDocumentResult",
    "IngestDocumentResult",
    "AnswerQueryResult",
    "SearchChunksResult",
    # Error types
    "DocumentError",
    "DocumentErrorCode",
]
