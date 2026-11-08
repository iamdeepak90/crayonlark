from __future__ import annotations

import pytest

from crayonlark.core import telegram_actions
from crayonlark.core.config import get_settings


@pytest.fixture
def admin_chat(monkeypatch: pytest.MonkeyPatch):  # type: ignore[no-untyped-def]
    get_settings.cache_clear()
    monkeypatch.setenv("TELEGRAM_ADMIN_CHAT_ID", "777")
    yield
    get_settings.cache_clear()


def test_other_chats_rejected(db, admin_chat) -> None:  # type: ignore[no-untyped-def]
    with pytest.raises(PermissionError):
        telegram_actions.handle_callback("niche:1:1", 999)


def test_niche_and_image_buttons(db, admin_chat) -> None:  # type: ignore[no-untyped-def]
    from crayonlark.core.models import AuditLog, Book, Image, Niche

    with db() as s:
        n = Niche(theme="dinos", name="Cute dinosaurs")
        b = Book(title="b", slug="b")
        s.add_all([n, b])
        s.flush()
        img = Image(book_id=b.id)
        s.add(img)
        s.flush()
        nid, iid = n.id, img.id
    assert "approved" in telegram_actions.handle_callback(f"niche:{nid}:1", 777)
    assert "Rejected" in telegram_actions.handle_callback(f"img:{iid}:0", 777)
    with db() as s:
        assert s.get(Niche, nid).status == "approved"
        assert s.get(Image, iid).approval == "rejected"
        assert {a.actor for a in s.query(AuditLog)} == {"telegram:777"}
