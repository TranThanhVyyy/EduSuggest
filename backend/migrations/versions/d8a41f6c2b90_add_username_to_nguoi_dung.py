"""add username to NguoiDung

Revision ID: d8a41f6c2b90
Revises: c13a4e8d92bf
Create Date: 2026-11-22 01:38:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "d8a41f6c2b90"
down_revision: str | Sequence[str] | None = "c13a4e8d92bf"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "NguoiDung",
        sa.Column("tenTaiKhoan", sa.String(length=50), nullable=True),
    )
    op.execute(
        sa.text(
            'UPDATE "NguoiDung" '
            'SET "tenTaiKhoan" = \'user_\' || "maNguoiDung"::text '
            'WHERE "tenTaiKhoan" IS NULL'
        )
    )
    op.alter_column(
        "NguoiDung",
        "tenTaiKhoan",
        existing_type=sa.String(length=50),
        nullable=False,
    )
    op.create_check_constraint(
        "ck_NguoiDung_tenTaiKhoan_format",
        "NguoiDung",
        '"tenTaiKhoan" = lower(btrim("tenTaiKhoan")) '
        'AND "tenTaiKhoan" ~ \'^[a-z0-9._-]{3,50}$\'',
    )
    op.create_unique_constraint(
        "uq_NguoiDung_tenTaiKhoan",
        "NguoiDung",
        ["tenTaiKhoan"],
    )


def downgrade() -> None:
    op.drop_constraint(
        "uq_NguoiDung_tenTaiKhoan",
        "NguoiDung",
        type_="unique",
    )
    op.drop_constraint(
        "ck_NguoiDung_tenTaiKhoan_format",
        "NguoiDung",
        type_="check",
    )
    op.drop_column("NguoiDung", "tenTaiKhoan")
