"""Cutover all primary and foreign keys to UUID, add route_jobs, idempotency_keys, bookings, incidents, and run constraints

Revision ID: 20260830_uuid_cutover
Revises: 20260829_fk_indexes
Create Date: 2026-08-30
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "20260830_uuid_cutover"
down_revision = "20260829_auth_trigger"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # 1. Enums
    op.execute("""
        DO $$
        BEGIN
            IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'route_job_status') THEN
                CREATE TYPE route_job_status AS ENUM ('queued', 'running', 'succeeded', 'failed');
            END IF;

            IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'ticket_status') THEN
                CREATE TYPE ticket_status AS ENUM ('reserved', 'assigned', 'used', 'cancelled', 'expired');
            ELSE
                ALTER TYPE ticket_status ADD VALUE IF NOT EXISTS 'reserved';
                ALTER TYPE ticket_status ADD VALUE IF NOT EXISTS 'assigned';
                ALTER TYPE ticket_status ADD VALUE IF NOT EXISTS 'cancelled';
            END IF;

            IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'route_status') THEN
                CREATE TYPE route_status AS ENUM ('pending', 'in_progress', 'completed');
            END IF;

            IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'bookingstatus') THEN
                CREATE TYPE bookingstatus AS ENUM ('confirmed', 'cancelled', 'completed');
            END IF;

            IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'incident_status') THEN
                CREATE TYPE incident_status AS ENUM ('pending', 'processing', 'resolved');
            END IF;
        END$$;
    """)

    # Drop existing tables if converting fresh staging DB to UUID safely
    op.execute("DROP TABLE IF EXISTS incidents CASCADE;")
    op.execute("DROP TABLE IF EXISTS idempotency_keys CASCADE;")
    op.execute("DROP TABLE IF EXISTS bookings CASCADE;")
    op.execute("DROP TABLE IF EXISTS route_stops CASCADE;")
    op.execute("DROP TABLE IF EXISTS tickets CASCADE;")
    op.execute("DROP TABLE IF EXISTS routes CASCADE;")
    op.execute("DROP TABLE IF EXISTS route_jobs CASCADE;")
    op.execute("DROP TABLE IF EXISTS vehicles CASCADE;")
    op.execute("DROP TABLE IF EXISTS locations CASCADE;")

    # 2. Re-create tables with UUID (In strict dependency order)
    op.create_table(
        "locations",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("name", sa.String(length=100), nullable=False),
        sa.Column("latitude", sa.Float(), nullable=False),
        sa.Column("longitude", sa.Float(), nullable=False),
        sa.Column("time_window_start", sa.DateTime(), nullable=True),
        sa.Column("time_window_end", sa.DateTime(), nullable=True),
        sa.Column("demand", sa.Integer(), server_default="1", nullable=False),
    )

    op.create_table(
        "vehicles",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("license_plate", sa.String(length=20), nullable=False, unique=True),
        sa.Column("capacity", sa.Integer(), server_default="30", nullable=False),
        sa.Column("driver_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("profiles.id", ondelete="SET NULL"), nullable=True),
    )
    op.create_index("ix_vehicles_driver_id", "vehicles", ["driver_id"])

    route_job_status = postgresql.ENUM("queued", "running", "succeeded", "failed", name="route_job_status", create_type=False)
    op.create_table(
        "route_jobs",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("service_date", sa.Date(), nullable=False, index=True),
        sa.Column("session_id", sa.String(length=50), nullable=False, index=True),
        sa.Column("trip_type", sa.String(length=50), nullable=False),
        sa.Column("depot_location_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("locations.id"), nullable=False),
        sa.Column("status", route_job_status, nullable=False, server_default="queued", index=True),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
    )
    op.execute("""
        CREATE UNIQUE INDEX ix_route_jobs_active_run ON route_jobs (service_date, session_id, trip_type)
        WHERE status IN ('queued', 'running');
    """)

    route_status = postgresql.ENUM("pending", "in_progress", "completed", name="route_status", create_type=False)
    op.create_table(
        "routes",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("route_job_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("route_jobs.id", ondelete="SET NULL"), nullable=True, index=True),
        sa.Column("service_date", sa.Date(), nullable=False, index=True),
        sa.Column("session_id", sa.String(length=50), nullable=False, index=True),
        sa.Column("trip_type", sa.String(length=50), nullable=False, index=True),
        sa.Column("vehicle_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("vehicles.id", ondelete="SET NULL"), nullable=True, index=True),
        sa.Column("status", route_status, nullable=False, server_default="pending"),
        sa.Column("total_distance", sa.Float(), server_default="0.0", nullable=False),
    )
    op.create_index("ix_routes_run", "routes", ["service_date", "session_id", "trip_type"])

    op.create_table(
        "route_stops",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("route_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("routes.id", ondelete="CASCADE"), nullable=False, index=True),
        sa.Column("location_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("locations.id", ondelete="CASCADE"), nullable=False, index=True),
        sa.Column("arrival_time", sa.DateTime(timezone=True), nullable=True),
        sa.Column("stop_order", sa.Integer(), nullable=False),
        sa.UniqueConstraint("route_id", "stop_order", name="uq_route_stops_order"),
    )

    ticket_status = postgresql.ENUM("reserved", "assigned", "used", "cancelled", "expired", name="ticket_status", create_type=False)
    op.create_table(
        "tickets",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("profiles.id", ondelete="CASCADE"), nullable=False, index=True),
        sa.Column("route_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("routes.id", ondelete="SET NULL"), nullable=True, index=True),
        sa.Column("service_date", sa.Date(), nullable=False, index=True),
        sa.Column("session_id", sa.String(length=50), nullable=False, index=True),
        sa.Column("trip_type", sa.String(length=50), nullable=False, index=True),
        sa.Column("pickup_location_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("locations.id", ondelete="CASCADE"), nullable=False, index=True),
        sa.Column("qr_code", sa.String(length=255), nullable=False, unique=True, index=True),
        sa.Column("status", ticket_status, nullable=False, server_default="reserved"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.UniqueConstraint("user_id", "service_date", "session_id", "trip_type", name="uq_tickets_user_run"),
    )
    op.create_index("ix_tickets_run_status", "tickets", ["service_date", "session_id", "trip_type", "status"])

    bookingstatus = postgresql.ENUM("confirmed", "cancelled", "completed", name="bookingstatus", create_type=False)
    op.create_table(
        "bookings",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("profiles.id", ondelete="CASCADE"), nullable=False, index=True),
        sa.Column("ticket_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("tickets.id", ondelete="CASCADE"), nullable=False, unique=True, index=True),
        sa.Column("route_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("routes.id", ondelete="SET NULL"), nullable=True, index=True),
        sa.Column("pickup_location_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("locations.id", ondelete="CASCADE"), nullable=False, index=True),
        sa.Column("schedule_time", sa.String(), nullable=True),
        sa.Column("note", sa.String(), nullable=True),
        sa.Column("status", bookingstatus, nullable=False, server_default="confirmed"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
    )

    incident_status = postgresql.ENUM("pending", "processing", "resolved", name="incident_status", create_type=False)
    op.create_table(
        "incidents",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("driver_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("profiles.id", ondelete="CASCADE"), nullable=False, index=True),
        sa.Column("vehicle_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("vehicles.id", ondelete="SET NULL"), nullable=True, index=True),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("status", incident_status, nullable=False, server_default="pending"),
        sa.Column("reported_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
    )

    op.create_table(
        "idempotency_keys",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("profiles.id", ondelete="CASCADE"), nullable=False, index=True),
        sa.Column("endpoint", sa.String(length=255), nullable=False),
        sa.Column("key", sa.String(length=255), nullable=False),
        sa.Column("request_hash", sa.String(length=255), nullable=False),
        sa.Column("response_code", sa.Integer(), nullable=False),
        sa.Column("response_body", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False, index=True),
        sa.UniqueConstraint("user_id", "endpoint", "key", name="uq_idempotency_user_endpoint_key"),
    )


def downgrade() -> None:
    op.drop_table("idempotency_keys")
    op.drop_table("incidents")
    op.drop_table("bookings")
    op.drop_table("tickets")
    op.drop_table("route_stops")
    op.drop_table("routes")
    op.drop_table("route_jobs")
    op.drop_table("vehicles")
    op.drop_table("locations")
