"""merge expert specialty and material integrity heads

Revision ID: 401255c76a96
Revises: b2c3d4e5f6a7, f1a2b3c4d5e6
Create Date: 2026-11-25 22:19:28.863262

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '401255c76a96'
down_revision: Union[str, Sequence[str], None] = ('b2c3d4e5f6a7', 'f1a2b3c4d5e6')
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    pass


def downgrade() -> None:
    """Downgrade schema."""
    pass
