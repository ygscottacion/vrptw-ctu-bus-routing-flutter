"""rls_alembic_version

Bật Row Level Security trên bảng `alembic_version` để xóa cảnh báo bảo mật
từ Supabase Security Advisor:
  "Table public.alembic_version is public, but RLS has not been enabled."

Không tạo policy nào → mặc định deny-all cho PostgREST/client roles.
Bảng `alembic_version` chỉ được truy cập bởi service role (backend/Alembic) nên
deny-all với client role là hành vi mong muốn.

Revision ID: 20260901_rls_alembic_version
Revises: 20260831_rls_policies_v1
Create Date: 2026-09-01
"""
from alembic import op

revision = "20260901_rls_alembic_version"
down_revision = "20260831_rls_policies_v1"
branch_labels = None
depends_on = None


def upgrade():
    # Bật RLS trên alembic_version — deny-all với PostgREST/client roles
    # Bảng này chỉ được dùng nội bộ bởi Alembic qua service_role key
    op.execute("ALTER TABLE alembic_version ENABLE ROW LEVEL SECURITY;")
    op.execute("ALTER TABLE alembic_version FORCE ROW LEVEL SECURITY;")

    # Không tạo policy → mọi client role (authenticated, anon) đều bị denied.
    # Chỉ service_role (BYPASSRLS) mới truy cập được — hành vi đúng cho bảng internal.


def downgrade():
    op.execute("ALTER TABLE alembic_version NO FORCE ROW LEVEL SECURITY;")
    op.execute("ALTER TABLE alembic_version DISABLE ROW LEVEL SECURITY;")
