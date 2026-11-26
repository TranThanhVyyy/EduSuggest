"""add phase 4.7a.2 financial integrity tables, append-only event log, durable recovery queue, and JSONB backfill

Revision ID: e5f6a7b8c9d0
Revises: d4e5f6a7b8c9
Create Date: 2026-11-26 21:05:00.000000
"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "e5f6a7b8c9d0"
down_revision = "d4e5f6a7b8c9"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # 1. Extend ThanhToan with explicit capture columns & CAPTURED_UNAPPLIED / PARTIALLY_REFUNDED statuses
    op.alter_column(
        "ThanhToan",
        "trangThai",
        existing_type=sa.String(length=20),
        type_=sa.String(length=30),
        existing_nullable=False,
    )
    op.add_column(
        "ThanhToan",
        sa.Column("daThuTien", sa.Boolean(), nullable=False, server_default=sa.text("false")),
    )
    op.add_column(
        "ThanhToan",
        sa.Column(
            "soTienDaThuThucTe",
            sa.Numeric(precision=12, scale=0),
            nullable=False,
            server_default=sa.text("0"),
        ),
    )
    op.drop_constraint("ck_ThanhToan_trangThai", "ThanhToan", type_="check")
    op.create_check_constraint(
        "ck_ThanhToan_trangThai",
        "ThanhToan",
        "\"trangThai\" IN ('PENDING', 'PAID', 'CAPTURED_UNAPPLIED', 'FAILED', 'CANCELLED', "
        "'EXPIRED', 'REFUNDED', 'PARTIALLY_REFUNDED')",
    )
    op.create_check_constraint(
        "ck_ThanhToan_soTienDaThuThucTe_non_negative",
        "ThanhToan",
        '"soTienDaThuThucTe" >= 0',
    )

    # 2. HoanTienNgoaiLe (Exception Refund Ledger)
    op.create_table(
        "HoanTienNgoaiLe",
        sa.Column("maHoanTien", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("maSoHoanTien", sa.String(length=40), nullable=False),
        sa.Column("maDonHang", sa.Integer(), sa.ForeignKey("DonHang.maDonHang", ondelete="RESTRICT"), nullable=False),
        sa.Column("maThanhToan", sa.Integer(), sa.ForeignKey("ThanhToan.maThanhToan", ondelete="RESTRICT"), nullable=False),
        sa.Column("khoaChongTrung", sa.String(length=128), nullable=False),
        sa.Column("phamViHoan", sa.String(length=30), nullable=False),
        sa.Column("loaiSuCo", sa.String(length=40), nullable=False),
        sa.Column("soTienDaThu", sa.Numeric(precision=12, scale=0), nullable=False),
        sa.Column("soTienHoan", sa.Numeric(precision=12, scale=0), nullable=False),
        sa.Column("donViTienTe", sa.String(length=3), nullable=False, server_default=sa.text("'VND'")),
        sa.Column("trangThai", sa.String(length=30), nullable=False, server_default=sa.text("'PENDING_REVIEW'")),
        sa.Column("lyDo", sa.Text(), nullable=False),
        sa.Column("ghiChuXacMinh", sa.Text(), nullable=True),
        sa.Column("maGiaoDichHoanCong", sa.String(length=100), nullable=True),
        sa.Column("maNguoiTao", sa.Integer(), sa.ForeignKey("NguoiDung.maNguoiDung", ondelete="SET NULL"), nullable=True),
        sa.Column("maNguoiXacMinh", sa.Integer(), sa.ForeignKey("NguoiDung.maNguoiDung", ondelete="SET NULL"), nullable=True),
        sa.Column("maNguoiXuLy", sa.Integer(), sa.ForeignKey("NguoiDung.maNguoiDung", ondelete="SET NULL"), nullable=True),
        sa.Column("lichSuTrangThai", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("ngayTao", sa.DateTime(), nullable=False, server_default=sa.text("(CURRENT_TIMESTAMP AT TIME ZONE 'UTC')")),
        sa.Column("ngayCapNhat", sa.DateTime(), nullable=False, server_default=sa.text("(CURRENT_TIMESTAMP AT TIME ZONE 'UTC')")),
        sa.Column("ngayHoanTat", sa.DateTime(), nullable=True),
        sa.UniqueConstraint("maSoHoanTien", name="uq_HoanTienNgoaiLe_maSoHoanTien"),
        sa.UniqueConstraint("khoaChongTrung", name="uq_HoanTienNgoaiLe_khoaChongTrung"),
        sa.CheckConstraint(
            "\"phamViHoan\" IN ('EXCESS_PAYMENT', 'FULL_ORDER', 'PARTIAL_OVERCHARGE')",
            name="ck_HoanTienNgoaiLe_phamViHoan",
        ),
        sa.CheckConstraint(
            "\"loaiSuCo\" IN ('DUPLICATE_CHARGE', 'WRONG_AMOUNT', 'CANNOT_PROVISION_COURSE', "
            "'LATE_AFTER_CANCEL', 'LATE_AFTER_EXPIRE', 'SYSTEM_ERROR', 'REGULATORY')",
            name="ck_HoanTienNgoaiLe_loaiSuCo",
        ),
        sa.CheckConstraint(
            "\"trangThai\" IN ('PENDING_REVIEW', 'VERIFIED', 'REFUND_PENDING', 'REFUNDED', "
            "'REFUND_FAILED', 'UNKNOWN', 'REJECTED')",
            name="ck_HoanTienNgoaiLe_trangThai",
        ),
        sa.CheckConstraint("\"donViTienTe\" = 'VND'", name="ck_HoanTienNgoaiLe_donViTienTe"),
        sa.CheckConstraint(
            '"soTienHoan" > 0 AND "soTienHoan" <= "soTienDaThu"',
            name="ck_HoanTienNgoaiLe_soTien_bounds",
        ),
    )
    op.create_index(
        "uq_HoanTienNgoaiLe_active_per_payment",
        "HoanTienNgoaiLe",
        ["maThanhToan"],
        unique=True,
        postgresql_where=sa.text("\"trangThai\" IN ('PENDING_REVIEW', 'VERIFIED', 'REFUND_PENDING', 'UNKNOWN')"),
    )
    op.create_index("ix_HoanTienNgoaiLe_order", "HoanTienNgoaiLe", ["maDonHang"])
    op.create_index("ix_HoanTienNgoaiLe_status_updated", "HoanTienNgoaiLe", ["trangThai", sa.text('"ngayCapNhat" DESC')])

    # 3. LanThuHoanTien (Refund Gateway Attempts)
    op.create_table(
        "LanThuHoanTien",
        sa.Column("maLanThuHoan", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("maHoanTien", sa.Integer(), sa.ForeignKey("HoanTienNgoaiLe.maHoanTien", ondelete="RESTRICT"), nullable=False),
        sa.Column("thuTuLanThu", sa.Integer(), nullable=False),
        sa.Column("maYeuCauCong", sa.String(length=64), nullable=False),
        sa.Column("maGiaoDichHoanCong", sa.String(length=100), nullable=True),
        sa.Column("soTienYeuCau", sa.Numeric(precision=12, scale=0), nullable=False),
        sa.Column("trangThai", sa.String(length=20), nullable=False, server_default=sa.text("'SENT'")),
        sa.Column("maPhanHoiCong", sa.String(length=32), nullable=True),
        sa.Column("phanHoiAnToan", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("maNguoiThucThi", sa.Integer(), sa.ForeignKey("NguoiDung.maNguoiDung", ondelete="SET NULL"), nullable=True),
        sa.Column("ngayGui", sa.DateTime(), nullable=False, server_default=sa.text("(CURRENT_TIMESTAMP AT TIME ZONE 'UTC')")),
        sa.Column("ngayPhanHoi", sa.DateTime(), nullable=True),
        sa.UniqueConstraint("maYeuCauCong", name="uq_LanThuHoanTien_maYeuCauCong"),
        sa.UniqueConstraint("maHoanTien", "thuTuLanThu", name="uq_LanThuHoanTien_refund_seq"),
        sa.CheckConstraint('"thuTuLanThu" >= 1', name="ck_LanThuHoanTien_thuTu_positive"),
        sa.CheckConstraint('"soTienYeuCau" > 0', name="ck_LanThuHoanTien_soTien_positive"),
        sa.CheckConstraint(
            "\"trangThai\" IN ('SENT', 'SUCCEEDED', 'FAILED', 'UNKNOWN')",
            name="ck_LanThuHoanTien_trangThai",
        ),
    )
    op.create_index(
        "uq_LanThuHoanTien_inflight_per_refund",
        "LanThuHoanTien",
        ["maHoanTien"],
        unique=True,
        postgresql_where=sa.text("\"trangThai\" IN ('SENT', 'UNKNOWN')"),
    )
    op.create_index("ix_LanThuHoanTien_refund", "LanThuHoanTien", ["maHoanTien"])

    # 4. BaoCaoSuCoThanhToan (Payment Incident Reports)
    op.create_table(
        "BaoCaoSuCoThanhToan",
        sa.Column("maSuCo", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("maSoSuCo", sa.String(length=40), nullable=False),
        sa.Column("maDonHang", sa.Integer(), sa.ForeignKey("DonHang.maDonHang", ondelete="RESTRICT"), nullable=False),
        sa.Column("maThanhToan", sa.Integer(), sa.ForeignKey("ThanhToan.maThanhToan", ondelete="RESTRICT"), nullable=True),
        sa.Column("maNguoiBaoCao", sa.Integer(), sa.ForeignKey("NguoiDung.maNguoiDung", ondelete="RESTRICT"), nullable=False),
        sa.Column("loaiSuCo", sa.String(length=40), nullable=False),
        sa.Column("moTa", sa.Text(), nullable=False),
        sa.Column("trangThai", sa.String(length=20), nullable=False, server_default=sa.text("'OPEN'")),
        sa.Column("maAdminPhuTrach", sa.Integer(), sa.ForeignKey("NguoiDung.maNguoiDung", ondelete="SET NULL"), nullable=True),
        sa.Column("ghiChuXuLy", sa.Text(), nullable=True),
        sa.Column("ngayBaoCao", sa.DateTime(), nullable=False, server_default=sa.text("(CURRENT_TIMESTAMP AT TIME ZONE 'UTC')")),
        sa.Column("ngayCapNhat", sa.DateTime(), nullable=False, server_default=sa.text("(CURRENT_TIMESTAMP AT TIME ZONE 'UTC')")),
        sa.UniqueConstraint("maSoSuCo", name="uq_BaoCaoSuCoThanhToan_maSoSuCo"),
        sa.CheckConstraint(
            "\"loaiSuCo\" IN ('DUPLICATE_CHARGE', 'CHARGED_NO_ACCESS', 'WRONG_AMOUNT', "
            "'CANCELLED_OR_EXPIRED_CHARGED', 'OTHER_PAYMENT_ERROR')",
            name="ck_BaoCaoSuCoThanhToan_loaiSuCo",
        ),
        sa.CheckConstraint(
            "\"trangThai\" IN ('OPEN', 'IN_REVIEW', 'RESOLVED', 'DISMISSED')",
            name="ck_BaoCaoSuCoThanhToan_trangThai",
        ),
    )
    op.create_index("ix_BaoCaoSuCoThanhToan_status_date", "BaoCaoSuCoThanhToan", ["trangThai", sa.text('"ngayBaoCao" DESC')])
    op.create_index("ix_BaoCaoSuCoThanhToan_order", "BaoCaoSuCoThanhToan", ["maDonHang"])
    op.create_index("ix_BaoCaoSuCoThanhToan_user", "BaoCaoSuCoThanhToan", ["maNguoiBaoCao"])

    # 5. SuKienThanhToan (Immutable Append-Only Financial Event Log with DB-level Trigger)
    op.create_table(
        "SuKienThanhToan",
        sa.Column("maSuKien", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("maDonHang", sa.Integer(), sa.ForeignKey("DonHang.maDonHang", ondelete="RESTRICT"), nullable=False),
        sa.Column("maThanhToan", sa.Integer(), sa.ForeignKey("ThanhToan.maThanhToan", ondelete="RESTRICT"), nullable=True),
        sa.Column("maHoanTien", sa.Integer(), sa.ForeignKey("HoanTienNgoaiLe.maHoanTien", ondelete="RESTRICT"), nullable=True),
        sa.Column("loaiSuKien", sa.String(length=50), nullable=False),
        sa.Column("nguonSuKien", sa.String(length=40), nullable=False),
        sa.Column("khoaChongTrung", sa.String(length=128), nullable=True),
        sa.Column("duLieuAnToan", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("ngayTao", sa.DateTime(), nullable=False, server_default=sa.text("(CURRENT_TIMESTAMP AT TIME ZONE 'UTC')")),
    )
    op.create_index(
        "uq_SuKienThanhToan_khoaChongTrung",
        "SuKienThanhToan",
        ["khoaChongTrung"],
        unique=True,
        postgresql_where=sa.text('"khoaChongTrung" IS NOT NULL'),
    )
    op.create_index("ix_SuKienThanhToan_order_created", "SuKienThanhToan", ["maDonHang", sa.text('"ngayTao" DESC')])
    op.create_index("ix_SuKienThanhToan_payment_created", "SuKienThanhToan", ["maThanhToan", sa.text('"ngayTao" DESC')])

    # DB-level append-only trigger (cannot be bypassed by service bugs)
    op.execute(
        """
        CREATE OR REPLACE FUNCTION fn_sukienthanhtoan_append_only()
        RETURNS TRIGGER AS $$
        BEGIN
            RAISE EXCEPTION 'SuKienThanhToan is append-only: % is forbidden', TG_OP;
        END;
        $$ LANGUAGE plpgsql;
        """
    )
    op.execute(
        """
        CREATE TRIGGER trg_SuKienThanhToan_append_only
        BEFORE UPDATE OR DELETE ON "SuKienThanhToan"
        FOR EACH ROW EXECUTE FUNCTION fn_sukienthanhtoan_append_only();
        """
    )

    # 6. TacVuDoiSoatThanhToan (Durable Payment Reconciliation Queue)
    op.create_table(
        "TacVuDoiSoatThanhToan",
        sa.Column("maTacVu", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("loaiTacVu", sa.String(length=40), nullable=False),
        sa.Column("maDonHang", sa.Integer(), sa.ForeignKey("DonHang.maDonHang", ondelete="RESTRICT"), nullable=False),
        sa.Column("maThanhToan", sa.Integer(), sa.ForeignKey("ThanhToan.maThanhToan", ondelete="RESTRICT"), nullable=False),
        sa.Column("maHoanTien", sa.Integer(), sa.ForeignKey("HoanTienNgoaiLe.maHoanTien", ondelete="RESTRICT"), nullable=True),
        sa.Column("khoaChongTrung", sa.String(length=128), nullable=False),
        sa.Column("trangThai", sa.String(length=30), nullable=False, server_default=sa.text("'PENDING'")),
        sa.Column("soLanThu", sa.Integer(), nullable=False, server_default=sa.text("0")),
        sa.Column("soLanThuToiDa", sa.Integer(), nullable=False, server_default=sa.text("6")),
        sa.Column("thoiDiemChayTiepTheo", sa.DateTime(), nullable=False, server_default=sa.text("(CURRENT_TIMESTAMP AT TIME ZONE 'UTC')")),
        sa.Column("maWorker", sa.String(length=100), nullable=True),
        sa.Column("claimToken", sa.String(length=64), nullable=True),
        sa.Column("leaseGeneration", sa.Integer(), nullable=False, server_default=sa.text("0")),
        sa.Column("hanLease", sa.DateTime(), nullable=True),
        sa.Column("loiGanNhat", sa.Text(), nullable=True),
        sa.Column("ngayTao", sa.DateTime(), nullable=False, server_default=sa.text("(CURRENT_TIMESTAMP AT TIME ZONE 'UTC')")),
        sa.Column("ngayCapNhat", sa.DateTime(), nullable=False, server_default=sa.text("(CURRENT_TIMESTAMP AT TIME ZONE 'UTC')")),
        sa.UniqueConstraint("khoaChongTrung", name="uq_TacVuDoiSoatThanhToan_khoaChongTrung"),
        sa.CheckConstraint(
            "\"loaiTacVu\" IN ('QUERY_PENDING_PAYMENT', 'VERIFY_EXPIRED_ORDER', "
            "'RETRY_CAPTURED_UNAPPLIED', 'QUERY_UNKNOWN_REFUND')",
            name="ck_TacVuDoiSoatThanhToan_loaiTacVu",
        ),
        sa.CheckConstraint(
            "\"trangThai\" IN ('PENDING', 'PROCESSING', 'DONE', 'RETRY_WAIT', 'ESCALATED_ADMIN', 'CANCELLED')",
            name="ck_TacVuDoiSoatThanhToan_trangThai",
        ),
        sa.CheckConstraint('"soLanThu" >= 0 AND "soLanThuToiDa" > 0', name="ck_TacVuDoiSoatThanhToan_retries"),
        sa.CheckConstraint('"leaseGeneration" >= 0', name="ck_TacVuDoiSoatThanhToan_lease_gen"),
    )
    op.create_index("ix_TacVuDoiSoatThanhToan_claimable", "TacVuDoiSoatThanhToan", ["trangThai", "thoiDiemChayTiepTheo"])
    op.create_index(
        "ix_TacVuDoiSoatThanhToan_stale_lease",
        "TacVuDoiSoatThanhToan",
        ["hanLease"],
        postgresql_where=sa.text("\"trangThai\" = 'PROCESSING'"),
    )

    # 7. Idempotent JSONB Backfill (strictly preserves original JSONB evidence; never fabricates money)
    op.execute(
        """
        UPDATE "ThanhToan"
        SET "daThuTien" = TRUE,
            "soTienDaThuThucTe" = "soTien"
        WHERE "trangThai" IN ('PAID', 'REFUNDED')
          AND "daThuTien" = FALSE;
        """
    )
    op.execute(
        """
        UPDATE "ThanhToan"
        SET "trangThai" = 'CAPTURED_UNAPPLIED',
            "daThuTien" = TRUE,
            "soTienDaThuThucTe" = CASE
                WHEN ("duLieuPhanHoiAnToan"->>'capturedAmountVnd') ~ '^[0-9]+$'
                THEN ("duLieuPhanHoiAnToan"->>'capturedAmountVnd')::numeric(12,0)
                ELSE "soTien"
            END
        WHERE "trangThai" = 'FAILED'
          AND COALESCE(("duLieuPhanHoiAnToan"->>'fundsCaptured')::boolean, FALSE) = TRUE;
        """
    )
    # Backfill existing exceptionRefund JSONB into HoanTienNgoaiLe idempotently
    op.execute(
        """
        INSERT INTO "HoanTienNgoaiLe" (
            "maSoHoanTien", "maDonHang", "maThanhToan", "khoaChongTrung",
            "phamViHoan", "loaiSuCo", "soTienDaThu", "soTienHoan", "donViTienTe",
            "trangThai", "lyDo", "maGiaoDichHoanCong", "maNguoiXuLy", "lichSuTrangThai",
            "ngayTao", "ngayCapNhat"
        )
        SELECT
            COALESCE(t."duLieuPhanHoiAnToan"->'exceptionRefund'->>'refundId', 'REF-BF-' || t."maThanhToan"),
            t."maDonHang",
            t."maThanhToan",
            COALESCE(t."duLieuPhanHoiAnToan"->'exceptionRefund'->>'idempotencyKey', 'bf-ref-' || t."maThanhToan"),
            COALESCE(t."duLieuPhanHoiAnToan"->'exceptionRefund'->>'phamViHoan', 'FULL_ORDER'),
            COALESCE(t."duLieuPhanHoiAnToan"->'exceptionRefund'->>'loaiSuCo', 'SYSTEM_ERROR'),
            GREATEST(t."soTienDaThuThucTe", (t."duLieuPhanHoiAnToan"->'exceptionRefund'->>'soTienHoan')::numeric(12,0)),
            (t."duLieuPhanHoiAnToan"->'exceptionRefund'->>'soTienHoan')::numeric(12,0),
            'VND',
            COALESCE(t."duLieuPhanHoiAnToan"->'exceptionRefund'->>'trangThai', 'PENDING_REVIEW'),
            COALESCE(t."duLieuPhanHoiAnToan"->'exceptionRefund'->>'lyDo', 'Backfilled from JSONB'),
            t."duLieuPhanHoiAnToan"->'exceptionRefund'->>'maGiaoDichHoanCong',
            NULLIF(t."duLieuPhanHoiAnToan"->'exceptionRefund'->>'maNguoiXuLy', '')::integer,
            t."duLieuPhanHoiAnToan"->'exceptionRefund'->'lichSuTrangThai',
            t."ngayTao",
            t."ngayCapNhat"
        FROM "ThanhToan" t
        WHERE jsonb_typeof(t."duLieuPhanHoiAnToan"->'exceptionRefund') = 'object'
        ON CONFLICT ("khoaChongTrung") DO NOTHING;
        """
    )
    # Backfill existing incidentReports JSONB into BaoCaoSuCoThanhToan idempotently
    op.execute(
        """
        INSERT INTO "BaoCaoSuCoThanhToan" (
            "maSoSuCo", "maDonHang", "maThanhToan", "maNguoiBaoCao",
            "loaiSuCo", "moTa", "trangThai", "ngayBaoCao", "ngayCapNhat"
        )
        SELECT
            inc->>'maSuCo',
            t."maDonHang",
            t."maThanhToan",
            COALESCE(NULLIF(inc->>'maNguoiBaoCao', '')::integer, t."maNguoiDung"),
            COALESCE(inc->>'loaiSuCo', 'OTHER_PAYMENT_ERROR'),
            COALESCE(inc->>'moTa', 'Backfilled incident report'),
            COALESCE(inc->>'trangThai', 'OPEN'),
            t."ngayTao",
            t."ngayCapNhat"
        FROM "ThanhToan" t,
             jsonb_array_elements(COALESCE(t."duLieuPhanHoiAnToan"->'incidentReports', '[]'::jsonb)) AS inc
        WHERE inc->>'maSuCo' IS NOT NULL
        ON CONFLICT ("maSoSuCo") DO NOTHING;
        """
    )


def downgrade() -> None:
    op.drop_index("ix_TacVuDoiSoatThanhToan_stale_lease", table_name="TacVuDoiSoatThanhToan")
    op.drop_index("ix_TacVuDoiSoatThanhToan_claimable", table_name="TacVuDoiSoatThanhToan")
    op.drop_table("TacVuDoiSoatThanhToan")

    op.execute('DROP TRIGGER IF EXISTS trg_SuKienThanhToan_append_only ON "SuKienThanhToan";')
    op.execute("DROP FUNCTION IF EXISTS fn_sukienthanhtoan_append_only();")
    op.drop_index("ix_SuKienThanhToan_payment_created", table_name="SuKienThanhToan")
    op.drop_index("ix_SuKienThanhToan_order_created", table_name="SuKienThanhToan")
    op.drop_index("uq_SuKienThanhToan_khoaChongTrung", table_name="SuKienThanhToan")
    op.drop_table("SuKienThanhToan")

    op.drop_index("ix_BaoCaoSuCoThanhToan_user", table_name="BaoCaoSuCoThanhToan")
    op.drop_index("ix_BaoCaoSuCoThanhToan_order", table_name="BaoCaoSuCoThanhToan")
    op.drop_index("ix_BaoCaoSuCoThanhToan_status_date", table_name="BaoCaoSuCoThanhToan")
    op.drop_table("BaoCaoSuCoThanhToan")

    op.drop_index("ix_LanThuHoanTien_refund", table_name="LanThuHoanTien")
    op.drop_index("uq_LanThuHoanTien_inflight_per_refund", table_name="LanThuHoanTien")
    op.drop_table("LanThuHoanTien")

    op.drop_index("ix_HoanTienNgoaiLe_status_updated", table_name="HoanTienNgoaiLe")
    op.drop_index("ix_HoanTienNgoaiLe_order", table_name="HoanTienNgoaiLe")
    op.drop_index("uq_HoanTienNgoaiLe_active_per_payment", table_name="HoanTienNgoaiLe")
    op.drop_table("HoanTienNgoaiLe")

    op.execute(
        """
        UPDATE "ThanhToan" SET "trangThai" = 'FAILED'
        WHERE "trangThai" IN ('CAPTURED_UNAPPLIED', 'PARTIALLY_REFUNDED');
        """
    )
    op.drop_constraint("ck_ThanhToan_soTienDaThuThucTe_non_negative", "ThanhToan", type_="check")
    op.drop_constraint("ck_ThanhToan_trangThai", "ThanhToan", type_="check")
    op.create_check_constraint(
        "ck_ThanhToan_trangThai",
        "ThanhToan",
        "\"trangThai\" IN ('PENDING', 'PAID', 'FAILED', 'CANCELLED', 'EXPIRED', 'REFUNDED')",
    )
    op.drop_column("ThanhToan", "soTienDaThuThucTe")
    op.drop_column("ThanhToan", "daThuTien")
    op.alter_column(
        "ThanhToan",
        "trangThai",
        existing_type=sa.String(length=30),
        type_=sa.String(length=20),
        existing_nullable=False,
    )
