"""
Name: Fake Embeddings Service (Deterministic Test Double)

Qué es
------
Implementación **determinista** de `EmbeddingService` para tests/CI.
No realiza llamadas externas ni depende de APIs.

Arquitectura
------------
- Estilo: Clean Architecture / Hexagonal
- Capa: Infrastructure (test adapter / test double)
- Rol: reemplazar providers reales en tests (unit/integration) sin redes ni costos

Patrones
--------
- **Test Double (Fake):** simula un provider real con comportamiento determinista.
- **Adapter (conceptual):** cumple el contrato del dominio sin depender de SDKs.

SOLID
-----
- SRP: genera embeddings deterministas para pruebas.
- OCP: podés cambiar la estrategia hash sin romper a los consumidores (manteniendo la interfaz).
- LSP: sustituye a cualquier `EmbeddingService` real en tests.
- ISP/DIP: depende de la abstracción del dominio, no de un proveedor externo.

CRC (Class-Responsibility-Collaboration)
----------------------------------------
Class: FakeEmbeddingService
Responsibilities:
  - Generar embeddings deterministas para textos (query y batch)
  - Mantener dimensionalidad igual a producción (por defecto 768)
  - Exponer `model_id` estable para cache keys / métricas
Collaborators:
  - domain.services.EmbeddingService (contrato)
Constraints:
  - Sin IO / sin red / sin dependencias externas
  - Determinismo total: misma entrada → mismo vector
"""

from __future__ import annotations

import hashlib
import struct
from typing import List, Sequence

from ...crosscutting.exceptions import EmbeddingError
from ...crosscutting.logger import logger
from ...domain.services import EmbeddingService

# R: Dimensionalidad esperada para simular el provider real (Google text-embedding-004 → 768)
DEFAULT_EMBEDDING_DIMENSION = 768


def _normalize(text: str) -> str:
    """
    R: Normalización mínima para estabilidad en tests.

    Nota:
      - Mantener simple: strip() evita falsos negativos por espacios accidentalmente.
      - Si querés simular más realismo, podrías colapsar whitespace.
    """
    return (text or "").strip()


def _hash_to_unit_interval(text: str, index: int) -> float:
    """
    R: Convierte (text, index) en un float determinista en [0, 1).

    Detalle:
      - SHA-256 es estable y rápido.
      - Tomamos 8 bytes (uint64) para obtener un entero grande uniforme.
    """
    digest = hashlib.sha256(f"{text}|{index}".encode("utf-8")).digest()
    value_u64 = struct.unpack(">Q", digest[:8])[0]  # uint64
    return value_u64 / 2**64  # [0, 1)


def _hash_to_signed_float(text: str, index: int) -> float:
    """
    R: Mapea determinísticamente a [-1, 1).

    Usamos:
      signed = (unit * 2) - 1
    """
    unit = _hash_to_unit_interval(text, index)
    return (unit * 2.0) - 1.0


def _build_embedding(text: str, dimension: int) -> List[float]:
    """R: Construye un vector determinista de tamaño `dimension`."""
    normalized = _normalize(text)
    return [_hash_to_signed_float(normalized, i) for i in range(dimension)]


class FakeEmbeddingService(EmbeddingService):
    """
    R: Deterministic EmbeddingService for tests/CI.

    Nota:
      - Esto NO pretende ser “semántico”; sólo estable y rápido.
      - Útil para:
          * unit tests
          * CI sin credenciales
          * pruebas de caching/deduplicación
    """

    MODEL_ID = "fake-embedding-v1"

    def __init__(self, *, dimension: int = DEFAULT_EMBEDDING_DIMENSION) -> None:
        """
        R: Inicializa el fake.

        Args:
            dimension: tamaño del embedding (default 768 para compatibilidad con producción)
        """
        if dimension <= 0:
            raise ValueError("dimension must be > 0")
        self._dimension = dimension
        logger.debug(
            "FakeEmbeddingService initialized",
            extra={"dimension": self._dimension, "model_id": self.MODEL_ID},
        )

    def embed_batch(self, texts: Sequence[str]) -> List[List[float]]:
        """
        R: Embeddings deterministas para múltiples textos.

        Garantías:
          - Mantiene 1:1 el orden del input
          - No hace IO
        """
        # R: Validación mínima para mantener consistencia con providers reales
        for idx, t in enumerate(texts):
            if not (t or "").strip():
                raise EmbeddingError(f"Batch text at index {idx} must not be empty")

        return [_build_embedding(text, self._dimension) for text in texts]

    def embed_query(self, query: str) -> List[float]:
        """R: Embedding determinista para una query."""
        if not (query or "").strip():
            raise EmbeddingError("Query must not be empty")
        return _build_embedding(query, self._dimension)

    @property
    def model_id(self) -> str:
        """R: Identificador estable del modelo (para composición de cache keys)."""
        return self.MODEL_ID
