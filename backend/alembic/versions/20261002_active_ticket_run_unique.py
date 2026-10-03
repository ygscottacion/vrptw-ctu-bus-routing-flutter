"""Allow replacement purchases after a ticket is cancelled or refunded.

Revision ID: 20261002_active_ticket_run
Revises: 3eed03f3ffda, 20260930_routes_enums
Create Date: 2026-10-02
"""
from alembic import op
import sqlalchemy as sa


revision = "20261002_active_ticket_run"
down_revision = ("3eed03f3ffda", "20260930_routes_enums")
branch_labels = None
depends_on = None


ACTIVE_TICKET_STATUSES = "'paid_pending_route', 'reserved', 'assigned', 'used'"


def upgrade():
    op.drop_constraint("uq_tickets_user_run", "tickets", type_="unique")
    op.create_index(
        "uq_tickets_user_run_active",
        "tickets",
        ["user_id", "service_date", "session_id", "trip_type"],
        unique=True,
        postgresql_where=sa.text(f"status IN ({ACTIVE_TICKET_STATUSES})"),
    )


def downgrade():
    op.drop_index("uq_tickets_user_run_active", table_name="tickets")
    op.create_unique_constraint(
        "uq_tickets_user_run",
        "tickets",
        ["user_id", "service_date", "session_id", "trip_type"],
    )
