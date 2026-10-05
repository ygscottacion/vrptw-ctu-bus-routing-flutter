"""Persist generated flexible time windows and driving duration.

Revision ID: 20261004_flex_station_win
Revises: 20261002_active_ticket_run
Create Date: 2026-10-04
"""
from alembic import op
import sqlalchemy as sa


revision = "20261004_flex_station_win"
down_revision = "20261002_active_ticket_run"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("routes", sa.Column("driving_duration_minutes", sa.Float(), nullable=True))
    op.add_column("routes", sa.Column("waiting_duration_minutes", sa.Float(), nullable=True))
    op.add_column("routes", sa.Column("service_duration_minutes", sa.Float(), nullable=True))
    op.add_column("routes", sa.Column("departure_time", sa.DateTime(timezone=True), nullable=True))
    op.add_column("routes", sa.Column("estimated_school_arrival_time", sa.DateTime(timezone=True), nullable=True))
    op.add_column("route_stops", sa.Column("departure_time", sa.DateTime(timezone=True), nullable=True))
    op.add_column("route_stops", sa.Column("time_window_start", sa.DateTime(timezone=True), nullable=True))
    op.add_column("route_stops", sa.Column("time_window_end", sa.DateTime(timezone=True), nullable=True))


def downgrade():
    op.drop_column("route_stops", "time_window_end")
    op.drop_column("route_stops", "time_window_start")
    op.drop_column("route_stops", "departure_time")
    op.drop_column("routes", "estimated_school_arrival_time")
    op.drop_column("routes", "departure_time")
    op.drop_column("routes", "driving_duration_minutes")
    op.drop_column("routes", "service_duration_minutes")
    op.drop_column("routes", "waiting_duration_minutes")
