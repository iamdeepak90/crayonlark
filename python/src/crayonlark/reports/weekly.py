"""Weekly report (Monday morning, Telegram + email): sales, spend, pipeline, what waits for me,
KDP slots, pins, subscribers and the last backup."""

from __future__ import annotations

from datetime import UTC, date, datetime, timedelta
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from crayonlark.core import backup, budget, kdp_slots, sales
from crayonlark.core.config import get_settings
from crayonlark.core.enums import ApprovalState, BookStatus, NicheStatus, PinStatus, PostStatus
from crayonlark.core.models import ApiCost, BlogPost, Book, Image, Niche, Pin, Subscriber

WAITING = {
    BookStatus.AWAITING_IMAGE_APPROVAL: "image sets to approve",
    BookStatus.AWAITING_COVER_APPROVAL: "covers to approve",
    BookStatus.AWAITING_LISTING_APPROVAL: "listings to approve",
    BookStatus.KDP_PACK_READY: "KDP packs to upload by hand",
}


def collect(session: Session, today: date | None = None) -> dict[str, Any]:
    today = today or datetime.now(UTC).date()
    start = today - timedelta(days=7)
    end = today - timedelta(days=1)
    since = datetime(start.year, start.month, start.day, tzinfo=UTC)
    week_spend = session.scalar(
        select(func.coalesce(func.sum(ApiCost.cost_usd), 0.0)).where(
            ApiCost.status == "committed", ApiCost.created_at >= since
        )
    )
    statuses = dict(
        session.execute(
            select(Book.status, func.count(Book.id))
            .where(Book.status != BookStatus.ARCHIVED)
            .group_by(Book.status)
        ).all()
    )
    pending_images = session.scalar(
        select(func.count(Image.id))
        .join(Book, Book.id == Image.book_id)
        .where(
            Image.approval == ApprovalState.PENDING,
            Image.original_key.is_not(None),
            Book.status == BookStatus.AWAITING_IMAGE_APPROVAL,
        )
    )
    pins = dict(
        session.execute(
            select(Pin.status, func.count(Pin.id))
            .where(Pin.updated_at >= since)
            .group_by(Pin.status)
        ).all()
    )
    return {
        "start": start.isoformat(),
        "end": end.isoformat(),
        "sales": sales.totals(session, start, end),
        "spend": {
            "week_usd": round(float(week_spend or 0), 2),
            "week_inr": round(float(week_spend or 0) * budget.limits(session).usd_inr_rate),
            "month": budget.summary(session),
        },
        "pipeline": {str(k): int(v) for k, v in statuses.items()},
        "waiting": {label: int(statuses.get(st, 0)) for st, label in WAITING.items()},
        "pending_images": int(pending_images or 0),
        "niches_to_review": int(
            session.scalar(select(func.count(Niche.id)).where(Niche.status == NicheStatus.PROPOSED))
            or 0
        ),
        "posts_to_review": int(
            session.scalar(
                select(func.count(BlogPost.id)).where(
                    BlogPost.status == PostStatus.AWAITING_APPROVAL
                )
            )
            or 0
        ),
        "slots": kdp_slots.summary(session),
        "pins": {
            "posted": int(pins.get(PinStatus.POSTED, 0)),
            "failed": int(pins.get(PinStatus.FAILED, 0)),
        },
        "new_subscribers": int(
            session.scalar(
                select(func.count(Subscriber.id)).where(Subscriber.confirmed_at >= since)
            )
            or 0
        ),
        "backup": (backup.status().get("last") or {}),
    }


def _money(rows: list[dict[str, Any]]) -> str:
    if not rows:
        return "none"
    return ", ".join(f"{r['units']} units · {r['revenue']:.2f} {r['currency']}" for r in rows)


def render(d: dict[str, Any]) -> str:
    by_platform = d["sales"]["by_platform"]
    etsy = [r for r in by_platform if r["platform"] == "etsy"]
    kdp = [r for r in by_platform if r["platform"] == "kdp"]
    month = d["spend"]["month"]
    lines = [
        f"📊 Crayonlark week {d['start']} → {d['end']}",
        "",
        "Sales",
        f"• Etsy: {_money(etsy)}",
        f"• KDP: {_money(kdp)} (from the last CSV you imported)",
    ]
    top = [b for b in d["sales"]["by_book"] if b["book_id"]][:3]
    for b in top:
        lines.append(f"  – {b['title']}: {b['units']} units")
    lines += [
        "",
        "AI spend",
        f"• this week ₹{d['spend']['week_inr']:.0f} (${d['spend']['week_usd']:.2f})",
        f"• this month ₹{month['spent_inr']:.0f} of ₹{month['cap_inr']:.0f} "
        f"({month['ratio']:.0%}, {month['state']})",
        "",
        "Waiting for you",
    ]
    waiting = [f"• {n} {label}" for label, n in d["waiting"].items() if n]
    if d["niches_to_review"]:
        waiting.append(f"• {d['niches_to_review']} niche ideas to review")
    if d["posts_to_review"]:
        waiting.append(f"• {d['posts_to_review']} blog posts to approve")
    if d["pending_images"]:
        waiting.append(f"• {d['pending_images']} images not yet decided")
    lines += waiting or ["• nothing 🎉"]
    s = d["slots"]
    lines += [
        "",
        f"KDP slots this week: {s['paperback_left']}/{s['paperback_limit']} paperback, "
        f"{s['hardcover_left']}/{s['hardcover_limit']} hardcover left (reset Sunday 00:00 UTC)",
        f"Pins: {d['pins']['posted']} posted, {d['pins']['failed']} failed",
        f"New confirmed subscribers: {d['new_subscribers']}",
        "Pipeline: " + (", ".join(f"{k} {v}" for k, v in sorted(d["pipeline"].items())) or "empty"),
    ]
    b = d["backup"]
    if not b:
        lines.append("Last backup: none yet ⚠️")
    elif not b.get("ok", True):
        lines.append(f"Last backup: FAILED on {b['day']} ⚠️ {b.get('error', '')}")
    else:
        lines.append(f"Last backup: {b['day']} ({b['dump_mb']} MB dump)")
    return "\n".join(lines)


def send(session: Session) -> dict[str, Any]:
    from crayonlark.core.notify import notify
    from crayonlark.integrations import smtp

    text = render(collect(session))
    s = get_settings()
    telegram = notify(text, kind="report")
    email = smtp.send(s.owner_email, "Crayonlark weekly report", text) if s.owner_email else False
    return {"telegram": telegram, "email": email, "text": text}
