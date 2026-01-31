# =============================================================================
# FILE: application/rate_limiting.py
# =============================================================================
"""
===============================================================================
SERVICE: Rate Limiting (Usage Quota Management)
===============================================================================

Name:
    Rate Limiting Service

Qué es:
    Sistema de control de cuotas para prevenir abuso y gestionar costos.
    Implementa rate limiting por usuario/workspace con ventanas de tiempo.

Why:
    - Los LLMs son caros. Un usuario malicioso puede gastar la cuota en minutos.
    - Protege la estabilidad del servicio.
    - Permite planes diferenciados (free/pro/enterprise).

Arquitectura:
    - Capa: Application (policy/service)
    - Patrón: Sliding Window Counter (ventana deslizante)
    - Storage: Abstracción via Protocol (Redis, Postgres, Memory)

-------------------------------------------------------------------------------
CRC CARD
-------------------------------------------------------------------------------
Component: RateLimiter
Responsibilities:
  - Verificar si un actor puede realizar una acción
  - Incrementar contadores de uso
  - Retornar estado de cuota actual
  - Manejar diferentes resources (messages, tokens, uploads)
Collaborators:
  - QuotaStoragePort: persistencia de contadores
  - Settings: límites por defecto
===============================================================================
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Dict, Final, Optional, Protocol
from uuid import UUID

from ..domain.value_objects import UsageQuota

logger = logging.getLogger(__name__)

# -----------------------------------------------------------------------------
# Constants
# -----------------------------------------------------------------------------
_DEFAULT_MESSAGE_LIMIT: Final[int] = 100  # mensajes por hora
_DEFAULT_TOKEN_LIMIT: Final[int] = 50000  # tokens por hora
_DEFAULT_UPLOAD_LIMIT: Final[int] = 20  # uploads por hora
_DEFAULT_WINDOW_SECONDS: Final[int] = 3600  # 1 hora


# -----------------------------------------------------------------------------
# Ports
# -----------------------------------------------------------------------------
class QuotaStoragePort(Protocol):
    """
    Port para persistencia de cuotas.

    Implementaciones típicas:
      - RedisQuotaStorage: Redis con TTL automático
      - PostgresQuotaStorage: Postgres con cleanup periódico
      - InMemoryQuotaStorage: Para testing
    """

    def get_usage(
        self,
        *,
        scope_type: str,
        scope_id: str,
        resource: str,
        window_start: datetime,
    ) -> int:
        """Retorna uso actual en la ventana."""
        ...

    def increment_usage(
        self,
        *,
        scope_type: str,
        scope_id: str,
        resource: str,
        amount: int,
        window_start: datetime,
        window_ttl_seconds: int,
    ) -> int:
        """Incrementa uso y retorna nuevo total."""
        ...

    def reset_usage(
        self,
        *,
        scope_type: str,
        scope_id: str,
        resource: str,
    ) -> None:
        """Resetea el contador (para admin override)."""
        ...


# -----------------------------------------------------------------------------
# Configuration
# -----------------------------------------------------------------------------
@dataclass(frozen=True)
class RateLimitConfig:
    """
    Configuración de límites por recurso.

    Attributes:
        messages_per_hour: Límite de mensajes de chat
        tokens_per_hour: Límite de tokens consumidos
        uploads_per_hour: Límite de uploads de documentos
        window_seconds: Tamaño de la ventana en segundos
    """

    messages_per_hour: int = _DEFAULT_MESSAGE_LIMIT
    tokens_per_hour: int = _DEFAULT_TOKEN_LIMIT
    uploads_per_hour: int = _DEFAULT_UPLOAD_LIMIT
    window_seconds: int = _DEFAULT_WINDOW_SECONDS


# -----------------------------------------------------------------------------
# Result Types
# -----------------------------------------------------------------------------
@dataclass(frozen=True)
class RateLimitResult:
    """
    Resultado de una verificación de rate limit.

    Attributes:
        allowed: True si la acción está permitida
        quota: Estado actual de la cuota
        retry_after_seconds: Segundos hasta que se libere cuota (si bloqueado)
    """

    allowed: bool
    quota: UsageQuota
    retry_after_seconds: Optional[int] = None


# -----------------------------------------------------------------------------
# Rate Limiter Service
# -----------------------------------------------------------------------------
class RateLimiter:
    """
    Servicio de rate limiting.

    Uso típico:
        limiter = RateLimiter(storage, config)

        # Verificar antes de procesar
        result = limiter.check("messages", user_id=user_id)
        if not result.allowed:
            raise RateLimitExceeded(result.retry_after_seconds)

        # Procesar...

        # Registrar uso
        limiter.record("messages", user_id=user_id, amount=1)
    """

    def __init__(
        self,
        storage: QuotaStoragePort,
        config: Optional[RateLimitConfig] = None,
    ) -> None:
        self._storage = storage
        self._config = config or RateLimitConfig()
        self._limits: Dict[str, int] = {
            "messages": self._config.messages_per_hour,
            "tokens": self._config.tokens_per_hour,
            "uploads": self._config.uploads_per_hour,
        }

    def check(
        self,
        resource: str,
        *,
        user_id: Optional[UUID] = None,
        workspace_id: Optional[UUID] = None,
    ) -> RateLimitResult:
        """
        Verifica si una acción está permitida.

        Args:
            resource: Tipo de recurso ("messages", "tokens", "uploads")
            user_id: ID del usuario (scope por usuario)
            workspace_id: ID del workspace (scope por workspace)

        Returns:
            RateLimitResult con el estado de la cuota.
        """
        scope_type, scope_id = self._resolve_scope(user_id, workspace_id)
        limit = self._get_limit(resource)
        window_start, reset_at = self._get_window_bounds()

        current_usage = self._storage.get_usage(
            scope_type=scope_type,
            scope_id=scope_id,
            resource=resource,
            window_start=window_start,
        )

        quota = UsageQuota(
            limit=limit,
            used=current_usage,
            reset_at=reset_at.isoformat(),
            resource=resource,
        )

        if current_usage >= limit:
            retry_after = int((reset_at - datetime.now(timezone.utc)).total_seconds())
            retry_after = max(0, retry_after)

            logger.warning(
                "Rate limit exceeded",
                extra={
                    "scope_type": scope_type,
                    "scope_id": scope_id,
                    "resource": resource,
                    "limit": limit,
                    "used": current_usage,
                },
            )

            return RateLimitResult(
                allowed=False,
                quota=quota,
                retry_after_seconds=retry_after,
            )

        return RateLimitResult(allowed=True, quota=quota)

    def record(
        self,
        resource: str,
        *,
        user_id: Optional[UUID] = None,
        workspace_id: Optional[UUID] = None,
        amount: int = 1,
    ) -> UsageQuota:
        """
        Registra uso de un recurso.

        Args:
            resource: Tipo de recurso
            user_id: ID del usuario
            workspace_id: ID del workspace
            amount: Cantidad a incrementar (default 1)

        Returns:
            UsageQuota actualizada.
        """
        scope_type, scope_id = self._resolve_scope(user_id, workspace_id)
        limit = self._get_limit(resource)
        window_start, reset_at = self._get_window_bounds()

        new_usage = self._storage.increment_usage(
            scope_type=scope_type,
            scope_id=scope_id,
            resource=resource,
            amount=amount,
            window_start=window_start,
            window_ttl_seconds=self._config.window_seconds,
        )

        logger.debug(
            "Usage recorded",
            extra={
                "scope_type": scope_type,
                "scope_id": scope_id,
                "resource": resource,
                "amount": amount,
                "new_total": new_usage,
            },
        )

        return UsageQuota(
            limit=limit,
            used=new_usage,
            reset_at=reset_at.isoformat(),
            resource=resource,
        )

    def get_quota(
        self,
        resource: str,
        *,
        user_id: Optional[UUID] = None,
        workspace_id: Optional[UUID] = None,
    ) -> UsageQuota:
        """Obtiene el estado actual de la cuota sin modificarla."""
        scope_type, scope_id = self._resolve_scope(user_id, workspace_id)
        limit = self._get_limit(resource)
        window_start, reset_at = self._get_window_bounds()

        current_usage = self._storage.get_usage(
            scope_type=scope_type,
            scope_id=scope_id,
            resource=resource,
            window_start=window_start,
        )

        return UsageQuota(
            limit=limit,
            used=current_usage,
            reset_at=reset_at.isoformat(),
            resource=resource,
        )

    # =========================================================================
    # Helpers
    # =========================================================================

    def _resolve_scope(
        self,
        user_id: Optional[UUID],
        workspace_id: Optional[UUID],
    ) -> tuple[str, str]:
        """Determina el scope del rate limiting."""
        if workspace_id is not None:
            return "workspace", str(workspace_id)
        if user_id is not None:
            return "user", str(user_id)
        raise ValueError("Either user_id or workspace_id must be provided")

    def _get_limit(self, resource: str) -> int:
        """Obtiene el límite para un recurso."""
        limit = self._limits.get(resource)
        if limit is None:
            raise ValueError(f"Unknown resource: {resource}")
        return limit

    def _get_window_bounds(self) -> tuple[datetime, datetime]:
        """Calcula inicio y fin de la ventana actual."""
        now = datetime.now(timezone.utc)
        window_seconds = self._config.window_seconds

        # Alinear a ventanas fijas (ej: inicio de hora)
        window_start = now.replace(
            minute=0, second=0, microsecond=0
        )  # Para ventanas de 1 hora

        # Para ventanas más flexibles, usar:
        # window_start = now - timedelta(seconds=window_seconds)

        reset_at = window_start + timedelta(seconds=window_seconds)

        return window_start, reset_at


# -----------------------------------------------------------------------------
# In-Memory Implementation (for testing/development)
# -----------------------------------------------------------------------------
class InMemoryQuotaStorage:
    """
    Implementación en memoria para testing/desarrollo.

    Nota: No apta para producción (no persiste entre reinicios,
    no funciona con múltiples workers).
    """

    def __init__(self) -> None:
        self._data: Dict[str, int] = {}

    def _make_key(
        self, scope_type: str, scope_id: str, resource: str, window_start: datetime
    ) -> str:
        window_key = window_start.strftime("%Y%m%d%H")
        return f"{scope_type}:{scope_id}:{resource}:{window_key}"

    def get_usage(
        self,
        *,
        scope_type: str,
        scope_id: str,
        resource: str,
        window_start: datetime,
    ) -> int:
        key = self._make_key(scope_type, scope_id, resource, window_start)
        return self._data.get(key, 0)

    def increment_usage(
        self,
        *,
        scope_type: str,
        scope_id: str,
        resource: str,
        amount: int,
        window_start: datetime,
        window_ttl_seconds: int,
    ) -> int:
        key = self._make_key(scope_type, scope_id, resource, window_start)
        current = self._data.get(key, 0)
        new_value = current + amount
        self._data[key] = new_value
        return new_value

    def reset_usage(
        self,
        *,
        scope_type: str,
        scope_id: str,
        resource: str,
    ) -> None:
        # Eliminar todas las keys que matcheen
        prefix = f"{scope_type}:{scope_id}:{resource}:"
        keys_to_delete = [k for k in self._data if k.startswith(prefix)]
        for key in keys_to_delete:
            del self._data[key]
