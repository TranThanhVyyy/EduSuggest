"""add phase 4 marketplace commerce tables, enrollment entitlements, and pricing constraints

Revision ID: d4e5f6a7b8c9
Revises: c3d4e5f6a7b8
Create Date: 2026-11-26 19:05:00.000000

GĐ4.1 additive marketplace schema:
- 6 new tables: YeuThich, GioHang, ChiTietGioHang, DonHang, ChiTietDonHang, ThanhToan.
- KhoaHoc CHECK constraint: ck_KhoaHoc_gia_non_negative (COM-03).
- DangKyKhoaHoc upgrades:
  * UNIQUE (maNguoiDung, maKhoaHoc) (COM-02).
  * maDonHang nullable FK -> DonHang(maDonHang) ON DELETE RESTRICT.
  * nguonCapQuyen ('LEGACY' | 'FREE' | 'PURCHASE'), default 'LEGACY' (grandfathers all 150 existing rows).
  * trangThaiQuyenHoc ('ACTIVE' | 'REVOKED'), default 'ACTIVE' (preserves active access for all existing rows).
  * ngayThuHoi, lyDoThuHoi (supports refund revocation without deleting enrollment or learning history).

WARNING (Downgrade):
- Running downgrade() drops the 6 new marketplace tables and the 5 new columns on DangKyKhoaHoc.
- Any marketplace records (wishlist, cart, orders, payments, revocation audit) will be permanently lost on downgrade.
- Existing 150 DangKyKhoaHoc rows and 300 LichSuHocTap rows are preserved across downgrade.
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "d4e5f6a7b8c9"
down_revision: str | Sequence[str] | None = "c3d4e5f6a7b8"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

_UTC_NOW = sa.text("(CURRENT_TIMESTAMP AT TIME ZONE 'UTC')")


def upgrade() -> None:
    # ------------------------------------------------------------------
    # 1. YeuThich (Wishlist)
    # ------------------------------------------------------------------
    op.create_table(
        "YeuThich",
        sa.Column("maYeuThich", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column(
            "maNguoiDung",
            sa.Integer(),
            sa.ForeignKey("NguoiDung.maNguoiDung", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "maKhoaHoc",
            sa.Integer(),
            sa.ForeignKey("KhoaHoc.maKhoaHoc", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("ngayTao", sa.DateTime(), nullable=False, server_default=_UTC_NOW),
        sa.UniqueConstraint("maNguoiDung", "maKhoaHoc", name="uq_YeuThich_user_course"),
    )
    op.create_index(
        "ix_YeuThich_maNguoiDung_ngayTao",
        "YeuThich",
        ["maNguoiDung", sa.text('"ngayTao" DESC')],
    )

    # ------------------------------------------------------------------
    # 2. GioHang (Shopping Cart)
    # ------------------------------------------------------------------
    op.create_table(
        "GioHang",
        sa.Column("maGioHang", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column(
            "maNguoiDung",
            sa.Integer(),
            sa.ForeignKey("NguoiDung.maNguoiDung", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("ngayTao", sa.DateTime(), nullable=False, server_default=_UTC_NOW),
        sa.Column("ngayCapNhat", sa.DateTime(), nullable=False, server_default=_UTC_NOW),
        sa.UniqueConstraint("maNguoiDung", name="uq_GioHang_maNguoiDung"),
    )

    # ------------------------------------------------------------------
    # 3. ChiTietGioHang (Cart Items)
    # ------------------------------------------------------------------
    op.create_table(
        "ChiTietGioHang",
        sa.Column("maChiTietGioHang", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column(
            "maGioHang",
            sa.Integer(),
            sa.ForeignKey("GioHang.maGioHang", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "maKhoaHoc",
            sa.Integer(),
            sa.ForeignKey("KhoaHoc.maKhoaHoc", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("giaLucThem", sa.Numeric(12, 0), nullable=False),
        sa.Column("ngayTao", sa.DateTime(), nullable=False, server_default=_UTC_NOW),
        sa.UniqueConstraint("maGioHang", "maKhoaHoc", name="uq_ChiTietGioHang_cart_course"),
        sa.CheckConstraint('"giaLucThem" > 0', name="ck_ChiTietGioHang_giaLucThem_positive"),
    )
    op.create_index("ix_ChiTietGioHang_maGioHang", "ChiTietGioHang", ["maGioHang"])

    # ------------------------------------------------------------------
    # 4. DonHang (Orders)
    # ------------------------------------------------------------------
    op.create_table(
        "DonHang",
        sa.Column("maDonHang", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("maSoDonHang", sa.String(32), nullable=False),
        sa.Column(
            "maNguoiDung",
            sa.Integer(),
            sa.ForeignKey("NguoiDung.maNguoiDung", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column("nguonTao", sa.String(20), nullable=False),
        sa.Column("tongTien", sa.Numeric(12, 0), nullable=False),
        sa.Column(
            "donViTienTe",
            sa.String(3),
            nullable=False,
            server_default=sa.text("'VND'"),
        ),
        sa.Column(
            "trangThai",
            sa.String(20),
            nullable=False,
            server_default=sa.text("'PENDING'"),
        ),
        sa.Column("khoaChongTrung", sa.String(100), nullable=False),
        sa.Column("hanThanhToan", sa.DateTime(), nullable=False),
        sa.Column("ngayThanhToan", sa.DateTime(), nullable=True),
        sa.Column("ngayHuy", sa.DateTime(), nullable=True),
        sa.Column("ngayHoanTien", sa.DateTime(), nullable=True),
        sa.Column("lyDoHuyHoacHoan", sa.Text(), nullable=True),
        sa.Column("ngayTao", sa.DateTime(), nullable=False, server_default=_UTC_NOW),
        sa.Column("ngayCapNhat", sa.DateTime(), nullable=False, server_default=_UTC_NOW),
        sa.UniqueConstraint("maSoDonHang", name="uq_DonHang_maSoDonHang"),
        sa.UniqueConstraint("khoaChongTrung", name="uq_DonHang_khoaChongTrung"),
        sa.CheckConstraint("\"nguonTao\" IN ('CART', 'BUY_NOW')", name="ck_DonHang_nguonTao"),
        sa.CheckConstraint('"tongTien" > 0', name="ck_DonHang_tongTien_positive"),
        sa.CheckConstraint("\"donViTienTe\" = 'VND'", name="ck_DonHang_donViTienTe"),
        sa.CheckConstraint(
            "\"trangThai\" IN ('PENDING', 'PAID', 'FAILED', 'CANCELLED', 'EXPIRED', 'REFUNDED')",
            name="ck_DonHang_trangThai",
        ),
    )
    op.create_index(
        "ix_DonHang_user_created",
        "DonHang",
        ["maNguoiDung", sa.text('"ngayTao" DESC')],
    )
    op.create_index(
        "ix_DonHang_status_created",
        "DonHang",
        ["trangThai", sa.text('"ngayTao" DESC')],
    )
    op.create_index(
        "ix_DonHang_pending_expiry",
        "DonHang",
        ["hanThanhToan"],
        postgresql_where=sa.text("\"trangThai\" = 'PENDING'"),
    )

    # ------------------------------------------------------------------
    # 5. ChiTietDonHang (Order Line Items — Price & Owner Snapshots)
    # ------------------------------------------------------------------
    op.create_table(
        "ChiTietDonHang",
        sa.Column("maChiTietDonHang", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column(
            "maDonHang",
            sa.Integer(),
            sa.ForeignKey("DonHang.maDonHang", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column(
            "maKhoaHoc",
            sa.Integer(),
            sa.ForeignKey("KhoaHoc.maKhoaHoc", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column(
            "maNhaCungCap",
            sa.Integer(),
            sa.ForeignKey("NhaCungCapKhoaHoc.maNhaCungCap", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column("tieuDeSnapshot", sa.String(255), nullable=False),
        sa.Column("giaTaiThoiDiemMua", sa.Numeric(12, 0), nullable=False),
        sa.Column("ngayTao", sa.DateTime(), nullable=False, server_default=_UTC_NOW),
        sa.UniqueConstraint("maDonHang", "maKhoaHoc", name="uq_ChiTietDonHang_order_course"),
        sa.CheckConstraint('"giaTaiThoiDiemMua" > 0', name="ck_ChiTietDonHang_gia_positive"),
    )
    op.create_index(
        "ix_ChiTietDonHang_provider_created",
        "ChiTietDonHang",
        ["maNhaCungCap", sa.text('"ngayTao" DESC')],
    )
    op.create_index("ix_ChiTietDonHang_course", "ChiTietDonHang", ["maKhoaHoc"])

    # ------------------------------------------------------------------
    # 6. ThanhToan (Payment Transactions)
    # ------------------------------------------------------------------
    op.create_table(
        "ThanhToan",
        sa.Column("maThanhToan", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column(
            "maDonHang",
            sa.Integer(),
            sa.ForeignKey("DonHang.maDonHang", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column(
            "maNguoiDung",
            sa.Integer(),
            sa.ForeignKey("NguoiDung.maNguoiDung", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column("congThanhToan", sa.String(30), nullable=False),
        sa.Column("maGiaoDichNoiBo", sa.String(64), nullable=False),
        sa.Column("maGiaoDichCong", sa.String(100), nullable=True),
        sa.Column("soTien", sa.Numeric(12, 0), nullable=False),
        sa.Column(
            "donViTienTe",
            sa.String(3),
            nullable=False,
            server_default=sa.text("'VND'"),
        ),
        sa.Column(
            "trangThai",
            sa.String(20),
            nullable=False,
            server_default=sa.text("'PENDING'"),
        ),
        sa.Column("khoaChongTrung", sa.String(100), nullable=False),
        sa.Column("maPhanHoiCong", sa.String(32), nullable=True),
        sa.Column("duLieuPhanHoiAnToan", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column(
            "daXacMinhChuKy",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("false"),
        ),
        sa.Column("ngayThanhToan", sa.DateTime(), nullable=True),
        sa.Column("ngayTao", sa.DateTime(), nullable=False, server_default=_UTC_NOW),
        sa.Column("ngayCapNhat", sa.DateTime(), nullable=False, server_default=_UTC_NOW),
        sa.UniqueConstraint("maGiaoDichNoiBo", name="uq_ThanhToan_maGiaoDichNoiBo"),
        sa.UniqueConstraint("khoaChongTrung", name="uq_ThanhToan_khoaChongTrung"),
        sa.CheckConstraint(
            "\"congThanhToan\" IN ('MOCK_SANDBOX', 'VNPAY_SANDBOX')",
            name="ck_ThanhToan_congThanhToan",
        ),
        sa.CheckConstraint('"soTien" > 0', name="ck_ThanhToan_soTien_positive"),
        sa.CheckConstraint("\"donViTienTe\" = 'VND'", name="ck_ThanhToan_donViTienTe"),
        sa.CheckConstraint(
            "\"trangThai\" IN ('PENDING', 'PAID', 'FAILED', 'CANCELLED', 'EXPIRED', 'REFUNDED')",
            name="ck_ThanhToan_trangThai",
        ),
    )
    op.create_index(
        "uq_ThanhToan_maGiaoDichCong_not_null",
        "ThanhToan",
        ["maGiaoDichCong"],
        unique=True,
        postgresql_where=sa.text('"maGiaoDichCong" IS NOT NULL'),
    )
    op.create_index(
        "uq_ThanhToan_one_paid_per_order",
        "ThanhToan",
        ["maDonHang"],
        unique=True,
        postgresql_where=sa.text("\"trangThai\" = 'PAID'"),
    )
    op.create_index(
        "ix_ThanhToan_order_created",
        "ThanhToan",
        ["maDonHang", sa.text('"ngayTao" DESC')],
    )
    op.create_index(
        "ix_ThanhToan_user_created",
        "ThanhToan",
        ["maNguoiDung", sa.text('"ngayTao" DESC')],
    )

    # ------------------------------------------------------------------
    # 7. KhoaHoc pricing CHECK constraint (COM-03)
    # ------------------------------------------------------------------
    op.create_check_constraint(
        "ck_KhoaHoc_gia_non_negative",
        "KhoaHoc",
        '"gia" IS NULL OR "gia" >= 0',
    )

    # ------------------------------------------------------------------
    # 8. DangKyKhoaHoc uniqueness (COM-02) & entitlement lifecycle columns
    #    Grandfathers all existing 150 rows as LEGACY + ACTIVE, maDonHang=NULL
    # ------------------------------------------------------------------
    op.add_column(
        "DangKyKhoaHoc",
        sa.Column(
            "maDonHang",
            sa.Integer(),
            sa.ForeignKey("DonHang.maDonHang", ondelete="RESTRICT"),
            nullable=True,
        ),
    )
    op.add_column(
        "DangKyKhoaHoc",
        sa.Column(
            "nguonCapQuyen",
            sa.String(20),
            nullable=False,
            server_default=sa.text("'LEGACY'"),
        ),
    )
    op.add_column(
        "DangKyKhoaHoc",
        sa.Column(
            "trangThaiQuyenHoc",
            sa.String(20),
            nullable=False,
            server_default=sa.text("'ACTIVE'"),
        ),
    )
    op.add_column(
        "DangKyKhoaHoc",
        sa.Column("ngayThuHoi", sa.DateTime(), nullable=True),
    )
    op.add_column(
        "DangKyKhoaHoc",
        sa.Column("lyDoThuHoi", sa.Text(), nullable=True),
    )
    op.create_unique_constraint(
        "uq_DangKyKhoaHoc_user_course",
        "DangKyKhoaHoc",
        ["maNguoiDung", "maKhoaHoc"],
    )
    op.create_check_constraint(
        "ck_DangKyKhoaHoc_trangThaiQuyenHoc",
        "DangKyKhoaHoc",
        '"trangThaiQuyenHoc" IN (\'ACTIVE\', \'REVOKED\')',
    )
    op.create_check_constraint(
        "ck_DangKyKhoaHoc_nguonCapQuyen",
        "DangKyKhoaHoc",
        '"nguonCapQuyen" IN (\'LEGACY\', \'FREE\', \'PURCHASE\')',
    )
    op.create_index(
        "ix_DangKyKhoaHoc_user_status",
        "DangKyKhoaHoc",
        ["maNguoiDung", "trangThaiQuyenHoc"],
    )


def downgrade() -> None:
    # WARNING: Dropping marketplace tables permanently removes marketplace records.
    # Existing DangKyKhoaHoc rows and LichSuHocTap rows are preserved.
    op.drop_index("ix_DangKyKhoaHoc_user_status", table_name="DangKyKhoaHoc")
    op.drop_constraint("ck_DangKyKhoaHoc_nguonCapQuyen", "DangKyKhoaHoc", type_="check")
    op.drop_constraint("ck_DangKyKhoaHoc_trangThaiQuyenHoc", "DangKyKhoaHoc", type_="check")
    op.drop_constraint("uq_DangKyKhoaHoc_user_course", "DangKyKhoaHoc", type_="unique")
    op.drop_column("DangKyKhoaHoc", "lyDoThuHoi")
    op.drop_column("DangKyKhoaHoc", "ngayThuHoi")
    op.drop_column("DangKyKhoaHoc", "trangThaiQuyenHoc")
    op.drop_column("DangKyKhoaHoc", "nguonCapQuyen")
    op.drop_column("DangKyKhoaHoc", "maDonHang")

    op.drop_constraint("ck_KhoaHoc_gia_non_negative", "KhoaHoc", type_="check")

    op.drop_index("ix_ThanhToan_user_created", table_name="ThanhToan")
    op.drop_index("ix_ThanhToan_order_created", table_name="ThanhToan")
    op.drop_index("uq_ThanhToan_one_paid_per_order", table_name="ThanhToan")
    op.drop_index("uq_ThanhToan_maGiaoDichCong_not_null", table_name="ThanhToan")
    op.drop_table("ThanhToan")

    op.drop_index("ix_ChiTietDonHang_course", table_name="ChiTietDonHang")
    op.drop_index("ix_ChiTietDonHang_provider_created", table_name="ChiTietDonHang")
    op.drop_table("ChiTietDonHang")

    op.drop_index("ix_DonHang_pending_expiry", table_name="DonHang")
    op.drop_index("ix_DonHang_status_created", table_name="DonHang")
    op.drop_index("ix_DonHang_user_created", table_name="DonHang")
    op.drop_table("DonHang")

    op.drop_index("ix_ChiTietGioHang_maGioHang", table_name="ChiTietGioHang")
    op.drop_table("ChiTietGioHang")

    op.drop_table("GioHang")

    op.drop_index("ix_YeuThich_maNguoiDung_ngayTao", table_name="YeuThich")
    op.drop_table("YeuThich")
