"""add provider application table

Revision ID: c13a4e8d92bf
Revises: af69b9f42165
Create Date: 2026-11-22 00:00:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "c13a4e8d92bf"
down_revision: str | Sequence[str] | None = "af69b9f42165"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "DonXinNhaCungCap",
        sa.Column("maDon", sa.Integer(), nullable=False),
        sa.Column("maNguoiDung", sa.Integer(), nullable=False),
        sa.Column("toChuc", sa.String(length=255), nullable=False),
        sa.Column("kinhNghiem", sa.Text(), nullable=False),
        sa.Column("lyDoDangKy", sa.Text(), nullable=False),
        sa.Column("chuyenMon", sa.String(length=255), nullable=True),
        sa.Column("gioiThieu", sa.Text(), nullable=True),
        sa.Column(
            "trangThai",
            sa.String(length=50),
            server_default=sa.text("'PENDING'"),
            nullable=False,
        ),
        sa.Column("lyDoTuChoi", sa.Text(), nullable=True),
        sa.Column("ngayGui", sa.DateTime(), nullable=False),
        sa.Column("ngayXuLy", sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(
            ["maNguoiDung"],
            ["NguoiDung.maNguoiDung"],
        ),
        sa.PrimaryKeyConstraint("maDon"),
    )
    op.create_index(
        "ix_DonXinNhaCungCap_maNguoiDung",
        "DonXinNhaCungCap",
        ["maNguoiDung"],
    )
    op.create_index(
        "ix_DonXinNhaCungCap_trangThai",
        "DonXinNhaCungCap",
        ["trangThai"],
    )


def downgrade() -> None:
    op.drop_index("ix_DonXinNhaCungCap_trangThai", table_name="DonXinNhaCungCap")
    op.drop_index(
        "ix_DonXinNhaCungCap_maNguoiDung",
        table_name="DonXinNhaCungCap",
    )
    op.drop_table("DonXinNhaCungCap")
