"""book public assets (cover + preview keys for the website); drop unused preview_keys

Revision ID: adbaeb2d590d
Revises: c348f1442815
Create Date: 2026-11-08 13:20:55.569314
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "adbaeb2d590d"
down_revision = "c348f1442815"
branch_labels = None
depends_on = None

JSON = sa.JSON().with_variant(postgresql.JSONB(astext_type=sa.Text()), "postgresql")


def upgrade() -> None:
    op.add_column(
        "books",
        sa.Column("public_assets", JSON, nullable=False, server_default=sa.text("'{}'")),
    )
    op.alter_column("books", "public_assets", server_default=None)
    op.drop_column("books", "preview_keys")


def downgrade() -> None:
    op.add_column(
        "books",
        sa.Column("preview_keys", JSON, nullable=False, server_default=sa.text("'[]'")),
    )
    op.drop_column("books", "public_assets")
