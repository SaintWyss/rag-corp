"""
===============================================================================
SUBSISTEMA: Infraestructura / Queue
===============================================================================

CRC CARD (Módulo)
-------------------------------------------------------------------------------
Nombre:
    Rutas y Constantes de Jobs

Responsabilidades:
    - Centralizar nombres de colas y rutas "importables" de jobs.
    - Evitar strings mágicos dispersos (anti-drift).

Colaboradores:
    - rq_queue.RQDocumentProcessingQueue
    - worker.jobs.process_document_job (job ejecutado por el worker)

Notas:
    - Las rutas deben ser importables por el worker de RQ.
    - Si se renombra/mueve un job, se actualiza acá y se valida en runtime.
===============================================================================
"""

from __future__ import annotations

# Nombre por defecto de la cola de documentos.
DOCUMENTS_QUEUE_NAME: str = "documents"


# Job principal de procesamiento de documentos.
# IMPORTANTÍSIMO:
#   - Debe coincidir con la ubicación real del job.
#   - Se valida en runtime cuando se inicializa la cola.
PROCESS_DOCUMENT_JOB_PATH: str = "app.worker.jobs.process_document_job"
