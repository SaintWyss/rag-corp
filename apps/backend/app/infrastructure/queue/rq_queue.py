"""
===============================================================================
ARCHIVO: infrastructure/queue/rq_queue.py
===============================================================================

CRC CARD (Class)
-------------------------------------------------------------------------------
Clase:
    RQDocumentProcessingQueue (Adapter)

Responsabilidades:
    - Implementar el puerto de dominio `DocumentProcessingQueue` usando RQ.
    - Encolar el job de procesamiento de documentos de forma segura y observable.
    - Validar configuración (nombre de cola + job path importable) en modo fail-fast.
    - Encapsular dependencias externas (rq/redis) para no “filtrarlas” al dominio.

Colaboradores:
    - domain.services.DocumentProcessingQueue
    - job_paths.PROCESS_DOCUMENT_JOB_PATH
    - import_utils.is_importable_dotted_path
    - errors.QueueConfigurationError / QueueEnqueueError
    - crosscutting.logger

Patrones:
    - Adapter: traduce el puerto del dominio a una implementación RQ.
    - Fail-Fast: valida paths importables antes de encolar.
    - Lazy Import: rq se importa solo si se usa (dependencia opcional).
===============================================================================
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any
from uuid import UUID

from ...crosscutting.logger import logger
from ...domain.services import DocumentProcessingQueue
from .errors import QueueConfigurationError, QueueEnqueueError
from .import_utils import is_importable_dotted_path
from .job_paths import DOCUMENTS_QUEUE_NAME, PROCESS_DOCUMENT_JOB_PATH


@dataclass(frozen=True)
class RQQueueConfig:
    """Configuración del adaptador RQ.

    queue_name:
        Nombre de la cola en Redis.
    retry_max_attempts:
        Número de reintentos automáticos si el worker falla.
    job_timeout_seconds:
        Timeout máximo de ejecución del job en el worker.
    result_ttl_seconds:
        Tiempo de vida del resultado del job en Redis.
    """

    queue_name: str = DOCUMENTS_QUEUE_NAME
    retry_max_attempts: int = 3
    job_timeout_seconds: int = 900
    result_ttl_seconds: int = 0


class RQDocumentProcessingQueue(DocumentProcessingQueue):
    """Adapter RQ para el procesamiento asíncrono de documentos."""

    def __init__(self, *, redis: Any, config: RQQueueConfig) -> None:
        """Construye el adaptador.

        Diseño:
          - `redis` se inyecta desde el contenedor (DIP) para compartir pool.
          - Validamos configuración temprano para evitar jobs zombis.
        """
        self._redis = redis
        self._config = _validate_config(config)

        # Fail-fast: el worker necesita importar el job.
        if not is_importable_dotted_path(PROCESS_DOCUMENT_JOB_PATH):
            raise QueueConfigurationError(
                "Job path no importable para RQ: "
                f"{PROCESS_DOCUMENT_JOB_PATH}. "
                "Revisar `infrastructure/queue/job_paths.py` y `app/worker/jobs.py`."
            )

        # Lazy import: rq es dependencia opcional.
        self._rq = _lazy_import_rq()

        # Construimos la cola real.
        self._queue = self._rq.Queue(name=self._config.queue_name, connection=redis)

        # Retry policy (si max_attempts <= 0, desactivamos)
        self._retry = None
        if self._config.retry_max_attempts and self._config.retry_max_attempts > 0:
            # Nota: RQ soporta `Retry(max=...)`.
            self._retry = self._rq.Retry(max=self._config.retry_max_attempts)

        logger.info(
            "RQ inicializada",
            extra={
                "queue": self._config.queue_name,
                "retry_max_attempts": self._config.retry_max_attempts,
                "job_timeout_seconds": self._config.job_timeout_seconds,
            },
        )

    def enqueue_document_processing(
        self, document_id: UUID, *, workspace_id: UUID
    ) -> str:
        """Encola el job de procesamiento de un documento.

        Contrato de serialización:
          - En la cola guardamos strings (UUIDs como texto) para evitar problemas
            de pickling/compatibilidad.
        """
        try:
            job = self._queue.enqueue(
                PROCESS_DOCUMENT_JOB_PATH,
                args=(str(document_id), str(workspace_id)),
                retry=self._retry,
                job_timeout=self._config.job_timeout_seconds,
                result_ttl=self._config.result_ttl_seconds,
                description=f"process_document:{document_id}",
            )

            job_id = getattr(job, "id", None) or getattr(job, "get_id", lambda: "")()
            job_id = str(job_id) if job_id else ""

            logger.info(
                "Documento encolado",
                extra={
                    "document_id": str(document_id),
                    "workspace_id": str(workspace_id),
                    "job_id": job_id,
                    "queue": self._config.queue_name,
                },
            )

            return job_id

        except Exception as exc:
            logger.exception(
                "Error al encolar procesamiento de documento",
                extra={
                    "document_id": str(document_id),
                    "workspace_id": str(workspace_id),
                    "queue": self._config.queue_name,
                },
            )
            raise QueueEnqueueError(
                "No se pudo encolar el procesamiento del documento",
                original_error=exc,
            ) from exc


# -----------------------------------------------------------------------------
# Helpers privados (módulo)
# -----------------------------------------------------------------------------


def _validate_config(config: RQQueueConfig) -> RQQueueConfig:
    """Valida y normaliza configuración.

    Principio:
      - Fail-fast: errores de configuración deben explotar temprano.
    """
    queue_name = (config.queue_name or "").strip() or DOCUMENTS_QUEUE_NAME
    retry_max_attempts = int(config.retry_max_attempts)
    job_timeout_seconds = int(config.job_timeout_seconds)
    result_ttl_seconds = int(config.result_ttl_seconds)

    if retry_max_attempts < 0:
        raise QueueConfigurationError("retry_max_attempts no puede ser negativo")
    if job_timeout_seconds <= 0:
        raise QueueConfigurationError("job_timeout_seconds debe ser > 0")
    if result_ttl_seconds < 0:
        raise QueueConfigurationError("result_ttl_seconds no puede ser negativo")

    return RQQueueConfig(
        queue_name=queue_name,
        retry_max_attempts=retry_max_attempts,
        job_timeout_seconds=job_timeout_seconds,
        result_ttl_seconds=result_ttl_seconds,
    )


def _lazy_import_rq():
    """Importa RQ de forma lazy.

    Motivo:
      - Permite que el backend importe módulos (tests/lint) sin tener RQ instalado.
      - El error queda acotado a la funcionalidad de cola.
    """
    try:
        import rq  # type: ignore

        # Aseguramos que las APIs que usamos existan.
        _ = rq.Queue
        _ = rq.Retry
        return rq
    except Exception as exc:
        raise QueueConfigurationError(
            "RQ no está disponible. Instalar dependencia 'rq' para usar colas."
        ) from exc
