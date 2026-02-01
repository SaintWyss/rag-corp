"""
===============================================================================
TARJETA CRC — app/jobs.py (Entrypoints estables de jobs)
===============================================================================

Responsabilidades:
  - Exponer entrypoints de jobs con un path de import estable para RQ.
  - Evitar “strings mágicos frágiles” apuntando a módulos internos que cambian.
  - Centralizar exports para que el producer (queue) y el worker coincidan.

Colaboradores:
  - app.worker.jobs.process_document_job

Patrones aplicados:
  - Facade / Re-export (entrypoint estable)

Notas:
  - RQ encola jobs por import path string. Este módulo existe para garantizar
    que "app.jobs.process_document_job" siempre sea resoluble.
===============================================================================
"""

from .worker.jobs import process_document_job

__all__ = ["process_document_job"]
