"""
===============================================================================
CRC CARD — infrastructure/storage/errors.py
===============================================================================

Componente:
  Errores tipados de Storage (S3/MinIO)

Responsabilidades:
  - Definir un lenguaje común de fallas del subsistema de almacenamiento.
  - Evitar que excepciones de boto3/botocore se filtren a capas superiores.
  - Permitir manejo consistente (retry, status codes, logs, métricas).

Colaboradores:
  - infrastructure/storage/s3_file_storage.py (mapeo de ClientError -> StorageError)
===============================================================================
"""


class StorageError(Exception):
    """Base de errores del subsistema de Storage."""


class StorageConfigurationError(StorageError):
    """Configuración inválida o incompleta del adaptador de storage."""


class StorageNotFoundError(StorageError):
    """Objeto no encontrado (ej: NoSuchKey)."""

    def __init__(self, key: str):
        super().__init__(f"Archivo no encontrado en storage. key={key}")
        self.key = key


class StoragePermissionError(StorageError):
    """Credenciales inválidas o falta de permisos (ej: AccessDenied)."""

    def __init__(self, message: str = "Permiso denegado en storage."):
        super().__init__(message)


class StorageUnavailableError(StorageError):
    """Storage caído o temporalmente no disponible (timeouts, 503, etc.)."""

    def __init__(self, message: str = "Storage no disponible."):
        super().__init__(message)
