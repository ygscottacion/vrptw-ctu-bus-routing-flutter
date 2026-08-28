"""Add daily-ticket reservation fields used by the cutoff and routing pipeline.

Revision ID: 20260825_daily_tickets
Revises:
Create Date: 2026-08-25
"""

from alembic import op
import sqlalchemy as sa


revision = "20260825_daily_tickets"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("tickets", sa.Column("service_date", sa.Date(), nullable=True))
    op.add_column("tickets", sa.Column("session_id", sa.String(), nullable=True))
    op.add_column("tickets", sa.Column("trip_type", sa.String(), nullable=True))
    op.add_column("tickets", sa.Column("pickup_location_id", sa.Integer(), nullable=True))
    op.create_index("ix_tickets_service_date", "tickets", ["service_date"])
    op.create_index("ix_tickets_session_id", "tickets", ["session_id"])
    op.create_foreign_key(
        "fk_tickets_pickup_location_id_locations",
        "tickets",
        "locations",
        ["pickup_location_id"],
        ["id"],
    )


def downgrade() -> None:
    op.drop_constraint("fk_tickets_pickup_location_id_locations", "tickets", type_="foreignkey")
    op.drop_index("ix_tickets_session_id", table_name="tickets")
    op.drop_index("ix_tickets_service_date", table_name="tickets")
    op.drop_column("tickets", "pickup_location_id")
    op.drop_column("tickets", "trip_type")
    op.drop_column("tickets", "session_id")
    op.drop_column("tickets", "service_date")
