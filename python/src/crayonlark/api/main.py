"""FastAPI application. Only reachable on the internal Docker network (via web's /api rewrite)."""

from __future__ import annotations

from typing import Any

from fastapi import FastAPI
from fastapi.responses import JSONResponse
from sqlalchemy import text

from crayonlark import __version__
from crayonlark.core import storage
from crayonlark.core.db import get_engine
from crayonlark.core.redis import get_redis


def create_app() -> FastAPI:
    app = FastAPI(
        title="Crayonlark API",
        version=__version__,
        docs_url="/api/docs",
        openapi_url="/api/openapi.json",
        redoc_url=None,
    )

    def db_ping() -> None:
        # `with` returns the connection to the pool. Closing only the result used to leak one
        # pooled connection per health check, until the pool ran out and requests got 500s.
        with get_engine().connect() as conn:
            conn.execute(text("select 1"))

    @app.get("/api/health")
    def health() -> JSONResponse:
        checks: dict[str, Any] = {}
        for name, fn in (
            ("db", db_ping),
            ("redis", lambda: get_redis().ping()),
            ("storage", storage.ping),
        ):
            try:
                fn()
                checks[name] = "ok"
            except Exception as exc:  # health must never raise
                checks[name] = f"error: {type(exc).__name__}"
        ok = all(v == "ok" for v in checks.values())
        return JSONResponse(
            {"ok": ok, "version": __version__, "checks": checks}, status_code=200 if ok else 503
        )

    from crayonlark.api.routers import register

    register(app)
    return app


app = create_app()
