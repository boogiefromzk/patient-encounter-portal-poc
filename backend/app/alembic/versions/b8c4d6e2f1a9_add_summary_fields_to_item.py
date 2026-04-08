"""Add summary fields to item table

Revision ID: b8c4d6e2f1a9
Revises: a7b9c2d4e1f3
Create Date: 2026-04-08 13:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'b8c4d6e2f1a9'
down_revision = 'a7b9c2d4e1f3'
branch_labels = None
depends_on = None


def upgrade():
    op.add_column('item', sa.Column('summary', sa.Text(), nullable=True))
    op.add_column(
        'item',
        sa.Column('summary_updated_at', sa.DateTime(timezone=True), nullable=True),
    )


def downgrade():
    op.drop_column('item', 'summary_updated_at')
    op.drop_column('item', 'summary')
