"""S3-compatible object storage (Garage in production; any S3 works).

Buckets are named logically ("originals", "processed", "outputs", "public", "inbox") and
mapped to real bucket names in config.
"""

from __future__ import annotations

import mimetypes
from functools import lru_cache
from pathlib import Path
from typing import Any

import boto3
from botocore.config import Config

from crayonlark.core.config import get_settings


@lru_cache
def client() -> Any:
    s = get_settings()
    return boto3.client(
        "s3",
        endpoint_url=s.s3_endpoint_url,
        region_name=s.s3_region,
        aws_access_key_id=s.s3_access_key,
        aws_secret_access_key=s.s3_secret_key,
        config=Config(s3={"addressing_style": "path"}, retries={"max_attempts": 5}),
    )


def bucket(name: str) -> str:
    return get_settings().buckets[name]


def put_bytes(bucket_name: str, key: str, data: bytes, content_type: str | None = None) -> str:
    ctype = content_type or mimetypes.guess_type(key)[0] or "application/octet-stream"
    client().put_object(Bucket=bucket(bucket_name), Key=key, Body=data, ContentType=ctype)
    return key


def put_file(bucket_name: str, key: str, path: Path, content_type: str | None = None) -> str:
    ctype = content_type or mimetypes.guess_type(str(path))[0] or "application/octet-stream"
    client().upload_file(str(path), bucket(bucket_name), key, ExtraArgs={"ContentType": ctype})
    return key


def get_bytes(bucket_name: str, key: str) -> bytes:
    obj = client().get_object(Bucket=bucket(bucket_name), Key=key)
    data: bytes = obj["Body"].read()
    return data


def download(bucket_name: str, key: str, dest: Path) -> Path:
    dest.parent.mkdir(parents=True, exist_ok=True)
    client().download_file(bucket(bucket_name), key, str(dest))
    return dest


def exists(bucket_name: str, key: str) -> bool:
    try:
        client().head_object(Bucket=bucket(bucket_name), Key=key)
        return True
    except client().exceptions.ClientError:
        return False


def list_keys(bucket_name: str, prefix: str = "") -> list[str]:
    keys: list[str] = []
    paginator = client().get_paginator("list_objects_v2")
    for page in paginator.paginate(Bucket=bucket(bucket_name), Prefix=prefix):
        keys.extend(o["Key"] for o in page.get("Contents", []))
    return keys


def delete(bucket_name: str, key: str) -> None:
    client().delete_object(Bucket=bucket(bucket_name), Key=key)


def presigned_url(bucket_name: str, key: str, expires: int = 3600) -> str:
    url: str = client().generate_presigned_url(
        "get_object", Params={"Bucket": bucket(bucket_name), "Key": key}, ExpiresIn=expires
    )
    return url


def ping() -> bool:
    client().head_bucket(Bucket=bucket("outputs"))
    return True
