"""fix_profiles_role_privilege_escalation

CRITICAL FIX: phát hiện qua T7 security re-test — student tự đổi
`profiles.role` thành `admin` thành công qua PostgREST PATCH.

Nguyên nhân: thiết kế ban đầu (T3.2) chỉ dựa vào REVOKE/GRANT cấp cột
để chặn ghi `role`, không có gì ở tầng RLS policy kiểm tra cột nào bị
sửa. Sau fresh-install reset, quyền UPDATE toàn bảng có thể bị cấp lại
cho `authenticated` (default privileges của Supabase), vô hiệu hoá
REVOKE trước đó.

Fix có 2 lớp độc lập (defense in depth), không chỉ dựa vào 1 cơ chế:
  1. REVOKE ALL + GRANT lại tường minh, đảm bảo sạch quyền UPDATE toàn
     bảng, chỉ còn UPDATE(full_name, phone).
  2. Trigger BEFORE UPDATE chặn thay đổi `role` trừ khi caller là
     service_role — hoạt động độc lập với hệ thống GRANT/REVOKE, không
     bị vô hiệu hoá nếu default privileges bị áp lại sau này.

Revision ID: 20260904_fix_profiles_role_escalation
Revises: 20260903_revoke_excess_grants
Create Date: 2026-09-04
"""
from alembic import op

revision = "20260904_fix_profiles_role"
down_revision = "20260903_revoke_excess_grants"
branch_labels = None
depends_on = None


def upgrade():
    # ---- Lớp 1: dọn sạch GRANT, đảm bảo không còn UPDATE toàn bảng ----
    op.execute("REVOKE ALL ON TABLE profiles FROM authenticated;")
    op.execute("GRANT SELECT ON TABLE profiles TO authenticated;")
    op.execute("GRANT UPDATE (full_name, phone) ON TABLE profiles TO authenticated;")

    # ---- Lớp 2: trigger chặn đổi role, độc lập với hệ thống GRANT ----
    op.execute(
        """
        CREATE OR REPLACE FUNCTION prevent_role_self_change()
        RETURNS TRIGGER AS $$
        BEGIN
            IF NEW.role IS DISTINCT FROM OLD.role
               AND current_setting('request.jwt.claim.role', true) IS DISTINCT FROM 'service_role'
            THEN
                RAISE EXCEPTION 'Not allowed to change role directly';
            END IF;
            RETURN NEW;
        END;
        $$ LANGUAGE plpgsql SECURITY DEFINER;
        """
    )
    op.execute(
        """
        CREATE TRIGGER trg_prevent_role_self_change
        BEFORE UPDATE ON profiles
        FOR EACH ROW
        EXECUTE FUNCTION prevent_role_self_change();
        """
    )


def downgrade():
    op.execute("DROP TRIGGER IF EXISTS trg_prevent_role_self_change ON profiles;")
    op.execute("DROP FUNCTION IF EXISTS prevent_role_self_change();")
    op.execute("REVOKE ALL ON TABLE profiles FROM authenticated;")
    op.execute("GRANT SELECT ON TABLE profiles TO authenticated;")
    
