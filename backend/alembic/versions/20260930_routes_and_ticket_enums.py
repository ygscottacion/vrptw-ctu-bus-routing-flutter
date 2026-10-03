"""routes_state_machine_and_enums

Revision ID: 20260930_routes_enums
Revises: 20260923_wallets
Create Date: 2026-09-30
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "20260930_routes_enums"
down_revision = "20260923_wallets"
branch_labels = None
depends_on = None


def upgrade():
    conn = op.get_bind()
    # Add missing routes columns
    conn.execute(sa.text("""
        ALTER TABLE routes ADD COLUMN IF NOT EXISTS approved_by UUID REFERENCES profiles(id) ON DELETE SET NULL;
        ALTER TABLE routes ADD COLUMN IF NOT EXISTS approved_at TIMESTAMPTZ;
        ALTER TABLE routes ADD COLUMN IF NOT EXISTS rejection_reason VARCHAR(255);
    """))

    # Add missing ticket_status enum values in Postgres
    if conn.dialect.name == "postgresql":
        conn.execute(sa.text("""
            ALTER TYPE ticket_status ADD VALUE IF NOT EXISTS 'paid_pending_route';
            ALTER TYPE ticket_status ADD VALUE IF NOT EXISTS 'refunded';
        """))


def downgrade():
    op.drop_column("routes", "rejection_reason")
    op.drop_column("routes", "approved_at")
    op.drop_column("routes", "approved_by")
