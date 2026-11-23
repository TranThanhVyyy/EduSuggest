from datetime import UTC, datetime

from sqlalchemy import select, text
from sqlalchemy.orm import Session, joinedload

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
from repository import role_repository, user_repository, workflow_repository
from schemas.workflow import (
    CategoryCreateRequest,
    CategoryUpdateRequest,
    CourseCreateRequest,
    CourseDecisionRequest,
    CourseUpdateRequest,
    ExpertProfileUpdateRequest,
    GrantExpertRoleRequest,
    LessonCreateRequest,
    LessonUpdateRequest,
    MaterialCreateRequest,
    MaterialUpdateRequest,
    ProviderApplicationCreate,
    ProviderProfileUpdateRequest,
)


class WorkflowNotFoundError(Exception):
    pass


class WorkflowConflictError(Exception):
    pass


class WorkflowForbiddenError(Exception):
    pass


def _role_name(user: NguoiDung) -> str | None:
    return user.vaiTro.tenVaiTro.upper() if user.vaiTro and user.vaiTro.tenVaiTro else None


def _now() -> datetime:
    return datetime.now(UTC).replace(tzinfo=None)


def _get_provider_profile(db: Session, user_id: int) -> NhaCungCapKhoaHoc:
    profile = workflow_repository.get_provider_profile(db, user_id)
    if profile is None:
        raise WorkflowConflictError("Provider profile is not configured.")
    return profile


def _get_expert_profile(db: Session, user_id: int) -> ChuyenGia:
    profile = workflow_repository.get_expert_profile(db, user_id)
    if profile is None:
        raise WorkflowConflictError("Expert profile is not configured.")
    return profile


def get_expert_profile(db: Session, user_id: int) -> ChuyenGia:
    return _get_expert_profile(db, user_id)


def get_provider_profile(db: Session, user_id: int) -> NhaCungCapKhoaHoc:
    return _get_provider_profile(db, user_id)


def _get_owned_course(
    db: Session, course_id: int, user_id: int, *, for_update: bool = False
) -> KhoaHoc:
    course = workflow_repository.get_owned_course(
        db, course_id, user_id, for_update=for_update
    )
    if course is not None:
        return course
    if workflow_repository.get_course(db, course_id) is None:
        raise WorkflowNotFoundError("Course was not found.")
    raise WorkflowForbiddenError("You cannot manage another provider's course.")


def _require_editable_course(course: KhoaHoc) -> None:
    if course.trangThaiDuyet not in (None, "REJECTED", "NEEDS_REVISION"):
        raise WorkflowForbiddenError(
            "Only draft, rejected, or revision-requested courses may be edited."
        )


def submit_provider_application(
    db: Session, user_id: int, payload: ProviderApplicationCreate
) -> DonXinNhaCungCap:
    lock_key = f"provider-application:{user_id}"
    db.execute(
        text("SELECT pg_advisory_xact_lock(hashtextextended(:key, 0))"),
        {"key": lock_key},
    )
    user = user_repository.get_by_id(db, user_id)
    if user is None:
        raise WorkflowNotFoundError("User was not found.")
    if _role_name(user) != "USER":
        raise WorkflowForbiddenError("Only USER accounts may apply to become PROVIDER.")

    pending = db.scalar(
        select(DonXinNhaCungCap.maDon).where(
            DonXinNhaCungCap.maNguoiDung == user_id,
            DonXinNhaCungCap.trangThai == "PENDING",
        )
    )
    if pending is not None:
        raise WorkflowConflictError("A provider application is already pending.")

    user.soDienThoai = payload.soDienThoai
    application = DonXinNhaCungCap(
        maNguoiDung=user_id,
        toChuc=payload.toChuc,
        kinhNghiem=payload.kinhNghiem,
        lyDoDangKy=payload.lyDoDangKy,
        chuyenMon=payload.chuyenMon,
        gioiThieu=payload.gioiThieu,
        trangThai="PENDING",
        ngayGui=_now(),
    )
    db.add(application)
    db.commit()
    db.refresh(application)
    return application


def list_user_provider_applications(
    db: Session, user_id: int
) -> list[DonXinNhaCungCap]:
    return workflow_repository.list_provider_applications(db, user_id=user_id)


def list_admin_provider_applications(
    db: Session, status: str | None
) -> list[DonXinNhaCungCap]:
    if status is not None and status not in {"PENDING", "APPROVED", "REJECTED"}:
        raise WorkflowConflictError("Unsupported provider application status.")
    return workflow_repository.list_provider_applications(db, status=status)


def approve_provider_application(
    db: Session, application_id: int
) -> DonXinNhaCungCap:
    application = workflow_repository.get_provider_application(
        db, application_id, for_update=True
    )
    if application is None:
        raise WorkflowNotFoundError("Provider application was not found.")
    if application.trangThai != "PENDING":
        raise WorkflowConflictError("Only pending applications may be decided.")

    user = user_repository.get_by_id(db, application.maNguoiDung)
    provider_role = role_repository.get_by_name(db, "PROVIDER")
    if user is None:
        raise WorkflowNotFoundError("Applicant account was not found.")
    if _role_name(user) != "USER":
        raise WorkflowConflictError("Applicant must still have the USER role.")
    if provider_role is None:
        raise WorkflowConflictError("The PROVIDER role is not configured.")
    if workflow_repository.get_provider_profile(db, user.maNguoiDung) is not None:
        raise WorkflowConflictError("A provider profile already exists.")

    application.trangThai = "APPROVED"
    application.lyDoTuChoi = None
    application.ngayXuLy = _now()
    user.maVaiTro = provider_role.maVaiTro
    db.add(
        NhaCungCapKhoaHoc(
            maNguoiDung=user.maNguoiDung,
            tieuSu=application.kinhNghiem,
            chuyenMon=application.chuyenMon,
        )
    )
    db.commit()
    db.refresh(application)
    return application


def reject_provider_application(
    db: Session, application_id: int, reason: str
) -> DonXinNhaCungCap:
    application = workflow_repository.get_provider_application(
        db, application_id, for_update=True
    )
    if application is None:
        raise WorkflowNotFoundError("Provider application was not found.")
    if application.trangThai != "PENDING":
        raise WorkflowConflictError("Only pending applications may be decided.")

    application.trangThai = "REJECTED"
    application.lyDoTuChoi = reason
    application.ngayXuLy = _now()
    db.commit()
    db.refresh(application)
    return application


def list_admin_users(db: Session) -> list[NguoiDung]:
    statement = select(NguoiDung).options(joinedload(NguoiDung.vaiTro)).order_by(
        NguoiDung.maNguoiDung
    )
    return list(db.scalars(statement).all())


def grant_expert_role(
    db: Session, user_id: int, payload: GrantExpertRoleRequest
) -> NguoiDung:
    user = user_repository.get_by_id(db, user_id)
    expert_role = role_repository.get_by_name(db, "EXPERT")
    if user is None:
        raise WorkflowNotFoundError("User was not found.")
    if expert_role is None:
        raise WorkflowConflictError("The EXPERT role is not configured.")
    if _role_name(user) != "USER":
        raise WorkflowConflictError("Only USER accounts may be assigned the EXPERT role.")
    if workflow_repository.get_expert_profile(db, user_id) is not None:
        raise WorkflowConflictError("An expert profile already exists.")

    user.maVaiTro = expert_role.maVaiTro
    db.add(
        ChuyenGia(
            maNguoiDung=user_id,
            chuyenMon=payload.chuyenMon,
            tieuSu=payload.tieuSu,
        )
    )
    db.commit()
    return user_repository.get_by_id(db, user_id) or user


def update_expert_profile(
    db: Session, user_id: int, payload: ExpertProfileUpdateRequest
) -> ChuyenGia:
    profile = _get_expert_profile(db, user_id)
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(profile, field, value)
    db.commit()
    return profile


def update_provider_profile(
    db: Session, user_id: int, payload: ProviderProfileUpdateRequest
) -> NhaCungCapKhoaHoc:
    profile = _get_provider_profile(db, user_id)
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(profile, field, value)
    db.commit()
    return profile


def list_categories(db: Session) -> list[DanhMuc]:
    return workflow_repository.list_categories(db)


def create_category(db: Session, payload: CategoryCreateRequest) -> DanhMuc:
    category = DanhMuc(
        tenDanhMuc=payload.tenDanhMuc,
        moTa=payload.moTa,
    )
    db.add(category)
    db.commit()
    db.refresh(category)
    return category


def update_category(
    db: Session, category_id: int, payload: CategoryUpdateRequest
) -> DanhMuc:
    category = workflow_repository.get_category(db, category_id)
    if category is None:
        raise WorkflowNotFoundError("Category was not found.")
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(category, field, value)
    db.commit()
    return category


def delete_category(db: Session, category_id: int) -> None:
    category = workflow_repository.get_category(db, category_id)
    if category is None:
        raise WorkflowNotFoundError("Category was not found.")
    if db.scalar(
        select(KhoaHoc.maKhoaHoc).where(KhoaHoc.maDanhMuc == category_id).limit(1)
    ):
        raise WorkflowConflictError("Category is in use by one or more courses.")
    db.delete(category)
    db.commit()


def create_provider_course(
    db: Session, user_id: int, payload: CourseCreateRequest
) -> KhoaHoc:
    provider = _get_provider_profile(db, user_id)
    if workflow_repository.get_category(db, payload.maDanhMuc) is None:
        raise WorkflowNotFoundError("Category was not found.")
    now = _now()
    course = KhoaHoc(
        maNhaCungCap=provider.maNhaCungCap,
        maDanhMuc=payload.maDanhMuc,
        tieuDe=payload.tieuDe,
        moTa=payload.moTa,
        gia=payload.gia,
        trinhDo=payload.trinhDo,
        thoiLuong=payload.thoiLuong,
        trangThaiDuyet=None,
        trangThaiHienThi="HIDDEN",
        ngayTao=now,
        ngayCapNhat=now,
    )
    db.add(course)
    db.commit()
    db.refresh(course)
    return course


def list_provider_courses(db: Session, user_id: int) -> list[KhoaHoc]:
    _get_provider_profile(db, user_id)
    return workflow_repository.list_owned_courses(db, user_id)


def get_provider_course(db: Session, user_id: int, course_id: int) -> KhoaHoc:
    _get_provider_profile(db, user_id)
    return _get_owned_course(db, course_id, user_id)


def update_provider_course(
    db: Session,
    user_id: int,
    course_id: int,
    payload: CourseUpdateRequest,
) -> KhoaHoc:
    _get_provider_profile(db, user_id)
    course = _get_owned_course(db, course_id, user_id, for_update=True)
    _require_editable_course(course)
    changes = payload.model_dump(exclude_unset=True)
    if (
        "maDanhMuc" in changes
        and changes["maDanhMuc"] is not None
        and workflow_repository.get_category(db, changes["maDanhMuc"]) is None
    ):
        raise WorkflowNotFoundError("Category was not found.")
    for field, value in changes.items():
        setattr(course, field, value)
    course.ngayCapNhat = _now()
    db.commit()
    return course


def delete_provider_course(db: Session, user_id: int, course_id: int) -> None:
    _get_provider_profile(db, user_id)
    course = _get_owned_course(db, course_id, user_id, for_update=True)
    if course.trangThaiDuyet not in (None, "DRAFT"):
        raise WorkflowConflictError("Only an unsubmitted draft course may be deleted.")
    if course.trangThaiHienThi != "HIDDEN":
        raise WorkflowConflictError("Only hidden courses may be deleted.")

    related_records = (
        db.scalar(
            select(BaiHoc.maBaiHoc)
            .where(BaiHoc.maKhoaHoc == course_id)
            .limit(1)
        ),
        db.scalar(
            select(DangKyKhoaHoc.maDangKy)
            .where(DangKyKhoaHoc.maKhoaHoc == course_id)
            .limit(1)
        ),
        db.scalar(
            select(LichSuHocTap.maLichSu)
            .where(LichSuHocTap.maKhoaHoc == course_id)
            .limit(1)
        ),
        db.scalar(
            select(DanhGiaChuyenGia.maDanhGia)
            .where(DanhGiaChuyenGia.maKhoaHoc == course_id)
            .limit(1)
        ),
    )
    if any(record is not None for record in related_records):
        raise WorkflowConflictError(
            "A course with lessons, enrollments, learning history, or review records cannot be deleted."
        )

    db.delete(course)
    db.commit()


def submit_provider_course(db: Session, user_id: int, course_id: int) -> KhoaHoc:
    _get_provider_profile(db, user_id)
    course = _get_owned_course(db, course_id, user_id, for_update=True)
    _require_editable_course(course)
    if not course.tieuDe or not course.maDanhMuc:
        raise WorkflowConflictError("Course title and category are required to submit.")
    if not course.baiHocs:
        raise WorkflowConflictError("Add at least one lesson before submitting.")
    if any(not lesson.tieuDe for lesson in course.baiHocs):
        raise WorkflowConflictError("Every lesson must have a title before submission.")

    course.trangThaiDuyet = "PENDING"
    course.trangThaiHienThi = "HIDDEN"
    course.maNguoiDuyet = None
    course.ngayDuyet = None
    course.lyDoTuChoi = None
    course.ngayCapNhat = _now()
    db.commit()
    return course


def create_provider_lesson(
    db: Session, user_id: int, course_id: int, payload: LessonCreateRequest
) -> BaiHoc:
    _get_provider_profile(db, user_id)
    course = _get_owned_course(db, course_id, user_id, for_update=True)
    _require_editable_course(course)
    lesson = BaiHoc(
        maKhoaHoc=course.maKhoaHoc,
        tieuDe=payload.tieuDe,
        noiDung=payload.noiDung,
        duongDanVideo=payload.duongDanVideo,
        thoiLuong=payload.thoiLuong,
        thuTu=payload.thuTu,
        ngayTao=_now(),
    )
    course.ngayCapNhat = _now()
    db.add(lesson)
    db.commit()
    db.refresh(lesson)
    return lesson


def update_provider_lesson(
    db: Session,
    user_id: int,
    course_id: int,
    lesson_id: int,
    payload: LessonUpdateRequest,
) -> BaiHoc:
    _get_provider_profile(db, user_id)
    course = _get_owned_course(db, course_id, user_id, for_update=True)
    _require_editable_course(course)
    lesson = workflow_repository.get_owned_lesson(db, course, lesson_id)
    if lesson is None:
        raise WorkflowNotFoundError("Lesson was not found in this course.")
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(lesson, field, value)
    course.ngayCapNhat = _now()
    db.commit()
    return lesson


def delete_provider_lesson(
    db: Session, user_id: int, course_id: int, lesson_id: int
) -> None:
    _get_provider_profile(db, user_id)
    course = _get_owned_course(db, course_id, user_id, for_update=True)
    _require_editable_course(course)
    lesson = workflow_repository.get_owned_lesson(db, course, lesson_id)
    if lesson is None:
        raise WorkflowNotFoundError("Lesson was not found in this course.")
    if lesson.taiLieus:
        raise WorkflowConflictError("Delete lesson materials before deleting the lesson.")
    if db.scalar(
        select(LichSuHocTap.maLichSu)
        .where(LichSuHocTap.maBaiHoc == lesson_id)
        .limit(1)
    ):
        raise WorkflowConflictError("A lesson with learning history cannot be deleted.")
    db.delete(lesson)
    course.ngayCapNhat = _now()
    db.commit()


def create_provider_material(
    db: Session,
    user_id: int,
    course_id: int,
    lesson_id: int,
    payload: MaterialCreateRequest,
) -> TaiLieu:
    _get_provider_profile(db, user_id)
    course = _get_owned_course(db, course_id, user_id, for_update=True)
    _require_editable_course(course)
    lesson = workflow_repository.get_owned_lesson(db, course, lesson_id)
    if lesson is None:
        raise WorkflowNotFoundError("Lesson was not found in this course.")
    material = TaiLieu(
        maBaiHoc=lesson.maBaiHoc,
        tieuDe=payload.tieuDe,
        duongDanTep=payload.duongDanTep,
        loai=payload.loai,
        moTa=payload.moTa,
        ngayTao=_now(),
    )
    course.ngayCapNhat = _now()
    db.add(material)
    db.commit()
    db.refresh(material)
    return material


def update_provider_material(
    db: Session,
    user_id: int,
    course_id: int,
    lesson_id: int,
    material_id: int,
    payload: MaterialUpdateRequest,
) -> TaiLieu:
    _get_provider_profile(db, user_id)
    course = _get_owned_course(db, course_id, user_id, for_update=True)
    _require_editable_course(course)
    material = workflow_repository.get_owned_material(
        db, course, lesson_id, material_id
    )
    if material is None:
        raise WorkflowNotFoundError("Material was not found in this lesson.")
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(material, field, value)
    course.ngayCapNhat = _now()
    db.commit()
    return material


def delete_provider_material(
    db: Session,
    user_id: int,
    course_id: int,
    lesson_id: int,
    material_id: int,
) -> None:
    _get_provider_profile(db, user_id)
    course = _get_owned_course(db, course_id, user_id, for_update=True)
    _require_editable_course(course)
    material = workflow_repository.get_owned_material(
        db, course, lesson_id, material_id
    )
    if material is None:
        raise WorkflowNotFoundError("Material was not found in this lesson.")
    db.delete(material)
    course.ngayCapNhat = _now()
    db.commit()


def list_admin_courses(db: Session) -> list[KhoaHoc]:
    return workflow_repository.list_all_courses(db)


def set_course_visibility(
    db: Session, course_id: int, visibility: str
) -> KhoaHoc:
    course = workflow_repository.get_course_for_update(db, course_id)
    if course is None:
        raise WorkflowNotFoundError("Course was not found.")
    if course.trangThaiDuyet != "APPROVED":
        raise WorkflowForbiddenError(
            "Only EXPERT-approved courses may change visibility."
        )
    course.trangThaiHienThi = visibility
    course.ngayCapNhat = _now()
    db.commit()
    return course


def list_expert_courses(db: Session, user_id: int) -> list[KhoaHoc]:
    _get_expert_profile(db, user_id)
    return workflow_repository.list_courses_for_review(db)


def get_expert_course(db: Session, user_id: int, course_id: int) -> KhoaHoc:
    _get_expert_profile(db, user_id)
    course = workflow_repository.get_course(db, course_id)
    if course is None:
        raise WorkflowNotFoundError("Course was not found.")
    if course.trangThaiDuyet != "PENDING":
        raise WorkflowConflictError("Only pending courses are in the review queue.")
    return course


def decide_course(
    db: Session,
    user_id: int,
    course_id: int,
    payload: CourseDecisionRequest,
) -> tuple[KhoaHoc, DanhGiaChuyenGia]:
    expert = _get_expert_profile(db, user_id)
    course = workflow_repository.get_course_for_update(db, course_id)
    if course is None:
        raise WorkflowNotFoundError("Course was not found.")
    if course.trangThaiDuyet != "PENDING":
        raise WorkflowConflictError("Only pending courses may be reviewed.")

    now = _now()
    note = payload.ghiChu or payload.noiDungDanhGia
    review = DanhGiaChuyenGia(
        maKhoaHoc=course.maKhoaHoc,
        maChuyenGia=expert.maChuyenGia,
        noiDungDanhGia=payload.noiDungDanhGia,
        diemKyThuat=payload.diemKyThuat,
        diemNoiDung=payload.diemNoiDung,
        ghiChu=payload.ghiChu,
        trangThai=payload.trangThai,
        ngayTao=now,
    )
    course.trangThaiDuyet = payload.trangThai
    course.trangThaiHienThi = "HIDDEN"
    course.ngayCapNhat = now
    if payload.trangThai == "APPROVED":
        course.maNguoiDuyet = user_id
        course.ngayDuyet = now
        course.lyDoTuChoi = None
    else:
        course.maNguoiDuyet = None
        course.ngayDuyet = None
        course.lyDoTuChoi = note if payload.trangThai == "REJECTED" else None
    db.add(review)
    db.commit()
    db.refresh(course)
    db.refresh(review)
    return course, review


def list_expert_review_history(
    db: Session, user_id: int
) -> list[DanhGiaChuyenGia]:
    expert = _get_expert_profile(db, user_id)
    return workflow_repository.get_review_history_for_expert(
        db, expert.maChuyenGia
    )


def list_provider_course_review_history(
    db: Session, user_id: int, course_id: int
) -> list[DanhGiaChuyenGia]:
    _get_provider_profile(db, user_id)
    _get_owned_course(db, course_id, user_id)
    return workflow_repository.get_review_history_for_course(db, course_id)


def list_user_catalog(
    db: Session, *, query: str | None, category_id: int | None, limit: int
) -> list[KhoaHoc]:
    return workflow_repository.list_public_courses(
        db, query=query, category_id=category_id, limit=limit
    )


def get_user_course(
    db: Session, course_id: int, *, for_update: bool = False
) -> KhoaHoc:
    course = workflow_repository.get_public_course(
        db, course_id, for_update=for_update
    )
    if course is None:
        raise WorkflowNotFoundError("Course was not found.")
    return course


def user_is_enrolled(db: Session, user_id: int, course_id: int) -> bool:
    return workflow_repository.get_enrollment(db, user_id, course_id) is not None


def enroll_user_in_course(db: Session, user_id: int, course_id: int) -> DangKyKhoaHoc:
    # Serialize the (user, course) pair because the existing table has no unique constraint.
    db.execute(
        text("SELECT pg_advisory_xact_lock(:user_id, :course_id)"),
        {"user_id": user_id, "course_id": course_id},
    )
    course = get_user_course(db, course_id, for_update=True)
    existing = workflow_repository.get_enrollment(db, user_id, course_id)
    if existing is not None:
        raise WorkflowConflictError("You are already enrolled in this course.")
    enrollment = DangKyKhoaHoc(
        maNguoiDung=user_id,
        maKhoaHoc=course.maKhoaHoc,
        ngayDangKy=_now(),
        tienDo=0,
    )
    try:
        db.add(enrollment)
        db.commit()
        db.refresh(enrollment)
    except Exception:
        db.rollback()
        raise
    return enrollment


def list_user_enrollments(db: Session, user_id: int) -> list[DangKyKhoaHoc]:
    return workflow_repository.list_enrollments(db, user_id)


def get_user_learning_course(db: Session, user_id: int, course_id: int) -> tuple[KhoaHoc, set[int]]:
    course = get_user_course(db, course_id)
    if workflow_repository.get_enrollment(db, user_id, course_id) is None:
        raise WorkflowForbiddenError("Enroll in this course before accessing its lessons.")
    histories = workflow_repository.list_learning_history(db, user_id)
    completed = {
        item.maBaiHoc for item in histories
        if item.maKhoaHoc == course_id and item.tienDo == "COMPLETED" and item.maBaiHoc is not None
    }
    return course, completed


def complete_user_lesson(db: Session, user_id: int, course_id: int, lesson_id: int) -> tuple[KhoaHoc, set[int]]:
    course = get_user_course(db, course_id, for_update=True)
    if workflow_repository.get_enrollment(db, user_id, course_id, for_update=True) is None:
        raise WorkflowForbiddenError("Enroll in this course before updating lesson progress.")
    lesson = workflow_repository.get_owned_lesson(db, course, lesson_id)
    if lesson is None:
        raise WorkflowNotFoundError("Lesson was not found in this course.")
    history = workflow_repository.get_lesson_history(db, user_id, course_id, lesson_id, for_update=True)
    now = _now()
    if history is None:
        history = LichSuHocTap(
            maNguoiDung=user_id,
            maKhoaHoc=course_id,
            maBaiHoc=lesson_id,
            tienDo="COMPLETED",
            ngayTao=now,
        )
        db.add(history)
    elif history.tienDo != "COMPLETED":
        history.tienDo = "COMPLETED"
        history.ngayTao = now
    enrollment = workflow_repository.get_enrollment(db, user_id, course_id, for_update=True)
    completed = {
        item.maBaiHoc for item in workflow_repository.list_learning_history(db, user_id)
        if item.maKhoaHoc == course_id and item.tienDo == "COMPLETED" and item.maBaiHoc is not None
    }
    completed.add(lesson_id)
    total = len(course.baiHocs)
    percentage = round((len(completed & {item.maBaiHoc for item in course.baiHocs}) / total) * 100, 2) if total else 0
    enrollment.tienDo = percentage
    enrollment.ngayHoanThanh = now if total and percentage >= 100 else None
    try:
        db.commit()
    except Exception:
        db.rollback()
        raise
    return course, completed


def get_user_progress(db: Session, user_id: int, course_id: int):
    course = get_user_course(db, course_id)
    if workflow_repository.get_enrollment(db, user_id, course_id) is None:
        raise WorkflowForbiddenError("Enroll in this course before viewing its progress.")
    history = workflow_repository.list_learning_history(db, user_id)
    relevant = [item for item in history if item.maKhoaHoc == course_id]
    lesson_ids = {lesson.maBaiHoc for lesson in course.baiHocs}
    completed = {
        item.maBaiHoc for item in relevant
        if item.tienDo == "COMPLETED" and item.maBaiHoc in lesson_ids
    }
    total = len(lesson_ids)
    percentage = round((len(completed) / total) * 100, 2) if total else 0
    latest = max((item.ngayTao for item in relevant if item.ngayTao), default=None)
    return total, len(completed), percentage, latest


def get_user_learning_history(db: Session, user_id: int) -> list[LichSuHocTap]:
    return workflow_repository.list_learning_history(db, user_id)


