"""Idempotent first-run setup for Garage via its admin API (v2).

Creates the single-node layout, imports the S3 key from env, creates buckets and grants
the key access. Enables website access on the public bucket. Safe to run on every boot.
"""

from __future__ import annotations

import re
import time

import httpx

from crayonlark.core.config import get_settings

KEY_ID_RE = re.compile(r"^GK[0-9a-f]{24}$")
SECRET_RE = re.compile(r"^[0-9a-f]{64}$")


def _client() -> httpx.Client:
    s = get_settings()
    return httpx.Client(
        base_url=s.garage_admin_url,
        headers={"Authorization": f"Bearer {s.garage_admin_token}"},
        timeout=30,
    )


def wait_ready(c: httpx.Client, attempts: int = 60) -> None:
    for _ in range(attempts):
        try:
            if c.get("/v2/GetClusterStatus").status_code == 200:
                return
        except httpx.HTTPError:
            pass
        time.sleep(2)
    raise RuntimeError("Garage admin API not reachable")


def ensure_layout(c: httpx.Client, capacity_bytes: int) -> None:
    status = c.get("/v2/GetClusterStatus").json()
    node = status["nodes"][0]
    if node.get("role"):
        return
    c.post(
        "/v2/UpdateClusterLayout",
        json={"roles": [{"id": node["id"], "zone": "dc1", "capacity": capacity_bytes, "tags": []}]},
    ).raise_for_status()
    layout = c.get("/v2/GetClusterLayout").json()
    c.post("/v2/ApplyClusterLayout", json={"version": layout["version"] + 1}).raise_for_status()


def ensure_key(c: httpx.Client) -> str:
    s = get_settings()
    if not KEY_ID_RE.match(s.s3_access_key) or not SECRET_RE.match(s.s3_secret_key):
        raise ValueError(
            "S3_ACCESS_KEY must look like GK + 24 hex chars and S3_SECRET_KEY 64 hex chars. "
            "Generate with: echo GK$(openssl rand -hex 12); openssl rand -hex 32"
        )
    r = c.get("/v2/GetKeyInfo", params={"id": s.s3_access_key})
    if r.status_code == 200:
        return s.s3_access_key
    c.post(
        "/v2/ImportKey",
        json={
            "accessKeyId": s.s3_access_key,
            "secretAccessKey": s.s3_secret_key,
            "name": "crayonlark",
        },
    ).raise_for_status()
    return s.s3_access_key


def ensure_bucket(c: httpx.Client, name: str, key_id: str, website: bool = False) -> None:
    r = c.get("/v2/GetBucketInfo", params={"globalAlias": name})
    if r.status_code == 200:
        bucket_id = r.json()["id"]
    else:
        created = c.post("/v2/CreateBucket", json={"globalAlias": name})
        created.raise_for_status()
        bucket_id = created.json()["id"]
    c.post(
        "/v2/AllowBucketKey",
        json={
            "bucketId": bucket_id,
            "accessKeyId": key_id,
            "permissions": {"read": True, "write": True, "owner": True},
        },
    ).raise_for_status()
    if website:
        c.post(
            "/v2/UpdateBucket",
            params={"id": bucket_id},
            json={
                "websiteAccess": {
                    "enabled": True,
                    "indexDocument": "index.html",
                    "errorDocument": None,
                }
            },
        ).raise_for_status()


def run(capacity_gb: int = 150) -> list[str]:
    s = get_settings()
    with _client() as c:
        wait_ready(c)
        ensure_layout(c, capacity_gb * 1_000_000_000)
        # layout application is async; give it a moment before creating buckets
        time.sleep(2)
        key_id = ensure_key(c)
        for logical, real in s.buckets.items():
            ensure_bucket(c, real, key_id, website=(logical == "public"))
    return list(s.buckets.values())
