"""
===============================================================================
INGESTION USE CASES PACKAGE (Public API / Exports)
===============================================================================

Name:
    Ingestion Use Cases (package exports)

Business Goal:
    Exponer una API pública, clara y estable para los casos de uso vinculados
    a la ingesta de documentos (upload, procesamiento, re-procesamiento,
    ingest directo, cancelación y consulta de estado).

Why (Context / Intención):
    - La ingesta suele ser un pipeline con etapas (upload -> enqueue -> process).
    - Centralizar exports:
        * evita imports dispersos
        * mejora descubribilidad para el equipo
        * facilita refactors internos sin romper consumidores
    - Incluye operaciones de soporte:
        * Cancel: para recuperar documentos atascados
        * GetStatus: para polling desde frontend

-------------------------------------------------------------------------------
CRC CARD (Module-Responsibility-Collaborator)
-------------------------------------------------------------------------------
Component:
    ingestion usecases package (__init__.py)

Responsibilities:
    - Re-exportar inputs (DTOs), outputs y use cases del subdominio de Ingestion.
    - Declarar explícitamente el contrato público con __all__.

Collaborators:
    - Módulos internos del paquete:
        ingest_document, upload_document, process_uploaded_document,
        reprocess_document, cancel_document_processing, get_document_status
===============================================================================
"""

from __future__ import annotations

# Support operations
from .cancel_document_processing import (
    CancelDocumentProcessingInput,
    CancelDocumentProcessingResult,
    CancelDocumentProcessingUseCase,
)
from .get_document_status import (
    GetDocumentProcessingStatusInput,
    GetDocumentProcessingStatusResult,
    GetDocumentProcessingStatusUseCase,
)

# Core ingestion pipeline
from .ingest_document import IngestDocumentInput, IngestDocumentUseCase
from .process_uploaded_document import (
    ProcessUploadedDocumentInput,
    ProcessUploadedDocumentOutput,
    ProcessUploadedDocumentUseCase,
)
from .reprocess_document import ReprocessDocumentInput, ReprocessDocumentUseCase
from .upload_document import UploadDocumentInput, UploadDocumentUseCase

# -----------------------------------------------------------------------------
# Use Cases + Inputs/Outputs (DTOs)
# -----------------------------------------------------------------------------


# -----------------------------------------------------------------------------
# Public API (explicit exports)
# -----------------------------------------------------------------------------
__all__ = [
    # Core pipeline: Upload -> Process
    "UploadDocumentInput",
    "UploadDocumentUseCase",
    "ProcessUploadedDocumentInput",
    "ProcessUploadedDocumentOutput",
    "ProcessUploadedDocumentUseCase",
    # Core pipeline: Reprocess (retry failed)
    "ReprocessDocumentInput",
    "ReprocessDocumentUseCase",
    # Core pipeline: Direct ingest (text -> chunks -> embeddings)
    "IngestDocumentInput",
    "IngestDocumentUseCase",
    # Support: Cancel stuck documents
    "CancelDocumentProcessingInput",
    "CancelDocumentProcessingResult",
    "CancelDocumentProcessingUseCase",
    # Support: Query processing status (polling)
    "GetDocumentProcessingStatusInput",
    "GetDocumentProcessingStatusResult",
    "GetDocumentProcessingStatusUseCase",
]
