"""
===============================================================================
SUBSISTEMA: Infraestructura / Queue
===============================================================================

CRC CARD (Módulo)
-------------------------------------------------------------------------------
Nombre:
    Errores Tipados de Cola

Responsabilidades:
    - Definir excepciones explícitas para el adaptador de cola.
    - Habilitar un manejo consistente (logs / métricas / mapping) sin depender
      de excepciones genéricas.

Colaboradores:
    - rq_queue.RQDocumentProcessingQueue
    - capa de aplicación (casos de uso) que captura Exception al encolar
===============================================================================
"""

from __future__ import annotations


class QueueError(Exception):
    """Error base del subsistema de colas."""

    code: str = "QUEUE_ERROR"


class QueueConfigurationError(QueueError):
    """Se lanza cuando la cola está mal configurada (ej: job path inválido)."""

    code = "QUEUE_CONFIGURATION_ERROR"


class QueueEnqueueError(QueueError):
    """Se lanza cuando falla la operación de encolar un job."""

    code = "QUEUE_ENQUEUE_ERROR"

    def __init__(
        self, message: str, *, original_error: Exception | None = None
    ) -> None:
        super().__init__(message)
        self.original_error = original_error
