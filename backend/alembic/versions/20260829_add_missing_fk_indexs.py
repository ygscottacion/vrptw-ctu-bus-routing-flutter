"""Add missing indexes on FK columns for common query paths (my tickets, my routes...)

Revision ID: 20260829_fk_indexes
Revises: 20260829_auth_trigger
Create Date: 2026-08-29
"""

from alembic import op


revision = "20260829_fk_indexes"
down_revision = "20260829_auth_trigger"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_index("ix_bookings_user_id", "bookings", ["user_id"])
    op.create_index("ix_bookings_route_id", "bookings", ["route_id"])
    op.create_index("ix_tickets_user_id", "tickets", ["user_id"])
    op.create_index("ix_tickets_route_id", "tickets", ["route_id"])
    op.create_index("ix_vehicles_driver_id", "vehicles", ["driver_id"])
    op.create_index("ix_incidents_driver_id", "incidents", ["driver_id"])
    op.create_index("ix_incidents_vehicle_id", "incidents", ["vehicle_id"])
    op.create_index("ix_route_stops_route_id", "route_stops", ["route_id"])
    op.create_index("ix_route_stops_location_id", "route_stops", ["location_id"])
    op.create_index("ix_routes_vehicle_id", "routes", ["vehicle_id"])


def downgrade() -> None:
    op.drop_index("ix_routes_vehicle_id", table_name="routes")
    op.drop_index("ix_route_stops_location_id", table_name="route_stops")
    op.drop_index("ix_route_stops_route_id", table_name="route_stops")
    op.drop_index("ix_incidents_vehicle_id", table_name="incidents")
    op.drop_index("ix_incidents_driver_id", table_name="incidents")
    op.drop_index("ix_vehicles_driver_id", table_name="vehicles")
    op.drop_index("ix_tickets_route_id", table_name="tickets")
    op.drop_index("ix_tickets_user_id", table_name="tickets")
    op.drop_index("ix_bookings_route_id", table_name="bookings")
    op.drop_index("ix_bookings_user_id", table_name="bookings")