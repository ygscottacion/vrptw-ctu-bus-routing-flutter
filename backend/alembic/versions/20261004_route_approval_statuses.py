"""Add route approval states to the PostgreSQL enum.

Revision ID: 20261004_route_approval_statuses
Revises: 20261004_flex_station_win
Create Date: 2026-10-04
"""
from alembic import op


revision = "20261004_route_approval_statuses"
down_revision = "20261004_flex_station_win"
branch_labels = None
depends_on = None


def upgrade():
    bind = op.get_bind()
    if bind.dialect.name == "postgresql":
        op.execute("ALTER TYPE route_status ADD VALUE IF NOT EXISTS 'approved'")
        op.execute("ALTER TYPE route_status ADD VALUE IF NOT EXISTS 'rejected'")


def downgrade():
    # PostgreSQL cannot safely remove enum values in place. Keep them so rows
    # already using approved/rejected remain readable.
    pass
