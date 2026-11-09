"""Admin: sales (Etsy sync, KDP CSV import), backups and the weekly report."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from sqlalchemy import select
from sqlalchemy.orm import Session

from crayonlark.api.deps import Admin, db, require_admin
from crayonlark.core import backup, sales
from crayonlark.core.audit import record
from crayonlark.core.jobs import enqueue
from crayonlark.core.models import Sale
from crayonlark.integrations import etsy
from crayonlark.reports import weekly

router = APIRouter(prefix="/api/admin", tags=["admin-sales"])

MAX_CSV_BYTES = 10 * 1024 * 1024


@router.get("/sales")
def list_sales(
    days: int = 90, admin: Admin = Depends(require_admin), s: Session = Depends(db)
) -> dict:
    days = max(1, min(days, 3650))
    end = datetime.now(UTC).date()
    start = end - timedelta(days=days - 1)
    rows = s.scalars(
        select(Sale)
        .where(Sale.sold_on >= start)
        .order_by(Sale.sold_on.desc(), Sale.id.desc())
        .limit(300)
    )
    last_etsy = s.scalar(
        select(Sale.created_at).where(Sale.platform == "etsy").order_by(Sale.created_at.desc())
    )
    last_kdp = s.scalar(
        select(Sale.created_at).where(Sale.platform == "kdp").order_by(Sale.created_at.desc())
    )
    return {
        **sales.totals(s, start, end),
        "days": days,
        "etsy_configured": etsy.configured(),
        "last_etsy_import": last_etsy,
        "last_kdp_import": last_kdp,
        "rows": [
            {
                "id": r.id,
                "platform": r.platform,
                "sold_on": r.sold_on.isoformat(),
                "title": r.title,
                "book_id": r.book_id,
                "marketplace": r.marketplace,
                "units": r.units,
                "revenue": round(r.revenue_cents / 100, 2),
                "currency": r.currency,
            }
            for r in rows
        ],
    }


@router.post("/sales/etsy-sync")
def etsy_sync(admin: Admin = Depends(require_admin)) -> dict:
    if not etsy.configured():
        raise HTTPException(400, "Etsy keys are not set (see docs/API_KEYS.md)")
    return {"job_id": enqueue("crayonlark.sales.etsy_sync", {"days": 90}, "publish")}


@router.post("/sales/kdp-import")
async def kdp_import(
    file: UploadFile = File(...), admin: Admin = Depends(require_admin), s: Session = Depends(db)
) -> dict:
    data = await file.read()
    if len(data) > MAX_CSV_BYTES:
        raise HTTPException(400, "file larger than 10 MB")
    if (file.filename or "").lower().endswith((".xlsx", ".xls")):
        raise HTTPException(400, "save the KDP report as CSV first (File → Save as → CSV)")
    try:
        out = sales.import_kdp(s, data)
    except ValueError as exc:
        raise HTTPException(400, str(exc)) from exc
    record(s, admin.actor.name, "sales.kdp_import", "sales", file.filename or "csv", out)
    s.commit()
    return out


@router.get("/backups")
def backups(admin: Admin = Depends(require_admin)) -> dict:
    return backup.status()


@router.post("/backups/run")
def run_backup(admin: Admin = Depends(require_admin)) -> dict:
    return {"job_id": enqueue("crayonlark.backup.run", {}, "cpu-heavy")}


@router.get("/reports/weekly")
def weekly_preview(admin: Admin = Depends(require_admin), s: Session = Depends(db)) -> dict:
    data = weekly.collect(s)
    return {"text": weekly.render(data), "data": data}


@router.post("/reports/weekly/send")
def weekly_send(admin: Admin = Depends(require_admin)) -> dict:
    return {"job_id": enqueue("crayonlark.report.weekly", {}, "default")}
