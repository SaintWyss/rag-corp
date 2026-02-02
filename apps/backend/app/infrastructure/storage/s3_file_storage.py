"""
===============================================================================
CRC CARD — infrastructure/storage/s3_file_storage.py
===============================================================================

Clase:
  S3FileStorageAdapter (Adapter / Facade)

Responsabilidades:
  - Implementar FileStoragePort contra S3-compatible (AWS S3 / MinIO).
  - Encapsular boto3 (NO filtrar ClientError).
  - Subir (bytes o stream), descargar (bytes), borrar.
  - Generar presigned URLs (escala y seguridad).

Colaboradores:
  - domain.services.FileStoragePort (port)
  - infrastructure.storage.errors (errores tipados)
  - boto3/botocore (SDK, oculto por este adapter)

Decisiones de diseño (Senior):
  - Validación fail-fast de config.
  - Lazy import de boto3/botocore para mejorar cold start.
  - Mapeo explícito de errores (ClientError -> StorageError).
  - upload acepta bytes o BinaryIO para evitar OOM con archivos grandes.
===============================================================================
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import BinaryIO, Optional, Union

from ...crosscutting.logger import logger
from ...domain.services import FileStoragePort
from .errors import (
    StorageConfigurationError,
    StorageError,
    StorageNotFoundError,
    StoragePermissionError,
    StorageUnavailableError,
)


@dataclass(frozen=True)
class S3Config:
    """
    Configuración del storage S3-compatible.

    Nota:
      - endpoint_url permite MinIO u otros S3 compatibles.
      - region puede omitirse en MinIO.
    """

    bucket: str
    access_key: str
    secret_key: str
    region: Optional[str] = None
    endpoint_url: Optional[str] = None


class S3FileStorageAdapter(FileStoragePort):
    """
    Adapter S3-compatible.

    Implementa:
      - upload_file
      - download_file
      - delete_file
      - generate_presigned_url
    """

    def __init__(self, config: S3Config, *, client=None) -> None:
        self._config = config
        self._bucket = (config.bucket or "").strip()

        # ---------------------------------------------------------------------
        # Validaciones (fail-fast).
        # ---------------------------------------------------------------------
        if not self._bucket:
            raise StorageConfigurationError("S3 bucket es requerido.")
        if (
            not (config.access_key or "").strip()
            or not (config.secret_key or "").strip()
        ):
            raise StorageConfigurationError(
                "Credenciales S3 requeridas (access_key/secret_key)."
            )

        # ---------------------------------------------------------------------
        # Cliente: inyectable para tests (mocks).
        # ---------------------------------------------------------------------
        if client is not None:
            self._client = client
            return

        # Lazy import para reducir costo de arranque.
        try:
            import boto3
        except Exception as exc:
            raise StorageConfigurationError("boto3 no está instalado.") from exc

        self._client = boto3.client(
            "s3",
            aws_access_key_id=config.access_key,
            aws_secret_access_key=config.secret_key,
            region_name=config.region or None,
            endpoint_url=config.endpoint_url or None,
        )

    # =========================================================================
    # API pública (Port)
    # =========================================================================

    def upload_file(
        self,
        key: str,
        content: Union[bytes, BinaryIO],
        content_type: str | None,
    ) -> None:
        """
        Sube un objeto al bucket.

        Soporta:
          - bytes (pequeños/medianos)
          - stream (BinaryIO) para archivos grandes sin consumir RAM.

        Importante:
          - En S3, 'ContentType' mejora UX (descarga / previews).
        """
        self._require_key(key)

        effective_ct = (content_type or "application/octet-stream").strip()

        try:
            # Caso 1: bytes (rápido, simple)
            if isinstance(content, (bytes, bytearray, memoryview)):
                self._client.put_object(
                    Bucket=self._bucket,
                    Key=key,
                    Body=content,
                    ContentType=effective_ct,
                )
                return

            # Caso 2: stream (BinaryIO) -> upload_fileobj
            # ExtraArgs es el mecanismo recomendado para ContentType.
            self._client.upload_fileobj(
                Fileobj=content,
                Bucket=self._bucket,
                Key=key,
                ExtraArgs={"ContentType": effective_ct},
            )

        except Exception as exc:
            raise self._map_storage_error(exc, key=key, action="upload") from exc

    def download_file(self, key: str) -> bytes:
        """
        Descarga el objeto completo a memoria.

        Nota:
          - Para casos extremadamente grandes podrías agregar download_stream()
            (pero tu port de dominio hoy retorna bytes).
        """
        self._require_key(key)

        try:
            response = self._client.get_object(Bucket=self._bucket, Key=key)
            body = response["Body"]
            data = body.read()
            try:
                body.close()
            except Exception:
                pass
            return data

        except Exception as exc:
            raise self._map_storage_error(exc, key=key, action="download") from exc

    def delete_file(self, key: str) -> None:
        """
        Borra el objeto.

        Diseño:
          - Delete en S3 es idempotente: borrar algo inexistente “no debería” romper.
          - Si hay un error real (permiso/infra), lo tipamos.
        """
        self._require_key(key)

        try:
            self._client.delete_object(Bucket=self._bucket, Key=key)
        except Exception as exc:
            raise self._map_storage_error(exc, key=key, action="delete") from exc

    def generate_presigned_url(
        self,
        key: str,
        *,
        expires_in_seconds: int = 3600,
        filename: str | None = None,
    ) -> str:
        """
        Genera una URL firmada para descargar el objeto sin que el backend sea proxy.

        Ventajas:
          - Performance: cliente descarga directo del storage
          - Seguridad: URL expira
          - Escala: backend no transporta binarios
        """
        self._require_key(key)

        if expires_in_seconds <= 0:
            expires_in_seconds = 3600

        params: dict = {"Bucket": self._bucket, "Key": key}

        # Si el cliente quiere sugerir un nombre de archivo:
        # ResponseContentDisposition se respeta por la mayoría de browsers.
        if filename:
            safe_name = filename.replace('"', "'")
            params["ResponseContentDisposition"] = f'attachment; filename="{safe_name}"'

        try:
            url = self._client.generate_presigned_url(
                ClientMethod="get_object",
                Params=params,
                ExpiresIn=int(expires_in_seconds),
            )
            return str(url)
        except Exception as exc:
            raise self._map_storage_error(exc, key=key, action="presign") from exc

    # =========================================================================
    # Helpers privados (Clean / DRY)
    # =========================================================================

    @staticmethod
    def _require_key(key: str) -> None:
        if not (key or "").strip():
            raise StorageError("key de storage es requerido.")

    def _map_storage_error(
        self, exc: Exception, *, key: str, action: str
    ) -> StorageError:
        """
        Traduce errores del SDK a errores del subsistema.

        Regla:
          - Infra (boto3) queda encapsulada.
          - Capas superiores trabajan con StorageError.
        """
        # Lazy import del tipo específico (sin dependencia dura en import time).
        try:
            from botocore.exceptions import (
                ClientError,
                ConnectTimeoutError,
                EndpointConnectionError,
                ReadTimeoutError,
            )
        except Exception:
            ClientError = None  # type: ignore
            EndpointConnectionError = ()  # type: ignore
            ConnectTimeoutError = ()  # type: ignore
            ReadTimeoutError = ()  # type: ignore

        # Timeouts / endpoint caído
        if isinstance(
            exc, (EndpointConnectionError, ConnectTimeoutError, ReadTimeoutError)
        ):  # type: ignore
            logger.warning("Storage unavailable", extra={"action": action, "key": key})
            return StorageUnavailableError("Storage no disponible (timeout/conexión).")

        # Error S3 “estructurado”
        if ClientError is not None and isinstance(exc, ClientError):  # type: ignore
            code = (exc.response.get("Error") or {}).get("Code") or ""
            code = str(code)

            if code in {"NoSuchKey", "404", "NotFound"}:
                return StorageNotFoundError(key)

            if code in {"AccessDenied", "InvalidAccessKeyId", "SignatureDoesNotMatch"}:
                return StoragePermissionError(
                    "Permiso/credenciales inválidas en storage."
                )

            if code in {"SlowDown", "RequestTimeout", "ServiceUnavailable"}:
                return StorageUnavailableError("Storage temporalmente no disponible.")

            # Default: error genérico tipado
            logger.exception(
                "Storage ClientError",
                extra={"action": action, "key": key, "code": code},
            )
            return StorageError(f"Fallo de storage ({action}). code={code}")

        # Fallback genérico
        logger.exception("Storage error", extra={"action": action, "key": key})
        return StorageError(f"Fallo de storage ({action}).")
