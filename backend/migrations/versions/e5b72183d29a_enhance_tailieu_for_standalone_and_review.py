"""enhance TaiLieu for standalone and review

Revision ID: e5b72183d29a
Revises: d8a41f6c2b90
Create Date: 2026-11-24 22:05:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "e5b72183d29a"
down_revision: str | Sequence[str] | None = "d8a41f6c2b90"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # 1. Add columns to TaiLieu
    op.add_column("TaiLieu", sa.Column("maNhaCungCap", sa.Integer(), nullable=True))
    op.add_column("TaiLieu", sa.Column("maKhoaHoc", sa.Integer(), nullable=True))
    op.add_column("TaiLieu", sa.Column("maDanhMuc", sa.Integer(), nullable=True))
    op.add_column(
        "TaiLieu",
        sa.Column(
            "trangThaiDuyet",
            sa.String(length=50),
            nullable=False,
            server_default="APPROVED",
        ),
    )
    op.add_column(
        "TaiLieu",
        sa.Column(
            "trangThaiHienThi",
            sa.String(length=50),
            nullable=False,
            server_default="VISIBLE",
        ),
    )
    op.add_column("TaiLieu", sa.Column("lyDoTuChoi", sa.Text(), nullable=True))
    op.add_column("TaiLieu", sa.Column("maNguoiDuyet", sa.Integer(), nullable=True))
    op.add_column("TaiLieu", sa.Column("ngayDuyet", sa.DateTime(), nullable=True))
    op.add_column("TaiLieu", sa.Column("ngayCapNhat", sa.DateTime(), nullable=True))

    # 2. Add Foreign Keys to TaiLieu
    op.create_foreign_key(
        "fk_TaiLieu_maNhaCungCap",
        "TaiLieu",
        "NhaCungCapKhoaHoc",
        ["maNhaCungCap"],
        ["maNhaCungCap"],
        ondelete="SET NULL",
    )
    op.create_foreign_key(
        "fk_TaiLieu_maKhoaHoc",
        "TaiLieu",
        "KhoaHoc",
        ["maKhoaHoc"],
        ["maKhoaHoc"],
        ondelete="SET NULL",
    )
    op.create_foreign_key(
        "fk_TaiLieu_maDanhMuc",
        "TaiLieu",
        "DanhMuc",
        ["maDanhMuc"],
        ["maDanhMuc"],
        ondelete="SET NULL",
    )
    op.create_foreign_key(
        "fk_TaiLieu_maNguoiDuyet",
        "TaiLieu",
        "NguoiDung",
        ["maNguoiDuyet"],
        ["maNguoiDung"],
        ondelete="SET NULL",
    )

    # 3. Add column to DanhGiaChuyenGia
    op.add_column("DanhGiaChuyenGia", sa.Column("maTaiLieu", sa.Integer(), nullable=True))
    op.create_foreign_key(
        "fk_DanhGiaChuyenGia_maTaiLieu",
        "DanhGiaChuyenGia",
        "TaiLieu",
        ["maTaiLieu"],
        ["maTaiLieu"],
        ondelete="CASCADE",
    )

    # 4. Create Indexes for query performance
    op.create_index("ix_TaiLieu_maNhaCungCap", "TaiLieu", ["maNhaCungCap"])
    op.create_index("ix_TaiLieu_maKhoaHoc", "TaiLieu", ["maKhoaHoc"])
    op.create_index("ix_TaiLieu_maDanhMuc", "TaiLieu", ["maDanhMuc"])
    op.create_index("ix_TaiLieu_trangThaiDuyet", "TaiLieu", ["trangThaiDuyet"])
    op.create_index("ix_TaiLieu_trangThaiHienThi", "TaiLieu", ["trangThaiHienThi"])
    op.create_index("ix_DanhGiaChuyenGia_maTaiLieu", "DanhGiaChuyenGia", ["maTaiLieu"])

    # 5. Backfill existing 121 materials with their corresponding course, provider, category
    op.execute(
        sa.text(
            """
            UPDATE "TaiLieu" t
            SET "maKhoaHoc" = b."maKhoaHoc",
                "maNhaCungCap" = k."maNhaCungCap",
                "maDanhMuc" = k."maDanhMuc",
                "trangThaiDuyet" = 'APPROVED',
                "trangThaiHienThi" = 'VISIBLE',
                "ngayCapNhat" = COALESCE(t."ngayTao", NOW())
            FROM "BaiHoc" b
            JOIN "KhoaHoc" k ON b."maKhoaHoc" = k."maKhoaHoc"
            WHERE t."maBaiHoc" = b."maBaiHoc" AND t."maKhoaHoc" IS NULL;
            """
        )
    )

    # Change default for new materials to 'PENDING'
    op.alter_column(
        "TaiLieu",
        "trangThaiDuyet",
        server_default="PENDING",
    )


def downgrade() -> None:
    op.drop_index("ix_DanhGiaChuyenGia_maTaiLieu", table_name="DanhGiaChuyenGia")
    op.drop_index("ix_TaiLieu_trangThaiHienThi", table_name="TaiLieu")
    op.drop_index("ix_TaiLieu_trangThaiDuyet", table_name="TaiLieu")
    op.drop_index("ix_TaiLieu_maDanhMuc", table_name="TaiLieu")
    op.drop_index("ix_TaiLieu_maKhoaHoc", table_name="TaiLieu")
    op.drop_index("ix_TaiLieu_maNhaCungCap", table_name="TaiLieu")

    op.drop_constraint("fk_DanhGiaChuyenGia_maTaiLieu", "DanhGiaChuyenGia", type_="foreignkey")
    op.drop_column("DanhGiaChuyenGia", "maTaiLieu")

    op.drop_constraint("fk_TaiLieu_maNguoiDuyet", "TaiLieu", type_="foreignkey")
    op.drop_constraint("fk_TaiLieu_maDanhMuc", "TaiLieu", type_="foreignkey")
    op.drop_constraint("fk_TaiLieu_maKhoaHoc", "TaiLieu", type_="foreignkey")
    op.drop_constraint("fk_TaiLieu_maNhaCungCap", "TaiLieu", type_="foreignkey")

    op.drop_column("TaiLieu", "ngayCapNhat")
    op.drop_column("TaiLieu", "ngayDuyet")
    op.drop_column("TaiLieu", "maNguoiDuyet")
    op.drop_column("TaiLieu", "lyDoTuChoi")
    op.drop_column("TaiLieu", "trangThaiHienThi")
    op.drop_column("TaiLieu", "trangThaiDuyet")
    op.drop_column("TaiLieu", "maDanhMuc")
    op.drop_column("TaiLieu", "maKhoaHoc")
    op.drop_column("TaiLieu", "maNhaCungCap")
