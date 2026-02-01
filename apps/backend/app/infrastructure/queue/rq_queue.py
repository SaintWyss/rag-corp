"""
===============================================================================
PAQUETE: Infraestructura / Queue
===============================================================================

CRC CARD (Package)
-------------------------------------------------------------------------------
Nombre:
    infrastructure.queue

Responsabilidades:
    - Exponer adaptadores de cola usados por la composición (container).
    - Mantener un API de import estable para el resto del backend.

Colaboradores:
    - rq_queue.RQDocumentProcessingQueue
===============================================================================
"""

from .rq_queue import RQDocumentProcessingQueue, RQQueueConfig

__all__ = ["RQDocumentProcessingQueue", "RQQueueConfig"]
