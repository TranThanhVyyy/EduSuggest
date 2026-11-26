"""add phase 3 auto expert assignment, accountability, availability, and notifications

Revision ID: c3d4e5f6a7b8
Revises: 401255c76a96
Create Date: 2026-11-25 22:45:00.000000

Consolidated GĐ3.1 additive schema:
- 7 new tables: CauHinhPhanCong, PhanCongKiemDuyet, HangDoiPhanCong,
  ViPhamChuyenGia, NhatKyKyLuatChuyenGia, YeuCauTamNgungChuyenGia, ThongBao.
- 5 additive columns on 4 existing tables:
  ChuyenGia(chuKyKyLuatSo, mocChuKyKyLuat),
  KhoaHoc(soVongKiemDuyetHienTai),
  TaiLieu(soVongKiemDuyetHienTai),
  DanhGiaChuyenGia(maPhanCong).
- KhoaHoc visibility CHECK constraint: ck_KhoaHoc_visible_requires_approved.
- Idempotent singleton seed in CauHinhPhanCong (maCauHinh = 1).
- All timestamps standardized to UTC naive (CURRENT_TIMESTAMP AT TIME ZONE 'UTC').
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "c3d4e5f6a7b8"
down_revision: str | Sequence[str] | None = "401255c76a96"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

_UTC_NOW = sa.text("(CURRENT_TIMESTAMP AT TIME ZONE 'UTC')")


def upgrade() -> None:
    # ------------------------------------------------------------------
    # 1. Additive columns on existing tables (ChuyenGia, KhoaHoc, TaiLieu)
    # ------------------------------------------------------------------
    op.add_column(
        "ChuyenGia",
        sa.Column(
            "chuKyKyLuatSo",
            sa.Integer(),
            nullable=False,
            server_default=sa.text("1"),
        ),
    )
    op.add_column(
        "ChuyenGia",
        sa.Column("mocChuKyKyLuat", sa.DateTime(), nullable=True),
    )
    op.create_check_constraint(
        "ck_ChuyenGia_chuKyKyLuatSo",
        "ChuyenGia",
        '"chuKyKyLuatSo" >= 1',
    )

    op.add_column(
        "KhoaHoc",
        sa.Column(
            "soVongKiemDuyetHienTai",
            sa.Integer(),
            nullable=False,
            server_default=sa.text("0"),
        ),
    )
    op.create_check_constraint(
        "ck_KhoaHoc_soVongKiemDuyetHienTai",
        "KhoaHoc",
        '"soVongKiemDuyetHienTai" >= 0',
    )
    op.create_check_constraint(
        "ck_KhoaHoc_visible_requires_approved",
        "KhoaHoc",
        "(\"trangThaiHienThi\" IS DISTINCT FROM 'VISIBLE') OR (\"trangThaiDuyet\" IS NOT DISTINCT FROM 'APPROVED')",
    )

    op.add_column(
        "TaiLieu",
        sa.Column(
            "soVongKiemDuyetHienTai",
            sa.Integer(),
            nullable=False,
            server_default=sa.text("0"),
        ),
    )
    op.create_check_constraint(
        "ck_TaiLieu_soVongKiemDuyetHienTai",
        "TaiLieu",
        '"soVongKiemDuyetHienTai" >= 0',
    )

    # ------------------------------------------------------------------
    # 2. Table 1/7: CauHinhPhanCong (Singleton maCauHinh = 1)
    # ------------------------------------------------------------------
    op.create_table(
        "CauHinhPhanCong",
        sa.Column("maCauHinh", sa.Integer(), primary_key=True, autoincrement=False),
        sa.Column("gioiHanTaiToiDa", sa.Integer(), nullable=False, server_default=sa.text("5")),
        sa.Column("hanTiepNhanGio", sa.Integer(), nullable=False, server_default=sa.text("24")),
        sa.Column("hanKiemDuyetGio", sa.Integer(), nullable=False, server_default=sa.text("72")),
        sa.Column("khoangThongKeGio", sa.Integer(), nullable=False, server_default=sa.text("168")),
        sa.Column("nguongCanhBao", sa.Integer(), nullable=False, server_default=sa.text("2")),
        sa.Column("nguongKhoaTaiKhoan", sa.Integer(), nullable=False, server_default=sa.text("4")),
        sa.Column("tinhViPhamHetHan", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("tuDongKhoa", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("thoiGianTamNgungToiDaNgay", sa.Integer(), nullable=False, server_default=sa.text("30")),
        sa.Column("soLanTaiPhanCongToiDa", sa.Integer(), nullable=False, server_default=sa.text("5")),
        sa.Column("uuTienTuyetDoiChuyenMonChinh", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column(
            "maNguoiCapNhat",
            sa.Integer(),
            sa.ForeignKey("NguoiDung.maNguoiDung", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("ngayCapNhat", sa.DateTime(), nullable=False, server_default=_UTC_NOW),
        sa.CheckConstraint('"maCauHinh" = 1', name="ck_CauHinhPhanCong_singleton"),
        sa.CheckConstraint('"gioiHanTaiToiDa" BETWEEN 1 AND 50', name="ck_CauHinhPhanCong_gioiHanTai"),
        sa.CheckConstraint('"hanTiepNhanGio" BETWEEN 1 AND 168', name="ck_CauHinhPhanCong_hanTiepNhan"),
        sa.CheckConstraint('"hanKiemDuyetGio" BETWEEN 1 AND 720', name="ck_CauHinhPhanCong_hanKiemDuyet"),
        sa.CheckConstraint('"khoangThongKeGio" BETWEEN 24 AND 2160', name="ck_CauHinhPhanCong_khoangThongKe"),
        sa.CheckConstraint('"nguongCanhBao" >= 1', name="ck_CauHinhPhanCong_nguongCanhBao"),
        sa.CheckConstraint('"nguongKhoaTaiKhoan" > "nguongCanhBao"', name="ck_CauHinhPhanCong_nguongKhoa"),
        sa.CheckConstraint('"thoiGianTamNgungToiDaNgay" BETWEEN 1 AND 180', name="ck_CauHinhPhanCong_tamNgung"),
        sa.CheckConstraint('"soLanTaiPhanCongToiDa" BETWEEN 1 AND 20', name="ck_CauHinhPhanCong_taiPhanCong"),
    )

    # Idempotent singleton seed
    op.execute(
        'INSERT INTO "CauHinhPhanCong" ("maCauHinh") VALUES (1) '
        'ON CONFLICT ("maCauHinh") DO NOTHING'
    )

    # ------------------------------------------------------------------
    # 3. Table 2/7: PhanCongKiemDuyet
    # ------------------------------------------------------------------
    op.create_table(
        "PhanCongKiemDuyet",
        sa.Column("maPhanCong", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column(
            "maKhoaHoc",
            sa.Integer(),
            sa.ForeignKey("KhoaHoc.maKhoaHoc", ondelete="RESTRICT"),
            nullable=True,
        ),
        sa.Column(
            "maTaiLieu",
            sa.Integer(),
            sa.ForeignKey("TaiLieu.maTaiLieu", ondelete="RESTRICT"),
            nullable=True,
        ),
        sa.Column(
            "maChuyenGia",
            sa.Integer(),
            sa.ForeignKey("ChuyenGia.maChuyenGia", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column(
            "maDanhMuc",
            sa.Integer(),
            sa.ForeignKey("DanhMuc.maDanhMuc", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column(
            "maChuyenMonKhop",
            sa.Integer(),
            sa.ForeignKey("ChuyenMon.maChuyenMon", ondelete="RESTRICT"),
            nullable=True,
        ),
        sa.Column("soVongKiemDuyet", sa.Integer(), nullable=False, server_default=sa.text("1")),
        sa.Column("phuongThucPhanCong", sa.String(length=20), nullable=False, server_default=sa.text("'AUTO'")),
        sa.Column(
            "maNguoiPhanCong",
            sa.Integer(),
            sa.ForeignKey("NguoiDung.maNguoiDung", ondelete="RESTRICT"),
            nullable=True,
        ),
        sa.Column("diemPhuHop", sa.Numeric(5, 2), nullable=True),
        sa.Column("chiTietDiem", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("lyDoPhanCong", sa.Text(), nullable=True),
        sa.Column("trangThai", sa.String(length=30), nullable=False, server_default=sa.text("'ASSIGNED'")),
        sa.Column("ngayPhanCong", sa.DateTime(), nullable=False, server_default=_UTC_NOW),
        sa.Column("hanTiepNhan", sa.DateTime(), nullable=False),
        sa.Column("hanKiemDuyet", sa.DateTime(), nullable=True),
        sa.Column("ngayChapNhan", sa.DateTime(), nullable=True),
        sa.Column("ngayBatDau", sa.DateTime(), nullable=True),
        sa.Column("ngayHoanThanh", sa.DateTime(), nullable=True),
        sa.Column("maLyDoTuChoi", sa.String(length=50), nullable=True),
        sa.Column("lyDoTuChoi", sa.Text(), nullable=True),
        sa.Column("lyDoHuy", sa.Text(), nullable=True),
        sa.Column("banNhapDanhGia", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("ngayCapNhat", sa.DateTime(), nullable=False, server_default=_UTC_NOW),
        sa.CheckConstraint(
            '("maKhoaHoc" IS NOT NULL AND "maTaiLieu" IS NULL) '
            'OR ("maKhoaHoc" IS NULL AND "maTaiLieu" IS NOT NULL)',
            name="ck_PhanCong_exactly_one_target",
        ),
        sa.CheckConstraint('"soVongKiemDuyet" >= 1', name="ck_PhanCong_soVongKiemDuyet"),
        sa.CheckConstraint(
            "\"phuongThucPhanCong\" IN ('AUTO', 'MANUAL')",
            name="ck_PhanCong_phuongThuc",
        ),
        sa.CheckConstraint(
            "(\"phuongThucPhanCong\" = 'AUTO' AND \"maNguoiPhanCong\" IS NULL) "
            "OR (\"phuongThucPhanCong\" = 'MANUAL' AND \"maNguoiPhanCong\" IS NOT NULL)",
            name="ck_PhanCong_actor_consistency",
        ),
        sa.CheckConstraint(
            '"diemPhuHop" IS NULL OR ("diemPhuHop" >= 0 AND "diemPhuHop" <= 100)',
            name="ck_PhanCong_diemPhuHop",
        ),
        sa.CheckConstraint(
            "\"trangThai\" IN ('ASSIGNED','ACCEPTED','IN_PROGRESS','COMPLETED','DECLINED','EXPIRED','CANCELLED')",
            name="ck_PhanCong_trangThai",
        ),
        sa.CheckConstraint(
            '"hanTiepNhan" > "ngayPhanCong" '
            'AND ("hanKiemDuyet" IS NULL OR "hanKiemDuyet" > "ngayPhanCong") '
            'AND ("ngayChapNhan" IS NULL OR "hanKiemDuyet" IS NULL OR "hanKiemDuyet" > "ngayChapNhan")',
            name="ck_PhanCong_deadlines",
        ),
        sa.CheckConstraint(
            "\"maLyDoTuChoi\" IS NULL OR \"maLyDoTuChoi\" IN "
            "('WORKLOAD_PERSONAL','CONFLICT_OF_INTEREST','SYSTEM_MISASSIGNMENT','TECHNICAL_ISSUE','OTHER')",
            name="ck_PhanCong_maLyDoTuChoi",
        ),
    )

    op.execute(
        'CREATE UNIQUE INDEX uq_phancong_active_course '
        'ON "PhanCongKiemDuyet" ("maKhoaHoc") '
        'WHERE "maKhoaHoc" IS NOT NULL AND "trangThai" IN (\'ASSIGNED\', \'ACCEPTED\', \'IN_PROGRESS\')'
    )
    op.execute(
        'CREATE UNIQUE INDEX uq_phancong_active_material '
        'ON "PhanCongKiemDuyet" ("maTaiLieu") '
        'WHERE "maTaiLieu" IS NOT NULL AND "trangThai" IN (\'ASSIGNED\', \'ACCEPTED\', \'IN_PROGRESS\')'
    )
    op.execute(
        'CREATE INDEX ix_phancong_expert_active '
        'ON "PhanCongKiemDuyet" ("maChuyenGia", "trangThai") '
        'WHERE "trangThai" IN (\'ASSIGNED\', \'ACCEPTED\', \'IN_PROGRESS\')'
    )
    op.execute(
        'CREATE INDEX ix_phancong_assigned_deadline '
        'ON "PhanCongKiemDuyet" ("hanTiepNhan") '
        'WHERE "trangThai" = \'ASSIGNED\''
    )
    op.execute(
        'CREATE INDEX ix_phancong_review_deadline '
        'ON "PhanCongKiemDuyet" ("hanKiemDuyet") '
        'WHERE "trangThai" IN (\'ACCEPTED\', \'IN_PROGRESS\')'
    )
    op.create_index(
        "ix_phancong_target_round",
        "PhanCongKiemDuyet",
        ["maKhoaHoc", "maTaiLieu", "soVongKiemDuyet"],
    )

    # 5th additive column: DanhGiaChuyenGia.maPhanCong (ON DELETE RESTRICT + partial unique index)
    op.add_column(
        "DanhGiaChuyenGia",
        sa.Column(
            "maPhanCong",
            sa.Integer(),
            sa.ForeignKey("PhanCongKiemDuyet.maPhanCong", ondelete="RESTRICT"),
            nullable=True,
        ),
    )
    op.execute(
        'CREATE UNIQUE INDEX uq_danhgia_maPhanCong '
        'ON "DanhGiaChuyenGia" ("maPhanCong") '
        'WHERE "maPhanCong" IS NOT NULL'
    )

    # ------------------------------------------------------------------
    # 4. Table 3/7: HangDoiPhanCong (Event-scoped Durable Queue)
    # ------------------------------------------------------------------
    op.create_table(
        "HangDoiPhanCong",
        sa.Column("maCongViec", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("loaiDoiTuong", sa.String(length=20), nullable=False),
        sa.Column(
            "maKhoaHoc",
            sa.Integer(),
            sa.ForeignKey("KhoaHoc.maKhoaHoc", ondelete="CASCADE"),
            nullable=True,
        ),
        sa.Column(
            "maTaiLieu",
            sa.Integer(),
            sa.ForeignKey("TaiLieu.maTaiLieu", ondelete="CASCADE"),
            nullable=True,
        ),
        sa.Column("soVongKiemDuyet", sa.Integer(), nullable=False),
        sa.Column("loaiSuKien", sa.String(length=30), nullable=False),
        sa.Column(
            "maPhanCongNguon",
            sa.Integer(),
            sa.ForeignKey("PhanCongKiemDuyet.maPhanCong", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("khoaChongTrung", sa.String(length=150), nullable=False, unique=True),
        sa.Column("trangThai", sa.String(length=30), nullable=False, server_default=sa.text("'PENDING'")),
        sa.Column("uuTien", sa.Integer(), nullable=False, server_default=sa.text("0")),
        sa.Column("soLanThu", sa.Integer(), nullable=False, server_default=sa.text("0")),
        sa.Column("soLanThuToiDa", sa.Integer(), nullable=False, server_default=sa.text("5")),
        sa.Column("thoiDiemChayTiepTheo", sa.DateTime(), nullable=False, server_default=_UTC_NOW),
        sa.Column("maWorker", sa.String(length=100), nullable=True),
        sa.Column("claimToken", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("leaseGeneration", sa.Integer(), nullable=False, server_default=sa.text("0")),
        sa.Column("thoiDiemBatDauXuLy", sa.DateTime(), nullable=True),
        sa.Column("hanXuLy", sa.DateTime(), nullable=True),
        sa.Column("lyDoCho", sa.Text(), nullable=True),
        sa.Column("loiGanNhat", sa.Text(), nullable=True),
        sa.Column("ngayTao", sa.DateTime(), nullable=False, server_default=_UTC_NOW),
        sa.Column("ngayCapNhat", sa.DateTime(), nullable=False, server_default=_UTC_NOW),
        sa.CheckConstraint(
            "\"loaiDoiTuong\" IN ('COURSE', 'MATERIAL')",
            name="ck_HangDoi_loaiDoiTuong",
        ),
        sa.CheckConstraint(
            "(\"loaiDoiTuong\" = 'COURSE' AND \"maKhoaHoc\" IS NOT NULL AND \"maTaiLieu\" IS NULL) "
            "OR (\"loaiDoiTuong\" = 'MATERIAL' AND \"maTaiLieu\" IS NOT NULL AND \"maKhoaHoc\" IS NULL)",
            name="ck_HangDoi_exactly_one_target",
        ),
        sa.CheckConstraint('"soVongKiemDuyet" >= 1', name="ck_HangDoi_soVongKiemDuyet"),
        sa.CheckConstraint(
            "\"loaiSuKien\" IN ('SUBMIT','REASSIGN_DECLINED','REASSIGN_EXPIRED','REASSIGN_CANCELLED','ADMIN_RETRY')",
            name="ck_HangDoi_loaiSuKien",
        ),
        sa.CheckConstraint(
            "\"trangThai\" IN ('PENDING','PROCESSING','RETRYING','WAITING_ELIGIBLE','DONE','FAILED','CANCELLED')",
            name="ck_HangDoi_trangThai",
        ),
        sa.CheckConstraint(
            '"soLanThu" >= 0 AND "soLanThuToiDa" >= 1 AND "soLanThu" <= "soLanThuToiDa"',
            name="ck_HangDoi_retry_bounds",
        ),
        sa.CheckConstraint('"leaseGeneration" >= 0', name="ck_HangDoi_leaseGeneration"),
        sa.CheckConstraint(
            "\"trangThai\" <> 'PROCESSING' OR (\"claimToken\" IS NOT NULL AND \"maWorker\" IS NOT NULL AND \"hanXuLy\" IS NOT NULL)",
            name="ck_HangDoi_processing_requires_lease",
        ),
    )

    op.execute(
        'CREATE UNIQUE INDEX uq_hangdoi_open_course '
        'ON "HangDoiPhanCong" ("maKhoaHoc") '
        'WHERE "maKhoaHoc" IS NOT NULL AND "trangThai" IN (\'PENDING\', \'PROCESSING\', \'RETRYING\', \'WAITING_ELIGIBLE\')'
    )
    op.execute(
        'CREATE UNIQUE INDEX uq_hangdoi_open_material '
        'ON "HangDoiPhanCong" ("maTaiLieu") '
        'WHERE "maTaiLieu" IS NOT NULL AND "trangThai" IN (\'PENDING\', \'PROCESSING\', \'RETRYING\', \'WAITING_ELIGIBLE\')'
    )
    op.create_index(
        "ix_hangdoi_poll",
        "HangDoiPhanCong",
        ["trangThai", "thoiDiemChayTiepTheo"],
    )
    op.execute(
        'CREATE INDEX ix_hangdoi_stale_processing '
        'ON "HangDoiPhanCong" ("hanXuLy") '
        'WHERE "trangThai" = \'PROCESSING\''
    )

    # ------------------------------------------------------------------
    # 5. Table 4/7: ViPhamChuyenGia (ARCH-03: UNIQUE(maPhanCong), safe default PENDING_REVIEW)
    # ------------------------------------------------------------------
    op.create_table(
        "ViPhamChuyenGia",
        sa.Column("maViPham", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column(
            "maChuyenGia",
            sa.Integer(),
            sa.ForeignKey("ChuyenGia.maChuyenGia", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column(
            "maPhanCong",
            sa.Integer(),
            sa.ForeignKey("PhanCongKiemDuyet.maPhanCong", ondelete="RESTRICT"),
            nullable=False,
            unique=True,
        ),
        sa.Column("loaiViPham", sa.String(length=40), nullable=False),
        sa.Column("maLyDoTuChoi", sa.String(length=50), nullable=True),
        sa.Column("lyDo", sa.Text(), nullable=True),
        sa.Column(
            "trangThaiXuLy",
            sa.String(length=30),
            nullable=False,
            server_default=sa.text("'PENDING_REVIEW'"),
        ),
        sa.Column("chuKyKyLuatSo", sa.Integer(), nullable=False, server_default=sa.text("1")),
        sa.Column("mocChuKyApDung", sa.DateTime(), nullable=True),
        sa.Column("ngayViPham", sa.DateTime(), nullable=False, server_default=_UTC_NOW),
        sa.Column(
            "maNguoiXuLy",
            sa.Integer(),
            sa.ForeignKey("NguoiDung.maNguoiDung", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("ngayXuLy", sa.DateTime(), nullable=True),
        sa.Column("ghiChuXuLy", sa.Text(), nullable=True),
        sa.CheckConstraint(
            "\"loaiViPham\" IN ('EXPIRED_ACCEPTANCE','DECLINED_ASSIGNMENT','ABANDONED_ASSIGNMENT')",
            name="ck_ViPham_loaiViPham",
        ),
        sa.CheckConstraint(
            "\"maLyDoTuChoi\" IS NULL OR \"maLyDoTuChoi\" IN "
            "('WORKLOAD_PERSONAL','CONFLICT_OF_INTEREST','SYSTEM_MISASSIGNMENT','TECHNICAL_ISSUE','OTHER')",
            name="ck_ViPham_maLyDoTuChoi",
        ),
        sa.CheckConstraint(
            "\"trangThaiXuLy\" IN ('PENDING_REVIEW','CONFIRMED','EXEMPTED')",
            name="ck_ViPham_trangThaiXuLy",
        ),
        sa.CheckConstraint('"chuKyKyLuatSo" >= 1', name="ck_ViPham_chuKyKyLuatSo"),
    )
    op.create_index(
        "ix_vipham_expert_cycle_status",
        "ViPhamChuyenGia",
        ["maChuyenGia", "chuKyKyLuatSo", "trangThaiXuLy", "ngayViPham"],
    )

    # ------------------------------------------------------------------
    # 6. Table 5/7: NhatKyKyLuatChuyenGia
    # ------------------------------------------------------------------
    op.create_table(
        "NhatKyKyLuatChuyenGia",
        sa.Column("maNhatKy", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column(
            "maChuyenGia",
            sa.Integer(),
            sa.ForeignKey("ChuyenGia.maChuyenGia", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column(
            "maNguoiDung",
            sa.Integer(),
            sa.ForeignKey("NguoiDung.maNguoiDung", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column("hanhDong", sa.String(length=40), nullable=False),
        sa.Column("nguonThucHien", sa.String(length=20), nullable=False),
        sa.Column(
            "maNguoiThucHien",
            sa.Integer(),
            sa.ForeignKey("NguoiDung.maNguoiDung", ondelete="RESTRICT"),
            nullable=True,
        ),
        sa.Column("chuKyKyLuatSo", sa.Integer(), nullable=False, server_default=sa.text("1")),
        sa.Column("trangThaiTruoc", sa.String(length=30), nullable=True),
        sa.Column("trangThaiSau", sa.String(length=30), nullable=True),
        sa.Column("soViPhamTaiThoiDiem", sa.Integer(), nullable=True),
        sa.Column("lyDo", sa.Text(), nullable=False),
        sa.Column("chinhSachSnapshot", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("ngayTao", sa.DateTime(), nullable=False, server_default=_UTC_NOW),
        sa.CheckConstraint(
            "\"hanhDong\" IN ('REMINDER','WARNING_1','WARNING_FINAL','AUTO_LOCK','ADMIN_LOCK','ADMIN_UNLOCK','EXEMPT_VIOLATION','CONFIRM_VIOLATION')",
            name="ck_NhatKy_hanhDong",
        ),
        sa.CheckConstraint(
            "\"nguonThucHien\" IN ('SYSTEM','ADMIN')",
            name="ck_NhatKy_nguonThucHien",
        ),
        sa.CheckConstraint(
            "(\"nguonThucHien\" = 'SYSTEM' AND \"maNguoiThucHien\" IS NULL) "
            "OR (\"nguonThucHien\" = 'ADMIN' AND \"maNguoiThucHien\" IS NOT NULL)",
            name="ck_NhatKy_actor_consistency",
        ),
        sa.CheckConstraint('"chuKyKyLuatSo" >= 1', name="ck_NhatKy_chuKyKyLuatSo"),
    )
    op.create_index(
        "ix_nhatky_expert_created",
        "NhatKyKyLuatChuyenGia",
        ["maChuyenGia", "ngayTao"],
    )

    # ------------------------------------------------------------------
    # 7. Table 6/7: YeuCauTamNgungChuyenGia
    # ------------------------------------------------------------------
    op.create_table(
        "YeuCauTamNgungChuyenGia",
        sa.Column("maYeuCau", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column(
            "maChuyenGia",
            sa.Integer(),
            sa.ForeignKey("ChuyenGia.maChuyenGia", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column("ngayBatDau", sa.DateTime(), nullable=False),
        sa.Column("ngayKetThuc", sa.DateTime(), nullable=False),
        sa.Column("lyDo", sa.Text(), nullable=False),
        sa.Column("trangThai", sa.String(length=20), nullable=False, server_default=sa.text("'PENDING'")),
        sa.Column("ngayGuiYeuCau", sa.DateTime(), nullable=False, server_default=_UTC_NOW),
        sa.Column(
            "maNguoiXuLy",
            sa.Integer(),
            sa.ForeignKey("NguoiDung.maNguoiDung", ondelete="RESTRICT"),
            nullable=True,
        ),
        sa.Column("ngayXuLy", sa.DateTime(), nullable=True),
        sa.Column("ghiChuXuLy", sa.Text(), nullable=True),
        sa.Column("ngayHuy", sa.DateTime(), nullable=True),
        sa.Column("lyDoHuy", sa.Text(), nullable=True),
        sa.Column("ngayCapNhat", sa.DateTime(), nullable=False, server_default=_UTC_NOW),
        sa.CheckConstraint('"ngayKetThuc" > "ngayBatDau"', name="ck_TamNgung_range"),
        sa.CheckConstraint(
            "\"trangThai\" IN ('PENDING','APPROVED','REJECTED','CANCELLED','COMPLETED','EXPIRED')",
            name="ck_TamNgung_trangThai",
        ),
    )
    op.execute(
        'CREATE INDEX ix_tamngung_expert_active '
        'ON "YeuCauTamNgungChuyenGia" ("maChuyenGia", "ngayBatDau", "ngayKetThuc") '
        'WHERE "trangThai" IN (\'PENDING\', \'APPROVED\')'
    )

    # ------------------------------------------------------------------
    # 8. Table 7/7: ThongBao
    # ------------------------------------------------------------------
    op.create_table(
        "ThongBao",
        sa.Column("maThongBao", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column(
            "maNguoiNhan",
            sa.Integer(),
            sa.ForeignKey("NguoiDung.maNguoiDung", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("loaiThongBao", sa.String(length=50), nullable=False),
        sa.Column("tieuDe", sa.String(length=255), nullable=False),
        sa.Column("noiDung", sa.Text(), nullable=False),
        sa.Column("duLieuLienKet", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("daDoc", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("khoaChongTrung", sa.String(length=150), nullable=True, unique=True),
        sa.Column("ngayTao", sa.DateTime(), nullable=False, server_default=_UTC_NOW),
        sa.Column("ngayDoc", sa.DateTime(), nullable=True),
    )
    op.create_index(
        "ix_thongbao_user_unread",
        "ThongBao",
        ["maNguoiNhan", "daDoc", "ngayTao"],
    )


def downgrade() -> None:
    # Reverse exact FK dependency order back to 401255c76a96
    op.drop_index("ix_thongbao_user_unread", table_name="ThongBao")
    op.drop_table("ThongBao")

    op.execute("DROP INDEX IF EXISTS ix_tamngung_expert_active")
    op.drop_table("YeuCauTamNgungChuyenGia")

    op.drop_index("ix_nhatky_expert_created", table_name="NhatKyKyLuatChuyenGia")
    op.drop_table("NhatKyKyLuatChuyenGia")

    op.drop_index("ix_vipham_expert_cycle_status", table_name="ViPhamChuyenGia")
    op.drop_table("ViPhamChuyenGia")

    op.execute("DROP INDEX IF EXISTS ix_hangdoi_stale_processing")
    op.drop_index("ix_hangdoi_poll", table_name="HangDoiPhanCong")
    op.execute("DROP INDEX IF EXISTS uq_hangdoi_open_material")
    op.execute("DROP INDEX IF EXISTS uq_hangdoi_open_course")
    op.drop_table("HangDoiPhanCong")

    op.execute("DROP INDEX IF EXISTS uq_danhgia_maPhanCong")
    op.drop_column("DanhGiaChuyenGia", "maPhanCong")

    op.drop_index("ix_phancong_target_round", table_name="PhanCongKiemDuyet")
    op.execute("DROP INDEX IF EXISTS ix_phancong_review_deadline")
    op.execute("DROP INDEX IF EXISTS ix_phancong_assigned_deadline")
    op.execute("DROP INDEX IF EXISTS ix_phancong_expert_active")
    op.execute("DROP INDEX IF EXISTS uq_phancong_active_material")
    op.execute("DROP INDEX IF EXISTS uq_phancong_active_course")
    op.drop_table("PhanCongKiemDuyet")

    op.drop_table("CauHinhPhanCong")

    op.drop_constraint("ck_TaiLieu_soVongKiemDuyetHienTai", "TaiLieu", type_="check")
    op.drop_column("TaiLieu", "soVongKiemDuyetHienTai")

    op.drop_constraint("ck_KhoaHoc_visible_requires_approved", "KhoaHoc", type_="check")
    op.drop_constraint("ck_KhoaHoc_soVongKiemDuyetHienTai", "KhoaHoc", type_="check")
    op.drop_column("KhoaHoc", "soVongKiemDuyetHienTai")

    op.drop_constraint("ck_ChuyenGia_chuKyKyLuatSo", "ChuyenGia", type_="check")
    op.drop_column("ChuyenGia", "mocChuKyKyLuat")
    op.drop_column("ChuyenGia", "chuKyKyLuatSo")
