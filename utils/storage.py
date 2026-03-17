"""
MinIO / S3-compatible object storage wrapper.

Uses the boto3 SDK to interact with a self-hosted MinIO instance.
Environment variables:
    MINIO_ENDPOINT   – e.g. http://localhost:9000
    MINIO_ACCESS_KEY – root access key
    MINIO_SECRET_KEY – root secret key
    MINIO_BUCKET     – default bucket name (default: iksha)
"""

import os
import io
import boto3
from botocore.client import Config

MINIO_ENDPOINT = os.getenv("MINIO_ENDPOINT", "http://localhost:9000")
MINIO_ACCESS_KEY = os.getenv("MINIO_ACCESS_KEY", "minioadmin")
MINIO_SECRET_KEY = os.getenv("MINIO_SECRET_KEY", "minioadmin")
MINIO_BUCKET = os.getenv("MINIO_BUCKET", "iksha")

_client = boto3.client(
    "s3",
    endpoint_url=MINIO_ENDPOINT,
    aws_access_key_id=MINIO_ACCESS_KEY,
    aws_secret_access_key=MINIO_SECRET_KEY,
    config=Config(signature_version="s3v4"),
    region_name="us-east-1",
)


def _ensure_bucket():
    """Create the default bucket if it does not already exist."""
    try:
        _client.head_bucket(Bucket=MINIO_BUCKET)
    except Exception:
        _client.create_bucket(Bucket=MINIO_BUCKET)


def upload_file(local_path: str, object_key: str) -> str:
    """Upload a local file to MinIO and return its object key."""
    _ensure_bucket()
    _client.upload_file(local_path, MINIO_BUCKET, object_key)
    return object_key


def upload_bytes(data: bytes, object_key: str, content_type: str = "application/octet-stream") -> str:
    """Upload raw bytes to MinIO."""
    _ensure_bucket()
    _client.put_object(
        Bucket=MINIO_BUCKET,
        Key=object_key,
        Body=io.BytesIO(data),
        ContentLength=len(data),
        ContentType=content_type,
    )
    return object_key


def download_file(object_key: str, local_path: str) -> str:
    """Download a file from MinIO to a local path."""
    os.makedirs(os.path.dirname(local_path) or ".", exist_ok=True)
    _client.download_file(MINIO_BUCKET, object_key, local_path)
    return local_path


def download_bytes(object_key: str) -> bytes:
    """Download an object from MinIO as bytes."""
    response = _client.get_object(Bucket=MINIO_BUCKET, Key=object_key)
    return response["Body"].read()


def generate_presigned_url(object_key: str, expiration: int = 3600) -> str:
    """Generate a presigned URL for temporary access to an object."""
    return _client.generate_presigned_url(
        "get_object",
        Params={"Bucket": MINIO_BUCKET, "Key": object_key},
        ExpiresIn=expiration,
    )


def delete_object(object_key: str):
    """Delete an object from MinIO."""
    _client.delete_object(Bucket=MINIO_BUCKET, Key=object_key)
