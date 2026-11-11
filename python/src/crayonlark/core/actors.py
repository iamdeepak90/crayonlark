"""Who is acting. Approval gates accept only a HumanActor.

HumanActor can only be built through the three constructors below:
- from an authenticated admin session (API),
- from the whitelisted Telegram admin chat (bot),
- from the CLI (`cli:<name>`), used by me and by `make demo`.
Agent and worker code must never construct one (enforced by tests/test_gates.py).
"""

from __future__ import annotations

from dataclasses import dataclass

from crayonlark.core.config import get_settings

_TOKEN = object()


@dataclass(frozen=True)
class Actor:
    name: str  # e.g. "system", "agent:listing"

    @property
    def is_human(self) -> bool:
        return False

    @property
    def is_autopilot(self) -> bool:
        return False


SYSTEM = Actor("system")


@dataclass(frozen=True)
class AutopilotActor(Actor):
    """The owner-enabled Autopilot (core/autopilot.py). It may pass only the niche and image-set
    gates (state_machine.AUTOPILOT_GATES), and only while Autopilot is switched on in Settings
    (checked in approvals.py). Approval 1 (Etsy) and approval 2 (KDP) always need a HumanActor."""

    @property
    def is_autopilot(self) -> bool:
        return True


AUTOPILOT = AutopilotActor("autopilot")


def agent(name: str) -> Actor:
    return Actor(f"agent:{name}")


@dataclass(frozen=True)
class HumanActor(Actor):
    _token: object = None

    def __post_init__(self) -> None:
        if self._token is not _TOKEN:
            raise PermissionError("HumanActor must be created via its from_* constructors")

    @property
    def is_human(self) -> bool:
        return True

    @classmethod
    def from_admin(cls, email: str) -> HumanActor:
        return cls(f"admin:{email}", _TOKEN)

    @classmethod
    def from_telegram(cls, chat_id: int | str) -> HumanActor:
        allowed = get_settings().telegram_admin_chat_id
        if not allowed or str(chat_id) != str(allowed):
            raise PermissionError("telegram chat is not the admin chat")
        return cls(f"telegram:{chat_id}", _TOKEN)

    @classmethod
    def from_cli(cls, name: str) -> HumanActor:
        return cls(f"cli:{name}", _TOKEN)
