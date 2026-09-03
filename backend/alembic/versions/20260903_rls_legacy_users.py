"""enable_rls_legacy_users_table

Phát hiện qua security review T6: bảng `users` (legacy, trước UUID cutover)
không nằm trong 10 bảng migration 20260830_uuid_cutover quản lý, nên khi
fresh-install từ đầu, bảng này được tạo lại bởi migration cũ hơn mà
không có RLS -> có thể bị đọc/ghi qua PostgREST nếu có GRANT rộng trên
schema public.

Xử lý tạm thời: bật RLS deny-all (không tạo policy nào), an toàn và
không phá huỷ dữ liệu, trong lúc chờ xác nhận từ rà soát code cũ
(Khanh/Loi) xem còn module nào dùng bảng `users` hay không. Nếu xác
nhận không còn dùng, sẽ có migration riêng DROP TABLE users sau.

Revision ID: 20260903_rls_legacy_users
Revises: 20260903_fix_missing_uuid_defaults
Create Date: 2026-09-03
"""
from alembic import op

revision = "20260903_rls_legacy_users"
down_revision = "20260903_fix_uuid_defaults"
branch_labels = None
depends_on = None


def upgrade():
    op.execute("ALTER TABLE users ENABLE ROW LEVEL SECURITY;")
    op.execute("ALTER TABLE users FORCE ROW LEVEL SECURITY;")
    # Không tạo policy nào -> deny-all cho mọi client role.


def downgrade():
    op.execute("ALTER TABLE users NO FORCE ROW LEVEL SECURITY;")
    op.execute("ALTER TABLE users DISABLE ROW LEVEL SECURITY;")