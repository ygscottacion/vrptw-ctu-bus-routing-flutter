"""Create profiles table linked to auth.users (UUID)

Revision ID: 20260828_profiles_baseline
Revises: 20260825_daily_ticket_reservations
Create Date: 2026-08-28
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "20260828_profiles_baseline"
down_revision = "20260825_daily_tickets"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # 1. Tạo TYPE bằng PL/pgSQL block (chỉ tạo nếu chưa tồn tại, không bao giờ gây lỗi)
    op.execute("""
        DO $$
        BEGIN
            IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'profile_role') THEN
                CREATE TYPE profile_role AS ENUM ('admin', 'driver', 'passenger');
            END IF;
        END$$;
    """)

    # 2. Khai báo ENUM với create_type=False để SQLAlchemy KHÔNG tự động phát lệnh CREATE TYPE nữa
    profile_role = postgresql.ENUM(
        "admin", "driver", "passenger", name="profile_role", create_type=False
    )

    # 3. Tạo bảng profiles
    op.create_table(
        "profiles",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("role", profile_role, nullable=False, server_default="passenger"),
        sa.Column("full_name", sa.String(length=100), nullable=True),
        sa.Column("phone", sa.String(length=20), nullable=True),
        sa.ForeignKeyConstraint(["id"], ["auth.users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )


def downgrade() -> None:
    op.drop_table("profiles")
    postgresql.ENUM(name="profile_role").drop(op.get_bind(), checkfirst=True)