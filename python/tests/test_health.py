"""The health check must not hold on to database connections (it runs every few seconds)."""

from fastapi.testclient import TestClient

from crayonlark.api.main import create_app
from crayonlark.core.db import get_engine


def test_health_returns_db_connection_to_pool() -> None:
    client = TestClient(create_app())
    pool = get_engine().pool
    before = pool.checkedout()  # type: ignore[attr-defined]
    for _ in range(15):  # more than pool_size + max_overflow
        client.get("/api/health")
    assert pool.checkedout() == before  # type: ignore[attr-defined]
