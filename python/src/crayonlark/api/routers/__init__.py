"""Router registry."""

from __future__ import annotations

from fastapi import FastAPI


def register(app: FastAPI) -> None:
    from crayonlark.api.routers import (
        admin_books,
        admin_marketing,
        admin_ops,
        admin_publish,
        auth,
        oauth,
    )

    app.include_router(auth.router)
    app.include_router(admin_books.router)
    app.include_router(admin_ops.router)
    app.include_router(admin_publish.router)
    app.include_router(admin_marketing.router)
    app.include_router(oauth.router)
