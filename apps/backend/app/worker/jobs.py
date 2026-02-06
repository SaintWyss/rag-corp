"""
===============================================================================
TARJETA CRC — worker/jobs.py (Jobs RQ: Orquestación de Procesamiento)
===============================================================================

Responsabilidades:
  - Definir entrypoints de jobs ejecutados por RQ.
  - Validar inputs (UUIDs) de forma fail-fast y registrable.
  - Construir el caso de uso con dependencias inyectadas desde el contenedor.
  - Emitir logs/métricas/tracing con contexto consistente.
  - Garantizar limpieza de contexto al finalizar (éxito o fallo).

Patrones aplicados:
  - Command (Job): función pura como comando a ejecutar por el worker.
  - Composition Root (local): arma el use case con dependencias ya registradas.
  - Fail-fast + Observabilidad: valida temprano, mide tiempo, registra status.

Colaboradores:
  - application.usecases.ingestion.ProcessUploadedDocumentUseCase
  - container.get_* (repositorio, storage, extractor, chunker, embeddings)
  - crosscutting.metrics (record_worker_processed/failed, observe_worker_duration)
  - crosscutting.tracing.span
  - context (request_id_var, http_method_var, http_path_var, clear_context)
===============================================================================
"""

from __future__ import annotations

import time
from uuid import UUID

from rq import get_current_job

from ..application.usecases.ingestion import (
    ProcessUploadedDocumentInput,
    ProcessUploadedDocumentUseCase,
)
from ..container import (
    get_document_repository,
    get_document_text_extractor,
    get_embedding_service,
    get_file_storage,
    get_text_chunker,
)
from ..context import clear_context, http_method_var, http_path_var, request_id_var
from ..crosscutting.config import get_settings
from ..crosscutting.logger import logger
from ..crosscutting.metrics import (
    observe_worker_duration,
    record_worker_failed,
    record_worker_processed,
)
from ..crosscutting.tracing import span


def _parse_uuid(value: str, *, field_name: str, job_id: str | None) -> UUID | None:
    """
    Convierte un string a UUID con logging consistente.

    Retorna:
      - UUID si es válido
      - None si es inválido (y deja log/métrica al caller)
    """
    try:
        return UUID(value)
    except Exception:
        logger.error(
            "Job inválido: UUID malformado",
            extra={"field": field_name, "value": value, "job_id": job_id},
        )
        return None


def _build_use_case() -> ProcessUploadedDocumentUseCase:
    """
    Construye el caso de uso para el procesamiento del documento.

    Nota:
      - El contenedor ya decide implementaciones concretas (infraestructura).
      - Este job no debe conocer detalles de Redis/S3/Postgres/etc.
    """
    settings = get_settings()
    return ProcessUploadedDocumentUseCase(
        repository=get_document_repository(),
        storage=get_file_storage(),
        extractor=get_document_text_extractor(),
        chunker=get_text_chunker(),
        embedding_service=get_embedding_service(),
        enable_2tier_retrieval=settings.enable_2tier_retrieval,
        node_group_size=settings.node_group_size,
        node_text_max_chars=settings.node_text_max_chars,
    )


def process_document_job(document_id: str, workspace_id: str) -> None:
    """
    Job RQ: procesa un documento previamente subido.

    Contrato:
      - document_id/workspace_id llegan como string (RQ serializa argumentos).
      - Si el job explota, RQ aplica reintentos (configurado en el enqueue).
    """
    job = get_current_job()
    job_id = getattr(job, "id", None)

    # R: Contexto para logs y trazas (uniforme en worker).
    request_id_var.set(job_id or document_id)
    http_method_var.set("WORKER")
    http_path_var.set("rq.process_document_job")

    start = time.perf_counter()
    status = "UNKNOWN"
    chunks_created = 0

    try:
        doc_uuid = _parse_uuid(document_id, field_name="document_id", job_id=job_id)
        ws_uuid = _parse_uuid(workspace_id, field_name="workspace_id", job_id=job_id)

        if not doc_uuid or not ws_uuid:
            status = "INVALID"
            record_worker_processed(status)
            record_worker_failed()
            return

        logger.info(
            "Worker job iniciado",
            extra={
                "job_id": job_id,
                "document_id": str(doc_uuid),
                "workspace_id": str(ws_uuid),
            },
        )

        use_case = _build_use_case()

        with span(
            "worker.process_document",
            {
                "job_id": job_id or "",
                "document_id": str(doc_uuid),
                "workspace_id": str(ws_uuid),
            },
        ):
            result = use_case.execute(
                ProcessUploadedDocumentInput(document_id=doc_uuid, workspace_id=ws_uuid)
            )

        status = result.status
        chunks_created = getattr(result, "chunks_created", 0)

    except Exception as exc:
        # R: Marcamos FAILED y relanzamos para que RQ gestione retries.
        status = "FAILED"
        logger.exception(
            "Worker job falló con excepción",
            extra={
                "job_id": job_id,
                "document_id": document_id,
                "workspace_id": workspace_id,
                "error": str(exc),
            },
        )
        raise

    finally:
        duration = time.perf_counter() - start
        record_worker_processed(status)
        if status == "FAILED":
            record_worker_failed()

        observe_worker_duration(duration)

        logger.info(
            "Worker job finalizado",
            extra={
                "job_id": job_id,
                "document_id": document_id,
                "workspace_id": workspace_id,
                "status": status,
                "chunks_created": chunks_created,
                "duration_seconds": round(duration, 3),
            },
        )
        clear_context()


__all__ = ["process_document_job"]
