"""Nightly backups to the `backups` volume (14-day retention) and restore.

Layout under BACKUP_DIR (/backups):
    db/crayonlark-YYYY-MM-DD.dump          pg_dump custom format, one per night
    objects/<bucket>/<key>                 a mirror of every Garage bucket (only changes copied)
    objects/<bucket>/.manifest.json        key → ETag, so unchanged files are skipped
    objects-deleted/YYYY-MM-DD/<bucket>/…  files removed from Garage that night (kept 14 days)
    last.json                              result of the last run (shown in admin)

Optional off-site copy: set BACKUP_S3_BUCKET (+ endpoint/keys) for any S3-compatible storage
(Backblaze B2, Cloudflare R2, Wasabi, …). The same dumps and changed files are uploaded there.

Restore (`crayonlark restore --day YYYY-MM-DD --yes`, or scripts/restore.sh) replaces the database
with that night's dump and puts every mirrored file back into Garage.
"""

from __future__ import annotations

import json
import shutil
import subprocess
from datetime import UTC, date, datetime, timedelta
from pathlib import Path
from typing import Any

from sqlalchemy.engine import make_url

from crayonlark.core import storage
from crayonlark.core.config import get_settings


def root() -> Path:
    return Path(get_settings().backup_dir)


def _pg() -> tuple[str, dict[str, str]]:
    """libpq URL *without* the password, plus an environment carrying it (PGPASSWORD), so the
    password never shows up in process lists, job errors or Telegram alerts."""
    import os

    url = make_url(get_settings().database_url).set(drivername="postgresql")
    env = {**os.environ, "PGPASSWORD": url.password or ""}
    return url.set(password=None).render_as_string(hide_password=False), env


def _run(cmd: list[str]) -> None:
    """Run pg_dump/pg_restore; the string "DSN" in cmd is replaced by the database URL."""
    dsn, env = _pg()
    r = subprocess.run(
        [dsn if part == "DSN" else part for part in cmd],
        capture_output=True,
        text=True,
        timeout=3600,
        env=env,
    )
    if r.returncode != 0:
        raise RuntimeError(f"{cmd[0]} failed: {r.stderr.strip()[-1500:]}")


def dump_db(day: date) -> Path:
    dest = root() / "db" / f"crayonlark-{day.isoformat()}.dump"
    dest.parent.mkdir(parents=True, exist_ok=True)
    tmp = dest.with_suffix(".tmp")
    _run(["pg_dump", "--format=custom", "--no-owner", "--no-acl", f"--file={tmp}", "DSN"])
    tmp.replace(dest)  # never leave a half-written dump with the real name
    return dest


def _manifest_path(bucket: str) -> Path:
    return root() / "objects" / bucket / ".manifest.json"


def _remote_objects(bucket: str) -> dict[str, str]:
    out: dict[str, str] = {}
    paginator = storage.client().get_paginator("list_objects_v2")
    for page in paginator.paginate(Bucket=storage.bucket(bucket)):
        for o in page.get("Contents", []):
            out[o["Key"]] = str(o.get("ETag", "")).strip('"')
    return out


def mirror_bucket(bucket: str, day: date) -> dict[str, Any]:
    """Copy new/changed objects to the mirror; move objects deleted in Garage aside."""
    base = root() / "objects" / bucket
    base.mkdir(parents=True, exist_ok=True)
    mpath = _manifest_path(bucket)
    old: dict[str, str] = json.loads(mpath.read_text()) if mpath.exists() else {}
    now = _remote_objects(bucket)
    changed = [k for k, etag in now.items() if old.get(k) != etag or not (base / k).exists()]
    for key in changed:
        storage.download(bucket, key, base / key)
    removed = [k for k in old if k not in now]
    for key in removed:
        src = base / key
        if src.exists():
            dest = root() / "objects-deleted" / day.isoformat() / bucket / key
            dest.parent.mkdir(parents=True, exist_ok=True)
            shutil.move(str(src), dest)
    mpath.write_text(json.dumps(now))
    return {"objects": len(now), "copied": changed, "removed": len(removed)}


def prune(today: date, keep_days: int) -> list[str]:
    """Delete dumps and deleted-file folders older than keep_days."""
    cutoff = today - timedelta(days=keep_days)
    gone = []
    for f in sorted((root() / "db").glob("crayonlark-*.dump")):
        if date.fromisoformat(f.stem.removeprefix("crayonlark-")) < cutoff:
            f.unlink()
            gone.append(f.name)
    for d in sorted((root() / "objects-deleted").glob("*")):
        if d.is_dir() and date.fromisoformat(d.name) < cutoff:
            shutil.rmtree(d)
            gone.append(f"objects-deleted/{d.name}")
    return gone


# --------------------------------------------------------------------------- off-site (optional)


def offsite_client() -> Any | None:
    s = get_settings()
    if not s.backup_s3_bucket:
        return None
    import boto3

    return boto3.client(
        "s3",
        endpoint_url=s.backup_s3_endpoint or None,
        region_name=s.backup_s3_region or None,
        aws_access_key_id=s.backup_s3_access_key,
        aws_secret_access_key=s.backup_s3_secret_key,
    )


def offsite(
    dump: Path, copied: dict[str, list[str]], today: date, keep_days: int
) -> dict[str, Any]:
    c = offsite_client()
    if c is None:
        return {"enabled": False}
    b = get_settings().backup_s3_bucket
    c.upload_file(str(dump), b, f"db/{dump.name}")
    n = 0
    for bucket, keys in copied.items():
        for key in keys:
            c.upload_file(str(root() / "objects" / bucket / key), b, f"objects/{bucket}/{key}")
            n += 1
    cutoff = today - timedelta(days=keep_days)
    pruned = 0
    for page in c.get_paginator("list_objects_v2").paginate(Bucket=b, Prefix="db/"):
        for o in page.get("Contents", []):
            stem = Path(o["Key"]).stem.removeprefix("crayonlark-")
            try:
                if date.fromisoformat(stem) < cutoff:
                    c.delete_object(Bucket=b, Key=o["Key"])
                    pruned += 1
            except ValueError:
                continue
    return {"enabled": True, "files": n + 1, "pruned_dumps": pruned}


# --------------------------------------------------------------------------- run / status / restore


def run(today: date | None = None) -> dict[str, Any]:
    """One nightly backup. A failure is written to last.json too (ok: false), so the admin and
    the weekly report show it; the dumps of earlier days stay untouched."""
    today = today or datetime.now(UTC).date()
    started = datetime.now(UTC)
    try:
        result = _run_backup(today, started)
    except Exception as exc:
        failed = {
            "ok": False,
            "day": today.isoformat(),
            "started_at": started.isoformat(),
            "finished_at": datetime.now(UTC).isoformat(),
            "error": f"{type(exc).__name__}: {exc}"[:500],
        }
        root().mkdir(parents=True, exist_ok=True)
        (root() / "last.json").write_text(json.dumps(failed, indent=2))
        raise
    (root() / "last.json").write_text(json.dumps(result, indent=2))
    return result


def _run_backup(today: date, started: datetime) -> dict[str, Any]:
    s = get_settings()
    dump = dump_db(today)
    buckets = {}
    copied: dict[str, list[str]] = {}
    for name in s.buckets:
        r = mirror_bucket(name, today)
        copied[name] = r.pop("copied")
        buckets[name] = {**r, "copied": len(copied[name])}
    return {
        "ok": True,
        "day": today.isoformat(),
        "started_at": started.isoformat(),
        "finished_at": datetime.now(UTC).isoformat(),
        "dump": dump.name,
        "dump_mb": round(dump.stat().st_size / 1e6, 2),
        "buckets": buckets,
        "pruned": prune(today, s.backup_retention_days),
        "offsite": offsite(dump, copied, today, s.backup_retention_days),
    }


def status() -> dict[str, Any]:
    last = root() / "last.json"
    dumps = sorted(p.name for p in (root() / "db").glob("crayonlark-*.dump"))
    return {
        "last": json.loads(last.read_text()) if last.exists() else None,
        "dumps": dumps,
        "retention_days": get_settings().backup_retention_days,
        "offsite": bool(get_settings().backup_s3_bucket),
    }


def restore(day: str) -> dict[str, Any]:
    """Replace the database with that day's dump, then put mirrored files back into Garage
    (files that are missing or differ). Destructive for the database: the CLI asks first."""
    dump = root() / "db" / f"crayonlark-{date.fromisoformat(day).isoformat()}.dump"
    if not dump.exists():
        raise FileNotFoundError(f"no dump for {day}; have: {status()['dumps']}")
    _run(["pg_restore", "--clean", "--if-exists", "--no-owner", "--no-acl", "-d", "DSN", str(dump)])
    restored = 0
    for name in get_settings().buckets:
        base = root() / "objects" / name
        if not base.exists():
            continue
        current = _remote_objects(name)
        mpath = _manifest_path(name)
        mirrored: dict[str, str] = json.loads(mpath.read_text()) if mpath.exists() else {}
        for key, etag in mirrored.items():
            path = base / key
            if path.exists() and current.get(key) != etag:
                storage.put_file(name, key, path)
                restored += 1
    return {"database": dump.name, "files_restored": restored}
