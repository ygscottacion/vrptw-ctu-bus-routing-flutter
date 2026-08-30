"""Initial schema baseline — creates `users` only.

Legacy business tables (locations, vehicles, routes, route_stops, tickets)
are created directly by 20260830_uuid_cutover (UUID from the start), so
this baseline does not create them to avoid double-creation / duplicate
enum type errors.

`users` is not touched by uuid_cutover and nothing else creates it, so it
still needs an explicit baseline here.

Revision ID: 20260830_initial_schema_baseline
Revises:
Create Date: 2026-08-30
"""
from sqlalchemy.dialects import postgresql
from alembic import op
import sqlalchemy as sa


revision = "20260830_initial_schema_baseline"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("""
        DO $$
        BEGIN
            IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'userrole') THEN
                CREATE TYPE userrole AS ENUM ('admin', 'driver', 'passenger');
            END IF;
        END$$;
    """)
    
    userrole = postgresql.ENUM("admin", "driver", "passenger", name="userrole", create_type=False)
    op.create_table(
        "users",
        sa.Column("id", sa.Integer(), primary_key=True, index=True),
        sa.Column("username", sa.String(length=50), nullable=False, unique=True, index=True),
        sa.Column("password_hash", sa.String(length=255), nullable=False),
        sa.Column("role", userrole, nullable=False, server_default="passenger"),
        sa.Column("full_name", sa.String(length=100), nullable=True),
        sa.Column("phone", sa.String(length=20), nullable=True),
    )


def downgrade() -> None:
    op.drop_table("users")
    op.execute("DROP TYPE IF EXISTS userrole;")