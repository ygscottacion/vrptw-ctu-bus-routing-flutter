"""Add daily-ticket reservation fields used by the cutoff and routing pipeline.

SUPERSEDED: these 4 columns (service_date, session_id, trip_type,
pickup_location_id) are now created directly inside
create_table("tickets", ...) in 20260830_uuid_cutover, as part of the
UUID rebuild. Kept as a no-op (instead of deleting the file) to preserve
the revision chain — deleting it would break down_revision links for
every migration after it.

Revision ID: 20260825_daily_tickets
Revises: 20260830_initial_schema_baseline
Create Date: 2026-08-25
"""

from alembic import op
import sqlalchemy as sa


revision = "20260825_daily_tickets"
down_revision = "20260830_initial_schema_baseline"
branch_labels = None
depends_on = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass