"""Sales: Etsy via the official Open API (receipts → transactions) and KDP via the royalty
report I download from KDP and upload (CSV). Never scrapes Amazon or Etsy.

Both imports are idempotent: every sale has a stable external_id, unique per platform, so
re-running a sync or re-uploading the same CSV adds nothing twice.
"""

from __future__ import annotations

import csv
import io
import re
from collections import defaultdict
from datetime import UTC, date, datetime, timedelta
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from crayonlark.core.models import Book, EtsyListing, Listing, Sale
from crayonlark.integrations import etsy

# --------------------------------------------------------------------------- Etsy


def _cents(money: dict[str, Any] | None) -> tuple[int, str]:
    """Etsy Money {amount, divisor, currency_code} → (cents, currency)."""
    if not money:
        return 0, "USD"
    divisor = int(money.get("divisor") or 100)
    cents = round(int(money.get("amount") or 0) * 100 / divisor)
    return cents, str(money.get("currency_code") or "USD")[:3]


def _ts(value: Any) -> date:
    return datetime.fromtimestamp(int(value), UTC).date() if value else datetime.now(UTC).date()


def etsy_rows(receipts: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Flatten receipts into one row per transaction (pure; unit-tested)."""
    rows = []
    for rec in receipts:
        when = rec.get("created_timestamp") or rec.get("create_timestamp")
        for tx in rec.get("transactions") or []:
            qty = int(tx.get("quantity") or 1)
            unit, currency = _cents(tx.get("price"))
            rows.append(
                {
                    "external_id": f"{rec.get('receipt_id')}:{tx.get('transaction_id')}",
                    "etsy_listing_id": tx.get("listing_id"),
                    "title": str(tx.get("title") or "")[:400],
                    "units": qty,
                    "revenue_cents": unit * qty,
                    "currency": currency,
                    "sold_on": _ts(tx.get("paid_timestamp") or when),
                    "country": str(rec.get("country_iso") or "")[:40],
                }
            )
    return rows


def sync_etsy(session: Session, client: etsy.Etsy | None = None, days: int = 30) -> dict[str, int]:
    """Pull paid receipts since a little before the newest Etsy sale we have (or `days` ago)."""
    last = session.scalar(select(func.max(Sale.sold_on)).where(Sale.platform == "etsy"))
    start = (last - timedelta(days=2)) if last else (datetime.now(UTC).date() - timedelta(days))
    min_created = int(datetime(start.year, start.month, start.day, tzinfo=UTC).timestamp())
    api = client or etsy.Etsy(session)
    rows = etsy_rows(api.receipts(min_created))
    known = {
        r.etsy_listing_id: r.listing_id
        for r in session.scalars(
            select(EtsyListing).where(EtsyListing.etsy_listing_id.is_not(None))
        )
    }
    added = 0
    for row in rows:
        if session.scalar(
            select(Sale.id).where(Sale.platform == "etsy", Sale.external_id == row["external_id"])
        ):
            continue
        listing_id = known.get(row["etsy_listing_id"])
        book_id = (
            session.scalar(select(Listing.book_id).where(Listing.id == listing_id))
            if listing_id
            else None
        )
        session.add(
            Sale(
                platform="etsy",
                source="etsy_api",
                external_id=row["external_id"],
                sold_on=row["sold_on"],
                book_id=book_id,
                listing_id=listing_id,
                title=row["title"],
                marketplace=row["country"],
                units=row["units"],
                revenue_cents=row["revenue_cents"],
                currency=row["currency"],
                raw={"etsy_listing_id": row["etsy_listing_id"]},
            )
        )
        added += 1
    session.flush()
    return {"seen": len(rows), "added": added}


# --------------------------------------------------------------------------- KDP CSV

# Header names vary between KDP reports and over time; match loosely.
KDP_COLUMNS: dict[str, tuple[str, ...]] = {
    "date": ("royalty date", "order date", "date", "invoice date"),
    "title": ("title",),
    "asin": ("asin", "asin/isbn", "isbn"),
    "marketplace": ("marketplace", "store"),
    "units": ("net units sold", "units sold", "net units", "units", "quantity"),
    "royalty": ("royalty", "royalties", "earnings"),
    "currency": ("currency",),
    "type": ("transaction type", "royalty type", "format"),
}


def _norm(h: str) -> str:
    return re.sub(r"\s+", " ", h.replace("﻿", "").strip().lower())


def _find_header(rows: list[list[str]]) -> tuple[int, dict[str, int]]:
    for i, row in enumerate(rows[:30]):
        names = [_norm(c) for c in row]
        cols: dict[str, int] = {}
        for key, options in KDP_COLUMNS.items():
            for opt in options:
                if opt in names:
                    cols[key] = names.index(opt)
                    break
        if {"asin", "royalty"} <= cols.keys() and ("date" in cols):
            return i, cols
    raise ValueError(
        "could not find the KDP header row (need columns like Royalty Date, ASIN, Royalty)"
    )


def _number(text: str) -> float:
    t = re.sub(r"[^0-9.,\-]", "", text or "")
    if t.count(",") and t.count("."):
        t = t.replace(",", "")  # 1,234.56
    elif t.count(",") == 1 and len(t.split(",")[1]) == 2:
        t = t.replace(",", ".")  # 12,34 (EU)
    else:
        t = t.replace(",", "")
    return float(t) if t not in ("", "-", ".") else 0.0


def _date(text: str) -> date:
    t = text.strip()
    for fmt in ("%Y-%m-%d", "%m/%d/%Y", "%d/%m/%Y", "%Y-%m", "%b %d, %Y", "%d %b %Y", "%B %Y"):
        try:
            return datetime.strptime(t, fmt).date()
        except ValueError:
            continue
    raise ValueError(f"unknown date format: {text!r}")


def parse_kdp_csv(data: bytes) -> list[dict[str, Any]]:
    """KDP royalty report (CSV) → sale rows (pure; unit-tested)."""
    text = data.decode("utf-8-sig", errors="replace")
    try:
        dialect: Any = csv.Sniffer().sniff(text[:4096], delimiters=",;\t")
    except csv.Error:
        dialect = csv.excel
    rows = list(csv.reader(io.StringIO(text), dialect))
    start, cols = _find_header(rows)
    out: list[dict[str, Any]] = []
    seen: dict[str, int] = defaultdict(int)

    def cell(row: list[str], key: str) -> str:
        i = cols.get(key)
        return row[i].strip() if i is not None and i < len(row) else ""

    for row in rows[start + 1 :]:
        asin = cell(row, "asin")
        if not asin or not cell(row, "date"):
            continue  # blank or total lines
        try:
            sold_on = _date(cell(row, "date"))
        except ValueError:
            continue
        royalty = _number(cell(row, "royalty"))
        units = int(_number(cell(row, "units")) or 0)
        market = cell(row, "marketplace")[:40]
        currency = (cell(row, "currency") or "USD")[:3].upper()
        key = "|".join(
            [sold_on.isoformat(), asin, market, cell(row, "type"), str(units), f"{royalty:.2f}"]
        )
        seen[key] += 1  # identical lines in one report are kept apart, but stay stable
        out.append(
            {
                "external_id": f"{key}|{seen[key]}"[:200],
                "asin": asin[:20],
                "title": cell(row, "title")[:400],
                "sold_on": sold_on,
                "marketplace": market,
                "units": units,
                "revenue_cents": round(royalty * 100),
                "currency": currency,
            }
        )
    return out


def import_kdp(session: Session, data: bytes) -> dict[str, int]:
    rows = parse_kdp_csv(data)
    books = {b.kdp_asin.strip().upper(): b.id for b in session.scalars(select(Book)) if b.kdp_asin}
    added = 0
    for r in rows:
        if session.scalar(
            select(Sale.id).where(Sale.platform == "kdp", Sale.external_id == r["external_id"])
        ):
            continue
        session.add(
            Sale(
                platform="kdp",
                source="kdp_csv",
                external_id=r["external_id"],
                sold_on=r["sold_on"],
                book_id=books.get(r["asin"].upper()),
                title=r["title"],
                marketplace=r["marketplace"],
                units=r["units"],
                revenue_cents=r["revenue_cents"],
                currency=r["currency"],
                raw={"asin": r["asin"]},
            )
        )
        added += 1
    session.flush()
    return {"rows": len(rows), "added": added, "skipped": len(rows) - added}


# --------------------------------------------------------------------------- summaries


def totals(session: Session, start: date, end: date) -> dict[str, Any]:
    """Units and revenue per platform and currency, and per book, for start <= day <= end."""
    q = (
        select(Sale.platform, Sale.currency, func.sum(Sale.units), func.sum(Sale.revenue_cents))
        .where(Sale.sold_on >= start, Sale.sold_on <= end)
        .group_by(Sale.platform, Sale.currency)
    )
    by_platform = [
        {"platform": p, "currency": c, "units": int(u or 0), "revenue": round((r or 0) / 100, 2)}
        for p, c, u, r in session.execute(q)
    ]
    qb = (
        select(
            Sale.book_id,
            Book.title,
            Sale.currency,
            func.sum(Sale.units),
            func.sum(Sale.revenue_cents),
        )
        .outerjoin(Book, Book.id == Sale.book_id)
        .where(Sale.sold_on >= start, Sale.sold_on <= end)
        .group_by(Sale.book_id, Book.title, Sale.currency)
        .order_by(func.sum(Sale.units).desc())
    )
    by_book = [
        {
            "book_id": b,
            "title": t or "(not matched to a book)",
            "currency": c,
            "units": int(u or 0),
            "revenue": round((r or 0) / 100, 2),
        }
        for b, t, c, u, r in session.execute(qb)
    ]
    return {
        "start": start.isoformat(),
        "end": end.isoformat(),
        "by_platform": by_platform,
        "by_book": by_book,
    }
