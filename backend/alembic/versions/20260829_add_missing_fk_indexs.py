"""Add missing indexes on FK columns for common query paths (my tickets, my routes...)

Revision ID: 20260829_fk_indexes
Revises: 20260830_uuid_cutover
Create Date: 2026-08-29
"""

from alembic import op


revision = "20260829_fk_indexes"
down_revision = "20260830_uuid_cutover"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Dùng IF NOT EXISTS để tránh văng lỗi nếu uuid_cutover đã tạo sẵn index
    op.execute("CREATE INDEX IF NOT EXISTS ix_bookings_user_id ON bookings (user_id);")
    op.execute("CREATE INDEX IF NOT EXISTS ix_bookings_route_id ON bookings (route_id);")
    op.execute("CREATE INDEX IF NOT EXISTS ix_tickets_user_id ON tickets (user_id);")
    op.execute("CREATE INDEX IF NOT EXISTS ix_tickets_route_id ON tickets (route_id);")
    op.execute("CREATE INDEX IF NOT EXISTS ix_vehicles_driver_id ON vehicles (driver_id);")
    op.execute("CREATE INDEX IF NOT EXISTS ix_incidents_driver_id ON incidents (driver_id);")
    op.execute("CREATE INDEX IF NOT EXISTS ix_incidents_vehicle_id ON incidents (vehicle_id);")
    op.execute("CREATE INDEX IF NOT EXISTS ix_route_stops_route_id ON route_stops (route_id);")
    op.execute("CREATE INDEX IF NOT EXISTS ix_route_stops_location_id ON route_stops (location_id);")
    op.execute("CREATE INDEX IF NOT EXISTS ix_routes_vehicle_id ON routes (vehicle_id);")


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS ix_routes_vehicle_id;")
    op.execute("DROP INDEX IF EXISTS ix_route_stops_location_id;")
    op.execute("DROP INDEX IF EXISTS ix_route_stops_route_id;")
    op.execute("DROP INDEX IF EXISTS ix_incidents_vehicle_id;")
    op.execute("DROP INDEX IF EXISTS ix_incidents_driver_id;")
    op.execute("DROP INDEX IF EXISTS ix_vehicles_driver_id;")
    op.execute("DROP INDEX IF EXISTS ix_tickets_route_id;")
    op.execute("DROP INDEX IF EXISTS ix_tickets_user_id;")
    op.execute("DROP INDEX IF EXISTS ix_bookings_route_id;")
    op.execute("DROP INDEX IF EXISTS ix_bookings_user_id;")