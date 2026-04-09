"""Rename item table to patient and item_id FK to patient_id

Revision ID: d4f7a2b8c3e1
Revises: c5e3a7f9d2b6
Create Date: 2026-04-08 20:00:00.000000

"""
from alembic import op


revision = "d4f7a2b8c3e1"
down_revision = "c5e3a7f9d2b6"
branch_labels = None
depends_on = None


def upgrade():
    op.rename_table("item", "patient")

    op.execute("ALTER INDEX item_pkey RENAME TO patient_pkey")

    op.drop_constraint(
        "encounter_transcript_item_id_fkey",
        "encounter_transcript",
        type_="foreignkey",
    )
    op.alter_column("encounter_transcript", "item_id", new_column_name="patient_id")
    op.create_foreign_key(
        "encounter_transcript_patient_id_fkey",
        "encounter_transcript",
        "patient",
        ["patient_id"],
        ["id"],
        ondelete="CASCADE",
    )

    op.drop_constraint("item_owner_id_fkey", "patient", type_="foreignkey")
    op.create_foreign_key(
        "patient_owner_id_fkey",
        "patient",
        "user",
        ["owner_id"],
        ["id"],
        ondelete="CASCADE",
    )


def downgrade():
    op.drop_constraint("patient_owner_id_fkey", "patient", type_="foreignkey")
    op.create_foreign_key(
        "item_owner_id_fkey",
        "patient",
        "user",
        ["owner_id"],
        ["id"],
        ondelete="CASCADE",
    )

    op.drop_constraint(
        "encounter_transcript_patient_id_fkey",
        "encounter_transcript",
        type_="foreignkey",
    )
    op.alter_column("encounter_transcript", "patient_id", new_column_name="item_id")
    op.create_foreign_key(
        "encounter_transcript_item_id_fkey",
        "encounter_transcript",
        "patient",
        ["item_id"],
        ["id"],
        ondelete="CASCADE",
    )

    op.execute("ALTER INDEX patient_pkey RENAME TO item_pkey")

    op.rename_table("patient", "item")
