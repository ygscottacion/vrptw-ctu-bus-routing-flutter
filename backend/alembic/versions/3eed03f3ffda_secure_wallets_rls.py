"""secure_wallets_rls

Revision ID: 3eed03f3ffda
Revises: '24d41e7cd1e5'
Create Date: 2026-09-28 07:09:28.464501

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '3eed03f3ffda'
down_revision: Union[str, None] = '24d41e7cd1e5'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute("""
        -- 1. THU HỒI TOÀN BỘ QUYỀN CỦA CLIENT (ANON & AUTHENTICATED)
        REVOKE ALL ON wallets FROM anon, authenticated;
        REVOKE ALL ON wallet_transactions FROM anon, authenticated;

        -- 2. CHỈ CẤP LẠI QUYỀN ĐỌC (SELECT) CHO USER ĐÃ ĐĂNG NHẬP
        GRANT SELECT ON wallets TO authenticated;
        GRANT SELECT ON wallet_transactions TO authenticated;

        -- Đảm bảo Service Role (Backend) vẫn có full quyền
        GRANT ALL ON wallets TO service_role;
        GRANT ALL ON wallet_transactions TO service_role;

        -- 3. BẬT HÀNG RÀO BẢO MẬT (RLS)
        ALTER TABLE wallets ENABLE ROW LEVEL SECURITY;
        ALTER TABLE wallet_transactions ENABLE ROW LEVEL SECURITY;

        -- 4. TẠO POLICY: USER CHỈ ĐƯỢC XEM VÍ CỦA CHÍNH MÌNH
        CREATE POLICY "Users can view own wallet"
        ON wallets 
        FOR SELECT
        TO authenticated
        USING (auth.uid() = user_id);

        -- 5. TẠO POLICY: USER CHỈ ĐƯỢC XEM LỊCH SỬ GIAO DỊCH CỦA CHÍNH MÌNH
        CREATE POLICY "Users can view own transactions"
        ON wallet_transactions 
        FOR SELECT
        TO authenticated
        USING (auth.uid() = wallet_id);
    """)


def downgrade() -> None:
    pass
