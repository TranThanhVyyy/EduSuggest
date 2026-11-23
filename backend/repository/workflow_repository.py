from sqlalchemy import select
from sqlalchemy.orm import Session, joinedload, selectinload

from models import (
    BaiHoc,
    ChuyenGia,
    DangKyKhoaHoc,
    DanhGiaChuyenGia,
    DanhMuc,
    DonXinNhaCungCap,
    KhoaHoc,
    LichSuHocTap,
    NhaCungCapKhoaHoc,
    TaiLieu,
)


def get_provider_application(
    db: Session, application_id: int, *, for_update: bool = False
) -> DonXinNhaCungCap | None:
    statement = select(DonXinNhaCungCap).where(
        DonXinNhaCungCap.maDon == application_id
    )
    if for_update:
        statement = statement.with_for_update()
    return db.scalars(statement).first()


def list_provider_applications(
    db: Session, *, user_id: int | None = None, status: str | None = None
) -> list[DonXinNhaCungCap]:
    statement = select(DonXinNhaCungCap)
    if user_id is not None:
        statement = statement.where(DonXinNhaCungCap.maNguoiDung == user_id)
    if status is not None:
        statement = statement.where(DonXinNhaCungCap.trangThai == status)
    statement = statement.order_by(
        DonXinNhaCungCap.ngayGui.desc(), DonXinNhaCungCap.maDon.desc()
    )
    return list(db.scalars(statement).all())


def get_provider_profile(db: Session, user_id: int) -> NhaCungCapKhoaHoc | None:
    statement = select(NhaCungCapKhoaHoc).where(
        NhaCungCapKhoaHoc.maNguoiDung == user_id
    )
    return db.scalars(statement).first()


def get_expert_profile(db: Session, user_id: int) -> ChuyenGia | None:
    statement = select(ChuyenGia).where(ChuyenGia.maNguoiDung == user_id)
    return db.scalars(statement).first()


def get_category(db: Session, category_id: int) -> DanhMuc | None:
    return db.get(DanhMuc, category_id)


def list_categories(db: Session) -> list[DanhMuc]:
    statement = select(DanhMuc).order_by(DanhMuc.tenDanhMuc, DanhMuc.maDanhMuc)
    return list(db.scalars(statement).all())


def get_course(db: Session, course_id: int) -> KhoaHoc | None:
    return db.get(KhoaHoc, course_id)


def get_course_for_update(db: Session, course_id: int) -> KhoaHoc | None:
    statement = (
        select(KhoaHoc)
        .where(KhoaHoc.maKhoaHoc == course_id)
        .with_for_update()
    )
    return db.scalars(statement).first()


def get_owned_course(
    db: Session, course_id: int, user_id: int, *, for_update: bool = False
) -> KhoaHoc | None:
    statement = (
        select(KhoaHoc)
        .join(KhoaHoc.nhaCungCap)
        .where(
            KhoaHoc.maKhoaHoc == course_id,
            NhaCungCapKhoaHoc.maNguoiDung == user_id,
        )
    )
    if for_update:
        statement = statement.with_for_update(of=KhoaHoc)
    return db.scalars(statement).first()


def list_owned_courses(db: Session, user_id: int) -> list[KhoaHoc]:
    statement = (
        select(KhoaHoc)
        .join(KhoaHoc.nhaCungCap)
        .where(NhaCungCapKhoaHoc.maNguoiDung == user_id)
        .order_by(KhoaHoc.ngayCapNhat.desc(), KhoaHoc.maKhoaHoc.desc())
    )
    return list(db.scalars(statement).all())


def list_all_courses(db: Session) -> list[KhoaHoc]:
    statement = select(KhoaHoc).order_by(
        KhoaHoc.ngayTao.desc(), KhoaHoc.maKhoaHoc.desc()
    )
    return list(db.scalars(statement).all())


def list_courses_for_review(db: Session) -> list[KhoaHoc]:
    statement = (
        select(KhoaHoc)
        .where(KhoaHoc.trangThaiDuyet == "PENDING")
        .order_by(KhoaHoc.ngayTao, KhoaHoc.maKhoaHoc)
    )
    return list(db.scalars(statement).all())


def get_public_course(
    db: Session, course_id: int, *, for_update: bool = False
) -> KhoaHoc | None:
    statement = select(KhoaHoc).where(
        KhoaHoc.maKhoaHoc == course_id,
        KhoaHoc.trangThaiDuyet == "APPROVED",
        KhoaHoc.trangThaiHienThi == "VISIBLE",
    )
    if for_update:
        statement = statement.with_for_update()
    return db.scalars(statement).first()


def get_enrollment(db: Session, user_id: int, course_id: int, *, for_update: bool = False) -> DangKyKhoaHoc | None:
    statement = select(DangKyKhoaHoc).where(
        DangKyKhoaHoc.maNguoiDung == user_id,
        DangKyKhoaHoc.maKhoaHoc == course_id,
    )
    if for_update:
        statement = statement.with_for_update()
    return db.scalars(statement).first()


def list_enrollments(db: Session, user_id: int) -> list[DangKyKhoaHoc]:
    statement = (
        select(DangKyKhoaHoc)
        .options(joinedload(DangKyKhoaHoc.khoaHoc).joinedload(KhoaHoc.baiHocs))
        .join(DangKyKhoaHoc.khoaHoc)
        .where(DangKyKhoaHoc.maNguoiDung == user_id)
        .where(KhoaHoc.trangThaiDuyet == "APPROVED", KhoaHoc.trangThaiHienThi == "VISIBLE")
        .order_by(DangKyKhoaHoc.ngayDangKy.desc(), DangKyKhoaHoc.maDangKy.desc())
    )
    return list(db.scalars(statement).unique().all())


def list_learning_history(db: Session, user_id: int) -> list[LichSuHocTap]:
    statement = (
        select(LichSuHocTap)
        .options(joinedload(LichSuHocTap.khoaHoc), joinedload(LichSuHocTap.baiHoc))
        .join(LichSuHocTap.khoaHoc)
        .where(LichSuHocTap.maNguoiDung == user_id)
        .where(KhoaHoc.trangThaiDuyet == "APPROVED", KhoaHoc.trangThaiHienThi == "VISIBLE")
        .order_by(LichSuHocTap.ngayTao.desc(), LichSuHocTap.maLichSu.desc())
    )
    return list(db.scalars(statement).unique().all())


def get_lesson_history(db: Session, user_id: int, course_id: int, lesson_id: int, *, for_update: bool = False) -> LichSuHocTap | None:
    statement = select(LichSuHocTap).where(
        LichSuHocTap.maNguoiDung == user_id,
        LichSuHocTap.maKhoaHoc == course_id,
        LichSuHocTap.maBaiHoc == lesson_id,
    ).order_by(LichSuHocTap.maLichSu.desc())
    if for_update:
        statement = statement.with_for_update()
    return db.scalars(statement).first()


def _recommendation_course_options():
    return (
        joinedload(KhoaHoc.danhMuc),
        selectinload(KhoaHoc.baiHocs).selectinload(BaiHoc.taiLieus),
    )


def list_recommendation_courses(db: Session) -> list[KhoaHoc]:
    statement = (
        select(KhoaHoc)
        .options(*_recommendation_course_options())
        .where(
            KhoaHoc.trangThaiDuyet == "APPROVED",
            KhoaHoc.trangThaiHienThi == "VISIBLE",
        )
        .order_by(KhoaHoc.maKhoaHoc)
    )
    return list(db.scalars(statement).unique().all())


def get_recommendation_course(db: Session, course_id: int) -> KhoaHoc | None:
    statement = (
        select(KhoaHoc)
        .options(*_recommendation_course_options())
        .where(
            KhoaHoc.maKhoaHoc == course_id,
            KhoaHoc.trangThaiDuyet == "APPROVED",
            KhoaHoc.trangThaiHienThi == "VISIBLE",
        )
    )
    return db.scalars(statement).unique().first()


def list_user_recommendation_enrollments(
    db: Session, user_id: int
) -> list[DangKyKhoaHoc]:
    course_path = selectinload(DangKyKhoaHoc.khoaHoc)
    statement = (
        select(DangKyKhoaHoc)
        .join(DangKyKhoaHoc.khoaHoc)
        .options(
            course_path.joinedload(KhoaHoc.danhMuc),
            course_path.selectinload(KhoaHoc.baiHocs).selectinload(BaiHoc.taiLieus),
        )
        .where(
            DangKyKhoaHoc.maNguoiDung == user_id,
            KhoaHoc.trangThaiDuyet == "APPROVED",
            KhoaHoc.trangThaiHienThi == "VISIBLE",
        )
    )
    return list(db.scalars(statement).unique().all())


def list_user_recommendation_history(
    db: Session, user_id: int
) -> list[LichSuHocTap]:
    course_path = selectinload(LichSuHocTap.khoaHoc)
    statement = (
        select(LichSuHocTap)
        .join(LichSuHocTap.khoaHoc)
        .options(
            course_path.joinedload(KhoaHoc.danhMuc),
            course_path.selectinload(KhoaHoc.baiHocs).selectinload(BaiHoc.taiLieus),
            joinedload(LichSuHocTap.baiHoc),
        )
        .where(
            LichSuHocTap.maNguoiDung == user_id,
            KhoaHoc.trangThaiDuyet == "APPROVED",
            KhoaHoc.trangThaiHienThi == "VISIBLE",
        )
        .order_by(LichSuHocTap.ngayTao.desc(), LichSuHocTap.maLichSu.desc())
    )
    return list(db.scalars(statement).unique().all())


def list_recommendation_materials_for_enrolled_course(
    db: Session, user_id: int, course_id: int
) -> list[TaiLieu]:
    statement = (
        select(TaiLieu)
        .join(TaiLieu.baiHoc)
        .join(BaiHoc.khoaHoc)
        .join(KhoaHoc.dangKyKhoaHocs)
        .options(
            joinedload(TaiLieu.baiHoc)
            .joinedload(BaiHoc.khoaHoc)
            .joinedload(KhoaHoc.danhMuc)
        )
        .where(
            DangKyKhoaHoc.maNguoiDung == user_id,
            DangKyKhoaHoc.maKhoaHoc == course_id,
            KhoaHoc.maKhoaHoc == course_id,
            KhoaHoc.trangThaiDuyet == "APPROVED",
            KhoaHoc.trangThaiHienThi == "VISIBLE",
        )
        .order_by(BaiHoc.thuTu, TaiLieu.maTaiLieu)
    )
    return list(db.scalars(statement).unique().all())


def list_public_courses(
    db: Session, *, query: str | None, category_id: int | None, limit: int
) -> list[KhoaHoc]:
    statement = select(KhoaHoc).where(
        KhoaHoc.trangThaiDuyet == "APPROVED",
        KhoaHoc.trangThaiHienThi == "VISIBLE",
    )
    if query:
        statement = statement.where(KhoaHoc.tieuDe.ilike(f"%{query}%"))
    if category_id is not None:
        statement = statement.where(KhoaHoc.maDanhMuc == category_id)
    statement = statement.order_by(KhoaHoc.tieuDe, KhoaHoc.maKhoaHoc).limit(limit)
    return list(db.scalars(statement).all())


def get_owned_lesson(
    db: Session, course: KhoaHoc, lesson_id: int
) -> BaiHoc | None:
    statement = select(BaiHoc).where(
        BaiHoc.maBaiHoc == lesson_id,
        BaiHoc.maKhoaHoc == course.maKhoaHoc,
    )
    return db.scalars(statement).first()


def get_owned_material(
    db: Session, course: KhoaHoc, lesson_id: int, material_id: int
) -> TaiLieu | None:
    statement = (
        select(TaiLieu)
        .join(TaiLieu.baiHoc)
        .where(
            TaiLieu.maTaiLieu == material_id,
            BaiHoc.maBaiHoc == lesson_id,
            BaiHoc.maKhoaHoc == course.maKhoaHoc,
        )
    )
    return db.scalars(statement).first()


def get_review_history_for_expert(
    db: Session, expert_id: int
) -> list[DanhGiaChuyenGia]:
    statement = (
        select(DanhGiaChuyenGia)
        .options(joinedload(DanhGiaChuyenGia.khoaHoc))
        .where(DanhGiaChuyenGia.maChuyenGia == expert_id)
        .order_by(DanhGiaChuyenGia.ngayTao.desc(), DanhGiaChuyenGia.maDanhGia.desc())
    )
    return list(db.scalars(statement).all())


def get_review_history_for_course(
    db: Session, course_id: int
) -> list[DanhGiaChuyenGia]:
    statement = (
        select(DanhGiaChuyenGia)
        .where(DanhGiaChuyenGia.maKhoaHoc == course_id)
        .order_by(DanhGiaChuyenGia.ngayTao.desc(), DanhGiaChuyenGia.maDanhGia.desc())
    )
    return list(db.scalars(statement).all())
