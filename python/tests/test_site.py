"""Public website API: visibility rules, sanitising, blog approval gate, forms and spam rules."""

from __future__ import annotations

import time

import pytest
from fastapi.testclient import TestClient

from crayonlark.core import approvals, html_safe, site
from crayonlark.core.actors import SYSTEM, HumanActor
from crayonlark.core.config import get_settings
from crayonlark.core.enums import BookStatus, PostStatus
from crayonlark.core.models import BlogPost, Book, ContactMessage, Subscriber
from crayonlark.core.state_machine import GateError


def test_html_is_sanitised() -> None:
    dirty = (
        '<p onclick="x()">Hi <script>alert(1)</script><a href="javascript:evil()">x</a>'
        '<a href="https://ok.example">ok</a><img src=x onerror=y></p>'
    )
    out = html_safe.clean(dirty)
    assert "script" not in out and "onclick" not in out and "javascript" not in out
    assert "<img" not in out and 'href="https://ok.example"' in out and 'rel="noopener' in out
    assert (
        html_safe.markdown_to_html("## Hi\n\n- a\n- b")
        == "<h2>Hi</h2>\n<ul>\n<li>a</li>\n<li>b</li>\n</ul>"
    )


def test_amazon_tag(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("AMAZON_ASSOCIATES_TAG", "crayon-20")
    get_settings.cache_clear()
    try:
        assert site.amazon_link("https://www.amazon.com/dp/B0X?th=1") == (
            "https://www.amazon.com/dp/B0X?th=1&tag=crayon-20"
        )
        assert site.amazon_link("https://example.com/x") == "https://example.com/x"
    finally:
        get_settings.cache_clear()


def test_form_traps() -> None:
    now = int(time.time() * 1000)
    with pytest.raises(site.FormRejected):
        site.check_form("http://spam", now - 10_000, now)
    with pytest.raises(site.FormRejected):
        site.check_form("", now - 500, now)
    with pytest.raises(site.FormRejected):
        site.check_form("", None, now)
    site.check_form("", now - 5000, now)


@pytest.fixture
def client(db) -> TestClient:  # type: ignore[no-untyped-def]
    from crayonlark.api.main import create_app

    return TestClient(create_app())


def test_only_live_public_books_and_published_posts(db, client: TestClient) -> None:  # type: ignore[no-untyped-def]
    with db() as s:
        s.add_all(
            [
                Book(
                    title="Live Book",
                    slug="live",
                    status=BookStatus.LIVE,
                    is_public=True,
                    themes=["ocean animals"],
                    age_min=3,
                    age_max=6,
                    public_description="**Fun**",
                    ai_interior_images=True,
                ),
                Book(title="Hidden", slug="hidden", status=BookStatus.LIVE, is_public=False),
                Book(title="Draft", slug="draft", status=BookStatus.BUILDING, is_public=True),
            ]
        )
        s.add(
            BlogPost(slug="p1", title="Post", body_md="Hello", status=PostStatus.AWAITING_APPROVAL)
        )
    r = client.get("/api/public/books").json()
    assert [b["slug"] for b in r["books"]] == ["live"]
    b = r["books"][0]
    assert b["description_html"] == "<p><strong>Fun</strong></p>" and "AI tools" in b["ai_note"]
    assert client.get("/api/public/books?age=8").json()["books"] == []
    assert client.get("/api/public/books?theme=ocean-animals").json()["books"][0]["slug"] == "live"
    assert client.get("/api/public/books/hidden").status_code == 404
    assert client.get("/api/public/filters").json()["themes"][0]["slug"] == "ocean-animals"
    assert client.get("/api/public/posts").json()["posts"] == []
    assert client.get("/api/public/posts/p1").status_code == 404
    with db() as s:
        post = s.query(BlogPost).one()
        with pytest.raises(GateError):
            approvals.decide_post(s, post, True, SYSTEM)
        approvals.decide_post(s, post, True, HumanActor.from_cli("test"))
    assert client.get("/api/public/posts/p1").json()["html"] == "<p>Hello</p>"
    assert client.get("/api/public/media/../secret.jpg").status_code == 404


def test_double_opt_in_and_contact(db, client: TestClient) -> None:  # type: ignore[no-untyped-def]
    started = int(time.time() * 1000) - 5000
    r = client.post(
        "/api/public/subscribe",
        json={"email": "Parent@Example.com", "website": "", "started_at": started},
    )
    assert r.status_code == 200
    bot = client.post(
        "/api/public/subscribe",
        json={"email": "bot@example.com", "website": "x", "started_at": started},
    )
    assert bot.status_code == 200 and bot.json() == r.json()  # bots get the same answer
    with db() as s:
        subs = s.query(Subscriber).all()
        assert [x.email for x in subs] == ["parent@example.com"] and subs[0].status == "pending"
        token = subs[0].token
    assert client.get(f"/api/public/download?token={token}").status_code == 404  # not confirmed
    assert client.get("/api/public/confirm?token=nope").status_code == 400
    c = client.get(f"/api/public/confirm?token={token}").json()
    assert c["download_url"].endswith(token)
    client.get(f"/api/public/unsubscribe?token={token}")
    with db() as s:
        assert s.query(Subscriber).one().status == "unsubscribed"

    msg = {
        "name": "Sam",
        "email": "sam@example.com",
        "message": "Hello!",
        "website": "",
        "started_at": started,
    }
    assert client.post("/api/public/contact", json=msg).status_code == 200
    assert client.post("/api/public/contact", json={**msg, "website": "spam"}).status_code == 200
    for _ in range(4):
        client.post("/api/public/contact", json=msg)
    assert client.post("/api/public/contact", json=msg).status_code == 429
    with db() as s:
        assert s.query(ContactMessage).count() == 5
