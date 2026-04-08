"""Expand item description column to TEXT for medical history

Revision ID: 3f8a12c74b91
Revises: fe56fa70289e
Create Date: 2026-04-08 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '3f8a12c74b91'
down_revision = 'fe56fa70289e'
branch_labels = None
depends_on = None


def upgrade():
    op.alter_column(
        'item',
        'description',
        existing_type=sa.String(length=255),
        type_=sa.Text(),
        existing_nullable=True,
    )


def downgrade():
    op.alter_column(
        'item',
        'description',
        existing_type=sa.Text(),
        type_=sa.String(length=255),
        existing_nullable=True,
    )
