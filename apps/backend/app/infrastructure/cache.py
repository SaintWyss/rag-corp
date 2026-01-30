"""
============================================================
TARJETA CRC — app/crosscutting/embedding_cache.py  (ajustá la ruta real)
============================================================
Module: Embedding Cache (Facade + Backends)

Responsibilities:
  - Cachear embeddings para reducir llamadas a proveedores externos.
  - Proveer expiración por TTL (time-to-live) y métricas simples (hits/misses).
  - Seleccionar backend automáticamente:
      - Redis si REDIS_URL está disponible (y el import/ping funciona)
      - In-memory caso contrario
  - Generar claves estables via hash (SHA-256) del texto de entrada.
  - Exponer una fachada simple: get(text) / set(text, embedding) / clear() / stats

Collaborators:
  - Proveedor de embeddings (EmbeddingService) -> usa este módulo como cache opcional.
  - Redis (opcional) vía redis-py.
  - threading.Lock para thread-safety en backend in-memory.
  - json para serialización en Redis.

Policy / Design Notes (Clean / SOLID):
  - DIP: el resto del sistema depende de la abstracción (EmbeddingCache facade),
    no de Redis / estructuras internas.
  - Cache es best-effort: si Redis falla, degradamos a memoria sin romper flujo.
  - NO “silenciar” todo: fallos de Redis se manejan como miss (observables por stats).
  - LRU real: en memoria usamos OrderedDict para eviction determinística.
  - TTL coherente:
      - En memoria: expira por timestamp.
      - En Redis: TTL nativo (SETEX).
============================================================
"""

from __future__ import annotations

import hashlib
import json
import os
import time
from abc import ABC, abstractmethod
from collections import OrderedDict
from dataclasses import dataclass
from threading import Lock
from typing import Dict, List, Optional


# ============================================================
# Abstracción de backend (OCP / DIP)
# ============================================================
class CacheBackend(ABC):
    """Contrato mínimo para un backend de caché de embeddings."""

    @abstractmethod
    def get(self, key: str) -> Optional[List[float]]:
        """Devuelve embedding cacheado o None (miss)."""
        raise NotImplementedError

    @abstractmethod
    def set(self, key: str, embedding: List[float], ttl_seconds: float) -> None:
        """Persiste embedding con TTL."""
        raise NotImplementedError

    @abstractmethod
    def clear(self) -> None:
        """Limpia todas las entradas (del namespace del backend)."""
        raise NotImplementedError

    @abstractmethod
    def stats(self) -> dict:
        """Métricas del backend (para observabilidad)."""
        raise NotImplementedError


# ============================================================
# Entry con TTL (in-memory)
# ============================================================
@dataclass(frozen=True, slots=True)
class CacheEntry:
    """
    Entrada de caché con timestamp de inserción.

    Invariante:
      - created_at es epoch seconds.
    """

    embedding: List[float]
    created_at: float

    def is_expired(self, ttl_seconds: float, now: float) -> bool:
        """True si esta entrada ya excedió el TTL."""
        return (now - self.created_at) > ttl_seconds


# ============================================================
# In-memory backend (LRU + TTL)
# ============================================================
class InMemoryCacheBackend(CacheBackend):
    """
    Caché en memoria con:
      - TTL por entrada
      - Eviction LRU real usando OrderedDict
      - Thread-safety con Lock

    Nota:
      - Para cargas pequeñas/medianas (dev/tests) es suficiente.
      - Este backend NO comparte estado entre procesos (cada worker tiene su caché).
    """

    def __init__(self, *, max_size: int = 1000, ttl_seconds: float = 3600) -> None:
        if max_size <= 0:
            raise ValueError("max_size must be > 0")
        if ttl_seconds <= 0:
            raise ValueError("ttl_seconds must be > 0")

        self._ttl_seconds = float(ttl_seconds)
        self._max_size = int(max_size)

        # key -> CacheEntry (OrderedDict mantiene orden de uso)
        self._cache: "OrderedDict[str, CacheEntry]" = OrderedDict()
        self._lock = Lock()

        # stats
        self._hits = 0
        self._misses = 0
        self._evictions = 0
        self._expired = 0

    def get(self, key: str) -> Optional[List[float]]:
        """
        Lookup LRU:
          - hit => move_to_end(key) para marcar como "most recently used"
          - expired => borrar y contar como miss
        """
        now = time.time()

        with self._lock:
            entry = self._cache.get(key)
            if entry is None:
                self._misses += 1
                return None

            if entry.is_expired(self._ttl_seconds, now):
                # Expiró => remover y contabilizar
                self._cache.pop(key, None)
                self._expired += 1
                self._misses += 1
                return None

            # Hit => LRU touch
            self._cache.move_to_end(key, last=True)
            self._hits += 1
            return entry.embedding

    def set(self, key: str, embedding: List[float], ttl_seconds: float) -> None:
        """
        Inserta / reemplaza una entrada.

        TTL:
          - Este backend usa TTL global (self._ttl_seconds) por coherencia.
          - El parámetro ttl_seconds se respeta si querés overrides por llamada.
        """
        ttl = (
            float(ttl_seconds) if ttl_seconds and ttl_seconds > 0 else self._ttl_seconds
        )
        now = time.time()

        with self._lock:
            # Si existe, lo reemplazamos y lo marcamos como MRU.
            if key in self._cache:
                self._cache[key] = CacheEntry(embedding=embedding, created_at=now)
                self._cache.move_to_end(key, last=True)
                return

            # Si está lleno, evict LRU (el primero)
            if len(self._cache) >= self._max_size:
                self._cache.popitem(last=False)  # LRU
                self._evictions += 1

            # Guardar entrada
            self._cache[key] = CacheEntry(embedding=embedding, created_at=now)

            # Actualizamos TTL global si se pasó distinto (opcional y explícito)
            # Esto mantiene el backend consistente si alguien decide variar TTL por set.
            self._ttl_seconds = ttl

    def clear(self) -> None:
        """Vacía la caché completa."""
        with self._lock:
            self._cache.clear()

    def stats(self) -> dict:
        """Métricas simples y útiles para tuning."""
        with self._lock:
            total = self._hits + self._misses
            return {
                "backend": "in-memory",
                "size": len(self._cache),
                "max_size": self._max_size,
                "ttl_seconds": self._ttl_seconds,
                "hits": self._hits,
                "misses": self._misses,
                "expired": self._expired,
                "evictions": self._evictions,
                "hit_rate": (self._hits / total) if total > 0 else 0.0,
            }


# ============================================================
# Redis backend (TTL nativo + namespace)
# ============================================================
class RedisCacheBackend(CacheBackend):
    """
    Caché Redis para embeddings.

    Ventajas:
      - Persistente a reinicios del proceso
      - Compartible entre múltiples workers
      - TTL nativo por clave (SETEX)

    Nota Clean:
      - Redis es opcional: si falla, el sistema debe seguir (cache best-effort).
    """

    CACHE_PREFIX = "rag:embedding:"  # namespace para no pisar otras claves

    def __init__(self, *, redis_url: str, ttl_seconds: float = 3600) -> None:
        if not redis_url:
            raise ValueError("redis_url is required")

        # Import local para que el proyecto funcione sin redis-py instalado.
        import redis  # type: ignore

        self._client = redis.from_url(redis_url, decode_responses=True)
        self._ttl_seconds = int(ttl_seconds) if ttl_seconds > 0 else 3600

        # stats
        self._hits = 0
        self._misses = 0
        self._errors = 0

    def _k(self, key: str) -> str:
        """Compone clave namespaced."""
        return f"{self.CACHE_PREFIX}{key}"

    def get(self, key: str) -> Optional[List[float]]:
        """Lookup en Redis (si hay error, se considera miss)."""
        try:
            data = self._client.get(self._k(key))
            if data is None:
                self._misses += 1
                return None

            self._hits += 1
            value = json.loads(data)

            # Defensive: asegurar que sea lista de floats
            if not isinstance(value, list):
                self._misses += 1
                return None
            return value
        except Exception:
            self._errors += 1
            self._misses += 1
            return None

    def set(self, key: str, embedding: List[float], ttl_seconds: float) -> None:
        """SETEX con TTL. Si falla, ignoramos (best-effort)."""
        ttl = int(ttl_seconds) if ttl_seconds and ttl_seconds > 0 else self._ttl_seconds
        try:
            self._client.setex(self._k(key), ttl, json.dumps(embedding))
        except Exception:
            self._errors += 1

    def clear(self) -> None:
        """
        Limpia sólo claves del namespace.

        Nota: SCAN sería mejor que KEYS en prod grande.
        Acá dejamos implementación simple, pero con comment pro.
        """
        try:
            # Mejora futura: usar scan_iter para evitar bloqueo en clusters grandes.
            keys = self._client.keys(f"{self.CACHE_PREFIX}*")
            if keys:
                self._client.delete(*keys)
        except Exception:
            self._errors += 1

    def stats(self) -> dict:
        """Métricas + tamaño aproximado del namespace."""
        size = -1
        try:
            keys = self._client.keys(f"{self.CACHE_PREFIX}*")
            size = len(keys) if keys else 0
        except Exception:
            self._errors += 1

        total = self._hits + self._misses
        return {
            "backend": "redis",
            "size": size,
            "ttl_seconds": self._ttl_seconds,
            "hits": self._hits,
            "misses": self._misses,
            "errors": self._errors,
            "hit_rate": (self._hits / total) if total > 0 else 0.0,
        }


# ============================================================
# Facade principal (Simple API para el resto del sistema)
# ============================================================
class EmbeddingCache:
    """
    Fachada de caché de embeddings con selección automática de backend.

    Selección:
      - EMBEDDING_CACHE_BACKEND=memory => fuerza in-memory
      - EMBEDDING_CACHE_BACKEND=redis  => fuerza redis (si REDIS_URL funciona)
      - default => redis si está disponible, si no memory

    Importante:
      - Esto NO es “dev/prod” formal; es autodetección best-effort.
    """

    def __init__(self, *, max_size: int = 1000, ttl_seconds: float = 3600) -> None:
        if ttl_seconds <= 0:
            raise ValueError("ttl_seconds must be > 0")

        self._ttl_seconds = float(ttl_seconds)
        self._backend = self._create_backend(max_size=max_size, ttl_seconds=ttl_seconds)

    def _create_backend(self, *, max_size: int, ttl_seconds: float) -> CacheBackend:
        """
        Factory de backend.

        Política:
          - Si el usuario fuerza backend, respetamos, pero degradamos si Redis no anda.
          - Si no fuerza, preferimos Redis cuando está disponible.
        """
        forced = os.getenv("EMBEDDING_CACHE_BACKEND", "").strip().lower()
        redis_url = (os.getenv("REDIS_URL") or "").strip()

        def try_redis() -> Optional[CacheBackend]:
            if not redis_url:
                return None
            try:
                backend = RedisCacheBackend(
                    redis_url=redis_url, ttl_seconds=ttl_seconds
                )
                # Healthcheck temprano: si no responde, caemos a memoria
                backend._client.ping()
                return backend
            except Exception:
                return None

        if forced == "memory":
            return InMemoryCacheBackend(max_size=max_size, ttl_seconds=ttl_seconds)

        if forced == "redis":
            return try_redis() or InMemoryCacheBackend(
                max_size=max_size, ttl_seconds=ttl_seconds
            )

        # Autodetección
        return try_redis() or InMemoryCacheBackend(
            max_size=max_size, ttl_seconds=ttl_seconds
        )

    @staticmethod
    def _hash_text(text: str) -> str:
        """
        Genera una key estable para el texto.

        Nota:
          - SHA-256 reduce riesgo de colisiones a nivel práctico.
          - Hash evita almacenar texto sensible como clave en Redis.
        """
        return hashlib.sha256(text.encode("utf-8")).hexdigest()

    def get(self, text: str) -> Optional[List[float]]:
        """Lookup por texto. Devuelve embedding o None (miss)."""
        key = self._hash_text(text)
        return self._backend.get(key)

    def set(self, text: str, embedding: List[float]) -> None:
        """Persiste embedding en caché."""
        key = self._hash_text(text)
        self._backend.set(key, embedding, ttl_seconds=self._ttl_seconds)

    def clear(self) -> None:
        """Limpia la caché del backend actual."""
        self._backend.clear()

    @property
    def stats(self) -> dict:
        """Stats del backend (útil para métricas / debug)."""
        return self._backend.stats()


# ============================================================
# Singleton global (simple, controlado)
# ============================================================
_embedding_cache: Optional[EmbeddingCache] = None


def get_embedding_cache() -> EmbeddingCache:
    """
    Acceso al singleton global.

    Rationale:
      - Evita reinstanciar backends (Redis clients) muchas veces.
      - Simplifica inyección para partes legacy.
    """
    global _embedding_cache
    if _embedding_cache is None:
        _embedding_cache = EmbeddingCache()
    return _embedding_cache


def reset_embedding_cache() -> None:
    """
    Reset del singleton (útil para tests).

    Nota:
      - No limpia el backend; sólo reinstancia en el próximo get_embedding_cache().
      - Para limpiar explícito: get_embedding_cache().clear()
    """
    global _embedding_cache
    _embedding_cache = None
