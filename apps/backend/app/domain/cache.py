"""
===============================================================================
TARJETA CRC — domain/cache.py
===============================================================================

Módulo:
    Puerto de Cache de Embeddings (Dominio)

Responsabilidades:
    - Definir el contrato (Protocol) para cachear vectores de embedding.
    - Habilitar Inversión de Dependencias:
        * application/usecases depende de esta interfaz
        * infrastructure/cache implementa backends concretos (memoria / Redis)
    - Establecer un “lenguaje común” para operaciones básicas (get/set).

Colaboradores:
    - infrastructure/cache/*: implementaciones de cache (in-memory, Redis, etc.)
    - application/usecases/*: consulta cache antes de invocar EmbeddingService
    - crosscutting/metrics: métricas de hits/miss (desde infraestructura o UC)

Restricciones / Reglas:
    - Este módulo ES dominio: no debe importar Redis, SQLAlchemy, métricas, etc.
    - No contiene implementación: solo el contrato estable.
    - Los embeddings son listas de float serializables (provider-agnostic).

Notas de diseño (Senior / Sustentable):
    - El puerto expone solo lo mínimo (ISP): get/set.
    - El backend decide TTL/evicción/serialización.
    - Para evitar acoplamiento, el dominio NO expone “delete/ttl” a menos que sea necesario.
===============================================================================
"""

from __future__ import annotations

from typing import Protocol


class EmbeddingCachePort(Protocol):
    """
    Interfaz de cache para embeddings.

    Concepto:
      - Key: string determinística (ej: hash(query) + modelo + versión embeddings)
      - Value: vector embedding (list[float])

    Semántica:
      - get(key) retorna None si no existe / expiró / fue evictado
      - set(key, embedding) guarda o sobreescribe la entrada
    """

    def get(self, key: str) -> list[float] | None:
        """
        Obtiene un embedding cacheado.

        Args:
            key: clave determinística del embedding

        Returns:
            list[float] si existe, o None si no existe/expiró

        Importante:
            - No debe lanzar excepciones por “miss”.
            - Errores de infraestructura (Redis caído) deberían manejarse en la implementación:
              o degradar a None o lanzar una excepción de infraestructura que application capture.
        """
        ...

    def set(self, key: str, embedding: list[float]) -> None:
        """
        Guarda un embedding en cache.

        Args:
            key: clave determinística
            embedding: vector embedding

        Returns:
            None

        Importante:
            - La implementación decide TTL/evicción.
            - Idealmente es “best-effort”: si falla el cache, el sistema debe seguir funcionando.
        """
        ...
