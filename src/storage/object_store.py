from __future__ import annotations

import logging
import os
from pathlib import Path
from typing import BinaryIO

logger = logging.getLogger(__name__)

try:
    import boto3
    from botocore.client import Config
    from botocore.exceptions import ClientError
    BOTO3_AVAILABLE = True
except ImportError:
    boto3 = None
    Config = None
    ClientError = Exception
    BOTO3_AVAILABLE = False


def get_s3_settings() -> dict[str, str | int]:
    return {
        "bucket": os.environ.get("S3_BUCKET", "").strip(),
        "endpoint_url": os.environ.get("S3_ENDPOINT_URL", "").strip(),
        "access_key_id": os.environ.get("S3_ACCESS_KEY_ID") or os.environ.get("AWS_ACCESS_KEY_ID", "").strip(),
        "secret_access_key": os.environ.get("S3_SECRET_ACCESS_KEY") or os.environ.get("AWS_SECRET_ACCESS_KEY", "").strip(),
        "region": os.environ.get("S3_REGION", "auto").strip(),
        "presign_ttl": int(os.environ.get("S3_PRESIGN_TTL_SECONDS", "900")),
    }


def is_s3_configured() -> bool:
    if not BOTO3_AVAILABLE:
        return False
    settings = get_s3_settings()
    return bool(settings["bucket"] and settings["access_key_id"] and settings["secret_access_key"])


def get_s3_client():
    if not is_s3_configured():
        return None
    settings = get_s3_settings()
    config = Config(
        signature_version="s3v4",
        s3={"addressing_style": "virtual"},
        retries={"max_attempts": 3, "mode": "standard"},
    )
    client_kwargs = {
        "service_name": "s3",
        "aws_access_key_id": settings["access_key_id"],
        "aws_secret_access_key": settings["secret_access_key"],
        "region_name": settings["region"] if settings["region"] != "auto" else "us-east-1",
        "config": config,
    }
    if settings["endpoint_url"]:
        client_kwargs["endpoint_url"] = settings["endpoint_url"]
    return boto3.client(**client_kwargs)


def check_object_storage_connectivity() -> bool:
    """Live probe checking bucket reachability."""
    if not is_s3_configured():
        return False
    try:
        client = get_s3_client()
        settings = get_s3_settings()
        client.head_bucket(Bucket=settings["bucket"])
        return True
    except Exception as exc:
        logger.warning("Object storage health check probe failed: %s", exc)
        return False


def build_tenant_job_key(tenant_id: str, job_id: str, filename: str) -> str:
    """Strict tenant-isolated key: tenants/{tenant_id}/jobs/{job_id}/{filename}"""
    clean_tenant = tenant_id.strip("/ ")
    clean_job = job_id.strip("/ ")
    clean_file = Path(filename).name
    return f"tenants/{clean_tenant}/jobs/{clean_job}/{clean_file}"


def upload_file(local_path: str | Path, s3_key: str, content_type: str | None = None) -> str:
    path = Path(local_path)
    if not path.is_file():
        raise FileNotFoundError(f"Local file not found for S3 upload: {local_path}")
    if not is_s3_configured():
        raise RuntimeError("Object storage S3_BUCKET is not configured.")

    client = get_s3_client()
    settings = get_s3_settings()
    extra_args = {}
    if content_type:
        extra_args["ContentType"] = content_type

    client.upload_file(
        Filename=str(path.resolve()),
        Bucket=settings["bucket"],
        Key=s3_key,
        ExtraArgs=extra_args if extra_args else None,
    )
    logger.info("Uploaded artifact to s3://%s/%s", settings["bucket"], s3_key)
    return s3_key


def upload_fileobj(file_obj: BinaryIO, s3_key: str, content_type: str | None = None) -> str:
    if not is_s3_configured():
        raise RuntimeError("Object storage S3_BUCKET is not configured.")
    client = get_s3_client()
    settings = get_s3_settings()
    extra_args = {}
    if content_type:
        extra_args["ContentType"] = content_type

    client.upload_fileobj(
        Fileobj=file_obj,
        Bucket=settings["bucket"],
        Key=s3_key,
        ExtraArgs=extra_args if extra_args else None,
    )
    logger.info("Uploaded fileobj to s3://%s/%s", settings["bucket"], s3_key)
    return s3_key


def generate_presigned_url(
    s3_key: str,
    filename: str | None = None,
    expires_in: int | None = None,
    inline: bool = False,
) -> str:
    """Generate short-lived pre-signed GET URL (default 900s)."""
    if not is_s3_configured():
        raise RuntimeError("Object storage S3_BUCKET is not configured.")

    client = get_s3_client()
    settings = get_s3_settings()
    ttl = expires_in or settings["presign_ttl"]
    out_name = filename or Path(s3_key).name

    disposition = "inline" if inline else f'attachment; filename="{out_name}"'
    params = {
        "Bucket": settings["bucket"],
        "Key": s3_key,
        "ResponseContentDisposition": disposition,
    }

    url = client.generate_presigned_url(
        ClientMethod="get_object",
        Params=params,
        ExpiresIn=ttl,
    )
    return url


def delete_file(s3_key: str) -> bool:
    if not is_s3_configured():
        return False
    try:
        client = get_s3_client()
        settings = get_s3_settings()
        client.delete_object(Bucket=settings["bucket"], Key=s3_key)
        return True
    except Exception as exc:
        logger.warning("Failed to delete S3 object %s: %s", s3_key, exc)
        return False
