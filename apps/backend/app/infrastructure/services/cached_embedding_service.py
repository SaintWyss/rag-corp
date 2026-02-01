"""
Name: Cached Embedding Service (Decorator)

Qué hace
--------
Este módulo implementa un **Decorator** sobre `EmbeddingService` que agrega:
- Cache-aside (get → si miss → provider → set)
- Deduplicación de inputs en batch (mismo texto → 1 embedding)
- Preservación del orden original del batch
- Métricas de hit/miss (Prometheus; se asume no-op si no está habilitado)

Arquitectura
------------
- Estilo: Clean Architecture / Hexagonal
- Capa: Infrastructure (adapter/decorator)
- Puerto: `EmbeddingCachePort` (dominio) → permite reemplazar el backend de cache (Redis, memoria, etc.)

Patrones
--------
- **Decorator**: CachingEmbeddingService envuelve a un `EmbeddingService`.
- **Cache-Aside**: intenta cache, y si falla consulta al provider y guarda.
- **Idempotencia / dedupe**: evita recalcular embeddings repetidos en un mismo batch.

SOLID (por qué está bien)
-------------------------
- SRP: este componente SOLO agrega caching/métricas, no genera embeddings.
- OCP: podés añadir nuevas estrategias de key/normalización sin tocar el provider.
- LSP: al implementar `EmbeddingService`, es reemplazable por cualquier otro service.
- ISP: expone solo lo que define la interfaz (embed_query/embed_batch/model_id).
- DIP: depende de abstracciones (`EmbeddingService`, `EmbeddingCachePort`), no de implementaciones concretas.

CRC (Class-Responsibility-Collaboration)
----------------------------------------
Class: CachingEmbeddingService
Responsibilities:
  - Resolver embeddings con cache-aside (get/miss/set)
  - Deduplicar batch por clave estable y reconstruir resultados en el orden original
  - Emitir métricas de cache hit/miss (best-effort)
Collaborators:
  - EmbeddingService (provider): genera embeddings cuando hay miss
  - EmbeddingCachePort (cache): almacena y recupera vectores
  - metrics: record_embedding_cache_hit/miss
Constraints:
  - La cache es best-effort (si falla, NO debe romper embeddings)
  - La clave debe ser estable (normalización versionada)
"""

from __future__ import annotations

import re
from typing import List, cast

from ...crosscutting.exceptions import EmbeddingError
from ...crosscutting.logger import logger
from ...crosscutting.metrics import (
    record_embedding_cache_hit,
    record_embedding_cache_miss,
)
from ...domain.cache import EmbeddingCachePort
from ...domain.services import EmbeddingService

# ---------------------------------------------------------------------------
# Cache key policy (normalización versionada)
# ---------------------------------------------------------------------------
_WHITESPACE_RE = re.compile(r"\s+")
_TEXT_NORMALIZATION_VERSION = (
    "v1"  # R: bump cuando cambie la normalización (invalida cache vieja)
)

# R: task types (deben matchear los providers; separa embeddings optimizados para query vs document)
_TASK_QUERY = "retrieval_query"
_TASK_DOCUMENT = "retrieval_document"


def normalize_embedding_text(text: str) -> str:
    """
    R: Normaliza texto para claves de cache estables.

    Política actual (v1):
      - strip() bordes
      - colapsa whitespace múltiple a un espacio

    Nota:
      - Mantener esta función simple y explícita.
      - Si se cambia, incrementá _TEXT_NORMALIZATION_VERSION.
    """
    return _WHITESPACE_RE.sub(" ", text.strip())


def build_embedding_cache_key(model_id: str, text: str, task_type: str) -> str:
    """
    R: Construye una clave estable de cache.

    Componentes:
      - model_id: evita colisiones entre proveedores/modelos
      - task_type: separa embeddings para query/document
      - normalization version: invalidación controlada
      - normalized text: base del lookup
    """
    normalized = normalize_embedding_text(text)
    return f"{model_id}|{task_type}|{_TEXT_NORMALIZATION_VERSION}|{normalized}"


class CachingEmbeddingService(EmbeddingService):
    """
    R: Decorator de EmbeddingService que agrega cache-aside + métricas.

    Diseño:
      - Cache best-effort: si Redis/memcache falla, seguimos con provider (no rompemos el flujo).
      - Batch dedupe: reduce costo cuando hay textos repetidos.
    """

    def __init__(
        self,
        provider: EmbeddingService,
        cache: EmbeddingCachePort,
        model_id: str | None = None,
    ):
        """
        R: Constructor (inyección de dependencias).

        Args:
            provider: implementación real de EmbeddingService (Google, OpenAI, local, etc.)
            cache: puerto de cache (Redis/memoria/etc.)
            model_id: override explícito (si no, intenta leer provider.model_id)
        """
        self._provider = provider
        self._cache = cache

        # R: model_id se usa para namespacing de claves de cache
        self._model_id = model_id or getattr(provider, "model_id", "unknown")

    @property
    def model_id(self) -> str:
        """R: Expone model_id para composición (por ejemplo: cache keys arriba en la pila)."""
        return self._model_id

    # -----------------------------------------------------------------------
    # Query mode (1 texto)
    # -----------------------------------------------------------------------
    def embed_query(self, query: str) -> List[float]:
        """
        R: Embedding de una query con cache-aside.

        Flujo (Cache-Aside):
          1) key = f(model, task, norm_version, normalized_text)
          2) cache.get(key)
          3) hit → métricas hit → return
          4) miss → métricas miss → provider.embed_query → cache.set(key, vec) → return
        """
        if not (query or "").strip():
            raise EmbeddingError("Query must not be empty")

        key = build_embedding_cache_key(self._model_id, query, _TASK_QUERY)

        # R: Cache best-effort (si falla, seguimos con provider)
        try:
            cached = self._cache.get(key)
        except Exception as exc:
            logger.warning(
                "Embedding cache get failed (query); falling back to provider",
                exc_info=True,
                extra={"key_prefix": key[:64], "error_type": type(exc).__name__},
            )
            cached = None

        if cached is not None:
            record_embedding_cache_hit(kind="query")
            return cached

        record_embedding_cache_miss(kind="query")

        # R: Si el provider falla, propagamos como EmbeddingError (sin esconder el origen)
        try:
            embedding = self._provider.embed_query(query)
        except EmbeddingError:
            raise
        except Exception as exc:
            raise EmbeddingError("Provider failed to embed query") from exc

        # R: Cache set best-effort (no debe romper el flujo)
        try:
            self._cache.set(key, embedding)
        except Exception as exc:
            logger.warning(
                "Embedding cache set failed (query); continuing without cache",
                exc_info=True,
                extra={"key_prefix": key[:64], "error_type": type(exc).__name__},
            )

        return embedding

    # -----------------------------------------------------------------------
    # Batch mode (N textos)
    # -----------------------------------------------------------------------
    def embed_batch(self, texts: List[str]) -> List[List[float]]:
        """
        R: Embeddings para batch con dedupe + cache-aside.

        Objetivos:
          - Dedupe: si el mismo texto aparece 20 veces, pedimos 1 embedding al provider.
          - Orden: el resultado debe coincidir 1:1 con `texts` (misma posición).
          - Métricas: hits/misses cuentan duplicados (si 1 key cubre 5 índices → count=5).
        """
        if not texts:
            return []

        # R: Estructuras para deduplicación:
        # - key_to_indices: para reconstruir resultados en el orden original
        # - key_to_text: preserva el primer texto asociado a la key (source-of-truth para el provider)
        key_to_indices: dict[str, list[int]] = {}
        key_to_text: dict[str, str] = {}
        unique_keys_in_order: list[str] = []

        # R: Construye claves y dedupe preservando el orden de primera aparición
        for idx, text in enumerate(texts):
            if not (text or "").strip():
                raise EmbeddingError(f"Batch text at index {idx} must not be empty")

            key = build_embedding_cache_key(self._model_id, text, _TASK_DOCUMENT)

            if key not in key_to_indices:
                key_to_indices[key] = [idx]
                key_to_text[key] = text
                unique_keys_in_order.append(key)
            else:
                key_to_indices[key].append(idx)

        # R: Resultados finales (posición = índice de input). Usamos None como placeholder.
        results: list[List[float] | None] = [None] * len(texts)

        # R: Miss list conserva orden estable (según primera aparición en el input)
        miss_items: list[tuple[str, str, list[int]]] = []

        # R: 1) Intentamos resolver por cache cada key única
        for key in unique_keys_in_order:
            indices = key_to_indices[key]

            try:
                cached = self._cache.get(key)
            except Exception as exc:
                logger.warning(
                    "Embedding cache get failed (batch); treating as miss",
                    exc_info=True,
                    extra={"key_prefix": key[:64], "error_type": type(exc).__name__},
                )
                cached = None

            if cached is not None:
                # R: Hit: cubre potencialmente múltiples posiciones
                record_embedding_cache_hit(count=len(indices), kind="batch")
                for idx in indices:
                    results[idx] = cached
            else:
                # R: Miss: lo resolvemos luego con provider en un único call batch
                record_embedding_cache_miss(count=len(indices), kind="batch")
                miss_items.append((key, key_to_text[key], indices))

        # R: 2) Para misses, pedimos embeddings al provider (solo textos únicos faltantes)
        if miss_items:
            miss_texts = [item[1] for item in miss_items]

            try:
                embeddings = self._provider.embed_batch(miss_texts)
            except EmbeddingError:
                raise
            except Exception as exc:
                raise EmbeddingError("Provider failed to embed batch") from exc

            # R: Validación de integridad: provider debe devolver 1 vector por texto
            if len(embeddings) != len(miss_items):
                raise EmbeddingError(
                    "Embedding batch size mismatch in caching service: "
                    f"expected {len(miss_items)}, got {len(embeddings)}"
                )

            # R: Guardamos en cache (best-effort) y completamos todas las posiciones originales
            for (key, _text, indices), embedding in zip(miss_items, embeddings):
                try:
                    self._cache.set(key, embedding)
                except Exception as exc:
                    logger.warning(
                        "Embedding cache set failed (batch); continuing without cache",
                        exc_info=True,
                        extra={
                            "key_prefix": key[:64],
                            "error_type": type(exc).__name__,
                        },
                    )

                for idx in indices:
                    results[idx] = embedding

        # R: Invariante final: todos los resultados deben estar completos
        if any(embedding is None for embedding in results):
            raise EmbeddingError(
                "CachingEmbeddingService failed to resolve all results"
            )

        # R: Cast seguro porque validamos que no hay None
        return cast(List[List[float]], results)
