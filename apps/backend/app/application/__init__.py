"""
===============================================================================
APPLICATION LAYER (Public API / Exports)
===============================================================================

Expone los puntos de entrada estables de la capa de aplicación:
  - ContextBuilder: ensamblador de contexto para RAG
  - prompt_injection_detector: política de seguridad para chunks

Nota:
  - Los casos de uso se importan desde `usecases/` subdirectories.
  - Este archivo define el contrato público de servicios de aplicación compartidos.
===============================================================================
"""

from .context_builder import ContextBuilder, get_context_builder
from .prompt_injection_detector import (
    DetectionResult,
    Mode,
    apply_injection_filter,
    detect,
    is_flagged,
)

__all__ = [
    # Context Builder
    "ContextBuilder",
    "get_context_builder",
    # Prompt Injection Detector
    "DetectionResult",
    "Mode",
    "apply_injection_filter",
    "detect",
    "is_flagged",
]
