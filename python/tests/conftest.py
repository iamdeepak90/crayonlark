from __future__ import annotations

import io
import os
import shutil

import numpy as np
import pytest
from PIL import Image, ImageDraw

os.environ.setdefault("ENVIRONMENT", "test")

# Integration tests use a separate database "<name>_test" on the same server.
_base_url = os.environ.get(
    "DATABASE_URL", "postgresql+psycopg://crayonlark:crayonlark@localhost:5432/crayonlark"
)
_head, _, _dbname = _base_url.rpartition("/")
TEST_DB = _dbname.split("?")[0] + "_test"
os.environ["DATABASE_URL"] = f"{_head}/{TEST_DB}"
os.environ.setdefault("REDIS_URL", "redis://localhost:6379/15")
os.environ["REDIS_URL"] = os.environ["REDIS_URL"].rsplit("/", 1)[0] + "/15"
os.environ["TELEGRAM_BOT_TOKEN"] = ""
os.environ["SMTP_HOST"] = ""

needs_tools = pytest.mark.skipif(
    not (shutil.which("potrace") and (shutil.which("magick") or shutil.which("convert"))),
    reason="ImageMagick/potrace not installed (runs in the worker image / CI)",
)


def png_bytes(img: Image.Image) -> bytes:
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()


@pytest.fixture
def line_art() -> bytes:
    """Clean coloring-page-like image: thick circle + square outlines on white."""
    img = Image.new("L", (1536, 2048), 255)
    d = ImageDraw.Draw(img)
    d.ellipse((300, 300, 1200, 1200), outline=0, width=24)
    d.rectangle((400, 1300, 1100, 1900), outline=0, width=24)
    return png_bytes(img)


@pytest.fixture
def design_png(tmp_path, line_art):  # type: ignore[no-untyped-def]
    """A 300-DPI-sized design (7.5 x 10 in)."""
    img = Image.open(io.BytesIO(line_art)).resize((2250, 3000))
    p = tmp_path / "design.png"
    img.save(p)
    return p


def gradient(w: int = 1536, h: int = 2048) -> bytes:
    arr = np.tile(np.linspace(0, 255, w, dtype=np.uint8), (h, 1))
    return png_bytes(Image.fromarray(arr, mode="L"))


def _ensure_test_db() -> bool:
    import psycopg

    admin_url = _base_url.replace("postgresql+psycopg://", "postgresql://")
    try:
        with psycopg.connect(admin_url, autocommit=True, connect_timeout=3) as conn:
            exists = conn.execute(
                "SELECT 1 FROM pg_database WHERE datname = %s", (TEST_DB,)
            ).fetchone()
            if not exists:
                conn.execute(f'CREATE DATABASE "{TEST_DB}"')
        return True
    except Exception:
        return False


@pytest.fixture(scope="session")
def _schema():  # type: ignore[no-untyped-def]
    if not _ensure_test_db():
        pytest.skip("Postgres not reachable (integration test)")
    from crayonlark.core.db import get_engine
    from crayonlark.core.models import Base

    engine = get_engine()
    Base.metadata.drop_all(engine)
    Base.metadata.create_all(engine)
    yield engine


@pytest.fixture
def db(_schema):  # type: ignore[no-untyped-def]
    """Clean tables before each integration test; yields a session factory scope."""
    from sqlalchemy import text

    from crayonlark.core.models import Base

    names = ", ".join(f'"{t.name}"' for t in Base.metadata.sorted_tables)
    with _schema.begin() as conn:
        conn.execute(text(f"TRUNCATE {names} RESTART IDENTITY CASCADE"))
    try:
        from crayonlark.core.redis import get_redis

        get_redis().flushdb()
    except Exception:
        pass
    from crayonlark.core.db import session_scope

    return session_scope


@pytest.fixture
def needs_storage():  # type: ignore[no-untyped-def]
    from crayonlark.core import storage

    try:
        storage.ping()
    except Exception:
        pytest.skip("S3 storage not reachable")
