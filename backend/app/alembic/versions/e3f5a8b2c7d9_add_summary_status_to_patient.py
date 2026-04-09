"""Add summary_status to patient

Revision ID: e3f5a8b2c7d9
Revises: d4f7a2b8c3e1
Create Date: 2026-04-09 12:00:00.000000

"""

import sqlalchemy as sa
from alembic import op

revision = "e3f5a8b2c7d9"
down_revision = "d4f7a2b8c3e1"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "patient",
        sa.Column("summary_status", sa.String(length=20), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("patient", "summary_status")
