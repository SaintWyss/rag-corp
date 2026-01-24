"""
Name: S3 File Storage Adapter

Responsibilities:
  - Upload and delete files in S3-compatible storage (AWS/MinIO)
  - Hide client initialization details from callers
"""

from dataclasses import dataclass
from typing import Optional

import boto3

from ...domain.services import FileStoragePort


@dataclass(frozen=True)
class S3Config:
    bucket: str
    access_key: str
    secret_key: str
    region: Optional[str] = None
    endpoint_url: Optional[str] = None


class S3FileStorageAdapter(FileStoragePort):
    """R: S3-compatible storage adapter (AWS S3 / MinIO)."""

    def __init__(self, config: S3Config):
        if not config.bucket:
            raise ValueError("S3 bucket is required")
        if not config.access_key or not config.secret_key:
            raise ValueError("S3 credentials are required")
        self._bucket = config.bucket
        self._client = boto3.client(
            "s3",
            aws_access_key_id=config.access_key,
            aws_secret_access_key=config.secret_key,
            region_name=config.region or None,
            endpoint_url=config.endpoint_url or None,
        )

    def upload_file(self, key: str, content: bytes, content_type: str | None) -> None:
        self._client.put_object(
            Bucket=self._bucket,
            Key=key,
            Body=content,
            ContentType=content_type or "application/octet-stream",
        )

    def download_file(self, key: str) -> bytes:
        response = self._client.get_object(
            Bucket=self._bucket,
            Key=key,
        )
        body = response["Body"]
        data = body.read()
        try:
            body.close()
        except Exception:
            pass
        return data

    def delete_file(self, key: str) -> None:
        self._client.delete_object(
            Bucket=self._bucket,
            Key=key,
        )
