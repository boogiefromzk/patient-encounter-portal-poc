"""Add updated_at to encounter_transcript

Revision ID: c5e3a7f9d2b6
Revises: b8c4d6e2f1a9
Create Date: 2026-04-08 18:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'c5e3a7f9d2b6'
down_revision = 'b8c4d6e2f1a9'
branch_labels = None
depends_on = None


def upgrade():
    op.add_column(
        'encounter_transcript',
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True),
    )


def downgrade():
    op.drop_column('encounter_transcript', 'updated_at')
