from __future__ import annotations

from pathlib import Path

from alembic import command
from alembic.config import Config

ALEMBIC_INI = Path(__file__).resolve().parents[3] / "alembic.ini"


def alembic_config() -> Config:
    cfg = Config(str(ALEMBIC_INI))
    cfg.set_main_option("script_location", str(ALEMBIC_INI.parent / "migrations"))
    return cfg


def upgrade_and_seed() -> None:
    command.upgrade(alembic_config(), "head")
    from crayonlark.core.app_settings import seed_defaults

    seed_defaults()
