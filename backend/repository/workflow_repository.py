from sqlalchemy import func, or_, select
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
    NguoiDung,
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
    statement = (
        select(KhoaHoc)
        .options(
            joinedload(KhoaHoc.nhaCungCap).joinedload(
                NhaCungCapKhoaHoc.nguoiDung
            )
        )
        .where(
            KhoaHoc.maKhoaHoc == course_id,
            KhoaHoc.trangThaiDuyet == "APPROVED",
            KhoaHoc.trangThaiHienThi == "VISIBLE",
        )
    )
    if for_update:
        statement = statement.with_for_update()
    return db.scalars(statement).first()


def get_enrollment(
    db: Session,
    user_id: int,
    course_id: int,
    *,
    for_update: bool = False,
    active_only: bool = True,
) -> DangKyKhoaHoc | None:
    statement = select(DangKyKhoaHoc).where(
        DangKyKhoaHoc.maNguoiDung == user_id,
        DangKyKhoaHoc.maKhoaHoc == course_id,
    )
    if active_only:
        statement = statement.where(DangKyKhoaHoc.trangThaiQuyenHoc == "ACTIVE")
    if for_update:
        statement = statement.with_for_update()
    return db.scalars(statement).first()


def list_enrolled_course_ids(
    db: Session, user_id: int, course_ids: set[int]
) -> set[int]:
    if not course_ids:
        return set()
    statement = select(DangKyKhoaHoc.maKhoaHoc).where(
        DangKyKhoaHoc.maNguoiDung == user_id,
        DangKyKhoaHoc.maKhoaHoc.in_(course_ids),
        DangKyKhoaHoc.trangThaiQuyenHoc == "ACTIVE",
    )
    return {cid for cid in db.scalars(statement).all() if cid is not None}


def list_enrollments(db: Session, user_id: int) -> list[DangKyKhoaHoc]:
    statement = (
        select(DangKyKhoaHoc)
        .options(joinedload(DangKyKhoaHoc.khoaHoc).joinedload(KhoaHoc.baiHocs))
        .join(DangKyKhoaHoc.khoaHoc)
        .where(
            DangKyKhoaHoc.maNguoiDung == user_id,
            DangKyKhoaHoc.trangThaiQuyenHoc == "ACTIVE",
        )
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
            DangKyKhoaHoc.trangThaiQuyenHoc == "ACTIVE",
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
        .outerjoin(BaiHoc, TaiLieu.maBaiHoc == BaiHoc.maBaiHoc)
        .join(
            KhoaHoc,
            or_(
                TaiLieu.maKhoaHoc == KhoaHoc.maKhoaHoc,
                BaiHoc.maKhoaHoc == KhoaHoc.maKhoaHoc,
            ),
        )
        .join(DangKyKhoaHoc, DangKyKhoaHoc.maKhoaHoc == KhoaHoc.maKhoaHoc)
        .options(
            joinedload(TaiLieu.baiHoc),
            joinedload(TaiLieu.khoaHoc).joinedload(KhoaHoc.danhMuc),
            joinedload(TaiLieu.danhMuc),
        )
        .where(
            DangKyKhoaHoc.maNguoiDung == user_id,
            DangKyKhoaHoc.maKhoaHoc == course_id,
            DangKyKhoaHoc.trangThaiQuyenHoc == "ACTIVE",
            KhoaHoc.maKhoaHoc == course_id,
            KhoaHoc.trangThaiDuyet == "APPROVED",
            KhoaHoc.trangThaiHienThi == "VISIBLE",
            TaiLieu.trangThaiDuyet == "APPROVED",
            TaiLieu.trangThaiHienThi == "VISIBLE",
        )
        .order_by(BaiHoc.thuTu.nulls_last(), TaiLieu.maTaiLieu)
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
        .options(
            joinedload(DanhGiaChuyenGia.khoaHoc),
            joinedload(DanhGiaChuyenGia.taiLieu),
        )
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


def get_admin_analytics_summary(db: Session) -> dict[str, int | float]:
    total_users = db.scalar(select(func.count(NguoiDung.maNguoiDung))) or 0
    total_courses = db.scalar(select(func.count(KhoaHoc.maKhoaHoc))) or 0
    total_lessons = db.scalar(select(func.count(BaiHoc.maBaiHoc))) or 0
    total_enrollments = db.scalar(select(func.count(DangKyKhoaHoc.maDangKy))) or 0
    completed_enrollments = (
        db.scalar(
            select(func.count(DangKyKhoaHoc.maDangKy)).where(
                or_(
                    DangKyKhoaHoc.ngayHoanThanh.is_not(None),
                    DangKyKhoaHoc.tienDo >= 100,
                )
            )
        )
        or 0
    )
    completion_rate = (
        round((completed_enrollments / total_enrollments) * 100, 1)
        if total_enrollments > 0
        else 0.0
    )
    return {
        "total_users": int(total_users),
        "total_courses": int(total_courses),
        "total_lessons": int(total_lessons),
        "total_enrollments": int(total_enrollments),
        "completed_enrollments": int(completed_enrollments),
        "completion_rate": float(completion_rate),
    }


def _material_options():
    return (
        joinedload(TaiLieu.danhMuc),
        joinedload(TaiLieu.khoaHoc),
        joinedload(TaiLieu.baiHoc),
        joinedload(TaiLieu.nhaCungCap),
    )


def list_owned_materials(db: Session, user_id: int) -> list[TaiLieu]:
    statement = (
        select(TaiLieu)
        .options(*_material_options())
        .join(NhaCungCapKhoaHoc, TaiLieu.maNhaCungCap == NhaCungCapKhoaHoc.maNhaCungCap)
        .where(NhaCungCapKhoaHoc.maNguoiDung == user_id)
        .order_by(TaiLieu.maTaiLieu.desc())
    )
    return list(db.scalars(statement).all())


def get_owned_material_by_id(
    db: Session, user_id: int, material_id: int, *, for_update: bool = False
) -> TaiLieu | None:
    statement = (
        select(TaiLieu)
        .options(*_material_options())
        .join(NhaCungCapKhoaHoc, TaiLieu.maNhaCungCap == NhaCungCapKhoaHoc.maNhaCungCap)
        .where(
            TaiLieu.maTaiLieu == material_id,
            NhaCungCapKhoaHoc.maNguoiDung == user_id,
        )
    )
    if for_update:
        statement = statement.with_for_update(of=TaiLieu)
    return db.scalars(statement).first()


def list_pending_materials_for_expert(db: Session) -> list[TaiLieu]:
    statement = (
        select(TaiLieu)
        .options(*_material_options())
        .where(TaiLieu.trangThaiDuyet == "PENDING")
        .order_by(TaiLieu.ngayTao.desc(), TaiLieu.maTaiLieu.desc())
    )
    return list(db.scalars(statement).all())


def get_expert_material(
    db: Session, material_id: int, *, for_update: bool = False
) -> TaiLieu | None:
    statement = (
        select(TaiLieu)
        .options(*_material_options())
        .where(TaiLieu.maTaiLieu == material_id)
    )
    if for_update:
        statement = statement.with_for_update(of=TaiLieu)
    return db.scalars(statement).first()


def list_public_materials(
    db: Session,
    *,
    query: str | None = None,
    category_id: int | None = None,
    material_type: str | None = None,
    limit: int = 20,
    offset: int = 0,
) -> tuple[list[TaiLieu], int]:
    base_filters = [
        TaiLieu.trangThaiDuyet == "APPROVED",
        TaiLieu.trangThaiHienThi == "VISIBLE",
    ]
    if query:
        base_filters.append(
            or_(
                TaiLieu.tieuDe.ilike(f"%{query}%"),
                TaiLieu.moTa.ilike(f"%{query}%"),
            )
        )
    if category_id is not None:
        base_filters.append(TaiLieu.maDanhMuc == category_id)
    if material_type:
        base_filters.append(TaiLieu.loai.ilike(material_type))

    total = db.scalar(
        select(func.count(TaiLieu.maTaiLieu)).where(*base_filters)
    ) or 0

    statement = (
        select(TaiLieu)
        .options(*_material_options())
        .where(*base_filters)
        .order_by(TaiLieu.ngayTao.desc(), TaiLieu.maTaiLieu.desc())
        .offset(offset)
        .limit(limit)
    )
    items = list(db.scalars(statement).all())
    return items, total


def get_public_material(db: Session, material_id: int) -> TaiLieu | None:
    statement = (
        select(TaiLieu)
        .options(*_material_options())
        .where(
            TaiLieu.maTaiLieu == material_id,
            TaiLieu.trangThaiDuyet == "APPROVED",
            TaiLieu.trangThaiHienThi == "VISIBLE",
        )
    )
    return db.scalars(statement).first()


def list_admin_materials(
    db: Session,
    *,
    query: str | None = None,
    category_id: int | None = None,
    status: str | None = None,
    limit: int = 20,
    offset: int = 0,
) -> tuple[list[TaiLieu], int]:
    filters = []
    if query:
        filters.append(
            or_(
                TaiLieu.tieuDe.ilike(f"%{query}%"),
                TaiLieu.moTa.ilike(f"%{query}%"),
            )
        )
    if category_id is not None:
        filters.append(TaiLieu.maDanhMuc == category_id)
    if status:
        filters.append(TaiLieu.trangThaiDuyet == status)

    total = (
        db.scalar(select(func.count(TaiLieu.maTaiLieu)).where(*filters)) or 0
    )

    statement = (
        select(TaiLieu)
        .options(*_material_options())
        .where(*filters)
        .order_by(TaiLieu.maTaiLieu.desc())
        .offset(offset)
        .limit(limit)
    )
    items = list(db.scalars(statement).all())
    return items, int(total)


def list_standalone_recommendation_materials(db: Session) -> list[TaiLieu]:
    statement = (
        select(TaiLieu)
        .options(*_material_options())
        .where(
            TaiLieu.trangThaiDuyet == "APPROVED",
            TaiLieu.trangThaiHienThi == "VISIBLE",
        )
        .order_by(TaiLieu.maTaiLieu.asc())
    )
    return list(db.scalars(statement).all())
