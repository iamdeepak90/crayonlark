"""Phase 7: Etsy sales sync, KDP CSV import, weekly report, backups and restore."""

from __future__ import annotations

from datetime import UTC, date, datetime
from pathlib import Path
from typing import Any

import pytest

from crayonlark.core import sales
from crayonlark.core.config import get_settings

KDP_CSV = """Sales Period,October 2026
,
Royalty Date,Title,Author Name,ASIN/ISBN,Marketplace,Royalty Type,Transaction Type,Units Sold,Units Refunded,Net Units Sold,Avg. List Price without tax,Avg. Offer Price without tax,Avg. Delivery/Manufacturing cost,Royalty,Currency
2026-10-03,Ocean Friends Coloring Book,Crayonlark,B0TEST1234,Amazon.com,60%,Standard - Paperback,2,0,2,9.99,9.99,2.15,"4.70",USD
2026-10-03,Ocean Friends Coloring Book,Crayonlark,B0TEST1234,Amazon.com,60%,Standard - Paperback,2,0,2,9.99,9.99,2.15,"4.70",USD
2026-10-05,Ocean Friends Coloring Book,Crayonlark,B0TEST1234,Amazon.de,60%,Standard - Paperback,1,0,1,"9,99","9,99","2,10","3,89",EUR
2026-10-07,Someone Else's Book,Crayonlark,B0OTHER999,Amazon.co.uk,60%,Standard - Paperback,1,0,1,8.99,8.99,2.0,3.39,GBP
Total,,,,,,,,,,,,,,
"""  # noqa: E501


def test_parse_kdp_csv_handles_preamble_eu_numbers_and_duplicates() -> None:
    rows = sales.parse_kdp_csv(KDP_CSV.encode())
    assert len(rows) == 4
    assert rows[0]["units"] == 2 and rows[0]["revenue_cents"] == 470
    assert rows[0]["external_id"] != rows[1]["external_id"]  # identical lines kept apart
    de = rows[2]
    assert (
        de["currency"] == "EUR"
        and de["revenue_cents"] == 389
        and de["sold_on"] == date(2026, 10, 5)
    )
    # stable ids: parsing again gives the same ids
    assert [r["external_id"] for r in sales.parse_kdp_csv(KDP_CSV.encode())] == [
        r["external_id"] for r in rows
    ]


def test_parse_kdp_csv_rejects_other_files() -> None:
    with pytest.raises(ValueError):
        sales.parse_kdp_csv(b"name,email\nx,y\n")


def test_etsy_rows_money_and_ids() -> None:
    rows = sales.etsy_rows(
        [
            {
                "receipt_id": 7,
                "created_timestamp": 1_762_000_000,
                "country_iso": "US",
                "transactions": [
                    {
                        "transaction_id": 70,
                        "listing_id": 555,
                        "title": "Ocean Coloring Pages",
                        "quantity": 2,
                        "price": {"amount": 499, "divisor": 100, "currency_code": "USD"},
                    }
                ],
            }
        ]
    )
    assert rows == [
        {
            "external_id": "7:70",
            "etsy_listing_id": 555,
            "title": "Ocean Coloring Pages",
            "units": 2,
            "revenue_cents": 998,
            "currency": "USD",
            "sold_on": datetime.fromtimestamp(1_762_000_000, UTC).date(),
            "country": "US",
        }
    ]


class FakeEtsy:
    def __init__(self, receipts: list[dict[str, Any]]) -> None:
        self.receipts_data, self.calls = receipts, []

    def receipts(self, min_created: int, limit: int = 100) -> list[dict[str, Any]]:
        self.calls.append(min_created)
        return self.receipts_data


def test_sales_imports_are_idempotent_and_matched(db) -> None:  # type: ignore[no-untyped-def]
    from crayonlark.core.models import Book, EtsyListing, Listing, Sale

    with db() as s:
        book = Book(title="Ocean Friends", slug="ocean-friends", kdp_asin="b0test1234")
        s.add(book)
        s.flush()
        lst = Listing(book_id=book.id, platform="etsy", product_kind="full_pdf", title="Ocean")
        s.add(lst)
        s.flush()
        s.add(EtsyListing(listing_id=lst.id, etsy_listing_id=555))
        s.flush()
        book_id = book.id

        first = sales.import_kdp(s, KDP_CSV.encode())
        again = sales.import_kdp(s, KDP_CSV.encode())
        assert first == {"rows": 4, "added": 4, "skipped": 0}
        assert again == {"rows": 4, "added": 0, "skipped": 4}

        receipt = {
            "receipt_id": 9,
            "created_timestamp": int(datetime.now(UTC).timestamp()),
            "transactions": [
                {"transaction_id": 1, "listing_id": 555, "quantity": 1,
                 "price": {"amount": 499, "divisor": 100, "currency_code": "USD"}},
                {"transaction_id": 2, "listing_id": 999, "quantity": 1,
                 "price": {"amount": 299, "divisor": 100, "currency_code": "USD"}},
            ],
        }  # fmt: skip
        fake = FakeEtsy([receipt])
        assert sales.sync_etsy(s, client=fake) == {"seen": 2, "added": 2}  # type: ignore[arg-type]
        assert sales.sync_etsy(s, client=fake) == {"seen": 2, "added": 0}  # type: ignore[arg-type]

        matched = {(x.platform, x.external_id): x.book_id for x in s.query(Sale)}
        assert matched[("etsy", "9:1")] == book_id and matched[("etsy", "9:2")] is None
        kdp_books = {x.raw["asin"]: x.book_id for x in s.query(Sale).filter_by(platform="kdp")}
        assert kdp_books["B0TEST1234"] == book_id and kdp_books["B0OTHER999"] is None

        t = sales.totals(s, date(2026, 10, 1), date(2026, 10, 31))
        usd = next(r for r in t["by_platform"] if r["platform"] == "kdp" and r["currency"] == "USD")
        assert usd == {"platform": "kdp", "currency": "USD", "units": 4, "revenue": 9.4}


def test_weekly_report_renders(db) -> None:  # type: ignore[no-untyped-def]
    from crayonlark.reports import weekly

    with db() as s:
        text = weekly.render(weekly.collect(s))
    assert "Sales" in text and "KDP slots this week" in text and "Last backup" in text


# --------------------------------------------------------------------------- backups


@pytest.fixture
def backup_dir(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):  # type: ignore[no-untyped-def]
    monkeypatch.setenv("BACKUP_DIR", str(tmp_path / "backups"))
    get_settings.cache_clear()
    yield tmp_path / "backups"
    get_settings.cache_clear()


def test_prune_keeps_14_days(backup_dir: Path) -> None:
    from crayonlark.core import backup

    (backup_dir / "db").mkdir(parents=True)
    for d in ("2026-10-20", "2026-10-26", "2026-11-08"):
        (backup_dir / "db" / f"crayonlark-{d}.dump").write_bytes(b"x")
    (backup_dir / "objects-deleted" / "2026-10-01" / "outputs").mkdir(parents=True)
    gone = backup.prune(date(2026, 11, 9), 14)
    assert gone == ["crayonlark-2026-10-20.dump", "objects-deleted/2026-10-01"]
    assert sorted(p.name for p in (backup_dir / "db").iterdir()) == [
        "crayonlark-2026-10-26.dump",
        "crayonlark-2026-11-08.dump",
    ]


def test_backup_mirror_and_restore(db, needs_storage, backup_dir: Path) -> None:  # type: ignore[no-untyped-def]
    import shutil

    from crayonlark.core import backup, storage
    from crayonlark.core.models import Niche

    if not shutil.which("pg_dump"):
        pytest.skip("pg_dump not installed (runs in the worker image)")
    key = "backup-test/page-1.png"
    storage.put_bytes("outputs", key, b"original", "image/png")
    with db() as s:
        s.add(Niche(theme="backup", name="Kept niche"))

    day1 = backup.run(date(2026, 11, 8))
    assert day1["dump_mb"] >= 0 and (backup_dir / "objects" / "outputs" / key).exists()
    assert day1["offsite"] == {"enabled": False}
    day2 = backup.run(date(2026, 11, 9))  # nothing changed → nothing copied again
    assert day2["buckets"]["outputs"]["copied"] == 0

    # disaster: the file and the row are gone
    storage.delete("outputs", key)
    with db() as s:
        s.query(Niche).delete()
    out = backup.restore("2026-11-09")
    assert out["files_restored"] >= 1
    assert storage.get_bytes("outputs", key) == b"original"
    with db() as s:
        assert [n.name for n in s.query(Niche)] == ["Kept niche"]
    storage.delete("outputs", key)


def test_failed_backup_is_recorded(backup_dir: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    from crayonlark.core import backup
    from crayonlark.reports import weekly

    def boom(day: date) -> Path:
        raise RuntimeError("pg_dump failed: disk full")

    monkeypatch.setattr(backup, "dump_db", boom)
    with pytest.raises(RuntimeError):
        backup.run(date(2026, 11, 9))
    last = backup.status()["last"]
    assert last["ok"] is False and "disk full" in last["error"]
    assert "FAILED" in weekly.render({**_empty_report(), "backup": last})


def _empty_report() -> dict[str, Any]:
    month = {"spent_inr": 0, "cap_inr": 2000, "ratio": 0, "state": "ok"}
    slots = {"paperback_left": 2, "paperback_limit": 2, "hardcover_left": 2, "hardcover_limit": 2}
    return {
        "start": "2026-11-02", "end": "2026-11-08",
        "sales": {"by_platform": [], "by_book": []},
        "spend": {"week_usd": 0.0, "month": month},
        "waiting": {}, "niches_to_review": 0, "posts_to_review": 0, "pending_images": 0,
        "slots": slots, "pins": {"posted": 0, "failed": 0}, "new_subscribers": 0, "pipeline": {},
    }  # fmt: skip
