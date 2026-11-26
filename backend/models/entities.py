from __future__ import annotations

from datetime import datetime
from decimal import Decimal
import uuid

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    String,
    Text,
    UniqueConstraint,
    text,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from config.database import Base


class NguoiDung(Base):
    __tablename__ = "NguoiDung"
    __table_args__ = (
        CheckConstraint(
            '"tenTaiKhoan" = lower(btrim("tenTaiKhoan")) '
            'AND "tenTaiKhoan" ~ \'^[a-z0-9._-]{3,50}$\'',
            name="ck_NguoiDung_tenTaiKhoan_format",
        ),
        UniqueConstraint("tenTaiKhoan", name="uq_NguoiDung_tenTaiKhoan"),
    )

    maNguoiDung: Mapped[int] = mapped_column(Integer, primary_key=True)
    maVaiTro: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("VaiTro.maVaiTro"), nullable=True
    )
    tenTaiKhoan: Mapped[str] = mapped_column(String(50), nullable=False)
    hoTen: Mapped[str | None] = mapped_column(String(255), nullable=True)
    email: Mapped[str | None] = mapped_column(String(255), nullable=True)
    matKhau: Mapped[str | None] = mapped_column(String(255), nullable=True)
    soDienThoai: Mapped[str | None] = mapped_column(String(20), nullable=True)
    trangThai: Mapped[str] = mapped_column(
        String(20), nullable=False, default="ACTIVE", server_default="ACTIVE"
    )
    batBuocDoiMatKhau: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False, server_default="false"
    )

    vaiTro: Mapped[VaiTro | None] = relationship(back_populates="nguoiDungs")
    nhaCungCapKhoaHocs: Mapped[list[NhaCungCapKhoaHoc]] = relationship(
        back_populates="nguoiDung"
    )
    donXinNhaCungCaps: Mapped[list[DonXinNhaCungCap]] = relationship(
        back_populates="nguoiDung"
    )
    chuyenGias: Mapped[list[ChuyenGia]] = relationship(
        back_populates="nguoiDung",
        foreign_keys=lambda: [ChuyenGia.maNguoiDung],
    )
    khoaHocDaDuyet: Mapped[list[KhoaHoc]] = relationship(
        back_populates="nguoiDuyet",
        foreign_keys=lambda: [KhoaHoc.maNguoiDuyet],
    )
    lichSuHocTaps: Mapped[list[LichSuHocTap]] = relationship(back_populates="nguoiDung")
    dangKyKhoaHocs: Mapped[list[DangKyKhoaHoc]] = relationship(
        back_populates="nguoiDung"
    )


class VaiTro(Base):
    __tablename__ = "VaiTro"

    maVaiTro: Mapped[int] = mapped_column(Integer, primary_key=True)
    tenVaiTro: Mapped[str | None] = mapped_column(String(100), nullable=True)
    moTa: Mapped[str | None] = mapped_column(Text, nullable=True)

    nguoiDungs: Mapped[list[NguoiDung]] = relationship(back_populates="vaiTro")


class NhaCungCapKhoaHoc(Base):
    __tablename__ = "NhaCungCapKhoaHoc"

    maNhaCungCap: Mapped[int] = mapped_column(Integer, primary_key=True)
    maNguoiDung: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("NguoiDung.maNguoiDung"), nullable=True
    )
    tieuSu: Mapped[str | None] = mapped_column(Text, nullable=True)
    chuyenMon: Mapped[str | None] = mapped_column(String(255), nullable=True)

    nguoiDung: Mapped[NguoiDung | None] = relationship(
        back_populates="nhaCungCapKhoaHocs"
    )
    khoaHocs: Mapped[list[KhoaHoc]] = relationship(back_populates="nhaCungCap")
    taiLieus: Mapped[list[TaiLieu]] = relationship(back_populates="nhaCungCap")


class DonXinNhaCungCap(Base):
    __tablename__ = "DonXinNhaCungCap"

    maDon: Mapped[int] = mapped_column(Integer, primary_key=True)
    maNguoiDung: Mapped[int] = mapped_column(
        Integer, ForeignKey("NguoiDung.maNguoiDung"), nullable=False, index=True
    )
    toChuc: Mapped[str] = mapped_column(String(255), nullable=False)
    kinhNghiem: Mapped[str] = mapped_column(Text, nullable=False)
    lyDoDangKy: Mapped[str] = mapped_column(Text, nullable=False)
    chuyenMon: Mapped[str | None] = mapped_column(String(255), nullable=True)
    gioiThieu: Mapped[str | None] = mapped_column(Text, nullable=True)
    trangThai: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        default="PENDING",
        server_default="PENDING",
        index=True,
    )
    lyDoTuChoi: Mapped[str | None] = mapped_column(Text, nullable=True)
    ngayGui: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    ngayXuLy: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    nguoiDung: Mapped[NguoiDung] = relationship(back_populates="donXinNhaCungCaps")


class DanhMuc(Base):
    __tablename__ = "DanhMuc"

    maDanhMuc: Mapped[int] = mapped_column(Integer, primary_key=True)
    tenDanhMuc: Mapped[str | None] = mapped_column(String(255), nullable=True)
    moTa: Mapped[str | None] = mapped_column(Text, nullable=True)

    khoaHocs: Mapped[list[KhoaHoc]] = relationship(back_populates="danhMuc")
    taiLieus: Mapped[list[TaiLieu]] = relationship(back_populates="danhMuc")
    chuyenMonLinks: Mapped[list[ChuyenMonDanhMuc]] = relationship(
        back_populates="danhMuc",
        cascade="all, delete-orphan",
    )


class KhoaHoc(Base):
    __tablename__ = "KhoaHoc"
    __table_args__ = (
        CheckConstraint(
            '"gia" IS NULL OR "gia" >= 0',
            name="ck_KhoaHoc_gia_non_negative",
        ),
    )

    maKhoaHoc: Mapped[int] = mapped_column(Integer, primary_key=True)
    maNhaCungCap: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("NhaCungCapKhoaHoc.maNhaCungCap"), nullable=True
    )
    maDanhMuc: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("DanhMuc.maDanhMuc"), nullable=True
    )
    maNguoiDuyet: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("NguoiDung.maNguoiDung"), nullable=True
    )
    tieuDe: Mapped[str | None] = mapped_column(String(255), nullable=True)
    moTa: Mapped[str | None] = mapped_column(Text, nullable=True)
    hinhAnh: Mapped[str | None] = mapped_column(String(500), nullable=True)
    gia: Mapped[Decimal | None] = mapped_column(Numeric, nullable=True)
    trinhDo: Mapped[str | None] = mapped_column(String(100), nullable=True)
    thoiLuong: Mapped[int | None] = mapped_column(Integer, nullable=True)
    trangThaiDuyet: Mapped[str | None] = mapped_column(String(50), nullable=True)
    trangThaiHienThi: Mapped[str | None] = mapped_column(String(50), nullable=True)
    lyDoTuChoi: Mapped[str | None] = mapped_column(Text, nullable=True)
    ngayDuyet: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    ngayTao: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    ngayCapNhat: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    soVongKiemDuyetHienTai: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0, server_default=text("0")
    )

    nhaCungCap: Mapped[NhaCungCapKhoaHoc | None] = relationship(
        back_populates="khoaHocs"
    )
    danhMuc: Mapped[DanhMuc | None] = relationship(back_populates="khoaHocs")
    nguoiDuyet: Mapped[NguoiDung | None] = relationship(
        back_populates="khoaHocDaDuyet",
        foreign_keys=lambda: [KhoaHoc.maNguoiDuyet],
    )
    baiHocs: Mapped[list[BaiHoc]] = relationship(back_populates="khoaHoc")
    taiLieus: Mapped[list[TaiLieu]] = relationship(back_populates="khoaHoc")
    danhGiaChuyenGias: Mapped[list[DanhGiaChuyenGia]] = relationship(
        back_populates="khoaHoc"
    )
    lichSuHocTaps: Mapped[list[LichSuHocTap]] = relationship(back_populates="khoaHoc")
    dangKyKhoaHocs: Mapped[list[DangKyKhoaHoc]] = relationship(back_populates="khoaHoc")


class BaiHoc(Base):
    __tablename__ = "BaiHoc"

    maBaiHoc: Mapped[int] = mapped_column(Integer, primary_key=True)
    maKhoaHoc: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("KhoaHoc.maKhoaHoc"), nullable=True
    )
    tieuDe: Mapped[str | None] = mapped_column(String(255), nullable=True)
    noiDung: Mapped[str | None] = mapped_column(Text, nullable=True)
    duongDanVideo: Mapped[str | None] = mapped_column(String(500), nullable=True)
    thoiLuong: Mapped[int | None] = mapped_column(Integer, nullable=True)
    thuTu: Mapped[int | None] = mapped_column(Integer, nullable=True)
    ngayTao: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    khoaHoc: Mapped[KhoaHoc | None] = relationship(back_populates="baiHocs")
    taiLieus: Mapped[list[TaiLieu]] = relationship(back_populates="baiHoc")
    lichSuHocTaps: Mapped[list[LichSuHocTap]] = relationship(back_populates="baiHoc")


class TaiLieu(Base):
    __tablename__ = "TaiLieu"

    maTaiLieu: Mapped[int] = mapped_column(Integer, primary_key=True)
    maNhaCungCap: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("NhaCungCapKhoaHoc.maNhaCungCap"), nullable=True
    )
    maKhoaHoc: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("KhoaHoc.maKhoaHoc"), nullable=True
    )
    maBaiHoc: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("BaiHoc.maBaiHoc"), nullable=True
    )
    maDanhMuc: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("DanhMuc.maDanhMuc"), nullable=True
    )
    tieuDe: Mapped[str | None] = mapped_column(String(255), nullable=True)
    duongDanTep: Mapped[str | None] = mapped_column(String(500), nullable=True)
    loai: Mapped[str | None] = mapped_column(String(100), nullable=True)
    moTa: Mapped[str | None] = mapped_column(Text, nullable=True)
    trangThaiDuyet: Mapped[str] = mapped_column(
        String(50), nullable=False, default="PENDING", server_default="PENDING"
    )
    trangThaiHienThi: Mapped[str] = mapped_column(
        String(50), nullable=False, default="VISIBLE", server_default="VISIBLE"
    )
    lyDoTuChoi: Mapped[str | None] = mapped_column(Text, nullable=True)
    maNguoiDuyet: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("NguoiDung.maNguoiDung"), nullable=True
    )
    ngayDuyet: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    ngayTao: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    ngayCapNhat: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    soVongKiemDuyetHienTai: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0, server_default=text("0")
    )

    nhaCungCap: Mapped[NhaCungCapKhoaHoc | None] = relationship(back_populates="taiLieus")
    khoaHoc: Mapped[KhoaHoc | None] = relationship(back_populates="taiLieus")
    baiHoc: Mapped[BaiHoc | None] = relationship(back_populates="taiLieus")
    danhMuc: Mapped[DanhMuc | None] = relationship(back_populates="taiLieus")
    nguoiDuyet: Mapped[NguoiDung | None] = relationship(
        foreign_keys=lambda: [TaiLieu.maNguoiDuyet]
    )
    danhGiaChuyenGias: Mapped[list[DanhGiaChuyenGia]] = relationship(
        back_populates="taiLieu"
    )

    @property
    def nguonPheDuyet(self) -> str:
        if self.trangThaiDuyet != "APPROVED":
            return "UNAPPROVED"
        if self.maNguoiDuyet is not None or self.ngayDuyet is not None:
            return "EXPERT_REVIEW"
        return "LEGACY_BACKFILL"


class ChuyenMon(Base):
    __tablename__ = "ChuyenMon"

    maChuyenMon: Mapped[int] = mapped_column(Integer, primary_key=True)
    tenChuyenMon: Mapped[str] = mapped_column(String(255), nullable=False)
    nhomChuyenMon: Mapped[str] = mapped_column(String(100), nullable=False)
    moTa: Mapped[str | None] = mapped_column(Text, nullable=True)
    trangThai: Mapped[str] = mapped_column(
        String(20), nullable=False, default="ACTIVE", server_default="ACTIVE"
    )
    maNguoiTao: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("NguoiDung.maNguoiDung", ondelete="SET NULL"), nullable=True
    )
    ngayTao: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    ngayCapNhat: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    nguoiTao: Mapped[NguoiDung | None] = relationship(
        foreign_keys=lambda: [ChuyenMon.maNguoiTao]
    )
    danhMucLinks: Mapped[list[ChuyenMonDanhMuc]] = relationship(
        back_populates="chuyenMon",
        cascade="all, delete-orphan",
    )
    chuyenGiaLinks: Mapped[list[ChuyenGiaChuyenMon]] = relationship(
        back_populates="chuyenMon"
    )


class ChuyenMonDanhMuc(Base):
    __tablename__ = "ChuyenMonDanhMuc"

    maChuyenMon: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("ChuyenMon.maChuyenMon", ondelete="CASCADE"),
        primary_key=True,
    )
    maDanhMuc: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("DanhMuc.maDanhMuc", ondelete="CASCADE"),
        primary_key=True,
    )
    ngayTao: Mapped[datetime] = mapped_column(DateTime, nullable=False)

    chuyenMon: Mapped[ChuyenMon] = relationship(back_populates="danhMucLinks")
    danhMuc: Mapped[DanhMuc] = relationship(back_populates="chuyenMonLinks")


class ChuyenGiaChuyenMon(Base):
    __tablename__ = "ChuyenGiaChuyenMon"

    maChuyenGia: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("ChuyenGia.maChuyenGia", ondelete="CASCADE"),
        primary_key=True,
    )
    maChuyenMon: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("ChuyenMon.maChuyenMon", ondelete="RESTRICT"),
        primary_key=True,
    )
    laChuyenMonChinh: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False, server_default="false"
    )
    ngayTao: Mapped[datetime] = mapped_column(DateTime, nullable=False)

    chuyenGia: Mapped[ChuyenGia] = relationship(back_populates="chuyenMonLinks")
    chuyenMon: Mapped[ChuyenMon] = relationship(back_populates="chuyenGiaLinks")


class ChuyenGia(Base):
    __tablename__ = "ChuyenGia"

    maChuyenGia: Mapped[int] = mapped_column(Integer, primary_key=True)
    maNguoiDung: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("NguoiDung.maNguoiDung"), nullable=True
    )
    chuyenMon: Mapped[str | None] = mapped_column(String(255), nullable=True)
    tieuSu: Mapped[str | None] = mapped_column(Text, nullable=True)
    soNamKinhNghiem: Mapped[int | None] = mapped_column(Integer, nullable=True)
    trangThaiHoSo: Mapped[str] = mapped_column(
        String(30), nullable=False, default="DRAFT", server_default="DRAFT"
    )
    ghiChuXacMinh: Mapped[str | None] = mapped_column(Text, nullable=True)
    maNguoiXacMinh: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("NguoiDung.maNguoiDung", ondelete="SET NULL"), nullable=True
    )
    ngayXacMinh: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    ngayCapNhat: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    chuKyKyLuatSo: Mapped[int] = mapped_column(
        Integer, nullable=False, default=1, server_default=text("1")
    )
    mocChuKyKyLuat: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    nguoiDung: Mapped[NguoiDung | None] = relationship(
        back_populates="chuyenGias",
        foreign_keys=lambda: [ChuyenGia.maNguoiDung],
    )
    nguoiXacMinh: Mapped[NguoiDung | None] = relationship(
        foreign_keys=lambda: [ChuyenGia.maNguoiXacMinh],
    )
    chuyenMonLinks: Mapped[list[ChuyenGiaChuyenMon]] = relationship(
        back_populates="chuyenGia",
        cascade="all, delete-orphan",
    )
    danhGiaChuyenGias: Mapped[list[DanhGiaChuyenGia]] = relationship(
        back_populates="chuyenGia"
    )


class DanhGiaChuyenGia(Base):
    __tablename__ = "DanhGiaChuyenGia"

    maDanhGia: Mapped[int] = mapped_column(Integer, primary_key=True)
    maKhoaHoc: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("KhoaHoc.maKhoaHoc"), nullable=True
    )
    maTaiLieu: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("TaiLieu.maTaiLieu"), nullable=True
    )
    maChuyenGia: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("ChuyenGia.maChuyenGia"), nullable=True
    )
    maPhanCong: Mapped[int | None] = mapped_column(
        Integer,
        ForeignKey("PhanCongKiemDuyet.maPhanCong", ondelete="RESTRICT"),
        nullable=True,
    )
    noiDungDanhGia: Mapped[str | None] = mapped_column(Text, nullable=True)
    diemKyThuat: Mapped[Decimal | None] = mapped_column(Numeric, nullable=True)
    diemNoiDung: Mapped[Decimal | None] = mapped_column(Numeric, nullable=True)
    ghiChu: Mapped[str | None] = mapped_column(Text, nullable=True)
    trangThai: Mapped[str | None] = mapped_column(String(50), nullable=True)
    ngayTao: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    khoaHoc: Mapped[KhoaHoc | None] = relationship(back_populates="danhGiaChuyenGias")
    taiLieu: Mapped[TaiLieu | None] = relationship(back_populates="danhGiaChuyenGias")
    chuyenGia: Mapped[ChuyenGia | None] = relationship(
        back_populates="danhGiaChuyenGias"
    )
    phanCong: Mapped[PhanCongKiemDuyet | None] = relationship(
        back_populates="danhGia",
        foreign_keys=lambda: [DanhGiaChuyenGia.maPhanCong],
    )


class LichSuHocTap(Base):
    __tablename__ = "LichSuHocTap"

    maLichSu: Mapped[int] = mapped_column(Integer, primary_key=True)
    maNguoiDung: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("NguoiDung.maNguoiDung"), nullable=True
    )
    maKhoaHoc: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("KhoaHoc.maKhoaHoc"), nullable=True
    )
    maBaiHoc: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("BaiHoc.maBaiHoc"), nullable=True
    )
    tienDo: Mapped[str | None] = mapped_column(String(100), nullable=True)
    thoiGianXem: Mapped[int | None] = mapped_column(Integer, nullable=True)
    danhGia: Mapped[Decimal | None] = mapped_column(Numeric, nullable=True)
    ngayTao: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    nguoiDung: Mapped[NguoiDung | None] = relationship(back_populates="lichSuHocTaps")
    khoaHoc: Mapped[KhoaHoc | None] = relationship(back_populates="lichSuHocTaps")
    baiHoc: Mapped[BaiHoc | None] = relationship(back_populates="lichSuHocTaps")


class DangKyKhoaHoc(Base):
    __tablename__ = "DangKyKhoaHoc"
    __table_args__ = (
        UniqueConstraint(
            "maNguoiDung",
            "maKhoaHoc",
            name="uq_DangKyKhoaHoc_user_course",
        ),
        CheckConstraint(
            '"trangThaiQuyenHoc" IN (\'ACTIVE\', \'REVOKED\')',
            name="ck_DangKyKhoaHoc_trangThaiQuyenHoc",
        ),
        CheckConstraint(
            '"nguonCapQuyen" IN (\'LEGACY\', \'FREE\', \'PURCHASE\')',
            name="ck_DangKyKhoaHoc_nguonCapQuyen",
        ),
    )

    maDangKy: Mapped[int] = mapped_column(Integer, primary_key=True)
    maNguoiDung: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("NguoiDung.maNguoiDung"), nullable=True
    )
    maKhoaHoc: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("KhoaHoc.maKhoaHoc"), nullable=True
    )
    ngayDangKy: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    tienDo: Mapped[Decimal | None] = mapped_column(Numeric, nullable=True)
    ngayHoanThanh: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    maDonHang: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("DonHang.maDonHang", ondelete="RESTRICT"), nullable=True
    )
    nguonCapQuyen: Mapped[str] = mapped_column(
        String(20), nullable=False, default="LEGACY", server_default=text("'LEGACY'")
    )
    trangThaiQuyenHoc: Mapped[str] = mapped_column(
        String(20), nullable=False, default="ACTIVE", server_default=text("'ACTIVE'")
    )
    ngayThuHoi: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    lyDoThuHoi: Mapped[str | None] = mapped_column(Text, nullable=True)

    nguoiDung: Mapped[NguoiDung | None] = relationship(back_populates="dangKyKhoaHocs")
    khoaHoc: Mapped[KhoaHoc | None] = relationship(back_populates="dangKyKhoaHocs")
    donHang: Mapped[DonHang | None] = relationship(
        foreign_keys=lambda: [DangKyKhoaHoc.maDonHang]
    )


class TokenBiThuHoi(Base):
    __tablename__ = "TokenBiThuHoi"

    maToken: Mapped[int] = mapped_column(Integer, primary_key=True)
    jti: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    thoiGianHetHan: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    ngayTao: Mapped[datetime] = mapped_column(DateTime, nullable=False)


class CauHinhPhanCong(Base):
    __tablename__ = "CauHinhPhanCong"

    maCauHinh: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=False)
    gioiHanTaiToiDa: Mapped[int] = mapped_column(Integer, nullable=False, default=5, server_default=text("5"))
    hanTiepNhanGio: Mapped[int] = mapped_column(Integer, nullable=False, default=24, server_default=text("24"))
    hanKiemDuyetGio: Mapped[int] = mapped_column(Integer, nullable=False, default=72, server_default=text("72"))
    khoangThongKeGio: Mapped[int] = mapped_column(Integer, nullable=False, default=168, server_default=text("168"))
    nguongCanhBao: Mapped[int] = mapped_column(Integer, nullable=False, default=2, server_default=text("2"))
    nguongKhoaTaiKhoan: Mapped[int] = mapped_column(Integer, nullable=False, default=4, server_default=text("4"))
    tinhViPhamHetHan: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True, server_default=text("true"))
    tuDongKhoa: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True, server_default=text("true"))
    thoiGianTamNgungToiDaNgay: Mapped[int] = mapped_column(Integer, nullable=False, default=30, server_default=text("30"))
    soLanTaiPhanCongToiDa: Mapped[int] = mapped_column(Integer, nullable=False, default=5, server_default=text("5"))
    uuTienTuyetDoiChuyenMonChinh: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, server_default=text("false"))
    maNguoiCapNhat: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("NguoiDung.maNguoiDung", ondelete="SET NULL"), nullable=True
    )
    ngayCapNhat: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, server_default=text("(CURRENT_TIMESTAMP AT TIME ZONE 'UTC')")
    )

    nguoiCapNhat: Mapped[NguoiDung | None] = relationship(
        foreign_keys=lambda: [CauHinhPhanCong.maNguoiCapNhat]
    )


class PhanCongKiemDuyet(Base):
    __tablename__ = "PhanCongKiemDuyet"

    maPhanCong: Mapped[int] = mapped_column(Integer, primary_key=True)
    maKhoaHoc: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("KhoaHoc.maKhoaHoc", ondelete="RESTRICT"), nullable=True
    )
    maTaiLieu: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("TaiLieu.maTaiLieu", ondelete="RESTRICT"), nullable=True
    )
    maChuyenGia: Mapped[int] = mapped_column(
        Integer, ForeignKey("ChuyenGia.maChuyenGia", ondelete="RESTRICT"), nullable=False
    )
    maDanhMuc: Mapped[int] = mapped_column(
        Integer, ForeignKey("DanhMuc.maDanhMuc", ondelete="RESTRICT"), nullable=False
    )
    maChuyenMonKhop: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("ChuyenMon.maChuyenMon", ondelete="RESTRICT"), nullable=True
    )
    soVongKiemDuyet: Mapped[int] = mapped_column(Integer, nullable=False, default=1, server_default=text("1"))
    phuongThucPhanCong: Mapped[str] = mapped_column(String(20), nullable=False, default="AUTO", server_default=text("'AUTO'"))
    maNguoiPhanCong: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("NguoiDung.maNguoiDung", ondelete="RESTRICT"), nullable=True
    )
    diemPhuHop: Mapped[Decimal | None] = mapped_column(Numeric(5, 2), nullable=True)
    chiTietDiem: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    lyDoPhanCong: Mapped[str | None] = mapped_column(Text, nullable=True)
    trangThai: Mapped[str] = mapped_column(String(30), nullable=False, default="ASSIGNED", server_default=text("'ASSIGNED'"))
    ngayPhanCong: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, server_default=text("(CURRENT_TIMESTAMP AT TIME ZONE 'UTC')")
    )
    hanTiepNhan: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    hanKiemDuyet: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    ngayChapNhan: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    ngayBatDau: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    ngayHoanThanh: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    maLyDoTuChoi: Mapped[str | None] = mapped_column(String(50), nullable=True)
    lyDoTuChoi: Mapped[str | None] = mapped_column(Text, nullable=True)
    lyDoHuy: Mapped[str | None] = mapped_column(Text, nullable=True)
    banNhapDanhGia: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    ngayCapNhat: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, server_default=text("(CURRENT_TIMESTAMP AT TIME ZONE 'UTC')")
    )

    khoaHoc: Mapped[KhoaHoc | None] = relationship(foreign_keys=lambda: [PhanCongKiemDuyet.maKhoaHoc])
    taiLieu: Mapped[TaiLieu | None] = relationship(foreign_keys=lambda: [PhanCongKiemDuyet.maTaiLieu])
    chuyenGia: Mapped[ChuyenGia] = relationship(foreign_keys=lambda: [PhanCongKiemDuyet.maChuyenGia])
    danhMuc: Mapped[DanhMuc] = relationship(foreign_keys=lambda: [PhanCongKiemDuyet.maDanhMuc])
    chuyenMonKhop: Mapped[ChuyenMon | None] = relationship(foreign_keys=lambda: [PhanCongKiemDuyet.maChuyenMonKhop])
    nguoiPhanCong: Mapped[NguoiDung | None] = relationship(foreign_keys=lambda: [PhanCongKiemDuyet.maNguoiPhanCong])
    danhGia: Mapped[DanhGiaChuyenGia | None] = relationship(
        back_populates="phanCong",
        uselist=False,
        passive_deletes=True,
    )
    viPham: Mapped[ViPhamChuyenGia | None] = relationship(
        back_populates="phanCong",
        uselist=False,
        passive_deletes=True,
    )


class HangDoiPhanCong(Base):
    __tablename__ = "HangDoiPhanCong"

    maCongViec: Mapped[int] = mapped_column(Integer, primary_key=True)
    loaiDoiTuong: Mapped[str] = mapped_column(String(20), nullable=False)
    maKhoaHoc: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("KhoaHoc.maKhoaHoc", ondelete="CASCADE"), nullable=True
    )
    maTaiLieu: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("TaiLieu.maTaiLieu", ondelete="CASCADE"), nullable=True
    )
    soVongKiemDuyet: Mapped[int] = mapped_column(Integer, nullable=False)
    loaiSuKien: Mapped[str] = mapped_column(String(30), nullable=False)
    maPhanCongNguon: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("PhanCongKiemDuyet.maPhanCong", ondelete="SET NULL"), nullable=True
    )
    khoaChongTrung: Mapped[str] = mapped_column(String(150), nullable=False, unique=True)
    trangThai: Mapped[str] = mapped_column(String(30), nullable=False, default="PENDING", server_default=text("'PENDING'"))
    uuTien: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default=text("0"))
    soLanThu: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default=text("0"))
    soLanThuToiDa: Mapped[int] = mapped_column(Integer, nullable=False, default=5, server_default=text("5"))
    thoiDiemChayTiepTheo: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, server_default=text("(CURRENT_TIMESTAMP AT TIME ZONE 'UTC')")
    )
    maWorker: Mapped[str | None] = mapped_column(String(100), nullable=True)
    claimToken: Mapped[uuid.UUID | None] = mapped_column(PG_UUID(as_uuid=True), nullable=True)
    leaseGeneration: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default=text("0"))
    thoiDiemBatDauXuLy: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    hanXuLy: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    lyDoCho: Mapped[str | None] = mapped_column(Text, nullable=True)
    loiGanNhat: Mapped[str | None] = mapped_column(Text, nullable=True)
    ngayTao: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, server_default=text("(CURRENT_TIMESTAMP AT TIME ZONE 'UTC')")
    )
    ngayCapNhat: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, server_default=text("(CURRENT_TIMESTAMP AT TIME ZONE 'UTC')")
    )

    khoaHoc: Mapped[KhoaHoc | None] = relationship(foreign_keys=lambda: [HangDoiPhanCong.maKhoaHoc])
    taiLieu: Mapped[TaiLieu | None] = relationship(foreign_keys=lambda: [HangDoiPhanCong.maTaiLieu])
    phanCongNguon: Mapped[PhanCongKiemDuyet | None] = relationship(foreign_keys=lambda: [HangDoiPhanCong.maPhanCongNguon])


class ViPhamChuyenGia(Base):
    __tablename__ = "ViPhamChuyenGia"

    maViPham: Mapped[int] = mapped_column(Integer, primary_key=True)
    maChuyenGia: Mapped[int] = mapped_column(
        Integer, ForeignKey("ChuyenGia.maChuyenGia", ondelete="RESTRICT"), nullable=False
    )
    maPhanCong: Mapped[int] = mapped_column(
        Integer, ForeignKey("PhanCongKiemDuyet.maPhanCong", ondelete="RESTRICT"), nullable=False, unique=True
    )
    loaiViPham: Mapped[str] = mapped_column(String(40), nullable=False)
    maLyDoTuChoi: Mapped[str | None] = mapped_column(String(50), nullable=True)
    lyDo: Mapped[str | None] = mapped_column(Text, nullable=True)
    trangThaiXuLy: Mapped[str] = mapped_column(
        String(30), nullable=False, default="PENDING_REVIEW", server_default=text("'PENDING_REVIEW'")
    )
    chuKyKyLuatSo: Mapped[int] = mapped_column(Integer, nullable=False, default=1, server_default=text("1"))
    mocChuKyApDung: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    ngayViPham: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, server_default=text("(CURRENT_TIMESTAMP AT TIME ZONE 'UTC')")
    )
    maNguoiXuLy: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("NguoiDung.maNguoiDung", ondelete="SET NULL"), nullable=True
    )
    ngayXuLy: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    ghiChuXuLy: Mapped[str | None] = mapped_column(Text, nullable=True)

    chuyenGia: Mapped[ChuyenGia] = relationship(foreign_keys=lambda: [ViPhamChuyenGia.maChuyenGia])
    phanCong: Mapped[PhanCongKiemDuyet] = relationship(
        back_populates="viPham",
        foreign_keys=lambda: [ViPhamChuyenGia.maPhanCong],
    )
    nguoiXuLy: Mapped[NguoiDung | None] = relationship(foreign_keys=lambda: [ViPhamChuyenGia.maNguoiXuLy])


class NhatKyKyLuatChuyenGia(Base):
    __tablename__ = "NhatKyKyLuatChuyenGia"

    maNhatKy: Mapped[int] = mapped_column(Integer, primary_key=True)
    maChuyenGia: Mapped[int] = mapped_column(
        Integer, ForeignKey("ChuyenGia.maChuyenGia", ondelete="RESTRICT"), nullable=False
    )
    maNguoiDung: Mapped[int] = mapped_column(
        Integer, ForeignKey("NguoiDung.maNguoiDung", ondelete="RESTRICT"), nullable=False
    )
    hanhDong: Mapped[str] = mapped_column(String(40), nullable=False)
    nguonThucHien: Mapped[str] = mapped_column(String(20), nullable=False)
    maNguoiThucHien: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("NguoiDung.maNguoiDung", ondelete="RESTRICT"), nullable=True
    )
    chuKyKyLuatSo: Mapped[int] = mapped_column(Integer, nullable=False, default=1, server_default=text("1"))
    trangThaiTruoc: Mapped[str | None] = mapped_column(String(30), nullable=True)
    trangThaiSau: Mapped[str | None] = mapped_column(String(30), nullable=True)
    soViPhamTaiThoiDiem: Mapped[int | None] = mapped_column(Integer, nullable=True)
    lyDo: Mapped[str] = mapped_column(Text, nullable=False)
    chinhSachSnapshot: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    ngayTao: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, server_default=text("(CURRENT_TIMESTAMP AT TIME ZONE 'UTC')")
    )

    chuyenGia: Mapped[ChuyenGia] = relationship(foreign_keys=lambda: [NhatKyKyLuatChuyenGia.maChuyenGia])
    nguoiDung: Mapped[NguoiDung] = relationship(foreign_keys=lambda: [NhatKyKyLuatChuyenGia.maNguoiDung])
    nguoiThucHien: Mapped[NguoiDung | None] = relationship(foreign_keys=lambda: [NhatKyKyLuatChuyenGia.maNguoiThucHien])


class YeuCauTamNgungChuyenGia(Base):
    __tablename__ = "YeuCauTamNgungChuyenGia"

    maYeuCau: Mapped[int] = mapped_column(Integer, primary_key=True)
    maChuyenGia: Mapped[int] = mapped_column(
        Integer, ForeignKey("ChuyenGia.maChuyenGia", ondelete="RESTRICT"), nullable=False
    )
    ngayBatDau: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    ngayKetThuc: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    lyDo: Mapped[str] = mapped_column(Text, nullable=False)
    trangThai: Mapped[str] = mapped_column(String(20), nullable=False, default="PENDING", server_default=text("'PENDING'"))
    ngayGuiYeuCau: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, server_default=text("(CURRENT_TIMESTAMP AT TIME ZONE 'UTC')")
    )
    maNguoiXuLy: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("NguoiDung.maNguoiDung", ondelete="RESTRICT"), nullable=True
    )
    ngayXuLy: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    ghiChuXuLy: Mapped[str | None] = mapped_column(Text, nullable=True)
    ngayHuy: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    lyDoHuy: Mapped[str | None] = mapped_column(Text, nullable=True)
    ngayCapNhat: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, server_default=text("(CURRENT_TIMESTAMP AT TIME ZONE 'UTC')")
    )

    chuyenGia: Mapped[ChuyenGia] = relationship(foreign_keys=lambda: [YeuCauTamNgungChuyenGia.maChuyenGia])
    nguoiXuLy: Mapped[NguoiDung | None] = relationship(foreign_keys=lambda: [YeuCauTamNgungChuyenGia.maNguoiXuLy])


class ThongBao(Base):
    __tablename__ = "ThongBao"

    maThongBao: Mapped[int] = mapped_column(Integer, primary_key=True)
    maNguoiNhan: Mapped[int] = mapped_column(
        Integer, ForeignKey("NguoiDung.maNguoiDung", ondelete="CASCADE"), nullable=False
    )
    loaiThongBao: Mapped[str] = mapped_column(String(50), nullable=False)
    tieuDe: Mapped[str] = mapped_column(String(255), nullable=False)
    noiDung: Mapped[str] = mapped_column(Text, nullable=False)
    duLieuLienKet: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    daDoc: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, server_default=text("false"))
    khoaChongTrung: Mapped[str | None] = mapped_column(String(150), nullable=True, unique=True)
    ngayTao: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, server_default=text("(CURRENT_TIMESTAMP AT TIME ZONE 'UTC')")
    )
    ngayDoc: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    nguoiNhan: Mapped[NguoiDung] = relationship(foreign_keys=lambda: [ThongBao.maNguoiNhan])


class YeuThich(Base):
    __tablename__ = "YeuThich"
    __table_args__ = (
        UniqueConstraint("maNguoiDung", "maKhoaHoc", name="uq_YeuThich_user_course"),
        Index("ix_YeuThich_maNguoiDung_ngayTao", "maNguoiDung", text('"ngayTao" DESC')),
    )

    maYeuThich: Mapped[int] = mapped_column(Integer, primary_key=True)
    maNguoiDung: Mapped[int] = mapped_column(
        Integer, ForeignKey("NguoiDung.maNguoiDung", ondelete="CASCADE"), nullable=False
    )
    maKhoaHoc: Mapped[int] = mapped_column(
        Integer, ForeignKey("KhoaHoc.maKhoaHoc", ondelete="CASCADE"), nullable=False
    )
    ngayTao: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, server_default=text("(CURRENT_TIMESTAMP AT TIME ZONE 'UTC')")
    )

    nguoiDung: Mapped[NguoiDung] = relationship(foreign_keys=lambda: [YeuThich.maNguoiDung])
    khoaHoc: Mapped[KhoaHoc] = relationship(foreign_keys=lambda: [YeuThich.maKhoaHoc])


class GioHang(Base):
    __tablename__ = "GioHang"
    __table_args__ = (
        UniqueConstraint("maNguoiDung", name="uq_GioHang_maNguoiDung"),
    )

    maGioHang: Mapped[int] = mapped_column(Integer, primary_key=True)
    maNguoiDung: Mapped[int] = mapped_column(
        Integer, ForeignKey("NguoiDung.maNguoiDung", ondelete="CASCADE"), nullable=False
    )
    ngayTao: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, server_default=text("(CURRENT_TIMESTAMP AT TIME ZONE 'UTC')")
    )
    ngayCapNhat: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, server_default=text("(CURRENT_TIMESTAMP AT TIME ZONE 'UTC')")
    )

    nguoiDung: Mapped[NguoiDung] = relationship(foreign_keys=lambda: [GioHang.maNguoiDung])
    chiTiets: Mapped[list[ChiTietGioHang]] = relationship(
        back_populates="gioHang",
        cascade="all, delete-orphan",
    )


class ChiTietGioHang(Base):
    __tablename__ = "ChiTietGioHang"
    __table_args__ = (
        UniqueConstraint("maGioHang", "maKhoaHoc", name="uq_ChiTietGioHang_cart_course"),
        CheckConstraint('"giaLucThem" > 0', name="ck_ChiTietGioHang_giaLucThem_positive"),
        Index("ix_ChiTietGioHang_maGioHang", "maGioHang"),
    )

    maChiTietGioHang: Mapped[int] = mapped_column(Integer, primary_key=True)
    maGioHang: Mapped[int] = mapped_column(
        Integer, ForeignKey("GioHang.maGioHang", ondelete="CASCADE"), nullable=False
    )
    maKhoaHoc: Mapped[int] = mapped_column(
        Integer, ForeignKey("KhoaHoc.maKhoaHoc", ondelete="CASCADE"), nullable=False
    )
    giaLucThem: Mapped[Decimal] = mapped_column(Numeric(12, 0), nullable=False)
    ngayTao: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, server_default=text("(CURRENT_TIMESTAMP AT TIME ZONE 'UTC')")
    )

    gioHang: Mapped[GioHang] = relationship(back_populates="chiTiets")
    khoaHoc: Mapped[KhoaHoc] = relationship(foreign_keys=lambda: [ChiTietGioHang.maKhoaHoc])


class DonHang(Base):
    __tablename__ = "DonHang"
    __table_args__ = (
        UniqueConstraint("maSoDonHang", name="uq_DonHang_maSoDonHang"),
        UniqueConstraint("khoaChongTrung", name="uq_DonHang_khoaChongTrung"),
        CheckConstraint("\"nguonTao\" IN ('CART', 'BUY_NOW')", name="ck_DonHang_nguonTao"),
        CheckConstraint('"tongTien" > 0', name="ck_DonHang_tongTien_positive"),
        CheckConstraint("\"donViTienTe\" = 'VND'", name="ck_DonHang_donViTienTe"),
        CheckConstraint(
            "\"trangThai\" IN ('PENDING', 'PAID', 'FAILED', 'CANCELLED', 'EXPIRED', 'REFUNDED')",
            name="ck_DonHang_trangThai",
        ),
        Index("ix_DonHang_user_created", "maNguoiDung", text('"ngayTao" DESC')),
        Index("ix_DonHang_status_created", "trangThai", text('"ngayTao" DESC')),
        Index(
            "ix_DonHang_pending_expiry",
            "hanThanhToan",
            postgresql_where=text("\"trangThai\" = 'PENDING'"),
        ),
    )

    maDonHang: Mapped[int] = mapped_column(Integer, primary_key=True)
    maSoDonHang: Mapped[str] = mapped_column(String(32), nullable=False)
    maNguoiDung: Mapped[int] = mapped_column(
        Integer, ForeignKey("NguoiDung.maNguoiDung", ondelete="RESTRICT"), nullable=False
    )
    nguonTao: Mapped[str] = mapped_column(String(20), nullable=False)
    tongTien: Mapped[Decimal] = mapped_column(Numeric(12, 0), nullable=False)
    donViTienTe: Mapped[str] = mapped_column(
        String(3), nullable=False, default="VND", server_default=text("'VND'")
    )
    trangThai: Mapped[str] = mapped_column(
        String(20), nullable=False, default="PENDING", server_default=text("'PENDING'")
    )
    khoaChongTrung: Mapped[str] = mapped_column(String(100), nullable=False)
    hanThanhToan: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    ngayThanhToan: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    ngayHuy: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    ngayHoanTien: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    lyDoHuyHoacHoan: Mapped[str | None] = mapped_column(Text, nullable=True)
    ngayTao: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, server_default=text("(CURRENT_TIMESTAMP AT TIME ZONE 'UTC')")
    )
    ngayCapNhat: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, server_default=text("(CURRENT_TIMESTAMP AT TIME ZONE 'UTC')")
    )

    nguoiDung: Mapped[NguoiDung] = relationship(foreign_keys=lambda: [DonHang.maNguoiDung])
    chiTiets: Mapped[list[ChiTietDonHang]] = relationship(back_populates="donHang")
    thanhToans: Mapped[list[ThanhToan]] = relationship(back_populates="donHang")


class ChiTietDonHang(Base):
    __tablename__ = "ChiTietDonHang"
    __table_args__ = (
        UniqueConstraint("maDonHang", "maKhoaHoc", name="uq_ChiTietDonHang_order_course"),
        CheckConstraint('"giaTaiThoiDiemMua" > 0', name="ck_ChiTietDonHang_gia_positive"),
        Index("ix_ChiTietDonHang_provider_created", "maNhaCungCap", text('"ngayTao" DESC')),
        Index("ix_ChiTietDonHang_course", "maKhoaHoc"),
    )

    maChiTietDonHang: Mapped[int] = mapped_column(Integer, primary_key=True)
    maDonHang: Mapped[int] = mapped_column(
        Integer, ForeignKey("DonHang.maDonHang", ondelete="RESTRICT"), nullable=False
    )
    maKhoaHoc: Mapped[int] = mapped_column(
        Integer, ForeignKey("KhoaHoc.maKhoaHoc", ondelete="RESTRICT"), nullable=False
    )
    maNhaCungCap: Mapped[int] = mapped_column(
        Integer, ForeignKey("NhaCungCapKhoaHoc.maNhaCungCap", ondelete="RESTRICT"), nullable=False
    )
    tieuDeSnapshot: Mapped[str] = mapped_column(String(255), nullable=False)
    giaTaiThoiDiemMua: Mapped[Decimal] = mapped_column(Numeric(12, 0), nullable=False)
    ngayTao: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, server_default=text("(CURRENT_TIMESTAMP AT TIME ZONE 'UTC')")
    )

    donHang: Mapped[DonHang] = relationship(back_populates="chiTiets")
    khoaHoc: Mapped[KhoaHoc] = relationship(foreign_keys=lambda: [ChiTietDonHang.maKhoaHoc])
    nhaCungCap: Mapped[NhaCungCapKhoaHoc] = relationship(
        foreign_keys=lambda: [ChiTietDonHang.maNhaCungCap]
    )


class ThanhToan(Base):
    __tablename__ = "ThanhToan"
    __table_args__ = (
        UniqueConstraint("maGiaoDichNoiBo", name="uq_ThanhToan_maGiaoDichNoiBo"),
        UniqueConstraint("khoaChongTrung", name="uq_ThanhToan_khoaChongTrung"),
        CheckConstraint(
            "\"congThanhToan\" IN ('MOCK_SANDBOX', 'VNPAY_SANDBOX')",
            name="ck_ThanhToan_congThanhToan",
        ),
        CheckConstraint('"soTien" > 0', name="ck_ThanhToan_soTien_positive"),
        CheckConstraint('"soTienDaThuThucTe" >= 0', name="ck_ThanhToan_soTienDaThuThucTe_non_negative"),
        CheckConstraint("\"donViTienTe\" = 'VND'", name="ck_ThanhToan_donViTienTe"),
        CheckConstraint(
            "\"trangThai\" IN ('PENDING', 'PAID', 'CAPTURED_UNAPPLIED', 'FAILED', 'CANCELLED', 'EXPIRED', 'REFUNDED', 'PARTIALLY_REFUNDED')",
            name="ck_ThanhToan_trangThai",
        ),
        Index(
            "uq_ThanhToan_maGiaoDichCong_not_null",
            "maGiaoDichCong",
            unique=True,
            postgresql_where=text('"maGiaoDichCong" IS NOT NULL'),
        ),
        Index(
            "uq_ThanhToan_one_paid_per_order",
            "maDonHang",
            unique=True,
            postgresql_where=text("\"trangThai\" = 'PAID'"),
        ),
        Index("ix_ThanhToan_order_created", "maDonHang", text('"ngayTao" DESC')),
        Index("ix_ThanhToan_user_created", "maNguoiDung", text('"ngayTao" DESC')),
    )

    maThanhToan: Mapped[int] = mapped_column(Integer, primary_key=True)
    maDonHang: Mapped[int] = mapped_column(
        Integer, ForeignKey("DonHang.maDonHang", ondelete="RESTRICT"), nullable=False
    )
    maNguoiDung: Mapped[int] = mapped_column(
        Integer, ForeignKey("NguoiDung.maNguoiDung", ondelete="RESTRICT"), nullable=False
    )
    congThanhToan: Mapped[str] = mapped_column(String(30), nullable=False)
    maGiaoDichNoiBo: Mapped[str] = mapped_column(String(64), nullable=False)
    maGiaoDichCong: Mapped[str | None] = mapped_column(String(100), nullable=True)
    soTien: Mapped[Decimal] = mapped_column(Numeric(12, 0), nullable=False)
    donViTienTe: Mapped[str] = mapped_column(
        String(3), nullable=False, default="VND", server_default=text("'VND'")
    )
    trangThai: Mapped[str] = mapped_column(
        String(30), nullable=False, default="PENDING", server_default=text("'PENDING'")
    )
    daThuTien: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False, server_default=text("false")
    )
    soTienDaThuThucTe: Mapped[Decimal] = mapped_column(
        Numeric(12, 0), nullable=False, default=Decimal("0"), server_default=text("0")
    )
    khoaChongTrung: Mapped[str] = mapped_column(String(100), nullable=False)
    maPhanHoiCong: Mapped[str | None] = mapped_column(String(32), nullable=True)
    duLieuPhanHoiAnToan: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    daXacMinhChuKy: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False, server_default=text("false")
    )
    ngayThanhToan: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    ngayTao: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, server_default=text("(CURRENT_TIMESTAMP AT TIME ZONE 'UTC')")
    )
    ngayCapNhat: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, server_default=text("(CURRENT_TIMESTAMP AT TIME ZONE 'UTC')")
    )

    donHang: Mapped[DonHang] = relationship(back_populates="thanhToans")
    nguoiDung: Mapped[NguoiDung] = relationship(foreign_keys=lambda: [ThanhToan.maNguoiDung])
    hoanTiens: Mapped[list[HoanTienNgoaiLe]] = relationship(back_populates="thanhToan")
    baoCaoSuCos: Mapped[list[BaoCaoSuCoThanhToan]] = relationship(back_populates="thanhToan")


class HoanTienNgoaiLe(Base):
    """GĐ4.7A.2 Normalized Exception Refund Ledger (zero buyer's-remorse refunds)."""

    __tablename__ = "HoanTienNgoaiLe"
    __table_args__ = (
        UniqueConstraint("maSoHoanTien", name="uq_HoanTienNgoaiLe_maSoHoanTien"),
        UniqueConstraint("khoaChongTrung", name="uq_HoanTienNgoaiLe_khoaChongTrung"),
        CheckConstraint(
            "\"phamViHoan\" IN ('EXCESS_PAYMENT', 'FULL_ORDER', 'PARTIAL_OVERCHARGE')",
            name="ck_HoanTienNgoaiLe_phamViHoan",
        ),
        CheckConstraint(
            "\"loaiSuCo\" IN ('DUPLICATE_CHARGE', 'WRONG_AMOUNT', 'CANNOT_PROVISION_COURSE', "
            "'LATE_AFTER_CANCEL', 'LATE_AFTER_EXPIRE', 'SYSTEM_ERROR', 'REGULATORY')",
            name="ck_HoanTienNgoaiLe_loaiSuCo",
        ),
        CheckConstraint(
            "\"trangThai\" IN ('PENDING_REVIEW', 'VERIFIED', 'REFUND_PENDING', 'REFUNDED', "
            "'REFUND_FAILED', 'UNKNOWN', 'REJECTED')",
            name="ck_HoanTienNgoaiLe_trangThai",
        ),
        CheckConstraint("\"donViTienTe\" = 'VND'", name="ck_HoanTienNgoaiLe_donViTienTe"),
        CheckConstraint(
            '"soTienHoan" > 0 AND "soTienHoan" <= "soTienDaThu"',
            name="ck_HoanTienNgoaiLe_soTien_bounds",
        ),
        Index(
            "uq_HoanTienNgoaiLe_active_per_payment",
            "maThanhToan",
            unique=True,
            postgresql_where=text(
                "\"trangThai\" IN ('PENDING_REVIEW', 'VERIFIED', 'REFUND_PENDING', 'UNKNOWN')"
            ),
        ),
        Index("ix_HoanTienNgoaiLe_order", "maDonHang"),
        Index("ix_HoanTienNgoaiLe_status_updated", "trangThai", text('"ngayCapNhat" DESC')),
    )

    maHoanTien: Mapped[int] = mapped_column(Integer, primary_key=True)
    maSoHoanTien: Mapped[str] = mapped_column(String(40), nullable=False)
    maDonHang: Mapped[int] = mapped_column(
        Integer, ForeignKey("DonHang.maDonHang", ondelete="RESTRICT"), nullable=False
    )
    maThanhToan: Mapped[int] = mapped_column(
        Integer, ForeignKey("ThanhToan.maThanhToan", ondelete="RESTRICT"), nullable=False
    )
    khoaChongTrung: Mapped[str] = mapped_column(String(128), nullable=False)
    phamViHoan: Mapped[str] = mapped_column(String(30), nullable=False)
    loaiSuCo: Mapped[str] = mapped_column(String(40), nullable=False)
    soTienDaThu: Mapped[Decimal] = mapped_column(Numeric(12, 0), nullable=False)
    soTienHoan: Mapped[Decimal] = mapped_column(Numeric(12, 0), nullable=False)
    donViTienTe: Mapped[str] = mapped_column(
        String(3), nullable=False, default="VND", server_default=text("'VND'")
    )
    trangThai: Mapped[str] = mapped_column(
        String(30), nullable=False, default="PENDING_REVIEW", server_default=text("'PENDING_REVIEW'")
    )
    lyDo: Mapped[str] = mapped_column(Text, nullable=False)
    ghiChuXacMinh: Mapped[str | None] = mapped_column(Text, nullable=True)
    maGiaoDichHoanCong: Mapped[str | None] = mapped_column(String(100), nullable=True)
    maNguoiTao: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("NguoiDung.maNguoiDung", ondelete="SET NULL"), nullable=True
    )
    maNguoiXacMinh: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("NguoiDung.maNguoiDung", ondelete="SET NULL"), nullable=True
    )
    maNguoiXuLy: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("NguoiDung.maNguoiDung", ondelete="SET NULL"), nullable=True
    )
    lichSuTrangThai: Mapped[list[dict] | None] = mapped_column(JSONB, nullable=True)
    ngayTao: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, server_default=text("(CURRENT_TIMESTAMP AT TIME ZONE 'UTC')")
    )
    ngayCapNhat: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, server_default=text("(CURRENT_TIMESTAMP AT TIME ZONE 'UTC')")
    )
    ngayHoanTat: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    donHang: Mapped[DonHang] = relationship(foreign_keys=lambda: [HoanTienNgoaiLe.maDonHang])
    thanhToan: Mapped[ThanhToan] = relationship(back_populates="hoanTiens")
    lanThus: Mapped[list[LanThuHoanTien]] = relationship(back_populates="hoanTien")


class LanThuHoanTien(Base):
    """GĐ4.7A.2 Per-call Refund Gateway Attempt Ledger (prevents blind concurrent retries)."""

    __tablename__ = "LanThuHoanTien"
    __table_args__ = (
        UniqueConstraint("maYeuCauCong", name="uq_LanThuHoanTien_maYeuCauCong"),
        UniqueConstraint("maHoanTien", "thuTuLanThu", name="uq_LanThuHoanTien_refund_seq"),
        CheckConstraint('"thuTuLanThu" >= 1', name="ck_LanThuHoanTien_thuTu_positive"),
        CheckConstraint('"soTienYeuCau" > 0', name="ck_LanThuHoanTien_soTien_positive"),
        CheckConstraint(
            "\"trangThai\" IN ('SENT', 'SUCCEEDED', 'FAILED', 'UNKNOWN')",
            name="ck_LanThuHoanTien_trangThai",
        ),
        Index(
            "uq_LanThuHoanTien_inflight_per_refund",
            "maHoanTien",
            unique=True,
            postgresql_where=text("\"trangThai\" IN ('SENT', 'UNKNOWN')"),
        ),
        Index("ix_LanThuHoanTien_refund", "maHoanTien"),
    )

    maLanThuHoan: Mapped[int] = mapped_column(Integer, primary_key=True)
    maHoanTien: Mapped[int] = mapped_column(
        Integer, ForeignKey("HoanTienNgoaiLe.maHoanTien", ondelete="RESTRICT"), nullable=False
    )
    thuTuLanThu: Mapped[int] = mapped_column(Integer, nullable=False)
    maYeuCauCong: Mapped[str] = mapped_column(String(64), nullable=False)
    maGiaoDichHoanCong: Mapped[str | None] = mapped_column(String(100), nullable=True)
    soTienYeuCau: Mapped[Decimal] = mapped_column(Numeric(12, 0), nullable=False)
    trangThai: Mapped[str] = mapped_column(String(20), nullable=False, default="SENT")
    maPhanHoiCong: Mapped[str | None] = mapped_column(String(32), nullable=True)
    phanHoiAnToan: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    maNguoiThucThi: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("NguoiDung.maNguoiDung", ondelete="SET NULL"), nullable=True
    )
    ngayGui: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, server_default=text("(CURRENT_TIMESTAMP AT TIME ZONE 'UTC')")
    )
    ngayPhanHoi: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    hoanTien: Mapped[HoanTienNgoaiLe] = relationship(back_populates="lanThus")


class BaoCaoSuCoThanhToan(Base):
    """GĐ4.7A.2 Normalized User Payment Incident Reports."""

    __tablename__ = "BaoCaoSuCoThanhToan"
    __table_args__ = (
        UniqueConstraint("maSoSuCo", name="uq_BaoCaoSuCoThanhToan_maSoSuCo"),
        CheckConstraint(
            "\"loaiSuCo\" IN ('DUPLICATE_CHARGE', 'CHARGED_NO_ACCESS', 'WRONG_AMOUNT', "
            "'CANCELLED_OR_EXPIRED_CHARGED', 'OTHER_PAYMENT_ERROR')",
            name="ck_BaoCaoSuCoThanhToan_loaiSuCo",
        ),
        CheckConstraint(
            "\"trangThai\" IN ('OPEN', 'IN_REVIEW', 'RESOLVED', 'DISMISSED')",
            name="ck_BaoCaoSuCoThanhToan_trangThai",
        ),
        Index("ix_BaoCaoSuCoThanhToan_status_date", "trangThai", text('"ngayBaoCao" DESC')),
        Index("ix_BaoCaoSuCoThanhToan_order", "maDonHang"),
        Index("ix_BaoCaoSuCoThanhToan_user", "maNguoiBaoCao"),
    )

    maSuCo: Mapped[int] = mapped_column(Integer, primary_key=True)
    maSoSuCo: Mapped[str] = mapped_column(String(40), nullable=False)
    maDonHang: Mapped[int] = mapped_column(
        Integer, ForeignKey("DonHang.maDonHang", ondelete="RESTRICT"), nullable=False
    )
    maThanhToan: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("ThanhToan.maThanhToan", ondelete="RESTRICT"), nullable=True
    )
    maNguoiBaoCao: Mapped[int] = mapped_column(
        Integer, ForeignKey("NguoiDung.maNguoiDung", ondelete="RESTRICT"), nullable=False
    )
    loaiSuCo: Mapped[str] = mapped_column(String(40), nullable=False)
    moTa: Mapped[str] = mapped_column(Text, nullable=False)
    trangThai: Mapped[str] = mapped_column(
        String(20), nullable=False, default="OPEN", server_default=text("'OPEN'")
    )
    maAdminPhuTrach: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("NguoiDung.maNguoiDung", ondelete="SET NULL"), nullable=True
    )
    ghiChuXuLy: Mapped[str | None] = mapped_column(Text, nullable=True)
    ngayBaoCao: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, server_default=text("(CURRENT_TIMESTAMP AT TIME ZONE 'UTC')")
    )
    ngayCapNhat: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, server_default=text("(CURRENT_TIMESTAMP AT TIME ZONE 'UTC')")
    )

    donHang: Mapped[DonHang] = relationship(foreign_keys=lambda: [BaoCaoSuCoThanhToan.maDonHang])
    thanhToan: Mapped[ThanhToan | None] = relationship(back_populates="baoCaoSuCos")


class SuKienThanhToan(Base):
    """GĐ4.7A.2 Immutable Append-Only Financial Event Log (enforced by PostgreSQL trigger)."""

    __tablename__ = "SuKienThanhToan"
    __table_args__ = (
        Index(
            "uq_SuKienThanhToan_khoaChongTrung",
            "khoaChongTrung",
            unique=True,
            postgresql_where=text('"khoaChongTrung" IS NOT NULL'),
        ),
        Index("ix_SuKienThanhToan_order_created", "maDonHang", text('"ngayTao" DESC')),
        Index("ix_SuKienThanhToan_payment_created", "maThanhToan", text('"ngayTao" DESC')),
    )

    maSuKien: Mapped[int] = mapped_column(Integer, primary_key=True)
    maDonHang: Mapped[int] = mapped_column(
        Integer, ForeignKey("DonHang.maDonHang", ondelete="RESTRICT"), nullable=False
    )
    maThanhToan: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("ThanhToan.maThanhToan", ondelete="RESTRICT"), nullable=True
    )
    maHoanTien: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("HoanTienNgoaiLe.maHoanTien", ondelete="RESTRICT"), nullable=True
    )
    loaiSuKien: Mapped[str] = mapped_column(String(50), nullable=False)
    nguonSuKien: Mapped[str] = mapped_column(String(40), nullable=False)
    khoaChongTrung: Mapped[str | None] = mapped_column(String(128), nullable=True)
    duLieuAnToan: Mapped[dict] = mapped_column(JSONB, nullable=False)
    ngayTao: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, server_default=text("(CURRENT_TIMESTAMP AT TIME ZONE 'UTC')")
    )


class TacVuDoiSoatThanhToan(Base):
    """GĐ4.7A.2 Durable Payment Reconciliation Queue (completely separate from HangDoiPhanCong)."""

    __tablename__ = "TacVuDoiSoatThanhToan"
    __table_args__ = (
        UniqueConstraint("khoaChongTrung", name="uq_TacVuDoiSoatThanhToan_khoaChongTrung"),
        CheckConstraint(
            "\"loaiTacVu\" IN ('QUERY_PENDING_PAYMENT', 'VERIFY_EXPIRED_ORDER', "
            "'RETRY_CAPTURED_UNAPPLIED', 'QUERY_UNKNOWN_REFUND')",
            name="ck_TacVuDoiSoatThanhToan_loaiTacVu",
        ),
        CheckConstraint(
            "\"trangThai\" IN ('PENDING', 'PROCESSING', 'DONE', 'RETRY_WAIT', 'ESCALATED_ADMIN', 'CANCELLED')",
            name="ck_TacVuDoiSoatThanhToan_trangThai",
        ),
        CheckConstraint('"soLanThu" >= 0 AND "soLanThuToiDa" > 0', name="ck_TacVuDoiSoatThanhToan_retries"),
        CheckConstraint('"leaseGeneration" >= 0', name="ck_TacVuDoiSoatThanhToan_lease_gen"),
        Index(
            "ix_TacVuDoiSoatThanhToan_claimable",
            "trangThai",
            "thoiDiemChayTiepTheo",
        ),
        Index(
            "ix_TacVuDoiSoatThanhToan_stale_lease",
            "hanLease",
            postgresql_where=text("\"trangThai\" = 'PROCESSING'"),
        ),
    )

    maTacVu: Mapped[int] = mapped_column(Integer, primary_key=True)
    loaiTacVu: Mapped[str] = mapped_column(String(40), nullable=False)
    maDonHang: Mapped[int] = mapped_column(
        Integer, ForeignKey("DonHang.maDonHang", ondelete="RESTRICT"), nullable=False
    )
    maThanhToan: Mapped[int] = mapped_column(
        Integer, ForeignKey("ThanhToan.maThanhToan", ondelete="RESTRICT"), nullable=False
    )
    maHoanTien: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("HoanTienNgoaiLe.maHoanTien", ondelete="RESTRICT"), nullable=True
    )
    khoaChongTrung: Mapped[str] = mapped_column(String(128), nullable=False)
    trangThai: Mapped[str] = mapped_column(
        String(30), nullable=False, default="PENDING", server_default=text("'PENDING'")
    )
    soLanThu: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default=text("0"))
    soLanThuToiDa: Mapped[int] = mapped_column(Integer, nullable=False, default=6, server_default=text("6"))
    thoiDiemChayTiepTheo: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, server_default=text("(CURRENT_TIMESTAMP AT TIME ZONE 'UTC')")
    )
    maWorker: Mapped[str | None] = mapped_column(String(100), nullable=True)
    claimToken: Mapped[str | None] = mapped_column(String(64), nullable=True)
    leaseGeneration: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default=text("0"))
    hanLease: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    loiGanNhat: Mapped[str | None] = mapped_column(Text, nullable=True)
    ngayTao: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, server_default=text("(CURRENT_TIMESTAMP AT TIME ZONE 'UTC')")
    )
    ngayCapNhat: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, server_default=text("(CURRENT_TIMESTAMP AT TIME ZONE 'UTC')")
    )
