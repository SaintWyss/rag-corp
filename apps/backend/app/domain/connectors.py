"""
===============================================================================
TARJETA CRC — domain/connectors.py
===============================================================================

Módulo:
    Entidades y Puertos del subdominio Connectors

Responsabilidades:
    - Definir ConnectorSource (entidad de dominio).
    - Definir ConnectorProvider (enum de proveedores soportados).
    - Definir ConnectorSourceStatus (estados del ciclo de vida).
    - Definir ConnectorSourceRepository (puerto de persistencia).
    - Definir ConnectorClient (puerto para interacción con proveedores).
    - Definir ConnectorAccount (entidad para cuentas OAuth vinculadas).
    - Definir ConnectorAccountRepository (puerto de persistencia de cuentas).
    - Definir OAuthPort (puerto para flujos OAuth con proveedores).
    - Definir TokenEncryptionPort (puerto para cifrado de tokens).

Colaboradores:
    - infrastructure/repositories: implementaciones concretas.
    - application/usecases/connectors: orquestación.
    - interfaces/api/http/routers: serialización HTTP.

Principios:
    - Sin dependencias a DB/Redis/FastAPI.
    - Solo interfaces + entidades puras.
===============================================================================
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional, Protocol, Tuple
from uuid import UUID

# ---------------------------------------------------------------------------
# Value Objects / Enums
# ---------------------------------------------------------------------------


class ConnectorProvider(str, Enum):
    """Proveedores de conectores soportados."""

    GOOGLE_DRIVE = "google_drive"


class ConnectorSourceStatus(str, Enum):
    """Estados del ciclo de vida de un ConnectorSource."""

    PENDING = "pending"
    ACTIVE = "active"
    SYNCING = "syncing"
    ERROR = "error"
    DISABLED = "disabled"


# ---------------------------------------------------------------------------
# Entidad
# ---------------------------------------------------------------------------


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


@dataclass
class ConnectorSource:
    """
    Representa una fuente de datos externa vinculada a un workspace.

    Ejemplo: una carpeta de Google Drive configurada para sincronizar
    documentos hacia un workspace de RAG Corp.
    """

    id: UUID
    workspace_id: UUID
    provider: ConnectorProvider
    folder_id: str
    status: ConnectorSourceStatus = ConnectorSourceStatus.PENDING
    cursor_json: Optional[Dict[str, Any]] = field(default_factory=dict)
    created_at: datetime = field(default_factory=_utcnow)
    updated_at: datetime = field(default_factory=_utcnow)

    def mark_active(self) -> None:
        self.status = ConnectorSourceStatus.ACTIVE
        self.updated_at = _utcnow()

    def mark_syncing(self) -> None:
        self.status = ConnectorSourceStatus.SYNCING
        self.updated_at = _utcnow()

    def mark_error(self) -> None:
        self.status = ConnectorSourceStatus.ERROR
        self.updated_at = _utcnow()

    def update_cursor(self, cursor: Dict[str, Any]) -> None:
        self.cursor_json = cursor
        self.updated_at = _utcnow()


# ---------------------------------------------------------------------------
# Puerto: Persistencia
# ---------------------------------------------------------------------------


class ConnectorSourceRepository(Protocol):
    """Contrato de persistencia para ConnectorSource."""

    def create(self, source: ConnectorSource) -> None:
        """Persiste un nuevo ConnectorSource."""
        ...

    def list_by_workspace(
        self,
        workspace_id: UUID,
        *,
        provider: ConnectorProvider | None = None,
    ) -> List[ConnectorSource]:
        """Lista fuentes de un workspace, opcionalmente filtradas por provider."""
        ...

    def get(self, source_id: UUID) -> Optional[ConnectorSource]:
        """Obtiene un ConnectorSource por ID."""
        ...

    def update_status(self, source_id: UUID, status: ConnectorSourceStatus) -> None:
        """Actualiza el status de un ConnectorSource."""
        ...

    def update_cursor(self, source_id: UUID, cursor_json: Dict[str, Any]) -> None:
        """Actualiza el cursor de sincronización."""
        ...

    def delete(self, source_id: UUID) -> bool:
        """Elimina un ConnectorSource. Devuelve True si existía."""
        ...


# ---------------------------------------------------------------------------
# Puerto: Cliente de conector (interacción con provider externo)
# ---------------------------------------------------------------------------


@dataclass
class ConnectorFile:
    """Metadata mínima de un archivo listado por el conector."""

    file_id: str
    name: str
    mime_type: str
    modified_time: Optional[datetime] = None
    etag: Optional[str] = None  # Fingerprint para detección de cambios


@dataclass
class ConnectorDelta:
    """Resultado de un delta-sync: archivos nuevos/modificados + nuevo cursor."""

    files: List[ConnectorFile] = field(default_factory=list)
    new_cursor: Optional[Dict[str, Any]] = None


class ConnectorClient(Protocol):
    """
    Contrato para interactuar con un proveedor externo de archivos.

    Nota: La implementación concreta (Google Drive SDK, etc.) vive en infra.
    """

    def list_files(
        self, folder_id: str, *, page_token: str | None = None
    ) -> List[ConnectorFile]:
        """Lista archivos de una carpeta."""
        ...

    def fetch_file_content(
        self, file_id: str, *, mime_type: str = ""
    ) -> Tuple[bytes, str]:
        """Descarga contenido de un archivo. Retorna (bytes, sha256_hex)."""
        ...

    def get_delta(
        self, folder_id: str, *, cursor: Dict[str, Any] | None = None
    ) -> ConnectorDelta:
        """Obtiene cambios incrementales desde el último cursor."""
        ...


# ---------------------------------------------------------------------------
# Entidad: Cuenta OAuth vinculada
# ---------------------------------------------------------------------------


@dataclass
class ConnectorAccount:
    """
    Cuenta OAuth vinculada a un workspace.

    Contiene el refresh_token cifrado (nunca en claro en memoria persistente).
    """

    id: UUID
    workspace_id: UUID
    provider: ConnectorProvider
    account_email: str
    encrypted_refresh_token: str  # Cifrado con Fernet
    created_at: datetime = field(default_factory=_utcnow)
    updated_at: datetime = field(default_factory=_utcnow)


# ---------------------------------------------------------------------------
# Puerto: Persistencia de cuentas OAuth
# ---------------------------------------------------------------------------


class ConnectorAccountRepository(Protocol):
    """Contrato de persistencia para ConnectorAccount."""

    def upsert(self, account: ConnectorAccount) -> None:
        """Crea o actualiza la cuenta (idempotente por workspace+provider)."""
        ...

    def get_by_workspace(
        self, workspace_id: UUID, provider: ConnectorProvider
    ) -> Optional[ConnectorAccount]:
        """Obtiene la cuenta vinculada al workspace/provider."""
        ...

    def delete(self, account_id: UUID) -> bool:
        """Elimina una cuenta. Devuelve True si existía."""
        ...


# ---------------------------------------------------------------------------
# Puerto: Cifrado de tokens
# ---------------------------------------------------------------------------


class TokenEncryptionPort(Protocol):
    """Contrato para cifrar/descifrar tokens sensibles."""

    def encrypt(self, plaintext: str) -> str:
        """Cifra y devuelve un string base64-safe."""
        ...

    def decrypt(self, ciphertext: str) -> str:
        """Descifra y devuelve el texto plano original."""
        ...


# ---------------------------------------------------------------------------
# Puerto: Flujo OAuth con proveedores
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class OAuthTokenResponse:
    """Resultado de un token exchange exitoso."""

    access_token: str
    refresh_token: str
    email: str
    expires_in: int = 3600


class OAuthPort(Protocol):
    """Contrato para flujos OAuth con proveedores externos."""

    def build_authorization_url(self, *, state: str, redirect_uri: str) -> str:
        """Construye la URL de autorización del proveedor."""
        ...

    def exchange_code(self, *, code: str, redirect_uri: str) -> OAuthTokenResponse:
        """Intercambia authorization code por tokens."""
        ...

    def refresh_access_token(self, refresh_token: str) -> str:
        """Refresca el access_token usando un refresh_token. Devuelve nuevo access_token."""
        ...
