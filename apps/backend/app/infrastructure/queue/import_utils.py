"""
===============================================================================
SUBSISTEMA: Infraestructura / Queue
===============================================================================

CRC CARD (Módulo)
-------------------------------------------------------------------------------
Nombre:
    Utilidades de Importación Segura

Responsabilidades:
    - Validar que un "dotted path" sea importable (module.attr).
    - Proveer un mecanismo de fail-fast: detectar paths rotos al inicio,
      en lugar de descubrir el error recién en el worker.

Colaboradores:
    - rq_queue.RQDocumentProcessingQueue
    - importlib (carga dinámica)
===============================================================================
"""

from __future__ import annotations

from functools import lru_cache
from importlib import import_module


@lru_cache(maxsize=128)
def is_importable_dotted_path(dotted_path: str) -> bool:
    """
    Retorna True si dotted_path ("modulo.func") es importable, existe y es callable.

    Notas:
      - Cacheamos para no repetir imports/costos.
      - No validamos firma, solo existencia y callability.
      - Si el import falla por ModuleNotFound/AttributeError, devolvemos False.
    """
    try:
        module_name, attr_name = _split_dotted_path(dotted_path)
        module = import_module(module_name)
        attr = getattr(module, attr_name)
        return callable(attr)
    except (ModuleNotFoundError, AttributeError):
        return False


def _split_dotted_path(dotted_path: str) -> tuple[str, str]:
    """Divide 'mod.attr' en (mod, attr) con validación mínima."""
    if not dotted_path or "." not in dotted_path:
        raise ValueError("dotted_path debe ser 'modulo.atributo'")
    module_name, attr_name = dotted_path.rsplit(".", 1)
    if not module_name or not attr_name:
        raise ValueError("dotted_path inválido")
    return module_name, attr_name
