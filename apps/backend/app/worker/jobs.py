"""
===============================================================================
WORKER: Definición de Jobs (RQ)
===============================================================================

CRC CARD (Módulo)
-------------------------------------------------------------------------------
Nombre:
    worker.jobs

Responsabilidades:
    - Definir entrypoints ejecutables por RQ (dotted paths importables).
    - Orquestar la ejecución de casos de uso en segundo plano.
    - Asegurar observabilidad: logs, métricas, tracing y limpieza de contexto.

Colaboradores:
    - rq.get_current_job
    - application.usecases.ingestion.ProcessUploadedDocumentUseCase
    - container: factories de repositorios/servicios (import lazy)
    - crosscutting.logger / metrics / tracing
    - context: request_id_var + clear_context

Notas de Arquitectura (Senior):
    - Imports "pesados" (container + use cases) se hacen de forma lazy dentro
      de la función del job para evitar ciclos y reducir costo de import.
    - Este módulo debe ser importable por el worker (y opcionalmente validado
      por el API) sin efectos secundarios.
===============================================================================
"""

from __future__ import annotations

import time
from uuid import UUID

from rq import get_current_job

from ..context import clear_context, request_id_var
from ..crosscutting.logger import logger
from ..crosscutting.metrics import (
    observe_worker_duration,
    record_worker_failed,
    record_worker_processed,
)
from ..crosscutting.tracing import span


def process_document_job(document_id: str, workspace_id: str) -> None:
    """Job RQ: procesa un documento subido.

    Contrato:
      - Los argumentos llegan como strings (serialización segura en cola).
      - Convertimos y validamos a UUID antes de ejecutar el caso de uso.

    Observabilidad:
      - request_id_var se setea con job_id para correlación.
      - Siempre registramos duración y status final.
      - clear_context() SIEMPRE, incluso en errores.
    """
    job = get_current_job()
    job_id = getattr(job, "id", None)
    request_id_var.set(job_id or document_id)

    start_time = time.perf_counter()
    status = "UNKNOWN"

    try:
        doc_uuid = _parse_uuid(document_id, field_name="document_id", job_id=job_id)
        ws_uuid = _parse_uuid(workspace_id, field_name="workspace_id", job_id=job_id)

        use_case = _build_process_document_use_case()

        logger.info(
            "Worker job started",
            extra={
                "document_id": str(doc_uuid),
                "workspace_id": str(ws_uuid),
                "job_id": job_id,
            },
        )

        with span(
            "worker.process_document",
            {
                "document_id": str(doc_uuid),
                "workspace_id": str(ws_uuid),
                "job_id": job_id or "",
            },
        ):
            from ..application.usecases.ingestion import ProcessUploadedDocumentInput

            result = use_case.execute(
                ProcessUploadedDocumentInput(
                    document_id=doc_uuid,
                    workspace_id=ws_uuid,
                )
            )
            status = result.status

    except _InvalidJobArgsError:
        status = "INVALID"
        record_worker_processed(status)
        record_worker_failed()
        return

    except Exception:
        status = "FAILED"
        logger.exception(
            "Worker job crashed",
            extra={
                "document_id": document_id,
                "workspace_id": workspace_id,
                "job_id": job_id,
            },
        )
        raise

    finally:
        duration = time.perf_counter() - start_time
        record_worker_processed(status)
        if status == "FAILED":
            record_worker_failed()
        observe_worker_duration(duration)
        logger.info(
            "Worker job finished",
            extra={
                "document_id": document_id,
                "workspace_id": workspace_id,
                "job_id": job_id,
                "status": status,
                "duration_seconds": round(duration, 3),
            },
        )
        clear_context()


# -----------------------------------------------------------------------------
# Helpers privados
# -----------------------------------------------------------------------------


class _InvalidJobArgsError(Exception):
    """Señal interna para abortar el job por argumentos inválidos."""


def _parse_uuid(value: str, *, field_name: str, job_id: str | None) -> UUID:
    """Parsea un UUID desde string con logging consistente."""
    try:
        return UUID(value)
    except ValueError:
        logger.error(
            "Invalid UUID for job",
            extra={"field": field_name, "value": value, "job_id": job_id},
        )
        raise _InvalidJobArgsError()


def _build_process_document_use_case():
    """Construye el caso de uso con dependencias (DI manual).

    Nota:
      - Importamos container de forma lazy para evitar ciclos cuando el API
        valida job paths o cuando se reorganizan imports.
    """
    from ..application.usecases.ingestion import ProcessUploadedDocumentUseCase
    from ..container import (
        get_document_repository,
        get_document_text_extractor,
        get_embedding_service,
        get_file_storage,
        get_text_chunker,
    )

    return ProcessUploadedDocumentUseCase(
        repository=get_document_repository(),
        storage=get_file_storage(),
        extractor=get_document_text_extractor(),
        chunker=get_text_chunker(),
        embedding_service=get_embedding_service(),
    )
