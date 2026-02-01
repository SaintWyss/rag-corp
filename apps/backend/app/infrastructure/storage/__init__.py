"""Adapters de infraestructura: Storage."""

from .errors import (
    StorageConfigurationError,
    StorageError,
    StorageNotFoundError,
    StoragePermissionError,
    StorageUnavailableError,
)
from .s3_file_storage import S3Config, S3FileStorageAdapter

__all__ = [
    "S3Config",
    "S3FileStorageAdapter",
    "StorageError",
    "StorageConfigurationError",
    "StorageNotFoundError",
    "StoragePermissionError",
    "StorageUnavailableError",
]
