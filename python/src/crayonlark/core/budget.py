"""Budget guard for every paid API call (LLM, image, search, …).

Monthly cap in INR, set in admin → Settings → Budget (setting "budget"; starts at ₹2,000 and
88 INR per USD). Each call:
    with paid_call(provider, model, agent, kind, estimate_usd) as call:
        ... do the request ...
        call.actual_usd = cost_from_usage(...)
reserve() locks the month row, refuses the call if spent + estimate would pass 100 %,
records a "reserved" cost; on exit the row becomes "committed" (actual) or "released" (error).
One Telegram warning at 80 %; at 100 % paid calls hard-stop and I'm notified.
"""

from __future__ import annotations

from collections.abc import Iterator
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from crayonlark.core import app_settings
from crayonlark.core.config import get_settings
from crayonlark.core.db import session_scope
from crayonlark.core.models import ApiCost, BudgetMonth
from crayonlark.core.notify import notify


class BudgetExceeded(RuntimeError):
    pass


@dataclass(frozen=True)
class Limits:
    cap_inr: float
    usd_inr_rate: float
    warn_ratio: float

    @property
    def cap_usd(self) -> float:
        return self.cap_inr / self.usd_inr_rate if self.usd_inr_rate > 0 else 0.0


MAX_CAP_INR = 1_000_000.0


def limits(session: Session | None = None) -> Limits:
    """The monthly cap and exchange rate from admin → Settings (built-in defaults until saved)."""
    s_ = get_settings()
    stored = app_settings.get("budget", session) or {}
    return Limits(
        cap_inr=float(stored.get("monthly_inr", s_.monthly_budget_inr)),
        usd_inr_rate=float(stored.get("usd_inr_rate", s_.usd_inr_rate)),
        warn_ratio=s_.budget_warn_ratio,
    )


def set_limits(session: Session, monthly_inr: float, usd_inr_rate: float, actor: str) -> Limits:
    """Save a new cap/rate (audited). This month's 80 %/100 % alerts are re-armed, so a raised
    cap warns again when the new 80 % is reached."""
    if not 0 <= monthly_inr <= MAX_CAP_INR:
        raise ValueError(f"monthly budget must be between ₹0 and ₹{MAX_CAP_INR:,.0f}")
    if not 1 <= usd_inr_rate <= 1000:
        raise ValueError("INR per USD must be between 1 and 1000")
    value = {"monthly_inr": round(monthly_inr, 2), "usd_inr_rate": round(usd_inr_rate, 4)}
    app_settings.set_value("budget", value, actor, session)
    row = session.get(BudgetMonth, month_key())
    if row is not None:
        row.warned_80 = row.stopped = False
    session.flush()
    return limits(session)


def month_key(now: datetime | None = None) -> str:
    return (now or datetime.now(UTC)).astimezone(UTC).strftime("%Y-%m")


def evaluate(spent_usd: float, add_usd: float, cap_usd: float, warn_ratio: float) -> str:
    """'ok' | 'warn' | 'stop'. Pure: the core rule, unit-tested."""
    total = spent_usd + add_usd
    if cap_usd <= 0 or total > cap_usd + 1e-9:
        return "stop"
    if total >= cap_usd * warn_ratio:
        return "warn"
    return "ok"


def spent_usd(session: Session, month: str) -> float:
    total = session.scalar(
        select(func.coalesce(func.sum(ApiCost.cost_usd), 0.0)).where(
            ApiCost.month == month, ApiCost.status.in_(("reserved", "committed"))
        )
    )
    return float(total or 0.0)


def _lock_month(session: Session, month: str) -> BudgetMonth:
    row = session.scalar(select(BudgetMonth).where(BudgetMonth.month == month).with_for_update())
    if row is None:
        session.add(BudgetMonth(month=month))
        session.flush()
        row = session.scalar(
            select(BudgetMonth).where(BudgetMonth.month == month).with_for_update()
        )
    assert row is not None
    return row


def _alerts(row: BudgetMonth, state: str, spent: float, cap: float, rate: float) -> None:
    if state in ("warn", "stop") and not row.warned_80:
        row.warned_80 = True
        notify(
            f"💸 API spend at {spent / cap:.0%} of this month's cap "
            f"(₹{spent * rate:.0f} / ₹{cap * rate:.0f}).",
            kind="budget",
        )
    if state == "stop" and not row.stopped:
        row.stopped = True
        notify(
            "🛑 Monthly API budget reached. Paid calls are stopped until next month "
            "(or raise it in admin → Settings → Budget).",
            kind="budget",
        )


def reserve(
    provider: str,
    model: str,
    agent: str,
    kind: str,
    estimate_usd: float,
    book_id: int | None = None,
    job_id: str | None = None,
) -> int:
    month = month_key()
    with session_scope() as s:
        row = _lock_month(s, month)
        lim = limits(s)
        cap = lim.cap_usd
        spent = spent_usd(s, month)
        state = evaluate(spent, estimate_usd, cap, lim.warn_ratio)
        if state == "stop":
            # flags are committed when the scope exits
            _alerts(row, "stop", spent, cap, lim.usd_inr_rate)
            blocked = True
        else:
            blocked = False
            _alerts(row, state, spent + estimate_usd, cap, lim.usd_inr_rate)
            cost = ApiCost(
                month=month,
                provider=provider,
                model=model,
                agent=agent,
                kind=kind,
                status="reserved",
                cost_usd=estimate_usd,
                cost_inr=estimate_usd * lim.usd_inr_rate,
                book_id=book_id,
                job_id=job_id,
            )
            s.add(cost)
            s.flush()
            cost_id = cost.id
    if blocked:
        raise BudgetExceeded(
            f"monthly budget ₹{lim.cap_inr:.0f} reached "
            f"(spent ${spent:.2f} of ${cap:.2f}); {agent} call blocked"
        )
    return cost_id


def settle(
    reservation_id: int,
    actual_usd: float | None,
    input_tokens: int = 0,
    output_tokens: int = 0,
    images: int = 0,
    model: str | None = None,
) -> None:
    """Commit the real cost (or release it with actual_usd=None after a failed call)."""
    with session_scope() as s:
        lim = limits(s)
        cost = s.get(ApiCost, reservation_id)
        if cost is None:
            return
        if actual_usd is None:
            cost.status, cost.cost_usd, cost.cost_inr = "released", 0.0, 0.0
            return
        cost.status = "committed"
        cost.cost_usd = actual_usd
        cost.cost_inr = actual_usd * lim.usd_inr_rate
        cost.input_tokens, cost.output_tokens, cost.images = input_tokens, output_tokens, images
        if model:  # e.g. a server-side fallback model answered instead
            cost.model = model[:100]
        row = _lock_month(s, cost.month)
        spent = spent_usd(s, cost.month)
        _alerts(
            row,
            evaluate(spent, 0, lim.cap_usd, lim.warn_ratio),
            spent,
            lim.cap_usd,
            lim.usd_inr_rate,
        )


@dataclass
class PaidCall:
    reservation_id: int
    estimate_usd: float
    actual_usd: float | None = None
    input_tokens: int = 0
    output_tokens: int = 0
    images: int = 0
    model: str | None = None


@contextmanager
def paid_call(
    provider: str,
    model: str,
    agent: str,
    kind: str,
    estimate_usd: float,
    book_id: int | None = None,
    job_id: str | None = None,
) -> Iterator[PaidCall]:
    rid = reserve(provider, model, agent, kind, estimate_usd, book_id, job_id)
    call = PaidCall(rid, estimate_usd)
    try:
        yield call
    except Exception:
        settle(rid, None)
        raise
    settle(
        rid,
        call.actual_usd if call.actual_usd is not None else estimate_usd,
        call.input_tokens,
        call.output_tokens,
        call.images,
        call.model,
    )


def summary(session: Session, now: datetime | None = None) -> dict[str, Any]:
    lim = limits(session)
    month = month_key(now)
    spent = spent_usd(session, month)
    cap = lim.cap_usd
    by_agent = session.execute(
        select(ApiCost.agent, ApiCost.provider, func.sum(ApiCost.cost_usd), func.count(ApiCost.id))
        .where(ApiCost.month == month, ApiCost.status == "committed")
        .group_by(ApiCost.agent, ApiCost.provider)
    ).all()
    return {
        "month": month,
        "spent_usd": round(spent, 4),
        "spent_inr": round(spent * lim.usd_inr_rate, 2),
        "cap_inr": lim.cap_inr,
        "usd_inr_rate": lim.usd_inr_rate,
        "ratio": round(spent / cap, 4) if cap else 1.0,
        "state": evaluate(spent, 0, cap, lim.warn_ratio),
        "by_agent": [
            {"agent": a, "provider": p, "usd": round(float(u or 0), 4), "calls": n}
            for a, p, u, n in by_agent
        ],
    }
