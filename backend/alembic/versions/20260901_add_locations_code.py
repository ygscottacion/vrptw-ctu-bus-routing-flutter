"""add_locations_code

Revision ID: 20260901_add_locations_code
Revises: 20260831_rls_policies_v1
Create Date: 2026-09-01
"""
from alembic import op
import sqlalchemy as sa


revision = "20260901_add_locations_code" 
down_revision = "20260831_rls_policies_v1"
branch_labels = None
depends_on = None

def upgrade():
    # Thêm cột code, cho phép NULL trước để không vỡ dữ liệu cũ (nếu có)
    op.add_column("locations", sa.Column("code", sa.String(length=50), nullable=True))

    # Xử lý dữ liệu cũ (Staging) trước khi ép NOT NULL
    op.execute("UPDATE locations SET code = 'LOC-' || substr(id::text, 1, 8) WHERE code IS NULL;")

    # Sau khi chắc chắn không còn NULL, mới set NOT NULL + UNIQUE
    op.alter_column("locations", "code", nullable=False)
    op.create_unique_constraint("uq_locations_code", "locations", ["code"])

def downgrade():
    op.drop_constraint("uq_locations_code", "locations", type_="unique")
    op.drop_column("locations", "code")