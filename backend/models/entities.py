from __future__ import annotations

from datetime import datetime
from decimal import Decimal

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    ForeignKey,
    Integer,
    Numeric,
    String,
    Text,
    UniqueConstraint,
)
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

    vaiTro: Mapped[VaiTro | None] = relationship(back_populates="nguoiDungs")
    nhaCungCapKhoaHocs: Mapped[list[NhaCungCapKhoaHoc]] = relationship(
        back_populates="nguoiDung"
    )
    donXinNhaCungCaps: Mapped[list[DonXinNhaCungCap]] = relationship(
        back_populates="nguoiDung"
    )
    chuyenGias: Mapped[list[ChuyenGia]] = relationship(back_populates="nguoiDung")
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


class KhoaHoc(Base):
    __tablename__ = "KhoaHoc"

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
    gia: Mapped[Decimal | None] = mapped_column(Numeric, nullable=True)
    trinhDo: Mapped[str | None] = mapped_column(String(100), nullable=True)
    thoiLuong: Mapped[int | None] = mapped_column(Integer, nullable=True)
    trangThaiDuyet: Mapped[str | None] = mapped_column(String(50), nullable=True)
    trangThaiHienThi: Mapped[str | None] = mapped_column(String(50), nullable=True)
    lyDoTuChoi: Mapped[str | None] = mapped_column(Text, nullable=True)
    ngayDuyet: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    ngayTao: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    ngayCapNhat: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    nhaCungCap: Mapped[NhaCungCapKhoaHoc | None] = relationship(
        back_populates="khoaHocs"
    )
    danhMuc: Mapped[DanhMuc | None] = relationship(back_populates="khoaHocs")
    nguoiDuyet: Mapped[NguoiDung | None] = relationship(
        back_populates="khoaHocDaDuyet",
        foreign_keys=lambda: [KhoaHoc.maNguoiDuyet],
    )
    baiHocs: Mapped[list[BaiHoc]] = relationship(back_populates="khoaHoc")
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
    maBaiHoc: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("BaiHoc.maBaiHoc"), nullable=True
    )
    tieuDe: Mapped[str | None] = mapped_column(String(255), nullable=True)
    duongDanTep: Mapped[str | None] = mapped_column(String(500), nullable=True)
    loai: Mapped[str | None] = mapped_column(String(100), nullable=True)
    moTa: Mapped[str | None] = mapped_column(Text, nullable=True)
    ngayTao: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    baiHoc: Mapped[BaiHoc | None] = relationship(back_populates="taiLieus")


class ChuyenGia(Base):
    __tablename__ = "ChuyenGia"

    maChuyenGia: Mapped[int] = mapped_column(Integer, primary_key=True)
    maNguoiDung: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("NguoiDung.maNguoiDung"), nullable=True
    )
    chuyenMon: Mapped[str | None] = mapped_column(String(255), nullable=True)
    tieuSu: Mapped[str | None] = mapped_column(Text, nullable=True)

    nguoiDung: Mapped[NguoiDung | None] = relationship(back_populates="chuyenGias")
    danhGiaChuyenGias: Mapped[list[DanhGiaChuyenGia]] = relationship(
        back_populates="chuyenGia"
    )


class DanhGiaChuyenGia(Base):
    __tablename__ = "DanhGiaChuyenGia"

    maDanhGia: Mapped[int] = mapped_column(Integer, primary_key=True)
    maKhoaHoc: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("KhoaHoc.maKhoaHoc"), nullable=True
    )
    maChuyenGia: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("ChuyenGia.maChuyenGia"), nullable=True
    )
    noiDungDanhGia: Mapped[str | None] = mapped_column(Text, nullable=True)
    diemKyThuat: Mapped[Decimal | None] = mapped_column(Numeric, nullable=True)
    diemNoiDung: Mapped[Decimal | None] = mapped_column(Numeric, nullable=True)
    ghiChu: Mapped[str | None] = mapped_column(Text, nullable=True)
    trangThai: Mapped[str | None] = mapped_column(String(50), nullable=True)
    ngayTao: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    khoaHoc: Mapped[KhoaHoc | None] = relationship(back_populates="danhGiaChuyenGias")
    chuyenGia: Mapped[ChuyenGia | None] = relationship(
        back_populates="danhGiaChuyenGias"
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

    nguoiDung: Mapped[NguoiDung | None] = relationship(back_populates="dangKyKhoaHocs")
    khoaHoc: Mapped[KhoaHoc | None] = relationship(back_populates="dangKyKhoaHocs")


class TokenBiThuHoi(Base):
    __tablename__ = "TokenBiThuHoi"

    maToken: Mapped[int] = mapped_column(Integer, primary_key=True)
    jti: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    thoiGianHetHan: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    ngayTao: Mapped[datetime] = mapped_column(DateTime, nullable=False)
