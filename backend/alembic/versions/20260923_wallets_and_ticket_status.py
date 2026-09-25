"""wallets_and_ticket_status

Revision ID: 20260923_wallets
Revises: 20260904_fix_profiles_role
Create Date: 2026-09-23
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "20260923_wallets"
down_revision = "20260904_fix_profiles_role"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "wallets",
        sa.Column("user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("profiles.id", ondelete="CASCADE"), primary_key=True),
        sa.Column("balance", sa.Integer(), nullable=False, server_default="200000"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )

    op.create_table(
        "wallet_transactions",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("wallet_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("wallets.user_id", ondelete="CASCADE"), nullable=False),
        sa.Column("ticket_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("tickets.id", ondelete="SET NULL"), nullable=True),
        sa.Column("type", sa.String(50), nullable=False),
        sa.Column("amount", sa.Integer(), nullable=False),
        sa.Column("balance_after", sa.Integer(), nullable=False),
        sa.Column("reason", sa.String(255), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    op.create_index("ix_wallet_transactions_wallet_id", "wallet_transactions", ["wallet_id"])
    op.create_index("ix_wallet_transactions_ticket_id", "wallet_transactions", ["ticket_id"])
    op.create_unique_constraint("uq_wallet_transactions_ticket_refund", "wallet_transactions", ["ticket_id", "type"])


def downgrade():
    op.drop_constraint("uq_wallet_transactions_ticket_refund", "wallet_transactions", type_="unique")
    op.drop_index("ix_wallet_transactions_ticket_id", table_name="wallet_transactions")
    op.drop_index("ix_wallet_transactions_wallet_id", table_name="wallet_transactions")
    op.drop_table("wallet_transactions")
    op.drop_table("wallets")
