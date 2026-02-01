"""
===============================================================================
SUBSISTEMA: Infraestructura / Queue
===============================================================================

CRC CARD (Package)
-------------------------------------------------------------------------------
Nombre:
    infrastructure.queue

Responsabilidades:
    - Exponer el adaptador de cola utilizado por DI (RQDocumentProcessingQueue).
    - Exponer el contrato de configuración (RQQueueConfig).
    - Mantener un API de import estable para el resto del backend.

Colaboradores:
    - rq_queue.RQDocumentProcessingQueue
    - rq_queue.RQQueueConfig
===============================================================================
"""

from .rq_queue import RQDocumentProcessingQueue, RQQueueConfig

__all__ = [
    "RQDocumentProcessingQueue",
    "RQQueueConfig",
]
