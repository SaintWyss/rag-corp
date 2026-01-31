"""
===============================================================================
DOCUMENT + RAG USE CASE RESULTS (Shared Result / Error Models)
===============================================================================

Name:
    Document Use Case Results

Business Goal:
    Proveer tipos consistentes de resultados y errores para casos de uso de:
      - Documentos (CRUD, ingest, procesamiento)
      - RAG/Chat (search chunks, answer query)

Why (Context / Intención):
    - Los use cases devuelven resultados tipados en lugar de propagar excepciones.
    - Facilita:
        * mapeo uniforme a HTTP (status codes y payloads)
        * testeo de flujos por resultado (sin mocks de HTTP)
        * consistencia transversal (Document + RAG)
    - El campo `resource` en DocumentError permite que errores reutilizables
      (ej. "Workspace not found") indiquen qué recurso falló.

-------------------------------------------------------------------------------
CRC CARD (Module-Responsibility-Collaborator)
-------------------------------------------------------------------------------
Component:
    document_results models (module)

Responsibilities:
    - Definir DocumentErrorCode como conjunto estable de categorías de error.
    - Definir DocumentError como contrato mínimo de error.
    - Definir DTOs de resultados por caso de uso:
        * ListDocumentsResult, GetDocumentResult, DeleteDocumentResult
        * UploadDocumentResult, ReprocessDocumentResult, IngestDocumentResult
        * AnswerQueryResult, SearchChunksResult

Collaborators:
    - domain.entities:
        Document, Chunk, QueryResult
===============================================================================
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import List
from uuid import UUID

from ....domain.entities import Chunk, Document, QueryResult


class DocumentErrorCode(str, Enum):
    """
    Categorías de error para casos de uso de Documentos y RAG.

    Notas de diseño:
      - str + Enum facilita serialización directa.
      - Los códigos son estables y representan categorías (no mensajes).
      - Mantener un set acotado evita fragmentación de errores.

    Códigos:
      - VALIDATION_ERROR: input inválido/incompleto.
      - FORBIDDEN: actor no autorizado para la operación.
      - NOT_FOUND: recurso inexistente o no visible en el contexto.
      - CONFLICT: colisión de reglas de negocio (unicidad, estados inválidos).
      - SERVICE_UNAVAILABLE: dependencia externa caída o degradada (LLM, storage, etc.).
    """

    VALIDATION_ERROR = "VALIDATION_ERROR"
    FORBIDDEN = "FORBIDDEN"
    NOT_FOUND = "NOT_FOUND"
    CONFLICT = "CONFLICT"
    SERVICE_UNAVAILABLE = "SERVICE_UNAVAILABLE"


@dataclass(frozen=True)
class DocumentError:
    """
    Error de caso de uso para Document/RAG.

    Campos:
      - code: DocumentErrorCode (categoría estable)
      - message: mensaje humano (UI/logs)
      - resource: nombre del recurso afectado (opcional)
          * Ej: "Workspace", "Document", "Chunk", etc.

    Nota:
      - Se mantiene simple: sin detalles de infraestructura.
      - Si luego necesitás enriquecer, se puede agregar un campo `details`.
    """

    code: DocumentErrorCode
    message: str
    resource: str | None = None


@dataclass
class ListDocumentsResult:
    """
    Resultado para listar documentos.

    Campos:
      - documents: lista de documentos visibles (posiblemente vacía).
      - next_cursor: cursor para paginación (si aplica).
      - error: error tipado si falló la operación.
    """

    documents: List[Document]
    next_cursor: str | None = None
    error: DocumentError | None = None


@dataclass
class GetDocumentResult:
    """
    Resultado para obtener un documento.

    Contrato:
      - Éxito: document != None y error == None
      - Falla:  document == None y error != None
    """

    document: Document | None = None
    error: DocumentError | None = None


@dataclass
class DeleteDocumentResult:
    """
    Resultado para eliminar (soft-delete) un documento.

    Campos:
      - deleted: True si el documento quedó eliminado lógicamente.
      - error: error tipado si la operación falló.
    """

    deleted: bool
    error: DocumentError | None = None


@dataclass
class UploadDocumentResult:
    """
    Resultado para la operación de upload/alta de documento.

    Campos:
      - document_id: ID del documento creado.
      - status: estado del documento (ej. PENDING/PROCESSING/READY/FAILED).
      - file_name: nombre del archivo subido.
      - mime_type: tipo MIME.
      - error: error tipado si falló.

    Nota:
      - El upload suele ser el inicio de un pipeline asíncrono (enqueue + procesamiento).
    """

    document_id: UUID | None = None
    status: str | None = None
    file_name: str | None = None
    mime_type: str | None = None
    error: DocumentError | None = None


@dataclass
class ReprocessDocumentResult:
    """
    Resultado para solicitar reprocesamiento de un documento.

    Campos:
      - document_id: ID objetivo.
      - status: estado resultante o actual.
      - enqueued: True si se encoló un job de reprocesamiento.
      - error: error tipado si falló.
    """

    document_id: UUID | None = None
    status: str | None = None
    enqueued: bool = False
    error: DocumentError | None = None


@dataclass
class IngestDocumentResult:
    """
    Resultado del proceso de ingest (parse/chunk/embed/store).

    Campos:
      - document_id: ID del documento ingerido.
      - chunks_created: cantidad de chunks generados y persistidos.
      - error: error tipado si falló.
    """

    document_id: UUID | None = None
    chunks_created: int = 0
    error: DocumentError | None = None


@dataclass
class AnswerQueryResult:
    """
    Resultado de responder una consulta (RAG).

    Campos:
      - result: QueryResult con respuesta, fuentes, metadata, etc.
      - error: error tipado si falló (por ejemplo, dependencia externa).
    """

    result: QueryResult | None = None
    error: DocumentError | None = None


@dataclass
class SearchChunksResult:
    """
    Resultado de búsqueda semántica (vector search) de chunks.

    Campos:
      - matches: lista de chunks encontrados (posiblemente vacía).
      - metadata: observabilidad de retrieval/rerank (opcional).
      - error: error tipado si falló.
    """

    matches: List[Chunk]
    metadata: dict | None = None
    error: DocumentError | None = None


@dataclass
class UpdateDocumentMetadataResult:
    """
    Resultado para actualizar metadatos de un documento (nombre, tags).

    Contrato:
      - Éxito: document != None y error == None
      - Falla: document == None y error != None
    """

    document: Document | None = None
    error: DocumentError | None = None


@dataclass
class DownloadDocumentResult:
    """
    Resultado para generar URL de descarga de un documento.

    Campos:
      - url: URL presignada para descarga directa (temporal).
      - file_name: nombre original del archivo.
      - mime_type: tipo MIME del archivo.
      - error: error tipado si falló.

    Nota:
      - La URL tiene expiración configurable (por defecto 1 hora).
      - El cliente descarga directamente del storage (S3/MinIO).
    """

    url: str | None = None
    file_name: str | None = None
    mime_type: str | None = None
    error: DocumentError | None = None
