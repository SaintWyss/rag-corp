"""
===============================================================================
TARJETA CRC — identity/auth.py
===============================================================================

Módulo:
    Autenticación por API Key (X-API-Key)

Responsabilidades:
    - Cargar/parsear la configuración de API keys desde Settings (env).
    - Validar API keys con comparación en tiempo constante (mitiga timing attacks).
    - Validar scopes (ej: ingest, ask, metrics) para endpoints.
    - Exponer dependencias FastAPI (require_scope, require_metrics_auth).
    - Nunca loguear la key en claro; solo hash recortado.

Colaboradores:
    - crosscutting.config.get_settings: obtiene API_KEYS_CONFIG + settings de métricas.
    - crosscutting.error_responses: unauthorized/forbidden estándar.
    - crosscutting.logger: logging estructurado.
    - identity.rbac: puede usar request.state.api_key_hash y/o permisos.

Decisiones de diseño (Senior):
    - "Config" se cachea: parse + validación de tipos una sola vez.
    - "Validator" es puro y testeable (sin dependencias de FastAPI).
    - El Adapter FastAPI es mínimo: extrae header, valida, setea request.state.
===============================================================================
"""

from __future__ import annotations

import hashlib
import hmac
import json
from functools import lru_cache
from typing import Callable

from fastapi import Header, Request
from fastapi.security import APIKeyHeader

from ..crosscutting.error_responses import forbidden, unauthorized
from ..crosscutting.logger import logger

# ---------------------------------------------------------------------------
# Constantes de seguridad
# ---------------------------------------------------------------------------

# R: Longitud del hash recortado para logs. Mantener pequeño pero útil.
_KEY_HASH_LEN: int = 12

# R: Security scheme (para OpenAPI). auto_error=False: controlamos el error nosotros.
api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)


# ---------------------------------------------------------------------------
# Helpers internos (NO exportados)
# ---------------------------------------------------------------------------


def _hash_key(key: str) -> str:
    """Hashea la API key para logging seguro (nunca loguear en claro)."""
    digest = hashlib.sha256(key.encode("utf-8")).hexdigest()
    return digest[:_KEY_HASH_LEN]


def _constant_time_compare(a: str, b: str) -> bool:
    """Comparación en tiempo constante (mitiga timing attacks)."""
    return hmac.compare_digest(a.encode("utf-8"), b.encode("utf-8"))


def _normalize_key(key: str | None) -> str | None:
    """Normaliza inputs triviales (espacios)."""
    if key is None:
        return None
    key = key.strip()
    return key or None


def _validate_config_shape(raw: object) -> dict[str, list[str]]:
    """Valida/normaliza el shape del JSON de API keys.

    Formato esperado:
        {
          "mi-key": ["ingest", "ask"],
          "otra-key": ["*"]   # wildcard
        }
    """
    if not isinstance(raw, dict):
        return {}

    cfg: dict[str, list[str]] = {}
    for k, v in raw.items():
        if not isinstance(k, str) or not k.strip():
            continue
        if not isinstance(v, list) or not all(isinstance(s, str) for s in v):
            continue
        scopes = [s.strip() for s in v if s.strip()]
        if scopes:
            cfg[k.strip()] = scopes
    return cfg


@lru_cache(maxsize=1)
def _parse_keys_config() -> dict[str, list[str]]:
    """Parsea API_KEYS_CONFIG desde Settings y lo valida.

    Retorna dict vacío si no está configurado o es inválido.
    """
    from ..crosscutting.config import get_settings

    config_str = (get_settings().api_keys_config or "").strip()
    if not config_str:
        return {}

    try:
        raw = json.loads(config_str)
    except json.JSONDecodeError as exc:
        logger.warning("API_KEYS_CONFIG inválido (JSON)", extra={"error": str(exc)})
        return {}

    cfg = _validate_config_shape(raw)
    if not cfg:
        logger.warning("API_KEYS_CONFIG inválido (shape)")
        return {}

    return cfg


# ---------------------------------------------------------------------------
# API pública del módulo (para otras capas)
# ---------------------------------------------------------------------------


def get_keys_config() -> dict[str, list[str]]:
    """Devuelve el config de keys (cacheado)."""
    return _parse_keys_config()


def clear_keys_cache() -> None:
    """Limpia el cache (tests / hot-reload local)."""
    _parse_keys_config.cache_clear()


def is_auth_enabled() -> bool:
    """Indica si hay API keys configuradas."""
    return bool(get_keys_config())


class APIKeyValidator:
    """Validador puro para API keys y scopes."""

    def __init__(self, keys_config: dict[str, list[str]]):
        self._keys = keys_config

    def validate_key(self, key: str) -> bool:
        """True si la key existe en el config (comparación constante)."""
        if not key:
            return False

        # R: Comparamos contra todas las keys para no filtrar timing por early-return.
        found = False
        for valid_key in self._keys.keys():
            if _constant_time_compare(key, valid_key):
                found = True
        return found

    def get_scopes(self, key: str) -> list[str]:
        """Scopes de la key (lista vacía si no existe)."""
        for valid_key, scopes in self._keys.items():
            if _constant_time_compare(key, valid_key):
                return scopes
        return []

    def validate_scope(self, key: str, required_scope: str) -> bool:
        """True si la key tiene el scope requerido o wildcard '*'."""
        scopes = self.get_scopes(key)
        return required_scope in scopes or "*" in scopes


@lru_cache(maxsize=1)
def _get_validator() -> APIKeyValidator | None:
    """Construye el validador una sola vez (performance + limpieza)."""
    cfg = get_keys_config()
    return APIKeyValidator(cfg) if cfg else None


def require_scope(scope: str) -> Callable:
    """Dependency FastAPI: requiere API key válida + scope.

    - Si auth está deshabilitada (sin keys configuradas), es NO-OP.
    - Si falta la key: 401.
    - Si la key es inválida o no tiene scope: 403.
    """

    async def dependency(
        request: Request,
        api_key: str | None = Header(None, alias="X-API-Key"),
    ) -> None:
        keys_cfg = get_keys_config()

        # R: Si no hay keys, consideramos auth deshabilitada.
        if not keys_cfg:
            return None

        api_key_norm = _normalize_key(api_key)

        if not api_key_norm:
            logger.warning(
                "Auth falló: falta X-API-Key",
                extra={"path": request.url.path, "scope": scope},
            )
            raise unauthorized("Falta API key. Enviá el header X-API-Key.")

        validator = _get_validator()
        if not validator:
            # R: No debería pasar si keys_cfg no está vacío, pero lo dejamos defensivo.
            raise unauthorized("Autenticación no disponible.")

        if not validator.validate_key(api_key_norm):
            logger.warning(
                "Auth falló: API key inválida",
                extra={"key_hash": _hash_key(api_key_norm), "path": request.url.path},
            )
            raise forbidden("API key inválida.")

        if not validator.validate_scope(api_key_norm, scope):
            logger.warning(
                "Auth falló: scope insuficiente",
                extra={
                    "key_hash": _hash_key(api_key_norm),
                    "path": request.url.path,
                    "required_scope": scope,
                    "available_scopes": validator.get_scopes(api_key_norm),
                },
            )
            raise forbidden(f"La API key no tiene el scope requerido: {scope}")

        # R: Dejamos hash en request.state para RBAC / rate limiting.
        request.state.api_key_hash = _hash_key(api_key_norm)
        return None

    return dependency


def require_metrics_auth() -> Callable:
    """Dependency FastAPI: auth opcional para /metrics (controlado por settings)."""

    async def dependency(
        request: Request,
        api_key: str | None = Header(None, alias="X-API-Key"),
    ) -> None:
        from ..crosscutting.config import get_settings

        if not get_settings().metrics_require_auth:
            return None

        # R: reutilizamos lógica de scopes.
        await require_scope("metrics")(request, api_key)
        return None

    return dependency
