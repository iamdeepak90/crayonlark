from __future__ import annotations

import pyotp
import pytest
from fastapi.testclient import TestClient

from crayonlark.core.auth import upsert_admin

H = {"X-Requested-With": "crayonlark"}


@pytest.fixture
def client(db) -> TestClient:  # type: ignore[no-untyped-def]
    from crayonlark.api.main import create_app

    upsert_admin("me@example.com", "correct horse battery")
    return TestClient(create_app())


def login(c: TestClient, **extra: str) -> object:
    return c.post(
        "/api/auth/login",
        json={"email": "me@example.com", "password": "correct horse battery", **extra},
    )


def test_login_required_and_csrf(client: TestClient) -> None:
    assert client.get("/api/admin/books").status_code == 401
    assert login(client).status_code == 200  # type: ignore[attr-defined]
    assert client.get("/api/admin/books").json() == []
    r = client.post("/api/admin/books", json={"title": "No header"})
    assert r.status_code == 403  # CSRF header missing
    r = client.post("/api/admin/books", json={"title": "Dino Fun"}, headers=H)
    assert r.status_code == 200 and r.json()["status"] == "niche_approved"


def test_wrong_password_and_rate_limit(client: TestClient) -> None:
    for _ in range(10):
        r = client.post("/api/auth/login", json={"email": "me@example.com", "password": "nope"})
        assert r.status_code == 401
    assert (
        client.post(
            "/api/auth/login", json={"email": "me@example.com", "password": "nope"}
        ).status_code
        == 429
    )


def test_totp_flow(client: TestClient) -> None:
    login(client)
    setup = client.post("/api/auth/totp/setup", headers=H).json()
    code = pyotp.TOTP(setup["secret"]).now()
    assert client.post("/api/auth/totp/enable", json={"code": code}, headers=H).status_code == 200
    client.post("/api/auth/logout")
    r = login(client)
    assert r.status_code == 401 and r.json()["detail"] == "totp_required"  # type: ignore[attr-defined]
    r = login(client, totp=pyotp.TOTP(setup["secret"]).now())
    assert r.status_code == 200  # type: ignore[attr-defined]


def test_single_admin_only(db) -> None:  # type: ignore[no-untyped-def]
    upsert_admin("me@example.com", "correct horse battery")
    with pytest.raises(ValueError):
        upsert_admin("other@example.com", "another long password")


def test_approvals_are_audited(client: TestClient, db) -> None:  # type: ignore[no-untyped-def]
    from crayonlark.core.models import AuditLog, Image

    login(client)
    book = client.post("/api/admin/books", json={"title": "Audit Book"}, headers=H).json()
    with db() as s:
        img = Image(book_id=book["id"], position=1, status="qa_done", original_key="a.png")
        s.add(img)
        s.flush()
        image_id = img.id
    r = client.post(f"/api/admin/images/{image_id}/decision", json={"approve": True}, headers=H)
    assert r.json()["approval"] == "approved"
    r = client.post(f"/api/admin/books/{book['id']}/approve-images", headers=H)
    assert r.status_code == 400  # needs 25 by default, and book isn't awaiting approval
    with db() as s:
        actions = [a.action for a in s.query(AuditLog).order_by(AuditLog.id)]
    assert "image.approve" in actions and "book.create" in actions
    audit = client.get("/api/admin/audit").json()
    assert audit[0]["actor"] == "admin:me@example.com"


def test_dashboard_has_slots_and_budget(client: TestClient) -> None:
    login(client)
    d = client.get("/api/admin/dashboard").json()
    assert d["kdp_slots"]["paperback_limit"] == 2
    assert d["budget"]["cap_inr"] > 0


def test_budget_is_edited_in_settings(client: TestClient) -> None:
    login(client)
    assert client.get("/api/admin/budget").json()["cap_inr"] == 2000
    r = client.put("/api/admin/budget", json={"monthly_inr": 3000, "usd_inr_rate": 90}, headers=H)
    assert r.status_code == 200 and r.json()["cap_inr"] == 3000
    assert client.get("/api/admin/dashboard").json()["budget"]["cap_inr"] == 3000
    bad = client.put("/api/admin/budget", json={"monthly_inr": -5, "usd_inr_rate": 90}, headers=H)
    assert bad.status_code == 422
    assert (
        client.put("/api/admin/settings/budget", json={"value": {}}, headers=H).status_code == 400
    )
