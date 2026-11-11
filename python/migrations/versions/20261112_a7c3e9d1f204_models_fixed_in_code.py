"""Models, picture provider and the Etsy schedule are fixed in code now.

Removes the stored choices so the code defaults apply (providers/llm/base.py AUTO_MODELS,
providers/image/base.py image_config, core/marketing.py DAILY). Also removes the rows the old
startup seeder copied from the code defaults (updated_by = 'system'), so the current defaults
apply, e.g. the Autopilot is on unless the owner switched it off.

Revision ID: a7c3e9d1f204
Revises: 183761f5e096
Create Date: 2026-11-12
"""

from __future__ import annotations

from alembic import op

revision = "a7c3e9d1f204"
down_revision = "183761f5e096"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("DELETE FROM settings WHERE key IN ('agent_models', 'image_provider', 'etsy_daily')")
    op.execute("DELETE FROM settings WHERE updated_by = 'system'")


def downgrade() -> None:
    pass  # the code defaults apply either way
