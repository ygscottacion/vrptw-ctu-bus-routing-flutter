"""revoke_excess_grants_deny_all_tables

Phát hiện qua security review T6: Supabase mặc định ALTER DEFAULT PRIVILEGES
cấp full CRUD (SELECT/INSERT/UPDATE/DELETE/TRUNCATE/REFERENCES/TRIGGER) cho
`anon` và `authenticated` trên MỌI bảng mới trong schema public — kể cả các
bảng được thiết kế deny-all (không có policy client nào).

RLS deny-all + FORCE ROW LEVEL SECURITY về lý thuyết đã chặn đủ, nhưng để
phòng thủ theo chiều sâu (defense in depth), revoke luôn quyền write nguy
hiểm khỏi anon/authenticated cho các bảng client không bao giờ nên đụng tới
trực tiếp. Việc này giảm rủi ro nếu sau này có ai vô tình thêm 1 policy
permissive mà không rà kỹ.

Áp dụng cho: bookings, route_jobs, idempotency_keys, alembic_version,
gps_logs, users (legacy).

Revision ID: 20260903_revoke_excess_grants
Revises: 20260903_rls_legacy_users
Create Date: 2026-09-03
"""
from alembic import op

revision = "20260903_revoke_excess_grants"
down_revision = "20260903_rls_legacy_users"
branch_labels = None
depends_on = None

DENY_ALL_TABLES = [
    "bookings",
    "route_jobs",
    "idempotency_keys",
    "alembic_version",
    "gps_logs",
    "users",
]


def upgrade():
    for table in DENY_ALL_TABLES:
        op.execute(f'REVOKE ALL ON TABLE "{table}" FROM anon;')
        op.execute(f'REVOKE ALL ON TABLE "{table}" FROM authenticated;')
    # service_role giữ nguyên quyền (bypass RLS, dùng bởi backend/worker).


def downgrade():
    for table in DENY_ALL_TABLES:
        op.execute(f'GRANT ALL ON TABLE "{table}" TO anon;')
        op.execute(f'GRANT ALL ON TABLE "{table}" TO authenticated;')