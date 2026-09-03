"""fix_missing_uuid_defaults

Bug phát hiện qua fresh-install test (T6): migration 20260830_uuid_cutover
tạo cột id kiểu UUID cho các bảng nghiệp vụ nhưng KHÔNG set
server_default gen_random_uuid(). Ghi qua FastAPI/SQLAlchemy vẫn chạy được
vì model Python tự sinh UUID trước khi insert, nhưng ghi trực tiếp qua
Supabase client (vd seed script) sẽ lỗi:
  null value in column "id" of relation "<table>" violates not-null constraint

Áp dụng cho toàn bộ bảng nghiệp vụ tự sinh id, TRỪ `profiles`:
`profiles.id` cố ý không có default vì giá trị lấy từ `auth.users.id`
qua trigger `on_auth_user_created`, không tự sinh.

Revision ID: 20260903_fix_missing_uuid_defaults
Revises: 20260902_gps_logs_v1
Create Date: 2026-09-03
"""
from alembic import op
import sqlalchemy as sa

revision = "20260903_fix_uuid_defaults"
down_revision = "20260902_gps_logs_v1"
branch_labels = None
depends_on = None

AFFECTED_TABLES = [
    "bookings",
    "idempotency_keys",
    "incidents",
    "locations",
    "route_jobs",
    "route_stops",
    "routes",
    "tickets",
    "vehicles",
]
# profiles KHÔNG nằm trong danh sách — id lấy từ auth.users.id qua trigger.


def upgrade():
    for table in AFFECTED_TABLES:
        op.execute(
            f'ALTER TABLE "{table}" ALTER COLUMN id SET DEFAULT gen_random_uuid();'
        )


def downgrade():
    for table in AFFECTED_TABLES:
        op.execute(f'ALTER TABLE "{table}" ALTER COLUMN id DROP DEFAULT;')