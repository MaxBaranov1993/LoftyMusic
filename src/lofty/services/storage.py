"""S3/MinIO storage client wrapper."""

import io
import logging

import boto3
from botocore.exceptions import ClientError

from lofty.config import settings

logger = logging.getLogger(__name__)


class StorageClient:
    """Wrapper around S3-compatible object storage (MinIO in dev, S3 in prod)."""

    def __init__(self) -> None:
        self._client = boto3.client(
            "s3",
            endpoint_url=f"{'https' if settings.storage_use_ssl else 'http'}://{settings.storage_endpoint}",
            aws_access_key_id=settings.storage_access_key,
            aws_secret_access_key=settings.storage_secret_key,
            region_name="us-east-1",
        )
        self._bucket = settings.storage_bucket

    def ensure_bucket(self) -> None:
        """Create the storage bucket if it doesn't exist."""
        try:
            self._client.head_bucket(Bucket=self._bucket)
        except ClientError:
            self._client.create_bucket(Bucket=self._bucket)
            logger.info(f"Created storage bucket: {self._bucket}")

    def upload_bytes(self, key: str, data: bytes, content_type: str = "audio/wav") -> int:
        """Upload bytes to storage. Returns the size in bytes."""
        self._client.put_object(
            Bucket=self._bucket,
            Key=key,
            Body=io.BytesIO(data),
            ContentLength=len(data),
            ContentType=content_type,
        )
        return len(data)

    def generate_presigned_url(self, key: str, expires_in: int = 3600) -> str:
        """Generate a presigned download URL."""
        url = self._client.generate_presigned_url(
            "get_object",
            Params={"Bucket": self._bucket, "Key": key},
            ExpiresIn=expires_in,
        )
        # Replace internal endpoint with public endpoint for client access
        if settings.storage_endpoint != settings.storage_public_endpoint:
            url = url.replace(settings.storage_endpoint, settings.storage_public_endpoint)
        return url

    def delete_object(self, key: str) -> None:
        """Delete an object from storage."""
        self._client.delete_object(Bucket=self._bucket, Key=key)


# Module-level singleton
storage_client = StorageClient()
