"""
Name: S3 Storage Adapter Tests

Responsibilities:
  - Validate adapter uses boto3 client correctly
  - Avoid real network calls (mocked client)
"""

from unittest.mock import MagicMock, patch

import pytest

from app.infrastructure.storage import S3Config, S3FileStorageAdapter


pytestmark = pytest.mark.unit


def test_upload_file_uses_put_object():
    mock_client = MagicMock()
    with patch(
        "app.infrastructure.storage.s3_file_storage.boto3.client",
        return_value=mock_client,
    ):
        adapter = S3FileStorageAdapter(
            S3Config(
                bucket="bucket",
                access_key="key",
                secret_key="secret",
                region="us-east-1",
                endpoint_url="http://minio:9000",
            )
        )
        adapter.upload_file("doc.pdf", b"data", "application/pdf")

    mock_client.put_object.assert_called_once_with(
        Bucket="bucket",
        Key="doc.pdf",
        Body=b"data",
        ContentType="application/pdf",
    )


def test_delete_file_uses_delete_object():
    mock_client = MagicMock()
    with patch(
        "app.infrastructure.storage.s3_file_storage.boto3.client",
        return_value=mock_client,
    ):
        adapter = S3FileStorageAdapter(
            S3Config(
                bucket="bucket",
                access_key="key",
                secret_key="secret",
            )
        )
        adapter.delete_file("doc.pdf")

    mock_client.delete_object.assert_called_once_with(
        Bucket="bucket",
        Key="doc.pdf",
    )


def test_download_file_uses_get_object():
    mock_client = MagicMock()
    mock_body = MagicMock()
    mock_body.read.return_value = b"data"
    mock_client.get_object.return_value = {"Body": mock_body}

    with patch(
        "app.infrastructure.storage.s3_file_storage.boto3.client",
        return_value=mock_client,
    ):
        adapter = S3FileStorageAdapter(
            S3Config(
                bucket="bucket",
                access_key="key",
                secret_key="secret",
            )
        )
        data = adapter.download_file("doc.pdf")

    assert data == b"data"
    mock_client.get_object.assert_called_once_with(
        Bucket="bucket",
        Key="doc.pdf",
    )
    mock_body.read.assert_called_once()
