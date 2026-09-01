"""gps_logs_v1

Bảng lưu lịch sử vị trí GPS của tài xế, phục vụ:
- App sinh viên: vẽ vị trí hiện tại / polyline vài phút gần nhất
- Đối soát lộ trình thực tế vs route đề xuất từ VRPTW solver
- Retention 48h bằng Supabase pg_cron (chạy trong DB, không phụ thuộc Render)

Chốt cùng Duy (ownership/status check ở tầng API), Khanh (cột phục vụ map),
Nha (tên cột recorded_at, retention 48h qua pg_cron).

Revision ID: 20260902_gps_logs_v1
Revises: 20260901_merge_heads
Create Date: 2026-09-02
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "20260902_gps_logs_v1"
down_revision = "afa633d6e992"
branch_labels = None
depends_on = None

CRON_JOB_NAME = "gps_logs_retention_cleanup"


def upgrade():
    # ---- Bảng gps_logs ----
    op.create_table(
        "gps_logs",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column(
            "route_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("routes.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("latitude", sa.Double(), nullable=False),
        sa.Column("longitude", sa.Double(), nullable=False),
        sa.Column("heading", sa.REAL(), nullable=False),  # độ, 0 <= heading < 360
        sa.Column("speed", sa.REAL(), nullable=False),  # km/h
        sa.Column("accuracy", sa.REAL(), nullable=False),  # mét
        sa.Column(
            "recorded_at",
            sa.TIMESTAMP(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
    )

    # ---- Constraints kiểm tra giá trị hợp lệ ----
    op.create_check_constraint(
        "ck_gps_logs_latitude_range",
        "gps_logs",
        "latitude >= -90 AND latitude <= 90",
    )
    op.create_check_constraint(
        "ck_gps_logs_longitude_range",
        "gps_logs",
        "longitude >= -180 AND longitude <= 180",
    )
    op.create_check_constraint(
        "ck_gps_logs_heading_range",
        "gps_logs",
        "heading >= 0 AND heading < 360",
    )
    op.create_check_constraint(
        "ck_gps_logs_speed_nonnegative",
        "gps_logs",
        "speed >= 0",
    )
    op.create_check_constraint(
        "ck_gps_logs_accuracy_nonnegative",
        "gps_logs",
        "accuracy >= 0",
    )

    # ---- Index phục vụ đọc lịch sử/vị trí mới nhất theo route, và xoá nhanh theo thời gian ----
    op.create_index(
        "ix_gps_logs_route_recorded_at",
        "gps_logs",
        ["route_id", sa.text("recorded_at DESC")],
    )
    op.create_index("ix_gps_logs_recorded_at", "gps_logs", ["recorded_at"])

    # ---- RLS deny-all: mọi ghi/đọc phải qua API, không cấp policy client ----
    op.execute("ALTER TABLE gps_logs ENABLE ROW LEVEL SECURITY;")
    op.execute("ALTER TABLE gps_logs FORCE ROW LEVEL SECURITY;")
    # Không tạo policy nào cho 'authenticated' -> deny-all mặc định.

    # ---- Retention 48h qua Supabase pg_cron ----
    op.execute("CREATE EXTENSION IF NOT EXISTS pg_cron;")
    op.execute(
        f"""
        SELECT cron.schedule(
            '{CRON_JOB_NAME}',
            '0 * * * *',  -- chạy mỗi giờ
            $$DELETE FROM public.gps_logs WHERE recorded_at < now() - interval '48 hours';$$
        );
        """
    )


def downgrade():
    op.execute(f"SELECT cron.unschedule('{CRON_JOB_NAME}');")

    op.execute("ALTER TABLE gps_logs NO FORCE ROW LEVEL SECURITY;")
    op.execute("ALTER TABLE gps_logs DISABLE ROW LEVEL SECURITY;")

    op.drop_index("ix_gps_logs_recorded_at", table_name="gps_logs")
    op.drop_index("ix_gps_logs_route_recorded_at", table_name="gps_logs")

    op.drop_constraint("ck_gps_logs_accuracy_nonnegative", "gps_logs", type_="check")
    op.drop_constraint("ck_gps_logs_speed_nonnegative", "gps_logs", type_="check")
    op.drop_constraint("ck_gps_logs_heading_range", "gps_logs", type_="check")
    op.drop_constraint("ck_gps_logs_longitude_range", "gps_logs", type_="check")
    op.drop_constraint("ck_gps_logs_latitude_range", "gps_logs", type_="check")

    op.drop_table("gps_logs")