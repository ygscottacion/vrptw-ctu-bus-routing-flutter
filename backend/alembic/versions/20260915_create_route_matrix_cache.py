"""create route_matrix_cache table

Cache kết quả khoảng cách/thời gian giữa các cặp tọa độ từ Google Routes API
(hoặc OSRM) để giảm chi phí gọi API, tránh rate-limit và tăng tốc routing.

Revision ID: 20260915_route_matrix_cache
Revises: 20260904_fix_profiles_role
Create Date: 2026-09-15
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "20260915_route_matrix_cache"
down_revision = "20260904_fix_profiles_role"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "route_matrix_cache",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column("cache_key", sa.String(255), nullable=False),
        sa.Column("origin_lat", sa.Numeric(10, 7), nullable=False),
        sa.Column("origin_lng", sa.Numeric(10, 7), nullable=False),
        sa.Column("dest_lat", sa.Numeric(10, 7), nullable=False),
        sa.Column("dest_lng", sa.Numeric(10, 7), nullable=False),
        sa.Column(
            "travel_mode",
            sa.String(50),
            nullable=False,
            server_default="DRIVE",
        ),
        sa.Column("distance_km", sa.Float(), nullable=False),
        sa.Column("duration_mins", sa.Float(), nullable=False),
        sa.Column(
            "provider",
            sa.String(50),
            nullable=False,
            server_default="GOOGLE_ROUTES",
        ),
        sa.Column("raw_response", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column(
            "expires_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now() + interval '30 days'"),
        ),
    )

    op.create_index(
        "idx_cache_key",
        "route_matrix_cache",
        ["cache_key"],
        unique=True,
    )
    op.create_index(
        "idx_origin_dest",
        "route_matrix_cache",
        ["origin_lat", "origin_lng", "dest_lat", "dest_lng"],
        unique=False,
    )

    op.create_check_constraint(
        "ck_route_matrix_cache_origin_lat",
        "route_matrix_cache",
        "origin_lat >= -90 AND origin_lat <= 90",
    )
    op.create_check_constraint(
        "ck_route_matrix_cache_origin_lng",
        "route_matrix_cache",
        "origin_lng >= -180 AND origin_lng <= 180",
    )
    op.create_check_constraint(
        "ck_route_matrix_cache_dest_lat",
        "route_matrix_cache",
        "dest_lat >= -90 AND dest_lat <= 90",
    )
    op.create_check_constraint(
        "ck_route_matrix_cache_dest_lng",
        "route_matrix_cache",
        "dest_lng >= -180 AND dest_lng <= 180",
    )
    op.create_check_constraint(
        "ck_route_matrix_cache_distance_nonnegative",
        "route_matrix_cache",
        "distance_km >= 0",
    )
    op.create_check_constraint(
        "ck_route_matrix_cache_duration_nonnegative",
        "route_matrix_cache",
        "duration_mins >= 0",
    )

    # Deny-all phía PostgREST: chỉ backend/service_role được đọc-ghi cache.
    op.execute("ALTER TABLE route_matrix_cache ENABLE ROW LEVEL SECURITY;")
    op.execute("ALTER TABLE route_matrix_cache FORCE ROW LEVEL SECURITY;")
    op.execute('REVOKE ALL ON TABLE "route_matrix_cache" FROM anon;')
    op.execute('REVOKE ALL ON TABLE "route_matrix_cache" FROM authenticated;')


def downgrade():
    op.execute('GRANT ALL ON TABLE "route_matrix_cache" TO anon;')
    op.execute('GRANT ALL ON TABLE "route_matrix_cache" TO authenticated;')
    op.execute("ALTER TABLE route_matrix_cache NO FORCE ROW LEVEL SECURITY;")
    op.execute("ALTER TABLE route_matrix_cache DISABLE ROW LEVEL SECURITY;")

    op.drop_constraint("ck_route_matrix_cache_duration_nonnegative", "route_matrix_cache", type_="check")
    op.drop_constraint("ck_route_matrix_cache_distance_nonnegative", "route_matrix_cache", type_="check")
    op.drop_constraint("ck_route_matrix_cache_dest_lng", "route_matrix_cache", type_="check")
    op.drop_constraint("ck_route_matrix_cache_dest_lat", "route_matrix_cache", type_="check")
    op.drop_constraint("ck_route_matrix_cache_origin_lng", "route_matrix_cache", type_="check")
    op.drop_constraint("ck_route_matrix_cache_origin_lat", "route_matrix_cache", type_="check")
    op.drop_index("idx_origin_dest", table_name="route_matrix_cache")
    op.drop_index("idx_cache_key", table_name="route_matrix_cache")
    op.drop_table("route_matrix_cache")
