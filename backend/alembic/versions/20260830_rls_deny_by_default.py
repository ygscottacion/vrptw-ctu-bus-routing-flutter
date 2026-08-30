"""Enable Row Level Security (deny-by-default) on all business tables.

No policies are created for `anon`/`authenticated` roles at this stage —
per architecture decision, Flutter never talks to Supabase directly for
business data in the MVP; all reads/writes go through FastAPI.

IMPORTANT: this migration does NOT use `FORCE ROW LEVEL SECURITY`.
FastAPI connects to Postgres directly (via SQLAlCHEMY_DATABASE_URI) as the
`postgres` role, which is the OWNER of these tables (it ran the migrations).
By default, Postgres table owners bypass RLS unless FORCE is explicitly
set. Using FORCE here would lock the backend itself out of its own data,
since no policies exist yet. Only `anon`/`authenticated` (non-owner roles
used by direct Supabase client access) are affected by RLS as configured
below.

Revision ID: 20260830_rls_deny_by_default
Revises: 20260829_fk_indexes
Create Date: 2026-08-30
"""

from alembic import op


revision = "20260830_rls_deny_by_default"
down_revision = "20260830_uuid_cutover"
branch_labels = None
depends_on = None

TABLES = [
    "profiles",
    "tickets",
    "bookings",
    "routes",
    "route_stops",
    "vehicles",
    "incidents",
    "locations",
]


def upgrade() -> None:
    for table in TABLES:
        op.execute(f"ALTER TABLE public.{table} ENABLE ROW LEVEL SECURITY;")
        # Không dùng FORCE — xem ghi chú ở đầu file.


def downgrade() -> None:
    for table in TABLES:
        op.execute(f"ALTER TABLE public.{table} DISABLE ROW LEVEL SECURITY;")