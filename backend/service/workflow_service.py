from datetime import UTC, datetime
from decimal import Decimal
import secrets
import string

from sqlalchemy import func, select, text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, joinedload

from utils.security import hash_password

from models import (
    BaiHoc,
    ChuyenGia,
    ChuyenGiaChuyenMon,
    ChuyenMon,
    ChuyenMonDanhMuc,
    DangKyKhoaHoc,
    DanhGiaChuyenGia,
    DanhMuc,
    DonXinNhaCungCap,
    KhoaHoc,
    LichSuHocTap,
    NguoiDung,
    NhaCungCapKhoaHoc,
    TaiLieu,
    VaiTro,
)
from repository import role_repository, user_repository, workflow_repository
from schemas.workflow import (
    AdminCreateExpertRequest,
    AdminVerifyExpertRequest,
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
    MaterialDecisionRequest,
    MaterialUpdateRequest,
    ProviderApplicationCreate,
    ProviderProfileUpdateRequest,
    SpecialtyCreateRequest,
    SpecialtyUpdateRequest,
)


class WorkflowNotFoundError(Exception):
    pass


class WorkflowConflictError(Exception):
    pass


class WorkflowForbiddenError(Exception):
    pass


class WorkflowPaymentRequiredError(Exception):
    pass


def _role_name(user: NguoiDung) -> str | None:
    return user.vaiTro.tenVaiTro.upper() if user.vaiTro and user.vaiTro.tenVaiTro else None


def _now() -> datetime:
    return datetime.now(UTC).replace(tzinfo=None)


def _is_auto_assignment_workflow_enabled() -> bool:
    """Server-side fail-closed flag (default False on Production until approved rollout)."""
    from config.config import get_settings

    return bool(get_settings().auto_assignment_workflow_enabled)


def _is_commerce_enrollment_gate_enabled() -> bool:
    """GĐ4.1 COM-01 rollout flag (default False until GĐ4.3/4.4 checkout is enabled)."""
    from config.config import get_settings

    return bool(get_settings().commerce_enrollment_gate_enabled)


def _get_provider_profile(db: Session, user_id: int) -> NhaCungCapKhoaHoc:
    profile = workflow_repository.get_provider_profile(db, user_id)
    if profile is None:
        raise WorkflowConflictError("Provider profile is not configured.")
    return profile


def _get_expert_profile(db: Session, user_id: int) -> ChuyenGia:
    statement = (
        select(ChuyenGia)
        .join(NguoiDung, ChuyenGia.maNguoiDung == NguoiDung.maNguoiDung)
        .join(VaiTro, NguoiDung.maVaiTro == VaiTro.maVaiTro)
        .options(
            joinedload(ChuyenGia.chuyenMonLinks).joinedload(
                ChuyenGiaChuyenMon.chuyenMon
            ),
            joinedload(ChuyenGia.nguoiDung).joinedload(NguoiDung.vaiTro),
        )
        .where(
            ChuyenGia.maNguoiDung == user_id,
            func.upper(VaiTro.tenVaiTro) == "EXPERT",
        )
    )
    profile = db.scalars(statement).unique().first()
    if profile is None:
        raise WorkflowConflictError("Hồ sơ chuyên gia chưa được cấu hình hoặc tài khoản không có vai trò Chuyên gia.")
    return profile


_VERIFICATION_STATUS_LABELS: dict[str, str] = {
    "DRAFT": "Bản nháp (chưa gửi xác minh)",
    "PENDING_VERIFICATION": "Đang chờ Quản trị viên xác minh",
    "NEEDS_UPDATE": "Cần bổ sung hồ sơ theo yêu cầu Quản trị viên",
}


def _require_verified_expert(
    db: Session, user_id: int, *, for_update: bool = False
) -> ChuyenGia:
    """Centralized SEC-01 guard: only ACTIVE, password-changed, VERIFIED EXPERTs may review content."""
    user_stmt = (
        select(NguoiDung)
        .options(joinedload(NguoiDung.vaiTro))
        .where(NguoiDung.maNguoiDung == user_id)
    )
    if for_update:
        user_stmt = user_stmt.with_for_update(of=NguoiDung)
    user = db.scalars(user_stmt).unique().first()
    if user is None or _role_name(user) != "EXPERT":
        raise WorkflowForbiddenError(
            "Tài khoản không có vai trò Chuyên gia kiểm duyệt hợp lệ."
        )
    if (getattr(user, "trangThai", "ACTIVE") or "ACTIVE").upper() != "ACTIVE":
        raise WorkflowForbiddenError(
            "Tài khoản chuyên gia không ở trạng thái hoạt động (ACTIVE) và không thể thực hiện kiểm duyệt."
        )
    if bool(getattr(user, "batBuocDoiMatKhau", False)):
        raise WorkflowForbiddenError(
            "Bạn cần đổi mật khẩu lần đầu trước khi thực hiện kiểm duyệt."
        )

    profile_stmt = (
        select(ChuyenGia)
        .options(
            joinedload(ChuyenGia.chuyenMonLinks).joinedload(
                ChuyenGiaChuyenMon.chuyenMon
            ),
        )
        .where(ChuyenGia.maNguoiDung == user_id)
    )
    if for_update:
        profile_stmt = profile_stmt.with_for_update(of=ChuyenGia)
    profile = db.scalars(profile_stmt).unique().first()
    if profile is None:
        raise WorkflowForbiddenError(
            "Hồ sơ chuyên gia chưa được thiết lập. Vui lòng liên hệ Quản trị viên."
        )
    profile_status = getattr(profile, "trangThaiHoSo", None) or "DRAFT"
    if profile_status != "VERIFIED":
        status_label = _VERIFICATION_STATUS_LABELS.get(profile_status, profile_status)
        raise WorkflowForbiddenError(
            f"Hồ sơ chuyên gia chưa được Quản trị viên xác minh ({status_label}). "
            "Vui lòng hoàn thiện hồ sơ chuyên môn và chờ xác minh trước khi kiểm duyệt."
        )
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


def list_admin_experts(db: Session) -> list[tuple[NguoiDung, ChuyenGia | None]]:
    statement = (
        select(NguoiDung)
        .join(VaiTro, NguoiDung.maVaiTro == VaiTro.maVaiTro)
        .options(
            joinedload(NguoiDung.vaiTro),
            joinedload(NguoiDung.chuyenGias)
            .joinedload(ChuyenGia.chuyenMonLinks)
            .joinedload(ChuyenGiaChuyenMon.chuyenMon),
        )
        .where(func.upper(VaiTro.tenVaiTro) == "EXPERT")
        .order_by(NguoiDung.maNguoiDung)
    )
    users = list(db.scalars(statement).unique().all())
    return [
        (user, user.chuyenGias[0] if user.chuyenGias else None)
        for user in users
    ]


def _load_specialty(db: Session, specialty_id: int) -> ChuyenMon | None:
    statement = (
        select(ChuyenMon)
        .options(
            joinedload(ChuyenMon.danhMucLinks).joinedload(ChuyenMonDanhMuc.danhMuc),
            joinedload(ChuyenMon.chuyenGiaLinks),
        )
        .where(ChuyenMon.maChuyenMon == specialty_id)
    )
    return db.scalars(statement).unique().first()


def list_admin_specialties(
    db: Session,
    *,
    status: str | None = None,
    group: str | None = None,
    query: str | None = None,
) -> list[ChuyenMon]:
    statement = (
        select(ChuyenMon)
        .options(
            joinedload(ChuyenMon.danhMucLinks).joinedload(ChuyenMonDanhMuc.danhMuc),
            joinedload(ChuyenMon.chuyenGiaLinks),
        )
        .order_by(ChuyenMon.nhomChuyenMon, ChuyenMon.tenChuyenMon)
    )
    if status and status.upper() in {"ACTIVE", "INACTIVE"}:
        statement = statement.where(ChuyenMon.trangThai == status.upper())
    if group and group.strip():
        statement = statement.where(ChuyenMon.nhomChuyenMon == group.strip())
    items = list(db.scalars(statement).unique().all())
    if query and query.strip():
        q = query.strip().lower()
        items = [
            item
            for item in items
            if q in (item.tenChuyenMon or "").lower()
            or q in (item.nhomChuyenMon or "").lower()
            or q in (item.moTa or "").lower()
        ]
    return items


def list_expert_specialty_catalog(db: Session) -> list[ChuyenMon]:
    return list_admin_specialties(db, status="ACTIVE")


def _assert_unique_specialty_name(
    db: Session, name: str, *, exclude_id: int | None = None
) -> None:
    normalized = name.strip().lower()
    statement = select(ChuyenMon.maChuyenMon).where(
        func.lower(func.btrim(ChuyenMon.tenChuyenMon)) == normalized
    )
    if exclude_id is not None:
        statement = statement.where(ChuyenMon.maChuyenMon != exclude_id)
    if db.scalar(statement.limit(1)) is not None:
        raise WorkflowConflictError(
            f'Chuyên môn "{name.strip()}" đã tồn tại trong danh mục hệ thống.'
        )


def _validate_category_ids(db: Session, category_ids: list[int]) -> None:
    if not category_ids:
        return
    found = set(
        db.scalars(
            select(DanhMuc.maDanhMuc).where(DanhMuc.maDanhMuc.in_(category_ids))
        ).all()
    )
    missing = [cid for cid in category_ids if cid not in found]
    if missing:
        raise WorkflowNotFoundError(
            f"Không tìm thấy danh mục khóa học/tài liệu với mã: {missing}."
        )


def create_specialty(
    db: Session, admin_user_id: int, payload: SpecialtyCreateRequest
) -> ChuyenMon:
    _assert_unique_specialty_name(db, payload.tenChuyenMon)
    _validate_category_ids(db, payload.danhMucIds)
    now = _now()
    specialty = ChuyenMon(
        tenChuyenMon=payload.tenChuyenMon,
        nhomChuyenMon=payload.nhomChuyenMon,
        moTa=payload.moTa,
        trangThai="ACTIVE",
        maNguoiTao=admin_user_id,
        ngayTao=now,
        ngayCapNhat=now,
    )
    db.add(specialty)
    db.flush()
    for cat_id in payload.danhMucIds:
        db.add(
            ChuyenMonDanhMuc(
                maChuyenMon=specialty.maChuyenMon,
                maDanhMuc=cat_id,
                ngayTao=now,
            )
        )
    db.commit()
    return _load_specialty(db, specialty.maChuyenMon) or specialty


def update_specialty(
    db: Session, specialty_id: int, payload: SpecialtyUpdateRequest
) -> ChuyenMon:
    specialty = _load_specialty(db, specialty_id)
    if specialty is None:
        raise WorkflowNotFoundError("Không tìm thấy chuyên môn.")
    from service import eligibility_service

    eligibility_service.lock_specialty_experts(db, specialty_id)
    db.refresh(specialty)
    changes = payload.model_dump(exclude_unset=True)
    if "tenChuyenMon" in changes and changes["tenChuyenMon"] is not None:
        _assert_unique_specialty_name(
            db, changes["tenChuyenMon"], exclude_id=specialty_id
        )
        specialty.tenChuyenMon = changes["tenChuyenMon"]
    if "nhomChuyenMon" in changes and changes["nhomChuyenMon"] is not None:
        specialty.nhomChuyenMon = changes["nhomChuyenMon"]
    if "moTa" in changes:
        specialty.moTa = changes["moTa"]
    now = _now()
    if "danhMucIds" in changes and changes["danhMucIds"] is not None:
        cat_ids = changes["danhMucIds"]
        _validate_category_ids(db, cat_ids)
        specialty.danhMucLinks.clear()
        db.flush()
        for cat_id in cat_ids:
            specialty.danhMucLinks.append(
                ChuyenMonDanhMuc(
                    maChuyenMon=specialty.maChuyenMon,
                    maDanhMuc=cat_id,
                    ngayTao=now,
                )
            )
    specialty.ngayCapNhat = now
    db.commit()
    return _load_specialty(db, specialty_id) or specialty


def update_specialty_status(
    db: Session, specialty_id: int, trang_thai: str
) -> ChuyenMon:
    specialty = _load_specialty(db, specialty_id)
    if specialty is None:
        raise WorkflowNotFoundError("Không tìm thấy chuyên môn.")
    from service import eligibility_service

    eligibility_service.lock_specialty_experts(db, specialty_id)
    db.refresh(specialty)
    specialty.trangThai = trang_thai
    specialty.ngayCapNhat = _now()
    db.commit()
    return _load_specialty(db, specialty_id) or specialty


def create_expert_account(
    db: Session, payload: AdminCreateExpertRequest
) -> tuple[NguoiDung, ChuyenGia, str]:
    username = payload.tenTaiKhoan
    email = str(payload.email).strip().lower()
    for lock_key in sorted((email, f"username:{username}")):
        db.execute(
            text("SELECT pg_advisory_xact_lock(hashtextextended(:key, 0))"),
            {"key": lock_key},
        )
    if user_repository.get_by_username(db, username) is not None:
        raise WorkflowConflictError("Tên tài khoản đã tồn tại trong hệ thống.")
    if user_repository.get_by_email(db, email) is not None:
        raise WorkflowConflictError("Email đã được sử dụng cho một tài khoản khác.")

    expert_role = role_repository.get_by_name(db, "EXPERT")
    if expert_role is None:
        raise WorkflowConflictError("Vai trò EXPERT chưa được cấu hình.")

    if payload.matKhauTamThoi:
        temp_password = payload.matKhauTamThoi
    else:
        alphabet = string.ascii_letters + string.digits + "@#$"
        temp_password = "Edu@" + "".join(secrets.choice(alphabet) for _ in range(8))

    now = _now()
    user = NguoiDung(
        maVaiTro=expert_role.maVaiTro,
        tenTaiKhoan=username,
        hoTen=payload.hoTen,
        email=email,
        matKhau=hash_password(temp_password),
        soDienThoai=payload.soDienThoai,
        trangThai="ACTIVE",
        batBuocDoiMatKhau=True,
    )
    db.add(user)
    db.flush()
    profile = ChuyenGia(
        maNguoiDung=user.maNguoiDung,
        trangThaiHoSo="DRAFT",
        ngayCapNhat=now,
    )
    db.add(profile)
    db.commit()
    loaded_user = user_repository.get_by_id(db, user.maNguoiDung) or user
    loaded_profile = _get_expert_profile(db, user.maNguoiDung)
    return loaded_user, loaded_profile, temp_password


def verify_expert_profile(
    db: Session,
    admin_user_id: int,
    target_user_id: int,
    payload: AdminVerifyExpertRequest,
) -> tuple[NguoiDung, ChuyenGia]:
    user = user_repository.get_by_id(db, target_user_id)
    if user is None:
        raise WorkflowNotFoundError("Không tìm thấy tài khoản chuyên gia.")
    if _role_name(user) != "EXPERT":
        raise WorkflowConflictError("Tài khoản này không có vai trò Chuyên gia.")
    profile = _get_expert_profile(db, target_user_id)

    if payload.trangThaiHoSo == "VERIFIED":
        primary_links = [
            link for link in profile.chuyenMonLinks if link.laChuyenMonChinh
        ]
        if len(primary_links) != 1:
            raise WorkflowConflictError(
                "Chuyên gia chưa chọn chuyên môn chính hợp lệ nên chưa thể xác minh."
            )
        if primary_links[0].chuyenMon.trangThai != "ACTIVE":
            raise WorkflowConflictError(
                "Chuyên môn chính của chuyên gia hiện đang ngừng sử dụng."
            )

    now = _now()
    profile.trangThaiHoSo = payload.trangThaiHoSo
    profile.ghiChuXacMinh = payload.ghiChuXacMinh
    profile.maNguoiXacMinh = admin_user_id
    profile.ngayXacMinh = now
    profile.ngayCapNhat = now
    if payload.trangThaiHoSo == "VERIFIED" and _is_auto_assignment_workflow_enabled():
        from service import assignment_queue_service

        db.flush()
        assignment_queue_service.wake_waiting_eligible_jobs(db, now=now)
    db.commit()
    return (
        user_repository.get_by_id(db, target_user_id) or user,
        _get_expert_profile(db, target_user_id),
    )


def list_expert_candidates(
    db: Session, *, category_id: int | None = None
) -> list[dict]:
    category_spec_ids: set[int] = set()
    category_groups: set[str] = set()
    if category_id is not None:
        if workflow_repository.get_category(db, category_id) is None:
            raise WorkflowNotFoundError("Không tìm thấy danh mục.")
        mapped_specs = list(
            db.scalars(
                select(ChuyenMon)
                .join(
                    ChuyenMonDanhMuc,
                    ChuyenMonDanhMuc.maChuyenMon == ChuyenMon.maChuyenMon,
                )
                .where(
                    ChuyenMonDanhMuc.maDanhMuc == category_id,
                    ChuyenMon.trangThai == "ACTIVE",
                )
            ).all()
        )
        category_spec_ids = {s.maChuyenMon for s in mapped_specs}
        category_groups = {s.nhomChuyenMon for s in mapped_specs if s.nhomChuyenMon}

    rows = list_admin_experts(db)
    review_counts = dict(
        db.execute(
            select(
                DanhGiaChuyenGia.maChuyenGia,
                func.count(DanhGiaChuyenGia.maDanhGia),
            ).group_by(DanhGiaChuyenGia.maChuyenGia)
        ).all()
    )

    candidates: list[dict] = []
    for user, profile in rows:
        if profile is None:
            continue
        if (getattr(user, "trangThai", "ACTIVE") or "ACTIVE").upper() != "ACTIVE":
            continue
        if bool(getattr(user, "batBuocDoiMatKhau", False)):
            continue
        if profile.trangThaiHoSo != "VERIFIED":
            continue

        primary = next(
            (link.chuyenMon for link in profile.chuyenMonLinks if link.laChuyenMonChinh),
            None,
        )
        secondaries = [
            link.chuyenMon
            for link in profile.chuyenMonLinks
            if not link.laChuyenMonChinh
        ]
        workload = int(review_counts.get(profile.maChuyenGia, 0) or 0)
        score = 0
        reasons: list[str] = ["Hồ sơ đã được Admin xác minh"]

        if category_id is not None:
            if primary and primary.maChuyenMon in category_spec_ids:
                score += 50
                reasons.append(
                    f'Chuyên môn chính "{primary.tenChuyenMon}" khớp trực tiếp với danh mục'
                )
            matched_sec = [
                s.tenChuyenMon
                for s in secondaries
                if s.maChuyenMon in category_spec_ids
            ]
            if matched_sec:
                score += 25
                reasons.append(
                    f'Chuyên môn phụ khớp danh mục: {", ".join(matched_sec)}'
                )
            elif primary and primary.nhomChuyenMon in category_groups:
                score += 10
                reasons.append(
                    f'Cùng nhóm chuyên môn "{primary.nhomChuyenMon}" với danh mục'
                )

        if profile.soNamKinhNghiem:
            score += min(profile.soNamKinhNghiem, 10)
            reasons.append(f"{profile.soNamKinhNghiem} năm kinh nghiệm thực tế")

        score -= workload * 2
        reasons.append(f"Tải hiện tại: {workload} lượt đánh giá đã ghi nhận")

        candidates.append(
            {
                "user": user,
                "profile": profile,
                "workload": workload,
                "score": score,
                "reasons": reasons,
            }
        )

    candidates.sort(key=lambda item: (-item["score"], item["workload"]))
    return candidates


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


def update_admin_user_status(
    db: Session,
    admin_user_id: int,
    target_user_id: int,
    trang_thai: str,
) -> NguoiDung:
    user = user_repository.get_by_id(db, target_user_id)
    if user is None:
        raise WorkflowNotFoundError("Không tìm thấy tài khoản người dùng.")
    if target_user_id == admin_user_id:
        raise WorkflowConflictError("Không thể tự khóa tài khoản quản trị đang đăng nhập.")
    if _role_name(user) == "ADMIN":
        raise WorkflowConflictError("Không thể thay đổi trạng thái khóa của tài khoản ADMIN.")

    from service import accountability_service

    if accountability_service.is_accountability_enabled() and _role_name(user) == "EXPERT":
        if (user.trangThai or "").upper() == "LOCKED" and trang_thai.upper() == "ACTIVE":
            raise WorkflowConflictError(
                "Không thể mở khóa tài khoản Chuyên gia qua API cập nhật chung. "
                "Vui lòng sử dụng quy trình mở khóa kỷ luật (ADMIN unlock) kèm lý do."
            )

    user.trangThai = trang_thai
    db.commit()
    return user_repository.get_by_id(db, target_user_id) or user


def delete_admin_user(
    db: Session,
    admin_user_id: int,
    target_user_id: int,
) -> None:
    user = user_repository.get_by_id(db, target_user_id)
    if user is None:
        raise WorkflowNotFoundError("Không tìm thấy tài khoản người dùng.")
    if target_user_id == admin_user_id:
        raise WorkflowConflictError("Không thể tự xóa tài khoản quản trị đang đăng nhập.")
    if _role_name(user) == "ADMIN":
        raise WorkflowConflictError("Không thể xóa tài khoản ADMIN.")

    provider_ids = list(
        db.scalars(
            select(NhaCungCapKhoaHoc.maNhaCungCap).where(
                NhaCungCapKhoaHoc.maNguoiDung == target_user_id
            )
        ).all()
    )
    expert_ids = list(
        db.scalars(
            select(ChuyenGia.maChuyenGia).where(
                ChuyenGia.maNguoiDung == target_user_id
            )
        ).all()
    )

    has_related = any(
        (
            db.scalar(
                select(DangKyKhoaHoc.maDangKy)
                .where(DangKyKhoaHoc.maNguoiDung == target_user_id)
                .limit(1)
            ),
            db.scalar(
                select(LichSuHocTap.maLichSu)
                .where(LichSuHocTap.maNguoiDung == target_user_id)
                .limit(1)
            ),
            db.scalar(
                select(DonXinNhaCungCap.maDon)
                .where(DonXinNhaCungCap.maNguoiDung == target_user_id)
                .limit(1)
            ),
            db.scalar(
                select(KhoaHoc.maKhoaHoc)
                .where(KhoaHoc.maNguoiDuyet == target_user_id)
                .limit(1)
            ),
            provider_ids
            and db.scalar(
                select(KhoaHoc.maKhoaHoc)
                .where(KhoaHoc.maNhaCungCap.in_(provider_ids))
                .limit(1)
            ),
            provider_ids
            and db.scalar(
                select(TaiLieu.maTaiLieu)
                .where(TaiLieu.maNhaCungCap.in_(provider_ids))
                .limit(1)
            ),
            expert_ids
            and db.scalar(
                select(DanhGiaChuyenGia.maDanhGia)
                .where(DanhGiaChuyenGia.maChuyenGia.in_(expert_ids))
                .limit(1)
            ),
        )
    )
    if has_related:
        raise WorkflowConflictError(
            "Tài khoản đã có dữ liệu khóa học, học tập hoặc kiểm duyệt nên không thể xóa. Hãy dùng tính năng Khóa tài khoản."
        )

    for profile in db.scalars(
        select(ChuyenGia).where(ChuyenGia.maNguoiDung == target_user_id)
    ).all():
        db.delete(profile)
    for profile in db.scalars(
        select(NhaCungCapKhoaHoc).where(
            NhaCungCapKhoaHoc.maNguoiDung == target_user_id
        )
    ).all():
        db.delete(profile)

    db.delete(user)
    db.commit()


def reset_expert_password(
    db: Session,
    target_user_id: int,
    new_password: str | None = None,
) -> tuple[NguoiDung, str]:
    user = user_repository.get_by_id(db, target_user_id)
    if user is None:
        raise WorkflowNotFoundError("Không tìm thấy tài khoản chuyên gia.")
    if _role_name(user) != "EXPERT":
        raise WorkflowConflictError(
            "Chỉ được cấp lại mật khẩu cho tài khoản có vai trò Chuyên gia (EXPERT)."
        )

    if new_password:
        plain_password = new_password
    else:
        alphabet = string.ascii_letters + string.digits + "@#$"
        plain_password = "Edu@" + "".join(secrets.choice(alphabet) for _ in range(8))

    user.matKhau = hash_password(plain_password)
    user.batBuocDoiMatKhau = True
    db.commit()
    return user_repository.get_by_id(db, target_user_id) or user, plain_password


def update_expert_profile(
    db: Session, user_id: int, payload: ExpertProfileUpdateRequest
) -> ChuyenGia:
    profile = _get_expert_profile(db, user_id)
    from service import eligibility_service

    eligibility_service.lock_expert_eligibility(db, int(profile.maChuyenGia))
    db.expire_all()
    profile = _get_expert_profile(db, user_id)
    changes = payload.model_dump(exclude_unset=True)
    now = _now()

    if "tieuSu" in changes:
        profile.tieuSu = changes["tieuSu"]
    if "soNamKinhNghiem" in changes:
        profile.soNamKinhNghiem = changes["soNamKinhNghiem"]
    if "chuyenMon" in changes:
        profile.chuyenMon = changes["chuyenMon"]

    specialties_changed = (
        "primarySpecialtyId" in changes or "secondarySpecialtyIds" in changes
    )
    if specialties_changed:
        existing_primary_id = next(
            (
                link.maChuyenMon
                for link in profile.chuyenMonLinks
                if link.laChuyenMonChinh
            ),
            None,
        )
        existing_secondary_ids = [
            link.maChuyenMon
            for link in profile.chuyenMonLinks
            if not link.laChuyenMonChinh
        ]
        existing_all_ids = {link.maChuyenMon for link in profile.chuyenMonLinks}

        new_primary_id = (
            changes["primarySpecialtyId"]
            if "primarySpecialtyId" in changes
            else existing_primary_id
        )
        new_secondary_ids = (
            changes["secondarySpecialtyIds"]
            if "secondarySpecialtyIds" in changes
            else existing_secondary_ids
        )
        if new_secondary_ids is None:
            new_secondary_ids = []

        if len(new_secondary_ids) != len(set(new_secondary_ids)):
            raise WorkflowConflictError(
                "Danh sách chuyên môn phụ không được chứa giá trị trùng lặp."
            )
        if new_primary_id is not None and new_primary_id in new_secondary_ids:
            raise WorkflowConflictError(
                "Chuyên môn chính không được đồng thời xuất hiện trong danh sách chuyên môn phụ."
            )

        requested_ids = list(
            dict.fromkeys(
                ([new_primary_id] if new_primary_id is not None else [])
                + new_secondary_ids
            )
        )
        if requested_ids:
            specs = list(
                db.scalars(
                    select(ChuyenMon).where(ChuyenMon.maChuyenMon.in_(requested_ids))
                ).all()
            )
            spec_by_id = {s.maChuyenMon: s for s in specs}
            missing = [sid for sid in requested_ids if sid not in spec_by_id]
            if missing:
                raise WorkflowNotFoundError(
                    f"Không tìm thấy chuyên môn với mã: {missing}."
                )
            for sid in requested_ids:
                spec = spec_by_id[sid]
                if spec.trangThai != "ACTIVE" and sid not in existing_all_ids:
                    raise WorkflowConflictError(
                        f'Chuyên môn "{spec.tenChuyenMon}" đã ngừng sử dụng, không thể chọn mới.'
                    )

        profile.chuyenMonLinks.clear()
        db.flush()
        if new_primary_id is not None:
            profile.chuyenMonLinks.append(
                ChuyenGiaChuyenMon(
                    maChuyenGia=profile.maChuyenGia,
                    maChuyenMon=new_primary_id,
                    laChuyenMonChinh=True,
                    ngayTao=now,
                )
            )
        for sec_id in new_secondary_ids:
            profile.chuyenMonLinks.append(
                ChuyenGiaChuyenMon(
                    maChuyenGia=profile.maChuyenGia,
                    maChuyenMon=sec_id,
                    laChuyenMonChinh=False,
                    ngayTao=now,
                )
            )

        # If a verified expert modifies their specialties, require re-verification
        if profile.trangThaiHoSo == "VERIFIED" and (
            new_primary_id != existing_primary_id
            or set(new_secondary_ids) != set(existing_secondary_ids)
        ):
            profile.trangThaiHoSo = "DRAFT"

    profile.ngayCapNhat = now
    db.commit()
    return _get_expert_profile(db, user_id)


def submit_expert_profile_for_verification(db: Session, user_id: int) -> ChuyenGia:
    profile = _get_expert_profile(db, user_id)
    primary_links = [
        link for link in profile.chuyenMonLinks if link.laChuyenMonChinh
    ]
    secondary_links = [
        link for link in profile.chuyenMonLinks if not link.laChuyenMonChinh
    ]
    if len(primary_links) != 1:
        raise WorkflowConflictError(
            "Vui lòng chọn đúng 1 chuyên môn chính trước khi gửi hồ sơ xác minh."
        )
    primary_spec = primary_links[0].chuyenMon
    if primary_spec.trangThai != "ACTIVE":
        raise WorkflowConflictError(
            f'Chuyên môn chính "{primary_spec.tenChuyenMon}" đã ngừng sử dụng. Vui lòng chọn chuyên môn khác đang hoạt động.'
        )
    for sec in secondary_links:
        if sec.maChuyenMon == primary_links[0].maChuyenMon:
            raise WorkflowConflictError(
                "Chuyên môn chính không được trùng với chuyên môn phụ."
            )
    if not (profile.tieuSu or "").strip():
        raise WorkflowConflictError(
            "Vui lòng nhập mô tả kinh nghiệm kiểm duyệt trước khi gửi hồ sơ."
        )
    if profile.soNamKinhNghiem is None:
        raise WorkflowConflictError(
            "Vui lòng cung cấp số năm kinh nghiệm trước khi gửi hồ sơ."
        )

    profile.trangThaiHoSo = "PENDING_VERIFICATION"
    profile.ngayCapNhat = _now()
    db.commit()
    return _get_expert_profile(db, user_id)


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
        hinhAnh=payload.hinhAnh,
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


def assert_provider_course_editable(
    db: Session,
    user_id: int,
    course_id: int,
) -> KhoaHoc:
    _get_provider_profile(db, user_id)
    course = _get_owned_course(db, course_id, user_id)
    _require_editable_course(course)
    return course


def set_provider_course_cover_image(
    db: Session,
    user_id: int,
    course_id: int,
    image_url: str | None,
) -> tuple[KhoaHoc, str | None]:
    _get_provider_profile(db, user_id)
    course = _get_owned_course(db, course_id, user_id, for_update=True)
    _require_editable_course(course)
    previous_url = course.hinhAnh
    course.hinhAnh = image_url
    course.ngayCapNhat = _now()
    db.commit()
    db.refresh(course)
    return course, previous_url


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
    if _is_auto_assignment_workflow_enabled():
        from service import assignment_queue_service

        course.soVongKiemDuyetHienTai = int(course.soVongKiemDuyetHienTai or 0) + 1
        db.flush()
        assignment_queue_service.enqueue_assignment_job(
            db,
            target_type="COURSE",
            target_id=course.maKhoaHoc,
            review_round=int(course.soVongKiemDuyetHienTai),
            event_type="SUBMIT",
            now=course.ngayCapNhat,
        )
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
    provider = _get_provider_profile(db, user_id)
    course = _get_owned_course(db, course_id, user_id, for_update=True)
    _require_editable_course(course)
    lesson = workflow_repository.get_owned_lesson(db, course, lesson_id)
    if lesson is None:
        raise WorkflowNotFoundError("Lesson was not found in this course.")
    now = _now()
    material = TaiLieu(
        maNhaCungCap=provider.maNhaCungCap,
        maKhoaHoc=course.maKhoaHoc,
        maBaiHoc=lesson.maBaiHoc,
        maDanhMuc=course.maDanhMuc,
        tieuDe=payload.tieuDe,
        duongDanTep=payload.duongDanTep,
        loai=payload.loai or "DOCUMENT",
        moTa=payload.moTa,
        trangThaiDuyet=course.trangThaiDuyet or "DRAFT",
        trangThaiHienThi=course.trangThaiHienThi or "HIDDEN",
        ngayTao=now,
        ngayCapNhat=now,
    )
    course.ngayCapNhat = now
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
    allowed_fields = {"tieuDe", "duongDanTep", "loai", "moTa", "maDanhMuc"}
    changes = payload.model_dump(exclude_unset=True)
    disallowed = set(changes) - allowed_fields
    if disallowed:
        raise WorkflowForbiddenError(
            "Course/lesson reassignment or visibility changes are not allowed via this endpoint."
        )
    if (
        "maDanhMuc" in changes
        and changes["maDanhMuc"] is not None
        and workflow_repository.get_category(db, changes["maDanhMuc"]) is None
    ):
        raise WorkflowNotFoundError("Category was not found.")
    for field, value in changes.items():
        setattr(material, field, value)
    now = _now()
    material.ngayCapNhat = now
    course.ngayCapNhat = now
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
    has_review = bool(material.danhGiaChuyenGias) or (
        db.scalar(
            select(DanhGiaChuyenGia.maDanhGia)
            .where(DanhGiaChuyenGia.maTaiLieu == material_id)
            .limit(1)
        )
        is not None
    )
    if has_review:
        raise WorkflowConflictError(
            "Materials with expert review history cannot be deleted."
        )
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
    expert = _require_verified_expert(db, user_id)
    if _is_auto_assignment_workflow_enabled():
        from models import PhanCongKiemDuyet

        assigned_course_ids = list(
            db.scalars(
                select(PhanCongKiemDuyet.maKhoaHoc).where(
                    PhanCongKiemDuyet.maChuyenGia == expert.maChuyenGia,
                    PhanCongKiemDuyet.maKhoaHoc.is_not(None),
                    PhanCongKiemDuyet.trangThai.in_(("ACCEPTED", "IN_PROGRESS")),
                )
            ).all()
        )
        if not assigned_course_ids:
            return []
        return list(
            db.scalars(
                select(KhoaHoc).where(
                    KhoaHoc.maKhoaHoc.in_(assigned_course_ids),
                    KhoaHoc.trangThaiDuyet == "PENDING",
                )
            ).all()
        )
    return workflow_repository.list_courses_for_review(db)


def get_expert_course(db: Session, user_id: int, course_id: int) -> KhoaHoc:
    if _is_auto_assignment_workflow_enabled():
        from service import assignment_lifecycle_service

        _, _, target = assignment_lifecycle_service.require_owned_review_assignment(
            db,
            user_id=user_id,
            target_type="COURSE",
            target_id=course_id,
            allowed_states={"ACCEPTED", "IN_PROGRESS"},
            require_current_round=True,
        )
        assert isinstance(target, KhoaHoc)
        if target.trangThaiDuyet != "PENDING":
            raise WorkflowConflictError("Only pending courses are in the review queue.")
        return target

    _require_verified_expert(db, user_id)
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
    if _is_auto_assignment_workflow_enabled():
        from service import assignment_lifecycle_service

        _, pc, _ = assignment_lifecycle_service.require_owned_review_assignment(
            db,
            user_id=user_id,
            target_type="COURSE",
            target_id=course_id,
            allowed_states={"ACCEPTED", "IN_PROGRESS"},
            require_current_round=True,
        )
        target, review, _ = assignment_lifecycle_service.submit_assignment_decision(
            db,
            user_id,
            int(pc.maPhanCong),
            trang_thai=payload.trangThai,
            noi_dung_danh_gia=payload.noiDungDanhGia,
            ghi_chu=payload.ghiChu,
            diem_ky_thuat=payload.diemKyThuat,
            diem_noi_dung=payload.diemNoiDung,
        )
        assert isinstance(target, KhoaHoc)
        return target, review

    course = workflow_repository.get_course_for_update(db, course_id)
    if course is None:
        raise WorkflowNotFoundError("Course was not found.")
    expert = _require_verified_expert(db, user_id, for_update=True)
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


def get_user_enrolled_course_ids(
    db: Session, user_id: int, course_ids: set[int]
) -> set[int]:
    return workflow_repository.list_enrolled_course_ids(db, user_id, course_ids)


def enroll_user_in_course(db: Session, user_id: int, course_id: int) -> DangKyKhoaHoc:
    # Serialize the (user, course) pair alongside DB UNIQUE (maNguoiDung, maKhoaHoc).
    db.execute(
        text("SELECT pg_advisory_xact_lock(:user_id, :course_id)"),
        {"user_id": user_id, "course_id": course_id},
    )
    course = get_user_course(db, course_id, for_update=True)

    # COM-01 & COM-03: When commerce gate is active, direct enrollment is strictly limited to free courses (gia == 0).
    if _is_commerce_enrollment_gate_enabled():
        if course.gia is None:
            raise WorkflowConflictError(
                "Khóa học chưa có học phí hợp lệ nên không thể đăng ký trực tiếp."
            )
        price = Decimal(course.gia)
        if price < Decimal("0"):
            raise WorkflowConflictError("Học phí khóa học không hợp lệ.")
        if price > Decimal("0"):
            raise WorkflowPaymentRequiredError(
                "Khóa học trả phí yêu cầu thanh toán hợp lệ trước khi cấp quyền học."
            )

    existing = workflow_repository.get_enrollment(
        db, user_id, course_id, for_update=True, active_only=False
    )
    if existing is not None:
        if existing.trangThaiQuyenHoc == "ACTIVE":
            raise WorkflowConflictError("You are already enrolled in this course.")
        # Re-activate a previously REVOKED enrollment while preserving tienDo and LichSuHocTap
        existing.trangThaiQuyenHoc = "ACTIVE"
        existing.nguonCapQuyen = (
            "FREE" if (course.gia is not None and Decimal(course.gia) == Decimal("0")) else "LEGACY"
        )
        existing.ngayThuHoi = None
        existing.lyDoThuHoi = None
        try:
            db.commit()
            db.refresh(existing)
        except Exception:
            db.rollback()
            raise
        return existing

    grant_source = (
        "FREE" if (course.gia is not None and Decimal(course.gia) == Decimal("0")) else "LEGACY"
    )
    enrollment = DangKyKhoaHoc(
        maNguoiDung=user_id,
        maKhoaHoc=course.maKhoaHoc,
        ngayDangKy=_now(),
        tienDo=0,
        nguonCapQuyen=grant_source,
        trangThaiQuyenHoc="ACTIVE",
    )
    try:
        db.add(enrollment)
        db.commit()
        db.refresh(enrollment)
    except IntegrityError as exc:
        db.rollback()
        raise WorkflowConflictError("You are already enrolled in this course.") from exc
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


def get_admin_analytics_summary(db: Session) -> dict[str, int | float]:
    return workflow_repository.get_admin_analytics_summary(db)


def list_provider_materials(db: Session, user_id: int) -> list[TaiLieu]:
    _get_provider_profile(db, user_id)
    return workflow_repository.list_owned_materials(db, user_id)


def get_provider_material(db: Session, user_id: int, material_id: int) -> TaiLieu:
    _get_provider_profile(db, user_id)
    material = workflow_repository.get_owned_material_by_id(
        db, user_id, material_id
    )
    if material is None:
        raise WorkflowNotFoundError("Material was not found for this provider.")
    return material


def create_provider_standalone_material(
    db: Session, user_id: int, payload: MaterialCreateRequest
) -> TaiLieu:
    provider = _get_provider_profile(db, user_id)
    course = None
    lesson = None

    if payload.maKhoaHoc is not None:
        course = _get_owned_course(db, payload.maKhoaHoc, user_id)
    if payload.maBaiHoc is not None:
        if course is None:
            lesson = db.get(BaiHoc, payload.maBaiHoc)
            if lesson is None:
                raise WorkflowNotFoundError("Lesson was not found.")
            course = _get_owned_course(db, lesson.maKhoaHoc, user_id)
        else:
            lesson = workflow_repository.get_owned_lesson(db, course, payload.maBaiHoc)
            if lesson is None:
                raise WorkflowNotFoundError(
                    "Lesson does not belong to the selected course."
                )

    category_id = payload.maDanhMuc
    if category_id is None and course is not None:
        category_id = course.maDanhMuc

    if category_id is not None:
        category = db.get(DanhMuc, category_id)
        if category is None:
            raise WorkflowNotFoundError("Category was not found.")

    now = _now()
    material = TaiLieu(
        maNhaCungCap=provider.maNhaCungCap,
        maKhoaHoc=course.maKhoaHoc if course else None,
        maBaiHoc=lesson.maBaiHoc if lesson else None,
        maDanhMuc=category_id,
        tieuDe=payload.tieuDe,
        duongDanTep=payload.duongDanTep,
        loai=payload.loai or "DOCUMENT",
        moTa=payload.moTa,
        trangThaiDuyet="DRAFT",
        trangThaiHienThi="HIDDEN",
        ngayTao=now,
        ngayCapNhat=now,
    )
    db.add(material)
    db.commit()
    db.refresh(material)
    return material


def update_provider_material_by_id(
    db: Session, user_id: int, material_id: int, payload: MaterialUpdateRequest
) -> TaiLieu:
    _get_provider_profile(db, user_id)
    material = workflow_repository.get_owned_material_by_id(
        db, user_id, material_id, for_update=True
    )
    if material is None:
        raise WorkflowNotFoundError("Material was not found for this provider.")

    if material.trangThaiDuyet not in {"DRAFT", "REJECTED", "NEEDS_REVISION"}:
        raise WorkflowConflictError(
            "Only draft, rejected, or needs-revision materials can be edited."
        )

    allowed_fields = {
        "tieuDe",
        "duongDanTep",
        "loai",
        "moTa",
        "maDanhMuc",
        "maKhoaHoc",
        "maBaiHoc",
    }
    data = payload.model_dump(exclude_unset=True)
    if set(data) - allowed_fields:
        raise WorkflowForbiddenError("One or more fields cannot be updated by provider.")

    target_course_id = (
        data["maKhoaHoc"] if "maKhoaHoc" in data else material.maKhoaHoc
    )
    target_lesson_id = (
        data["maBaiHoc"] if "maBaiHoc" in data else material.maBaiHoc
    )

    # If provider explicitly detaches the course without detaching the lesson, reject.
    if (
        "maKhoaHoc" in data
        and data["maKhoaHoc"] is None
        and target_lesson_id is not None
    ):
        raise WorkflowConflictError(
            "Cannot detach course while a lesson is still linked to this material."
        )

    course = None
    if target_course_id is not None:
        course = _get_owned_course(db, target_course_id, user_id)

    if target_lesson_id is not None:
        if course is None:
            lesson = db.get(BaiHoc, target_lesson_id)
            if lesson is None:
                raise WorkflowNotFoundError("Lesson was not found.")
            if lesson.maKhoaHoc is None:
                raise WorkflowConflictError("Lesson is not associated with any course.")
            course = _get_owned_course(db, lesson.maKhoaHoc, user_id)
            data["maKhoaHoc"] = course.maKhoaHoc
        else:
            lesson = workflow_repository.get_owned_lesson(db, course, target_lesson_id)
            if lesson is None:
                raise WorkflowConflictError(
                    "Lesson does not belong to the selected course."
                )

    if "maDanhMuc" in data and data["maDanhMuc"] is not None:
        cat = db.get(DanhMuc, data["maDanhMuc"])
        if cat is None:
            raise WorkflowNotFoundError("Category was not found.")

    for field, value in data.items():
        setattr(material, field, value)

    material.ngayCapNhat = _now()
    db.commit()
    db.refresh(material)
    return material


def delete_provider_material_by_id(
    db: Session, user_id: int, material_id: int
) -> None:
    _get_provider_profile(db, user_id)
    material = workflow_repository.get_owned_material_by_id(
        db, user_id, material_id, for_update=True
    )
    if material is None:
        raise WorkflowNotFoundError("Material was not found for this provider.")
    if material.trangThaiDuyet not in {"DRAFT", "REJECTED", "NEEDS_REVISION"}:
        raise WorkflowConflictError(
            "Only draft, rejected, or needs-revision materials can be deleted."
        )

    has_review = bool(material.danhGiaChuyenGias) or (
        db.scalar(
            select(DanhGiaChuyenGia.maDanhGia)
            .where(DanhGiaChuyenGia.maTaiLieu == material_id)
            .limit(1)
        )
        is not None
    )
    if has_review:
        raise WorkflowConflictError(
            "Materials with expert review history cannot be deleted. Please revise and resubmit instead."
        )

    db.delete(material)
    db.commit()


def submit_provider_material(
    db: Session, user_id: int, material_id: int
) -> TaiLieu:
    _get_provider_profile(db, user_id)
    material = workflow_repository.get_owned_material_by_id(
        db, user_id, material_id, for_update=True
    )
    if material is None:
        raise WorkflowNotFoundError("Material was not found for this provider.")
    if material.trangThaiDuyet not in {"DRAFT", "REJECTED", "NEEDS_REVISION"}:
        raise WorkflowConflictError(
            "Only draft, rejected, or needs-revision materials can be submitted."
        )
    if not material.tieuDe or not material.duongDanTep:
        raise WorkflowConflictError("Title and file path are required for submission.")
    is_standalone = material.maKhoaHoc is None and material.maBaiHoc is None
    if is_standalone:
        if material.maDanhMuc is None:
            raise WorkflowConflictError(
                "Vui lòng chọn danh mục cho tài liệu trước khi gửi kiểm duyệt."
            )
        if workflow_repository.get_category(db, material.maDanhMuc) is None:
            raise WorkflowNotFoundError(
                "Danh mục của tài liệu không tồn tại trên hệ thống."
            )

    material.trangThaiDuyet = "PENDING"
    material.trangThaiHienThi = "HIDDEN"
    material.maNguoiDuyet = None
    material.ngayDuyet = None
    material.lyDoTuChoi = None
    material.ngayCapNhat = _now()
    if _is_auto_assignment_workflow_enabled() and is_standalone:
        from service import assignment_queue_service

        material.soVongKiemDuyetHienTai = int(material.soVongKiemDuyetHienTai or 0) + 1
        db.flush()
        assignment_queue_service.enqueue_assignment_job(
            db,
            target_type="MATERIAL",
            target_id=material.maTaiLieu,
            review_round=int(material.soVongKiemDuyetHienTai),
            event_type="SUBMIT",
            now=material.ngayCapNhat,
        )
    db.commit()
    db.refresh(material)
    return material


def list_expert_materials(db: Session, user_id: int) -> list[TaiLieu]:
    expert = _require_verified_expert(db, user_id)
    if _is_auto_assignment_workflow_enabled():
        from models import PhanCongKiemDuyet

        assigned_mat_ids = list(
            db.scalars(
                select(PhanCongKiemDuyet.maTaiLieu).where(
                    PhanCongKiemDuyet.maChuyenGia == expert.maChuyenGia,
                    PhanCongKiemDuyet.maTaiLieu.is_not(None),
                    PhanCongKiemDuyet.trangThai.in_(("ACCEPTED", "IN_PROGRESS")),
                )
            ).all()
        )
        if not assigned_mat_ids:
            return []
        return list(
            db.scalars(
                select(TaiLieu).where(
                    TaiLieu.maTaiLieu.in_(assigned_mat_ids),
                    TaiLieu.trangThaiDuyet == "PENDING",
                )
            ).all()
        )
    return workflow_repository.list_pending_materials_for_expert(db)


def get_expert_material(db: Session, user_id: int, material_id: int) -> TaiLieu:
    if _is_auto_assignment_workflow_enabled():
        from service import assignment_lifecycle_service

        _, _, target = assignment_lifecycle_service.require_owned_review_assignment(
            db,
            user_id=user_id,
            target_type="MATERIAL",
            target_id=material_id,
            allowed_states={"ACCEPTED", "IN_PROGRESS"},
            require_current_round=True,
        )
        assert isinstance(target, TaiLieu)
        if target.trangThaiDuyet != "PENDING":
            raise WorkflowNotFoundError("Material was not found in review queue.")
        return target

    _require_verified_expert(db, user_id)
    material = workflow_repository.get_expert_material(db, material_id)
    if material is None or material.trangThaiDuyet != "PENDING":
        raise WorkflowNotFoundError("Material was not found in review queue.")
    return material


def decide_material(
    db: Session,
    user_id: int,
    material_id: int,
    payload: MaterialDecisionRequest,
) -> tuple[TaiLieu, DanhGiaChuyenGia]:
    if _is_auto_assignment_workflow_enabled():
        from service import assignment_lifecycle_service

        _, pc, _ = assignment_lifecycle_service.require_owned_review_assignment(
            db,
            user_id=user_id,
            target_type="MATERIAL",
            target_id=material_id,
            allowed_states={"ACCEPTED", "IN_PROGRESS"},
            require_current_round=True,
        )
        target, review, _ = assignment_lifecycle_service.submit_assignment_decision(
            db,
            user_id,
            int(pc.maPhanCong),
            trang_thai=payload.trangThai,
            noi_dung_danh_gia=payload.noiDungDanhGia,
            ghi_chu=payload.ghiChu,
        )
        assert isinstance(target, TaiLieu)
        return target, review

    material = workflow_repository.get_expert_material(
        db, material_id, for_update=True
    )
    if material is None:
        raise WorkflowNotFoundError("Material was not found.")
    expert = _require_verified_expert(db, user_id, for_update=True)
    if material.trangThaiDuyet != "PENDING":
        raise WorkflowConflictError("Only pending materials may be reviewed.")

    note = (payload.ghiChu or "").strip() or (payload.noiDungDanhGia or "").strip() or None
    if payload.trangThai in {"REJECTED", "NEEDS_REVISION"} and not note:
        raise WorkflowConflictError(
            "A review note or reason is required when rejecting or requesting revision."
        )

    now = _now()
    review = DanhGiaChuyenGia(
        maTaiLieu=material.maTaiLieu,
        maChuyenGia=expert.maChuyenGia,
        noiDungDanhGia=payload.noiDungDanhGia,
        ghiChu=payload.ghiChu,
        trangThai=payload.trangThai,
        ngayTao=now,
    )
    material.trangThaiDuyet = payload.trangThai
    material.trangThaiHienThi = (
        "VISIBLE" if payload.trangThai == "APPROVED" else "HIDDEN"
    )
    material.ngayCapNhat = now
    if payload.trangThai == "APPROVED":
        material.maNguoiDuyet = user_id
        material.ngayDuyet = now
        material.lyDoTuChoi = None
    else:
        material.maNguoiDuyet = None
        material.ngayDuyet = None
        material.lyDoTuChoi = note

    db.add(review)
    db.commit()
    db.refresh(material)
    db.refresh(review)
    return material, review


def list_public_materials(
    db: Session,
    query: str | None = None,
    category_id: int | None = None,
    material_type: str | None = None,
    limit: int = 50,
    offset: int = 0,
) -> tuple[list[TaiLieu], int]:
    return workflow_repository.list_public_materials(
        db,
        query=query,
        category_id=category_id,
        material_type=material_type,
        limit=limit,
        offset=offset,
    )


def get_public_material(db: Session, material_id: int) -> TaiLieu:
    material = workflow_repository.get_public_material(db, material_id)
    if material is None:
        raise WorkflowNotFoundError("Public learning material was not found.")
    return material


def list_admin_materials(
    db: Session,
    query: str | None = None,
    category_id: int | None = None,
    status: str | None = None,
    limit: int = 20,
    offset: int = 0,
) -> tuple[list[TaiLieu], int]:
    return workflow_repository.list_admin_materials(
        db,
        query=query,
        category_id=category_id,
        status=status,
        limit=limit,
        offset=offset,
    )


def set_material_visibility(db: Session, material_id: int, visibility: str) -> TaiLieu:
    material = db.get(TaiLieu, material_id)
    if material is None:
        raise WorkflowNotFoundError("Material was not found.")
    if material.trangThaiDuyet != "APPROVED":
        raise WorkflowForbiddenError(
            "Only EXPERT-approved materials may change visibility."
        )
    material.trangThaiHienThi = visibility
    material.ngayCapNhat = _now()
    db.commit()
    db.refresh(material)
    return material
