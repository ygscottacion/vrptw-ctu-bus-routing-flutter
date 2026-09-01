"""merge conflicting heads

Revision ID: afa633d6e992
Revises: "('20260901_add_locations_code', '20260901_rls_alembic_version')"
Create Date: 2026-09-01 09:57:40.231373

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'afa633d6e992'
down_revision: Union[str, None] = ('20260901_add_locations_code', '20260901_rls_alembic_version')
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
