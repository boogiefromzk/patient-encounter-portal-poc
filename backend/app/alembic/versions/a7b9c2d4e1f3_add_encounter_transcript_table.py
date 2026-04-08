"""Add encounter_transcript table

Revision ID: a7b9c2d4e1f3
Revises: 3f8a12c74b91
Create Date: 2026-04-08 12:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'a7b9c2d4e1f3'
down_revision = '3f8a12c74b91'
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        'encounter_transcript',
        sa.Column('id', sa.Uuid(), nullable=False),
        sa.Column('text', sa.Text(), nullable=False),
        sa.Column('encounter_date', sa.Date(), nullable=False),
        sa.Column('item_id', sa.Uuid(), nullable=False),
        sa.Column('created_by_id', sa.Uuid(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(['item_id'], ['item.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['created_by_id'], ['user.id']),
        sa.PrimaryKeyConstraint('id'),
    )


def downgrade():
    op.drop_table('encounter_transcript')
