from __future__ import annotations

import pytest

from crayonlark.core import budget
from crayonlark.core.config import get_settings


def test_evaluate_rule() -> None:
    assert budget.evaluate(0, 1, 10, 0.8) == "ok"
    assert budget.evaluate(7, 1, 10, 0.8) == "warn"  # 80 %
    assert budget.evaluate(9.5, 0.5, 10, 0.8) == "warn"  # exactly 100 % allowed
    assert budget.evaluate(9.5, 0.6, 10, 0.8) == "stop"
    assert budget.evaluate(0, 0.01, 0, 0.8) == "stop"  # cap 0 = no paid calls


def test_month_key() -> None:
    from datetime import UTC, datetime

    assert budget.month_key(datetime(2026, 11, 30, 23, 59, tzinfo=UTC)) == "2026-11"


@pytest.fixture
def small_cap(monkeypatch: pytest.MonkeyPatch):  # type: ignore[no-untyped-def]
    get_settings.cache_clear()
    monkeypatch.setenv("MONTHLY_BUDGET_INR", "88")  # = $1.00 at 88 INR/USD
    monkeypatch.setenv("USD_INR_RATE", "88")
    yield
    get_settings.cache_clear()


def test_guard_reserves_settles_and_stops(db, small_cap) -> None:  # type: ignore[no-untyped-def]
    from crayonlark.core.models import ApiCost, BudgetMonth

    with budget.paid_call("openai", "m", "listing", "llm", 0.30) as call:
        call.actual_usd = 0.25
    with pytest.raises(RuntimeError), budget.paid_call("openai", "m", "listing", "llm", 0.30):
        raise RuntimeError("provider down")  # released, not charged
    with budget.paid_call("openai", "m", "listing", "llm", 0.6) as call:
        call.actual_usd = 0.6  # now 0.85 → warn
    with db() as s:
        assert budget.spent_usd(s, budget.month_key()) == pytest.approx(0.85)
        statuses = sorted(c.status for c in s.query(ApiCost))
        assert statuses == ["committed", "committed", "released"]
        assert s.get(BudgetMonth, budget.month_key()).warned_80
    with pytest.raises(budget.BudgetExceeded), budget.paid_call("gemini", "m", "art", "image", 0.2):
        pass
    with db() as s:
        assert s.get(BudgetMonth, budget.month_key()).stopped
        assert budget.summary(s)["state"] == "warn"
