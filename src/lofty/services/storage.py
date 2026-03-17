"""S3/MinIO storage client wrapper."""

import io
import logging
from urllib.parse import urlparse, urlunparse

import boto3
from botocore.config import Config as BotoConfig
from botocore.exceptions import ClientError

from lofty.config import settings

logger = logging.getLogger(__name__)


class StorageClient:
    """Wrapper around S3-compatible object storage (MinIO in dev, S3 in prod)."""

    def __init__(self) -> None:
        scheme = "https" if settings.storage_use_ssl else "http"
        self._endpoint_url = f"{scheme}://{settings.storage_endpoint}"
        self._client = boto3.client(
            "s3",
            endpoint_url=self._endpoint_url,
            aws_access_key_id=settings.storage_access_key,
            aws_secret_access_key=settings.storage_secret_key,
            region_name="us-east-1",
            config=BotoConfig(
                max_pool_connections=25,
                connect_timeout=5,
                read_timeout=30,
            ),
        )
        self._bucket = settings.storage_bucket

    def ensure_bucket(self) -> None:
        """Create the storage bucket if it doesn't exist."""
        try:
            self._client.head_bucket(Bucket=self._bucket)
        except ClientError:
            self._client.create_bucket(Bucket=self._bucket)
            logger.info("Created storage bucket: %s", self._bucket)

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
        """Generate a presigned download URL.

        Safely replaces only the host:port portion of the URL when the
        internal and public endpoints differ (e.g., Docker internal vs
        external access).
        """
        url = self._client.generate_presigned_url(
            "get_object",
            Params={"Bucket": self._bucket, "Key": key},
            ExpiresIn=expires_in,
        )
        if settings.storage_endpoint != settings.storage_public_endpoint:
            parsed = urlparse(url)
            scheme = "https" if settings.storage_use_ssl else "http"
            public_netloc = settings.storage_public_endpoint
            url = urlunparse(parsed._replace(scheme=scheme, netloc=public_netloc))
        return url

    def delete_object(self, key: str) -> None:
        """Delete an object from storage."""
        self._client.delete_object(Bucket=self._bucket, Key=key)


# Module-level singleton
storage_client = StorageClient()
