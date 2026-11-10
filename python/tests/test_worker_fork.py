"""Celery forks its worker processes: the parent must not open DB connections at import time,
and every child must start with a fresh pool (shared sockets broke queries in production)."""

import importlib

from celery.signals import worker_process_init

from crayonlark.core import db


def test_celery_import_does_not_open_the_database(monkeypatch) -> None:  # type: ignore[no-untyped-def]
    import crayonlark.worker.celery_app as celery_app
    from crayonlark.core.config import get_settings

    opened: list[str] = []

    def spy() -> None:  # the settings loader swallows errors, so record instead of raising
        opened.append("db")
        raise RuntimeError("no database during import")

    monkeypatch.setattr(db, "session_scope", spy)
    get_settings.cache_clear()
    try:
        importlib.reload(celery_app)
    finally:
        get_settings.cache_clear()
    assert opened == []


def test_forked_worker_gets_a_fresh_pool(monkeypatch) -> None:  # type: ignore[no-untyped-def]
    import crayonlark.worker.celery_app  # noqa: F401  (connects the signal)

    calls: list[bool] = []

    class FakeEngine:
        def dispose(self, close: bool = True) -> None:
            calls.append(close)

    monkeypatch.setattr(db, "get_engine", lambda: FakeEngine())
    worker_process_init.send(sender=None)
    # dispose(close=False): forget the parent's connections without closing its sockets
    assert calls and all(c is False for c in calls)
