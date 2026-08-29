"""Auth trigger: auto-create profiles row on new auth.users signup (default role passenger)

Revision ID: 20260829_auth_trigger
Revises: 20260828_profiles_baseline
Create Date: 2026-08-29
"""

from alembic import op


revision = "20260829_auth_trigger"
down_revision = "20260828_profiles_baseline"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Function chạy với quyền của người tạo (SECURITY DEFINER) vì nó cần ghi vào
    # public.profiles trong lúc auth.users đang được Supabase Auth service ghi —
    # user gọi request lúc đó chưa có quyền ghi bảng profiles trực tiếp.
    op.execute(
        """
        CREATE OR REPLACE FUNCTION public.handle_new_user()
        RETURNS trigger
        LANGUAGE plpgsql
        SECURITY DEFINER
        SET search_path = public
        AS $$
        BEGIN
            INSERT INTO public.profiles (id, role)
            VALUES (NEW.id, 'passenger')
            ON CONFLICT (id) DO NOTHING;
            RETURN NEW;
        END;
        $$;
        """
    )

    op.execute(
        """
        DROP TRIGGER IF EXISTS on_auth_user_created ON auth.users;
        CREATE TRIGGER on_auth_user_created
            AFTER INSERT ON auth.users
            FOR EACH ROW
            EXECUTE FUNCTION public.handle_new_user();
        """
    )


def downgrade() -> None:
    op.execute("DROP TRIGGER IF EXISTS on_auth_user_created ON auth.users;")
    op.execute("DROP FUNCTION IF EXISTS public.handle_new_user();")