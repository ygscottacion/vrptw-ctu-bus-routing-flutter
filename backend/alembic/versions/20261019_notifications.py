"""Persist user notifications.

Revision ID: 20261019_notifications
Revises: 20261004_route_approval_statuses
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "20261019_notifications"
down_revision = "20261004_route_approval_statuses"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "notifications",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("profiles.id", ondelete="CASCADE"), nullable=False),
        sa.Column("event_key", sa.String(160), nullable=False),
        sa.Column("type", sa.String(32), nullable=False),
        sa.Column("title", sa.String(180), nullable=False),
        sa.Column("body", sa.Text(), nullable=False),
        sa.Column("is_read", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.UniqueConstraint("user_id", "event_key", name="uq_notifications_user_event"),
    )
    op.create_index("ix_notifications_user_created", "notifications", ["user_id", "created_at"])


def downgrade():
    op.drop_index("ix_notifications_user_created", table_name="notifications")
    op.drop_table("notifications")
