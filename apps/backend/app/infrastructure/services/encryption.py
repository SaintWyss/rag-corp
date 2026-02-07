"""
============================================================
TARJETA CRC — infrastructure/services/encryption.py
============================================================
Class: FernetTokenEncryption

Responsibilities:
  - Implementar TokenEncryptionPort usando cryptography.fernet.Fernet.
  - Cifrar/descifrar tokens sensibles (refresh_token).
  - Fail-fast si la key no está configurada o es inválida.

Collaborators:
  - domain.connectors.TokenEncryptionPort
  - cryptography.fernet.Fernet
============================================================
"""

from __future__ import annotations

from cryptography.fernet import Fernet, InvalidToken

from ...crosscutting.logger import logger


class FernetTokenEncryption:
    """Cifrado simétrico de tokens usando Fernet (AES-128-CBC + HMAC)."""

    def __init__(self, key: str):
        """
        Args:
            key: Key Fernet (base64, 32 bytes). Generar con Fernet.generate_key().

        Raises:
            ValueError: Si la key está vacía o es inválida.
        """
        if not key or not key.strip():
            raise ValueError(
                "CONNECTOR_ENCRYPTION_KEY is required for token storage. "
                'Generate one with: python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"'
            )
        try:
            self._fernet = Fernet(key.strip().encode())
        except Exception as exc:
            raise ValueError(
                f"CONNECTOR_ENCRYPTION_KEY is invalid (not a valid Fernet key): {exc}"
            ) from exc

    def encrypt(self, plaintext: str) -> str:
        """Cifra el texto y devuelve string base64-safe."""
        return self._fernet.encrypt(plaintext.encode()).decode()

    def decrypt(self, ciphertext: str) -> str:
        """Descifra y devuelve el texto plano original."""
        try:
            return self._fernet.decrypt(ciphertext.encode()).decode()
        except InvalidToken:
            logger.error("token decryption failed (invalid key or corrupted data)")
            raise ValueError("Failed to decrypt token (key rotation or corruption)")
