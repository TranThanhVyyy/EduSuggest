from collections.abc import Callable
from pathlib import Path
from typing import Annotated, ParamSpec, TypeVar
import uuid

from fastapi import APIRouter, Depends, File, HTTPException, Query, Response, UploadFile, status
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from api.dependencies import get_optional_current_user, require_roles
from config.database import get_db
from config.storage import course_media_directory
from models import KhoaHoc, NguoiDung
from schemas.workflow import (
    AdminAnalyticsSummaryResponse,
    AdminCreateExpertRequest,
    AdminCreateExpertResponse,
    AdminExpertCandidateResponse,
    AdminExpertSummaryResponse,
    AdminProviderApplicationResponse,
    AdminResetExpertPasswordRequest,
    AdminResetExpertPasswordResponse,
    AdminUserResponse,
    AdminUserStatusUpdateRequest,
    AdminVerifyExpertRequest,
    CategoryCreateRequest,
    CategoryResponse,
    CategoryUpdateRequest,
    CourseCreateRequest,
    CourseDecisionRequest,
    CourseDetailResponse,
    CourseLessonDetailResponse,
    CourseResponse,
    CourseUpdateRequest,
    ExpertProfileResponse,
    ExpertProfileUpdateRequest,
    ExpertReviewResponse,
    ExpertSpecialtyItem,
    GrantExpertRoleRequest,
    LessonCreateRequest,
    LessonResponse,
    LessonUpdateRequest,
    EnrollmentResponse,
    LearningCourseResponse,
    LearningHistoryResponse,
    LearningLessonResponse,
    LearningProgressResponse,
    MaterialCreateRequest,
    MaterialDecisionRequest,
    MaterialResponse,
    MaterialUpdateRequest,
    PaginatedMaterialResponse,
    ProviderApplicationCreate,
    ProviderApplicationResponse,
    ProviderProfileResponse,
    ProviderProfileUpdateRequest,
    PublicSyllabusLessonResponse,
    RejectProviderApplicationRequest,
    SpecialtyCategoryRef,
    SpecialtyCreateRequest,
    SpecialtyResponse,
    SpecialtyStatusUpdateRequest,
    SpecialtyUpdateRequest,
    VisibilityUpdateRequest,
)
from service import private_material_service, workflow_service
from service.private_file_storage import PrivateFileValidationError
from service.workflow_service import (
    WorkflowConflictError,
    WorkflowForbiddenError,
    WorkflowNotFoundError,
    WorkflowPaymentRequiredError,
)

router = APIRouter(tags=["workflow"])

P = ParamSpec("P")
T = TypeVar("T")

_COURSE_MEDIA_DIR = course_media_directory()
_ALLOWED_IMAGE_TYPES: dict[str, str] = {
    "image/jpeg": ".jpg",
    "image/png": ".png",
    "image/webp": ".webp",
    "image/gif": ".gif",
}
_MAX_COVER_IMAGE_BYTES = 5 * 1024 * 1024  # 5 MB


async def _save_course_cover_upload(file: UploadFile, *, prefix: str = "course") -> str:
    content_type = (file.content_type or "").lower().strip()
    ext = _ALLOWED_IMAGE_TYPES.get(content_type)
    if ext is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Chỉ hỗ trợ tệp ảnh JPG, PNG, WEBP hoặc GIF.",
        )
    data = await file.read(_MAX_COVER_IMAGE_BYTES + 1)
    if not data:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Tệp ảnh tải lên đang rỗng.",
        )
    if len(data) > _MAX_COVER_IMAGE_BYTES:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail="Ảnh bìa khóa học vượt quá giới hạn 5 MB.",
        )
    _COURSE_MEDIA_DIR.mkdir(parents=True, exist_ok=True)
    filename = f"{prefix}-{uuid.uuid4().hex[:12]}{ext}"
    target_path = _COURSE_MEDIA_DIR / filename
    target_path.write_bytes(data)
    return f"/media/courses/{filename}"


def _remove_local_course_cover(image_url: str | None) -> None:
    if not image_url or not image_url.startswith("/media/courses/"):
        return
    filename = Path(image_url).name
    if not filename or filename != image_url.removeprefix("/media/courses/"):
        return
    candidate = (_COURSE_MEDIA_DIR / filename).resolve()
    try:
        candidate.relative_to(_COURSE_MEDIA_DIR.resolve())
    except ValueError:
        return
    if candidate.is_file():
        try:
            candidate.unlink()
        except OSError:
            pass


def _run_workflow(operation: Callable[P, T], *args: P.args, **kwargs: P.kwargs) -> T:
    try:
        return operation(*args, **kwargs)
    except WorkflowNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)
        ) from exc
    except WorkflowForbiddenError as exc:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail=str(exc)
        ) from exc
    except WorkflowConflictError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT, detail=str(exc)
        ) from exc
    except WorkflowPaymentRequiredError as exc:
        raise HTTPException(
            status_code=status.HTTP_402_PAYMENT_REQUIRED, detail=str(exc)
        ) from exc


def _admin_application_response(application) -> AdminProviderApplicationResponse:
    applicant = application.nguoiDung
    return AdminProviderApplicationResponse(
        maDon=application.maDon,
        maNguoiDung=application.maNguoiDung,
        toChuc=application.toChuc,
        kinhNghiem=application.kinhNghiem,
        lyDoDangKy=application.lyDoDangKy,
        chuyenMon=application.chuyenMon,
        gioiThieu=application.gioiThieu,
        trangThai=application.trangThai,
        lyDoTuChoi=application.lyDoTuChoi,
        ngayGui=application.ngayGui,
        ngayXuLy=application.ngayXuLy,
        hoTen=applicant.hoTen,
        email=applicant.email,
        soDienThoai=applicant.soDienThoai,
    )


def _course_detail(
    course: KhoaHoc,
    *,
    include_learning_content: bool = True,
    public_only_materials: bool = False,
) -> CourseDetailResponse:
    provider_name = None
    if getattr(course, "nhaCungCap", None) is not None and getattr(course.nhaCungCap, "nguoiDung", None) is not None:
        provider_name = course.nhaCungCap.nguoiDung.hoTen or course.nhaCungCap.nguoiDung.tenTaiKhoan
    ordered_lessons = sorted(
        list(course.baiHocs or []),
        key=lambda l: (l.thuTu if l.thuTu is not None else 999999, l.maBaiHoc),
    )
    public_syllabus = [
        PublicSyllabusLessonResponse(
            maBaiHoc=lesson.maBaiHoc,
            tieuDe=lesson.tieuDe,
            thuTu=lesson.thuTu,
            thoiLuong=lesson.thoiLuong,
        )
        for lesson in ordered_lessons
    ]
    return CourseDetailResponse(
        **CourseResponse.model_validate(course).model_dump(),
        tenNhaCungCap=provider_name,
        soLuongBaiHoc=len(ordered_lessons),
        deCuongCongKhai=public_syllabus,
        baiHocs=[
            CourseLessonDetailResponse(
                **LessonResponse.model_validate(lesson).model_dump(),
                taiLieus=[
                    MaterialResponse.model_validate(material)
                    for material in lesson.taiLieus
                    if not public_only_materials
                    or (
                        material.trangThaiDuyet == "APPROVED"
                        and material.trangThaiHienThi == "VISIBLE"
                    )
                ],
            )
            for lesson in ordered_lessons
        ] if include_learning_content else [],
    )


@router.post(
    "/provider/applications",
    response_model=ProviderApplicationResponse,
    status_code=status.HTTP_201_CREATED,
)
def submit_provider_application(
    payload: ProviderApplicationCreate,
    user: Annotated[NguoiDung, Depends(require_roles("USER"))],
    db: Annotated[Session, Depends(get_db)],
) -> ProviderApplicationResponse:
    application = _run_workflow(
        workflow_service.submit_provider_application,
        db,
        user.maNguoiDung,
        payload,
    )
    return ProviderApplicationResponse.model_validate(application)


@router.get(
    "/provider/applications/me",
    response_model=list[ProviderApplicationResponse],
)
def get_my_provider_applications(
    user: Annotated[NguoiDung, Depends(require_roles("USER", "PROVIDER"))],
    db: Annotated[Session, Depends(get_db)],
) -> list[ProviderApplicationResponse]:
    applications = _run_workflow(
        workflow_service.list_user_provider_applications, db, user.maNguoiDung
    )
    return [ProviderApplicationResponse.model_validate(item) for item in applications]


@router.get(
    "/admin/provider-applications",
    response_model=list[AdminProviderApplicationResponse],
    dependencies=[Depends(require_roles("ADMIN"))],
)
def list_provider_applications(
    db: Annotated[Session, Depends(get_db)],
    application_status: str | None = Query(default=None, alias="status"),
) -> list[AdminProviderApplicationResponse]:
    applications = _run_workflow(
        workflow_service.list_admin_provider_applications,
        db,
        application_status,
    )
    return [_admin_application_response(item) for item in applications]


@router.post(
    "/admin/provider-applications/{application_id}/approve",
    response_model=AdminProviderApplicationResponse,
    dependencies=[Depends(require_roles("ADMIN"))],
)
def approve_provider_application(
    application_id: int,
    db: Annotated[Session, Depends(get_db)],
) -> AdminProviderApplicationResponse:
    application = _run_workflow(
        workflow_service.approve_provider_application, db, application_id
    )
    return _admin_application_response(application)


@router.post(
    "/admin/provider-applications/{application_id}/reject",
    response_model=AdminProviderApplicationResponse,
    dependencies=[Depends(require_roles("ADMIN"))],
)
def reject_provider_application(
    application_id: int,
    payload: RejectProviderApplicationRequest,
    db: Annotated[Session, Depends(get_db)],
) -> AdminProviderApplicationResponse:
    application = _run_workflow(
        workflow_service.reject_provider_application,
        db,
        application_id,
        payload.lyDoTuChoi,
    )
    return _admin_application_response(application)


@router.get(
    "/admin/analytics/summary",
    response_model=AdminAnalyticsSummaryResponse,
    dependencies=[Depends(require_roles("ADMIN"))],
)
def get_admin_analytics_summary(
    db: Annotated[Session, Depends(get_db)],
) -> AdminAnalyticsSummaryResponse:
    return AdminAnalyticsSummaryResponse(
        **workflow_service.get_admin_analytics_summary(db)
    )


def _admin_user_response(item: NguoiDung) -> AdminUserResponse:
    return AdminUserResponse(
        maNguoiDung=item.maNguoiDung,
        tenTaiKhoan=item.tenTaiKhoan,
        hoTen=item.hoTen,
        email=item.email,
        soDienThoai=item.soDienThoai,
        tenVaiTro=item.vaiTro.tenVaiTro if item.vaiTro else None,
        trangThai=getattr(item, "trangThai", None) or "ACTIVE",
    )


@router.get(
    "/admin/users",
    response_model=list[AdminUserResponse],
    dependencies=[Depends(require_roles("ADMIN"))],
)
def list_admin_users(
    db: Annotated[Session, Depends(get_db)],
) -> list[AdminUserResponse]:
    users = workflow_service.list_admin_users(db)
    return [_admin_user_response(item) for item in users]


@router.post(
    "/admin/users/{user_id}/expert-role",
    response_model=AdminUserResponse,
    dependencies=[Depends(require_roles("ADMIN"))],
)
def assign_expert_role(
    user_id: int,
    payload: GrantExpertRoleRequest,
    db: Annotated[Session, Depends(get_db)],
) -> AdminUserResponse:
    expert = _run_workflow(workflow_service.grant_expert_role, db, user_id, payload)
    return _admin_user_response(expert)


@router.patch(
    "/admin/users/{user_id}/status",
    response_model=AdminUserResponse,
)
def update_admin_user_status(
    user_id: int,
    payload: AdminUserStatusUpdateRequest,
    admin_user: Annotated[NguoiDung, Depends(require_roles("ADMIN"))],
    db: Annotated[Session, Depends(get_db)],
) -> AdminUserResponse:
    updated = _run_workflow(
        workflow_service.update_admin_user_status,
        db,
        admin_user.maNguoiDung,
        user_id,
        payload.trangThai,
    )
    return _admin_user_response(updated)


@router.delete(
    "/admin/users/{user_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
def delete_admin_user(
    user_id: int,
    admin_user: Annotated[NguoiDung, Depends(require_roles("ADMIN"))],
    db: Annotated[Session, Depends(get_db)],
) -> Response:
    _run_workflow(
        workflow_service.delete_admin_user,
        db,
        admin_user.maNguoiDung,
        user_id,
    )
    return Response(status_code=status.HTTP_204_NO_CONTENT)


def _specialty_response(item) -> SpecialtyResponse:
    return SpecialtyResponse(
        maChuyenMon=item.maChuyenMon,
        tenChuyenMon=item.tenChuyenMon,
        nhomChuyenMon=item.nhomChuyenMon,
        moTa=item.moTa,
        trangThai=item.trangThai,
        maNguoiTao=item.maNguoiTao,
        ngayTao=item.ngayTao,
        ngayCapNhat=item.ngayCapNhat,
        danhMucs=[
            SpecialtyCategoryRef(
                maDanhMuc=link.maDanhMuc,
                tenDanhMuc=link.danhMuc.tenDanhMuc if link.danhMuc else None,
            )
            for link in (item.danhMucLinks or [])
        ],
        soChuyenGiaDangSuDung=len(item.chuyenGiaLinks or []),
    )


def _extract_expert_specialties(
    profile,
) -> tuple[ExpertSpecialtyItem | None, list[ExpertSpecialtyItem]]:
    if profile is None:
        return None, []
    primary: ExpertSpecialtyItem | None = None
    secondaries: list[ExpertSpecialtyItem] = []
    for link in profile.chuyenMonLinks or []:
        spec = link.chuyenMon
        if spec is None:
            continue
        item = ExpertSpecialtyItem(
            maChuyenMon=spec.maChuyenMon,
            tenChuyenMon=spec.tenChuyenMon,
            nhomChuyenMon=spec.nhomChuyenMon,
            moTa=spec.moTa,
            trangThai=spec.trangThai,
            laChuyenMonChinh=bool(link.laChuyenMonChinh),
        )
        if link.laChuyenMonChinh:
            primary = item
        else:
            secondaries.append(item)
    secondaries.sort(key=lambda s: (s.nhomChuyenMon, s.tenChuyenMon))
    return primary, secondaries


def _admin_expert_summary_response(user: NguoiDung, profile) -> AdminExpertSummaryResponse:
    primary, secondaries = _extract_expert_specialties(profile)
    trang_thai_ho_so = getattr(profile, "trangThaiHoSo", None) or "DRAFT"
    user_status = getattr(user, "trangThai", None) or "ACTIVE"
    force_pwd = bool(getattr(user, "batBuocDoiMatKhau", False))
    ho_so_hoan_thien = bool(
        profile
        and primary is not None
        and (profile.tieuSu or "").strip()
        and profile.soNamKinhNghiem is not None
    )
    du_dieu_kien = (
        user_status.upper() == "ACTIVE"
        and not force_pwd
        and trang_thai_ho_so == "VERIFIED"
        and primary is not None
    )
    return AdminExpertSummaryResponse(
        maNguoiDung=user.maNguoiDung,
        tenTaiKhoan=user.tenTaiKhoan,
        hoTen=user.hoTen,
        email=user.email,
        soDienThoai=user.soDienThoai,
        tenVaiTro=user.vaiTro.tenVaiTro if user.vaiTro else None,
        trangThai=user_status,
        maChuyenGia=profile.maChuyenGia if profile else None,
        chuyenMon=profile.chuyenMon if profile else None,
        tieuSu=profile.tieuSu if profile else None,
        soNamKinhNghiem=profile.soNamKinhNghiem if profile else None,
        trangThaiHoSo=trang_thai_ho_so,
        ghiChuXacMinh=profile.ghiChuXacMinh if profile else None,
        ngayXacMinh=profile.ngayXacMinh if profile else None,
        batBuocDoiMatKhau=force_pwd,
        primarySpecialty=primary,
        secondarySpecialties=secondaries,
        hoSoHoanThien=ho_so_hoan_thien,
        duDieuKienPhanCong=du_dieu_kien,
    )


def _expert_profile_response(user: NguoiDung, profile) -> ExpertProfileResponse:
    primary, secondaries = _extract_expert_specialties(profile)
    trang_thai_ho_so = getattr(profile, "trangThaiHoSo", None) or "DRAFT"
    user_status = getattr(user, "trangThai", None) or "ACTIVE"
    force_pwd = bool(getattr(user, "batBuocDoiMatKhau", False))
    return ExpertProfileResponse(
        maChuyenGia=profile.maChuyenGia,
        maNguoiDung=profile.maNguoiDung,
        tieuSu=profile.tieuSu,
        chuyenMon=profile.chuyenMon,
        soNamKinhNghiem=profile.soNamKinhNghiem,
        trangThaiHoSo=trang_thai_ho_so,
        ghiChuXacMinh=profile.ghiChuXacMinh,
        ngayXacMinh=profile.ngayXacMinh,
        primarySpecialty=primary,
        secondarySpecialties=secondaries,
        duDieuKienPhanCong=(
            user_status.upper() == "ACTIVE"
            and not force_pwd
            and trang_thai_ho_so == "VERIFIED"
            and primary is not None
        ),
        batBuocDoiMatKhau=force_pwd,
    )


@router.get(
    "/admin/specialties",
    response_model=list[SpecialtyResponse],
    dependencies=[Depends(require_roles("ADMIN"))],
)
def list_admin_specialties(
    db: Annotated[Session, Depends(get_db)],
    specialty_status: str | None = Query(default=None, alias="status"),
    group: str | None = Query(default=None),
    query: str | None = Query(default=None, max_length=255),
) -> list[SpecialtyResponse]:
    items = workflow_service.list_admin_specialties(
        db, status=specialty_status, group=group, query=query
    )
    return [_specialty_response(item) for item in items]


@router.post(
    "/admin/specialties",
    response_model=SpecialtyResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_admin_specialty(
    payload: SpecialtyCreateRequest,
    admin_user: Annotated[NguoiDung, Depends(require_roles("ADMIN"))],
    db: Annotated[Session, Depends(get_db)],
) -> SpecialtyResponse:
    item = _run_workflow(
        workflow_service.create_specialty, db, admin_user.maNguoiDung, payload
    )
    return _specialty_response(item)


@router.patch(
    "/admin/specialties/{specialty_id}",
    response_model=SpecialtyResponse,
    dependencies=[Depends(require_roles("ADMIN"))],
)
def update_admin_specialty(
    specialty_id: int,
    payload: SpecialtyUpdateRequest,
    db: Annotated[Session, Depends(get_db)],
) -> SpecialtyResponse:
    item = _run_workflow(
        workflow_service.update_specialty, db, specialty_id, payload
    )
    return _specialty_response(item)


@router.patch(
    "/admin/specialties/{specialty_id}/status",
    response_model=SpecialtyResponse,
    dependencies=[Depends(require_roles("ADMIN"))],
)
def update_admin_specialty_status(
    specialty_id: int,
    payload: SpecialtyStatusUpdateRequest,
    db: Annotated[Session, Depends(get_db)],
) -> SpecialtyResponse:
    item = _run_workflow(
        workflow_service.update_specialty_status, db, specialty_id, payload.trangThai
    )
    return _specialty_response(item)


@router.get(
    "/admin/experts",
    response_model=list[AdminExpertSummaryResponse],
    dependencies=[Depends(require_roles("ADMIN"))],
)
def list_admin_experts(
    db: Annotated[Session, Depends(get_db)],
) -> list[AdminExpertSummaryResponse]:
    rows = workflow_service.list_admin_experts(db)
    return [_admin_expert_summary_response(user, profile) for user, profile in rows]


@router.post(
    "/admin/experts",
    response_model=AdminCreateExpertResponse,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_roles("ADMIN"))],
)
def create_admin_expert(
    payload: AdminCreateExpertRequest,
    db: Annotated[Session, Depends(get_db)],
) -> AdminCreateExpertResponse:
    user, profile, temp_password = _run_workflow(
        workflow_service.create_expert_account, db, payload
    )
    return AdminCreateExpertResponse(
        maNguoiDung=user.maNguoiDung,
        maChuyenGia=profile.maChuyenGia,
        tenTaiKhoan=user.tenTaiKhoan,
        hoTen=user.hoTen or "",
        email=user.email or "",
        matKhauTamThoi=temp_password,
        batBuocDoiMatKhau=True,
        message="Đã tạo tài khoản Chuyên gia. Chuyên gia bắt buộc đổi mật khẩu ở lần đăng nhập đầu tiên.",
    )


@router.patch(
    "/admin/experts/{user_id}/verification",
    response_model=AdminExpertSummaryResponse,
)
def verify_admin_expert(
    user_id: int,
    payload: AdminVerifyExpertRequest,
    admin_user: Annotated[NguoiDung, Depends(require_roles("ADMIN"))],
    db: Annotated[Session, Depends(get_db)],
) -> AdminExpertSummaryResponse:
    user, profile = _run_workflow(
        workflow_service.verify_expert_profile,
        db,
        admin_user.maNguoiDung,
        user_id,
        payload,
    )
    return _admin_expert_summary_response(user, profile)


@router.get(
    "/admin/experts/candidates",
    response_model=list[AdminExpertCandidateResponse],
    dependencies=[Depends(require_roles("ADMIN"))],
)
def list_admin_expert_candidates(
    db: Annotated[Session, Depends(get_db)],
    category_id: int | None = Query(default=None, gt=0),
) -> list[AdminExpertCandidateResponse]:
    rows = _run_workflow(
        workflow_service.list_expert_candidates, db, category_id=category_id
    )
    result: list[AdminExpertCandidateResponse] = []
    for entry in rows:
        user = entry["user"]
        profile = entry["profile"]
        primary, secondaries = _extract_expert_specialties(profile)
        result.append(
            AdminExpertCandidateResponse(
                maNguoiDung=user.maNguoiDung,
                maChuyenGia=profile.maChuyenGia,
                hoTen=user.hoTen,
                email=user.email,
                soNamKinhNghiem=profile.soNamKinhNghiem,
                primarySpecialty=primary,
                secondarySpecialties=secondaries,
                soCongViecDangXuLy=entry["workload"],
                diemPhuHop=entry["score"],
                lyDoDeXuat=entry["reasons"],
            )
        )
    return result


@router.post(
    "/admin/experts/{user_id}/reset-password",
    response_model=AdminResetExpertPasswordResponse,
    dependencies=[Depends(require_roles("ADMIN"))],
)
def reset_expert_password(
    user_id: int,
    payload: AdminResetExpertPasswordRequest,
    db: Annotated[Session, Depends(get_db)],
) -> AdminResetExpertPasswordResponse:
    expert, plain_password = _run_workflow(
        workflow_service.reset_expert_password,
        db,
        user_id,
        payload.matKhauMoi,
    )
    return AdminResetExpertPasswordResponse(
        maNguoiDung=expert.maNguoiDung,
        tenTaiKhoan=expert.tenTaiKhoan,
        matKhauMoi=plain_password,
        message="Đã cấp lại mật khẩu mới cho tài khoản chuyên gia.",
    )


@router.get(
    "/admin/categories",
    response_model=list[CategoryResponse],
    dependencies=[Depends(require_roles("ADMIN"))],
)
def get_categories_for_admin(
    db: Annotated[Session, Depends(get_db)],
) -> list[CategoryResponse]:
    return [
        CategoryResponse.model_validate(item)
        for item in workflow_service.list_categories(db)
    ]


@router.get(
    "/provider/categories",
    response_model=list[CategoryResponse],
    dependencies=[Depends(require_roles("PROVIDER"))],
)
def get_categories_for_provider(
    db: Annotated[Session, Depends(get_db)],
) -> list[CategoryResponse]:
    return [
        CategoryResponse.model_validate(item)
        for item in workflow_service.list_categories(db)
    ]


@router.post(
    "/admin/categories",
    response_model=CategoryResponse,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_roles("ADMIN"))],
)
def create_category(
    payload: CategoryCreateRequest,
    db: Annotated[Session, Depends(get_db)],
) -> CategoryResponse:
    return CategoryResponse.model_validate(
        workflow_service.create_category(db, payload)
    )


@router.patch(
    "/admin/categories/{category_id}",
    response_model=CategoryResponse,
    dependencies=[Depends(require_roles("ADMIN"))],
)
def update_category(
    category_id: int,
    payload: CategoryUpdateRequest,
    db: Annotated[Session, Depends(get_db)],
) -> CategoryResponse:
    category = _run_workflow(
        workflow_service.update_category, db, category_id, payload
    )
    return CategoryResponse.model_validate(category)


@router.delete(
    "/admin/categories/{category_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    dependencies=[Depends(require_roles("ADMIN"))],
)
def delete_category(
    category_id: int,
    db: Annotated[Session, Depends(get_db)],
) -> Response:
    _run_workflow(workflow_service.delete_category, db, category_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get(
    "/admin/courses",
    response_model=list[CourseResponse],
    dependencies=[Depends(require_roles("ADMIN"))],
)
def list_admin_courses(
    db: Annotated[Session, Depends(get_db)],
) -> list[CourseResponse]:
    return [
        CourseResponse.model_validate(item)
        for item in workflow_service.list_admin_courses(db)
    ]


@router.patch(
    "/admin/courses/{course_id}/visibility",
    response_model=CourseResponse,
    dependencies=[Depends(require_roles("ADMIN"))],
)
def update_course_visibility(
    course_id: int,
    payload: VisibilityUpdateRequest,
    db: Annotated[Session, Depends(get_db)],
) -> CourseResponse:
    course = _run_workflow(
        workflow_service.set_course_visibility,
        db,
        course_id,
        payload.trangThaiHienThi,
    )
    return CourseResponse.model_validate(course)


@router.get(
    "/admin/materials",
    response_model=PaginatedMaterialResponse,
    dependencies=[Depends(require_roles("ADMIN"))],
)
def list_admin_materials(
    db: Annotated[Session, Depends(get_db)],
    query: str | None = Query(default=None, max_length=255),
    category_id: int | None = Query(default=None, gt=0),
    status: str | None = Query(default=None),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    limit: int | None = Query(default=None, ge=1, le=100),
    offset: int | None = Query(default=None, ge=0),
) -> PaginatedMaterialResponse:
    effective_page_size = limit if limit is not None else page_size
    effective_offset = (
        offset if offset is not None else (page - 1) * effective_page_size
    )
    effective_page = (
        (effective_offset // effective_page_size) + 1
        if offset is not None
        else page
    )
    materials, total = workflow_service.list_admin_materials(
        db,
        query=query,
        category_id=category_id,
        status=status,
        limit=effective_page_size,
        offset=effective_offset,
    )
    total_pages = (
        (total + effective_page_size - 1) // effective_page_size
        if total > 0
        else 0
    )
    return PaginatedMaterialResponse(
        items=[MaterialResponse.model_validate(item) for item in materials],
        total=total,
        page=effective_page,
        page_size=effective_page_size,
        total_pages=total_pages,
    )


@router.patch("/admin/materials/{material_id}", response_model=MaterialResponse)
def update_material_visibility(
    material_id: int,
    payload: VisibilityUpdateRequest,
    user: Annotated[NguoiDung, Depends(require_roles("ADMIN"))],
    db: Annotated[Session, Depends(get_db)],
) -> MaterialResponse:
    _ = user.maNguoiDung
    material = _run_workflow(
        workflow_service.set_material_visibility,
        db,
        material_id,
        payload.trangThaiHienThi,
    )
    return MaterialResponse.model_validate(material)


@router.get("/expert/specialties", response_model=list[SpecialtyResponse])
def get_expert_specialties(
    user: Annotated[NguoiDung, Depends(require_roles("EXPERT"))],
    db: Annotated[Session, Depends(get_db)],
) -> list[SpecialtyResponse]:
    _ = user
    specialties = workflow_service.list_expert_specialty_catalog(db)
    return [_specialty_response(item) for item in specialties]


@router.get("/expert/profile", response_model=ExpertProfileResponse)
def get_expert_profile(
    user: Annotated[NguoiDung, Depends(require_roles("EXPERT"))],
    db: Annotated[Session, Depends(get_db)],
) -> ExpertProfileResponse:
    profile = _run_workflow(workflow_service.get_expert_profile, db, user.maNguoiDung)
    return _expert_profile_response(user, profile)


@router.put("/expert/profile", response_model=ExpertProfileResponse)
def update_expert_profile(
    payload: ExpertProfileUpdateRequest,
    user: Annotated[NguoiDung, Depends(require_roles("EXPERT"))],
    db: Annotated[Session, Depends(get_db)],
) -> ExpertProfileResponse:
    profile = _run_workflow(
        workflow_service.update_expert_profile, db, user.maNguoiDung, payload
    )
    return _expert_profile_response(user, profile)


@router.post("/expert/profile/submit", response_model=ExpertProfileResponse)
def submit_expert_profile(
    user: Annotated[NguoiDung, Depends(require_roles("EXPERT"))],
    db: Annotated[Session, Depends(get_db)],
) -> ExpertProfileResponse:
    profile = _run_workflow(
        workflow_service.submit_expert_profile_for_verification,
        db,
        user.maNguoiDung,
    )
    return _expert_profile_response(user, profile)


@router.get("/expert/courses/pending", response_model=list[CourseResponse])
def get_pending_expert_courses(
    user: Annotated[NguoiDung, Depends(require_roles("EXPERT"))],
    db: Annotated[Session, Depends(get_db)],
) -> list[CourseResponse]:
    courses = _run_workflow(
        workflow_service.list_expert_courses, db, user.maNguoiDung
    )
    return [CourseResponse.model_validate(item) for item in courses]


@router.get("/expert/courses/{course_id}", response_model=CourseDetailResponse)
def get_expert_course(
    course_id: int,
    user: Annotated[NguoiDung, Depends(require_roles("EXPERT"))],
    db: Annotated[Session, Depends(get_db)],
) -> CourseDetailResponse:
    course = _run_workflow(
        workflow_service.get_expert_course, db, user.maNguoiDung, course_id
    )
    return _course_detail(course)


@router.post(
    "/expert/courses/{course_id}/decision",
    response_model=CourseResponse,
)
def decide_course(
    course_id: int,
    payload: CourseDecisionRequest,
    user: Annotated[NguoiDung, Depends(require_roles("EXPERT"))],
    db: Annotated[Session, Depends(get_db)],
) -> CourseResponse:
    course, _ = _run_workflow(
        workflow_service.decide_course,
        db,
        user.maNguoiDung,
        course_id,
        payload,
    )
    return CourseResponse.model_validate(course)


@router.get("/expert/materials/pending", response_model=list[MaterialResponse])
def get_pending_expert_materials(
    user: Annotated[NguoiDung, Depends(require_roles("EXPERT"))],
    db: Annotated[Session, Depends(get_db)],
) -> list[MaterialResponse]:
    materials = _run_workflow(
        workflow_service.list_expert_materials, db, user.maNguoiDung
    )
    return [MaterialResponse.model_validate(item) for item in materials]


@router.get("/expert/materials/{material_id}", response_model=MaterialResponse)
def get_expert_material(
    material_id: int,
    user: Annotated[NguoiDung, Depends(require_roles("EXPERT"))],
    db: Annotated[Session, Depends(get_db)],
) -> MaterialResponse:
    material = _run_workflow(
        workflow_service.get_expert_material, db, user.maNguoiDung, material_id
    )
    return MaterialResponse.model_validate(material)


@router.post(
    "/expert/materials/{material_id}/decision",
    response_model=MaterialResponse,
)
def decide_material(
    material_id: int,
    payload: MaterialDecisionRequest,
    user: Annotated[NguoiDung, Depends(require_roles("EXPERT"))],
    db: Annotated[Session, Depends(get_db)],
) -> MaterialResponse:
    material, _ = _run_workflow(
        workflow_service.decide_material,
        db,
        user.maNguoiDung,
        material_id,
        payload,
    )
    return MaterialResponse.model_validate(material)


def _expert_review_response(review) -> ExpertReviewResponse:
    is_material = review.maTaiLieu is not None
    target_title = (
        (review.taiLieu.tieuDe if review.taiLieu else None)
        if is_material
        else (review.khoaHoc.tieuDe if review.khoaHoc else None)
    )
    return ExpertReviewResponse(
        maDanhGia=review.maDanhGia,
        maKhoaHoc=review.maKhoaHoc,
        maTaiLieu=review.maTaiLieu,
        loaiDoiTuong="MATERIAL" if is_material else "COURSE",
        tenDoiTuong=target_title,
        maChuyenGia=review.maChuyenGia,
        noiDungDanhGia=review.noiDungDanhGia,
        diemKyThuat=review.diemKyThuat,
        diemNoiDung=review.diemNoiDung,
        ghiChu=review.ghiChu,
        trangThai=review.trangThai,
        ngayTao=review.ngayTao,
    )


@router.get("/expert/reviews/history", response_model=list[ExpertReviewResponse])
def get_expert_review_history(
    user: Annotated[NguoiDung, Depends(require_roles("EXPERT"))],
    db: Annotated[Session, Depends(get_db)],
) -> list[ExpertReviewResponse]:
    reviews = _run_workflow(
        workflow_service.list_expert_review_history, db, user.maNguoiDung
    )
    return [_expert_review_response(item) for item in reviews]


@router.get(
    "/provider/courses/{course_id}/reviews",
    response_model=list[ExpertReviewResponse],
)
def get_provider_course_review_history(
    course_id: int,
    user: Annotated[NguoiDung, Depends(require_roles("PROVIDER"))],
    db: Annotated[Session, Depends(get_db)],
) -> list[ExpertReviewResponse]:
    reviews = _run_workflow(
        workflow_service.list_provider_course_review_history,
        db,
        user.maNguoiDung,
        course_id,
    )
    return [_expert_review_response(item) for item in reviews]


@router.get("/provider/profile", response_model=ProviderProfileResponse)
def get_provider_profile(
    user: Annotated[NguoiDung, Depends(require_roles("PROVIDER"))],
    db: Annotated[Session, Depends(get_db)],
) -> ProviderProfileResponse:
    profile = _run_workflow(
        workflow_service.get_provider_profile, db, user.maNguoiDung
    )
    return ProviderProfileResponse(
        maNhaCungCap=profile.maNhaCungCap,
        maNguoiDung=profile.maNguoiDung,
        tieuSu=profile.tieuSu,
        chuyenMon=profile.chuyenMon,
    )


@router.put("/provider/profile", response_model=ProviderProfileResponse)
def update_provider_profile(
    payload: ProviderProfileUpdateRequest,
    user: Annotated[NguoiDung, Depends(require_roles("PROVIDER"))],
    db: Annotated[Session, Depends(get_db)],
) -> ProviderProfileResponse:
    profile = _run_workflow(
        workflow_service.update_provider_profile, db, user.maNguoiDung, payload
    )
    return ProviderProfileResponse(
        maNhaCungCap=profile.maNhaCungCap,
        maNguoiDung=profile.maNguoiDung,
        tieuSu=profile.tieuSu,
        chuyenMon=profile.chuyenMon,
    )


@router.get("/provider/courses", response_model=list[CourseResponse])
def get_provider_courses(
    user: Annotated[NguoiDung, Depends(require_roles("PROVIDER"))],
    db: Annotated[Session, Depends(get_db)],
) -> list[CourseResponse]:
    courses = _run_workflow(
        workflow_service.list_provider_courses, db, user.maNguoiDung
    )
    return [CourseResponse.model_validate(item) for item in courses]


@router.post(
    "/provider/courses",
    response_model=CourseResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_provider_course(
    payload: CourseCreateRequest,
    user: Annotated[NguoiDung, Depends(require_roles("PROVIDER"))],
    db: Annotated[Session, Depends(get_db)],
) -> CourseResponse:
    course = _run_workflow(
        workflow_service.create_provider_course, db, user.maNguoiDung, payload
    )
    return CourseResponse.model_validate(course)


@router.get("/provider/courses/{course_id}", response_model=CourseDetailResponse)
def get_provider_course(
    course_id: int,
    user: Annotated[NguoiDung, Depends(require_roles("PROVIDER"))],
    db: Annotated[Session, Depends(get_db)],
) -> CourseDetailResponse:
    course = _run_workflow(
        workflow_service.get_provider_course, db, user.maNguoiDung, course_id
    )
    return _course_detail(course)


@router.put("/provider/courses/{course_id}", response_model=CourseResponse)
def update_provider_course(
    course_id: int,
    payload: CourseUpdateRequest,
    user: Annotated[NguoiDung, Depends(require_roles("PROVIDER"))],
    db: Annotated[Session, Depends(get_db)],
) -> CourseResponse:
    course = _run_workflow(
        workflow_service.update_provider_course,
        db,
        user.maNguoiDung,
        course_id,
        payload,
    )
    return CourseResponse.model_validate(course)


@router.delete(
    "/provider/courses/{course_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
def delete_provider_course(
    course_id: int,
    user: Annotated[NguoiDung, Depends(require_roles("PROVIDER"))],
    db: Annotated[Session, Depends(get_db)],
) -> Response:
    _run_workflow(
        workflow_service.delete_provider_course,
        db,
        user.maNguoiDung,
        course_id,
    )
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post("/provider/media/course-cover")
async def upload_course_cover_media(
    user: Annotated[NguoiDung, Depends(require_roles("PROVIDER"))],
    file: UploadFile = File(...),
) -> dict[str, str]:
    _ = user.maNguoiDung
    url = await _save_course_cover_upload(file, prefix="draft")
    return {"url": url}


@router.post(
    "/provider/courses/{course_id}/cover-image",
    response_model=CourseResponse,
)
async def upload_provider_course_cover(
    course_id: int,
    user: Annotated[NguoiDung, Depends(require_roles("PROVIDER"))],
    db: Annotated[Session, Depends(get_db)],
    file: UploadFile = File(...),
) -> CourseResponse:
    _run_workflow(
        workflow_service.assert_provider_course_editable,
        db,
        user.maNguoiDung,
        course_id,
    )
    new_url = await _save_course_cover_upload(file, prefix=f"course-{course_id}")
    try:
        course, previous_url = _run_workflow(
            workflow_service.set_provider_course_cover_image,
            db,
            user.maNguoiDung,
            course_id,
            new_url,
        )
    except Exception:
        _remove_local_course_cover(new_url)
        raise
    if previous_url and previous_url != new_url:
        _remove_local_course_cover(previous_url)
    return CourseResponse.model_validate(course)


@router.post("/provider/courses/{course_id}/submit", response_model=CourseResponse)
def submit_course(
    course_id: int,
    user: Annotated[NguoiDung, Depends(require_roles("PROVIDER"))],
    db: Annotated[Session, Depends(get_db)],
) -> CourseResponse:
    course = _run_workflow(
        workflow_service.submit_provider_course, db, user.maNguoiDung, course_id
    )
    return CourseResponse.model_validate(course)


@router.post(
    "/provider/courses/{course_id}/lessons",
    response_model=LessonResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_lesson(
    course_id: int,
    payload: LessonCreateRequest,
    user: Annotated[NguoiDung, Depends(require_roles("PROVIDER"))],
    db: Annotated[Session, Depends(get_db)],
) -> LessonResponse:
    lesson = _run_workflow(
        workflow_service.create_provider_lesson,
        db,
        user.maNguoiDung,
        course_id,
        payload,
    )
    return LessonResponse.model_validate(lesson)


@router.put(
    "/provider/courses/{course_id}/lessons/{lesson_id}",
    response_model=LessonResponse,
)
def update_lesson(
    course_id: int,
    lesson_id: int,
    payload: LessonUpdateRequest,
    user: Annotated[NguoiDung, Depends(require_roles("PROVIDER"))],
    db: Annotated[Session, Depends(get_db)],
) -> LessonResponse:
    lesson = _run_workflow(
        workflow_service.update_provider_lesson,
        db,
        user.maNguoiDung,
        course_id,
        lesson_id,
        payload,
    )
    return LessonResponse.model_validate(lesson)


@router.delete(
    "/provider/courses/{course_id}/lessons/{lesson_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
def delete_lesson(
    course_id: int,
    lesson_id: int,
    user: Annotated[NguoiDung, Depends(require_roles("PROVIDER"))],
    db: Annotated[Session, Depends(get_db)],
) -> Response:
    _run_workflow(
        workflow_service.delete_provider_lesson,
        db,
        user.maNguoiDung,
        course_id,
        lesson_id,
    )
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post(
    "/provider/courses/{course_id}/lessons/{lesson_id}/materials",
    response_model=MaterialResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_material(
    course_id: int,
    lesson_id: int,
    payload: MaterialCreateRequest,
    user: Annotated[NguoiDung, Depends(require_roles("PROVIDER"))],
    db: Annotated[Session, Depends(get_db)],
) -> MaterialResponse:
    material = _run_workflow(
        workflow_service.create_provider_material,
        db,
        user.maNguoiDung,
        course_id,
        lesson_id,
        payload,
    )
    return MaterialResponse.model_validate(material)


@router.put(
    "/provider/courses/{course_id}/lessons/{lesson_id}/materials/{material_id}",
    response_model=MaterialResponse,
)
def update_material(
    course_id: int,
    lesson_id: int,
    material_id: int,
    payload: MaterialUpdateRequest,
    user: Annotated[NguoiDung, Depends(require_roles("PROVIDER"))],
    db: Annotated[Session, Depends(get_db)],
) -> MaterialResponse:
    owned_before = _run_workflow(
        workflow_service.get_provider_material, db, user.maNguoiDung, material_id
    )
    old_reference = owned_before.duongDanTep
    material = _run_workflow(
        workflow_service.update_provider_material,
        db,
        user.maNguoiDung,
        course_id,
        lesson_id,
        material_id,
        payload,
    )
    if old_reference != material.duongDanTep:
        private_material_service.delete_managed_reference(db, old_reference)
    return MaterialResponse.model_validate(material)


@router.delete(
    "/provider/courses/{course_id}/lessons/{lesson_id}/materials/{material_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
def delete_material(
    course_id: int,
    lesson_id: int,
    material_id: int,
    user: Annotated[NguoiDung, Depends(require_roles("PROVIDER"))],
    db: Annotated[Session, Depends(get_db)],
) -> Response:
    owned_material = _run_workflow(
        workflow_service.get_provider_material, db, user.maNguoiDung, material_id
    )
    old_reference = owned_material.duongDanTep
    _run_workflow(
        workflow_service.delete_provider_material,
        db,
        user.maNguoiDung,
        course_id,
        lesson_id,
        material_id,
    )
    private_material_service.delete_managed_reference(db, old_reference)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get("/provider/materials", response_model=list[MaterialResponse])
def get_provider_materials(
    user: Annotated[NguoiDung, Depends(require_roles("PROVIDER"))],
    db: Annotated[Session, Depends(get_db)],
) -> list[MaterialResponse]:
    materials = _run_workflow(
        workflow_service.list_provider_materials, db, user.maNguoiDung
    )
    return [MaterialResponse.model_validate(item) for item in materials]


@router.get("/provider/materials/{material_id}", response_model=MaterialResponse)
def get_provider_material(
    material_id: int,
    user: Annotated[NguoiDung, Depends(require_roles("PROVIDER"))],
    db: Annotated[Session, Depends(get_db)],
) -> MaterialResponse:
    material = _run_workflow(
        workflow_service.get_provider_material, db, user.maNguoiDung, material_id
    )
    return MaterialResponse.model_validate(material)


@router.post("/provider/materials/{material_id}/file", response_model=MaterialResponse)
async def upload_provider_material_file(
    material_id: int,
    file: Annotated[UploadFile, File(...)],
    user: Annotated[NguoiDung, Depends(require_roles("PROVIDER"))],
    db: Annotated[Session, Depends(get_db)],
) -> MaterialResponse:
    try:
        material = await private_material_service.replace_provider_file(
            db,
            user_id=int(user.maNguoiDung),
            material_id=material_id,
            upload=file,
        )
    except PrivateFileValidationError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    except WorkflowNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except WorkflowForbiddenError as exc:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc)) from exc
    except WorkflowConflictError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc
    return MaterialResponse.model_validate(material)


@router.post(
    "/provider/materials",
    response_model=MaterialResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_standalone_material(
    payload: MaterialCreateRequest,
    user: Annotated[NguoiDung, Depends(require_roles("PROVIDER"))],
    db: Annotated[Session, Depends(get_db)],
) -> MaterialResponse:
    material = _run_workflow(
        workflow_service.create_provider_standalone_material,
        db,
        user.maNguoiDung,
        payload,
    )
    return MaterialResponse.model_validate(material)


@router.put("/provider/materials/{material_id}", response_model=MaterialResponse)
def update_provider_material_item(
    material_id: int,
    payload: MaterialUpdateRequest,
    user: Annotated[NguoiDung, Depends(require_roles("PROVIDER"))],
    db: Annotated[Session, Depends(get_db)],
) -> MaterialResponse:
    owned_before = _run_workflow(
        workflow_service.get_provider_material, db, user.maNguoiDung, material_id
    )
    old_reference = owned_before.duongDanTep
    material = _run_workflow(
        workflow_service.update_provider_material_by_id,
        db,
        user.maNguoiDung,
        material_id,
        payload,
    )
    if old_reference != material.duongDanTep:
        private_material_service.delete_managed_reference(db, old_reference)
    return MaterialResponse.model_validate(material)


@router.delete(
    "/provider/materials/{material_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
def delete_provider_material_item(
    material_id: int,
    user: Annotated[NguoiDung, Depends(require_roles("PROVIDER"))],
    db: Annotated[Session, Depends(get_db)],
) -> Response:
    owned_material = _run_workflow(
        workflow_service.get_provider_material, db, user.maNguoiDung, material_id
    )
    old_reference = owned_material.duongDanTep
    _run_workflow(
        workflow_service.delete_provider_material_by_id,
        db,
        user.maNguoiDung,
        material_id,
    )
    private_material_service.delete_managed_reference(db, old_reference)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post(
    "/provider/materials/{material_id}/submit",
    response_model=MaterialResponse,
)
def submit_material(
    material_id: int,
    user: Annotated[NguoiDung, Depends(require_roles("PROVIDER"))],
    db: Annotated[Session, Depends(get_db)],
) -> MaterialResponse:
    material = _run_workflow(
        workflow_service.submit_provider_material,
        db,
        user.maNguoiDung,
        material_id,
    )
    return MaterialResponse.model_validate(material)


def _is_learner_user(user: NguoiDung | None) -> bool:
    return (
        user is not None
        and user.vaiTro is not None
        and (user.vaiTro.tenVaiTro or "").upper() == "USER"
    )


def _public_material_response(
    material,
    *,
    allow_file_url: bool,
) -> MaterialResponse:
    response = MaterialResponse.model_validate(material)
    updates: dict[str, object] = {}
    if response.tenDanhMuc is None and getattr(material, "danhMuc", None) is not None:
        updates["tenDanhMuc"] = material.danhMuc.tenDanhMuc
    if not allow_file_url:
        updates["duongDanTep"] = None
    if updates:
        return response.model_copy(update=updates)
    return response


@router.get("/materials/{material_id}/file")
def access_private_material_file(
    material_id: int,
    user: Annotated[
        NguoiDung,
        Depends(require_roles("ADMIN", "PROVIDER", "EXPERT", "USER")),
    ],
    db: Annotated[Session, Depends(get_db)],
    download: bool = Query(default=False),
) -> FileResponse:
    material, stored = _run_workflow(
        private_material_service.authorize_private_file,
        db,
        user=user,
        material_id=material_id,
    )
    _ = material.maTaiLieu
    response = FileResponse(
        path=stored.path,
        media_type=stored.content_type,
        filename=stored.original_name,
        content_disposition_type="attachment" if download else "inline",
    )
    response.headers["Cache-Control"] = "private, no-store, max-age=0"
    response.headers["Pragma"] = "no-cache"
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["Referrer-Policy"] = "no-referrer"
    return response


@router.get(
    "/courses",
    response_model=list[CourseResponse],
)
def get_visible_course_catalog(
    db: Annotated[Session, Depends(get_db)],
    _current_user: Annotated[NguoiDung | None, Depends(get_optional_current_user)] = None,
    query: str | None = Query(default=None, max_length=255),
    category_id: int | None = Query(default=None, gt=0),
    limit: int = Query(default=50, ge=1, le=100),
) -> list[CourseResponse]:
    courses = workflow_service.list_user_catalog(
        db, query=query, category_id=category_id, limit=limit
    )
    return [CourseResponse.model_validate(item) for item in courses]


@router.get(
    "/materials",
    response_model=PaginatedMaterialResponse,
)
def get_visible_materials_catalog(
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[NguoiDung | None, Depends(get_optional_current_user)] = None,
    query: str | None = Query(default=None, max_length=255),
    category_id: int | None = Query(default=None, gt=0),
    material_type: str | None = Query(default=None, max_length=100),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    limit: int | None = Query(default=None, ge=1, le=100),
    offset: int | None = Query(default=None, ge=0),
) -> PaginatedMaterialResponse:
    effective_page_size = limit if limit is not None else page_size
    effective_offset = (
        offset if offset is not None else (page - 1) * effective_page_size
    )
    effective_page = (
        (effective_offset // effective_page_size) + 1
        if offset is not None
        else page
    )
    materials, total = workflow_service.list_public_materials(
        db,
        query=query,
        category_id=category_id,
        material_type=material_type,
        limit=effective_page_size,
        offset=effective_offset,
    )
    enrolled_course_ids: set[int] = set()
    if _is_learner_user(current_user):
        linked_course_ids = {
            item.maKhoaHoc for item in materials if item.maKhoaHoc is not None
        }
        if linked_course_ids:
            enrolled_course_ids = workflow_service.get_user_enrolled_course_ids(
                db, current_user.maNguoiDung, linked_course_ids
            )

    def _can_expose_file_url(item) -> bool:
        if current_user is None:
            return False
        if item.maKhoaHoc is None and item.maBaiHoc is None:
            return True
        return _is_learner_user(current_user) and item.maKhoaHoc in enrolled_course_ids

    total_pages = (
        (total + effective_page_size - 1) // effective_page_size
        if total > 0
        else 0
    )
    return PaginatedMaterialResponse(
        items=[
            _public_material_response(item, allow_file_url=_can_expose_file_url(item))
            for item in materials
        ],
        total=total,
        page=effective_page,
        page_size=effective_page_size,
        total_pages=total_pages,
    )


@router.get(
    "/materials/{material_id}",
    response_model=MaterialResponse,
)
def get_public_material_detail(
    material_id: int,
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[NguoiDung | None, Depends(get_optional_current_user)] = None,
) -> MaterialResponse:
    material = _run_workflow(
        workflow_service.get_public_material, db, material_id
    )
    if current_user is None:
        allow_file_url = False
    elif material.maKhoaHoc is None and material.maBaiHoc is None:
        allow_file_url = True
    elif _is_learner_user(current_user) and material.maKhoaHoc is not None:
        allow_file_url = workflow_service.user_is_enrolled(
            db, current_user.maNguoiDung, material.maKhoaHoc
        )
    else:
        allow_file_url = False
    return _public_material_response(material, allow_file_url=allow_file_url)


@router.get(
    "/categories",
    response_model=list[CategoryResponse],
)
def get_user_categories(
    db: Annotated[Session, Depends(get_db)],
    _current_user: Annotated[NguoiDung | None, Depends(get_optional_current_user)] = None,
) -> list[CategoryResponse]:
    return [
        CategoryResponse.model_validate(item)
        for item in workflow_service.list_categories(db)
    ]


@router.get(
    "/courses/{course_id}",
    response_model=CourseDetailResponse,
)
def get_visible_course(
    course_id: int,
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[NguoiDung | None, Depends(get_optional_current_user)] = None,
) -> CourseDetailResponse:
    course = _run_workflow(workflow_service.get_user_course, db, course_id)
    enrolled = (
        workflow_service.user_is_enrolled(db, current_user.maNguoiDung, course_id)
        if _is_learner_user(current_user)
        else False
    )
    return _course_detail(
        course,
        include_learning_content=enrolled,
        public_only_materials=True,
    )


@router.post(
    "/courses/{course_id}/enrollments",
    response_model=EnrollmentResponse,
    status_code=status.HTTP_201_CREATED,
)
def enroll_in_course(
    course_id: int,
    user: Annotated[NguoiDung, Depends(require_roles("USER"))],
    db: Annotated[Session, Depends(get_db)],
) -> EnrollmentResponse:
    enrollment = _run_workflow(
        workflow_service.enroll_user_in_course, db, user.maNguoiDung, course_id
    )
    course = workflow_service.get_user_course(db, course_id)
    return EnrollmentResponse(
        maDangKy=enrollment.maDangKy,
        maKhoaHoc=course_id,
        ngayDangKy=enrollment.ngayDangKy,
        tienDo=enrollment.tienDo,
        ngayHoanThanh=enrollment.ngayHoanThanh,
        khoaHoc=CourseResponse.model_validate(course),
        tongBaiHoc=len(course.baiHocs),
        baiHocHoanThanh=0,
    )


@router.get("/enrollments", response_model=list[EnrollmentResponse])
def get_my_enrollments(
    user: Annotated[NguoiDung, Depends(require_roles("USER"))],
    db: Annotated[Session, Depends(get_db)],
) -> list[EnrollmentResponse]:
    enrollments = workflow_service.list_user_enrollments(db, user.maNguoiDung)
    history = workflow_service.get_user_learning_history(db, user.maNguoiDung)
    completed_by_course: dict[int, set[int]] = {}
    for item in history:
        if item.tienDo == "COMPLETED" and item.maKhoaHoc is not None and item.maBaiHoc is not None:
            completed_by_course.setdefault(item.maKhoaHoc, set()).add(item.maBaiHoc)
    return [
        EnrollmentResponse(
            maDangKy=item.maDangKy,
            maKhoaHoc=item.maKhoaHoc,
            ngayDangKy=item.ngayDangKy,
            tienDo=item.tienDo,
            ngayHoanThanh=item.ngayHoanThanh,
            khoaHoc=CourseResponse.model_validate(item.khoaHoc),
            tongBaiHoc=len(item.khoaHoc.baiHocs),
            baiHocHoanThanh=len(
                completed_by_course.get(item.maKhoaHoc, set())
                & {lesson.maBaiHoc for lesson in item.khoaHoc.baiHocs}
            ),
        )
        for item in enrollments
        if item.khoaHoc is not None and item.maKhoaHoc is not None
    ]


@router.get("/learning/courses/{course_id}", response_model=LearningCourseResponse)
def get_learning_course(
    course_id: int,
    user: Annotated[NguoiDung, Depends(require_roles("USER"))],
    db: Annotated[Session, Depends(get_db)],
) -> LearningCourseResponse:
    course, completed = _run_workflow(
        workflow_service.get_user_learning_course, db, user.maNguoiDung, course_id
    )
    return LearningCourseResponse(
        khoaHoc=CourseResponse.model_validate(course),
        baiHocs=[
            LearningLessonResponse(
                **LessonResponse.model_validate(lesson).model_dump(),
                taiLieus=[
                    MaterialResponse.model_validate(item)
                    for item in lesson.taiLieus
                    if item.trangThaiDuyet == "APPROVED"
                    and item.trangThaiHienThi == "VISIBLE"
                ],
                daHoanThanh=lesson.maBaiHoc in completed,
            )
            for lesson in course.baiHocs
        ],
    )


@router.get("/learning/courses/{course_id}/progress", response_model=LearningProgressResponse)
def get_learning_progress(
    course_id: int,
    user: Annotated[NguoiDung, Depends(require_roles("USER"))],
    db: Annotated[Session, Depends(get_db)],
) -> LearningProgressResponse:
    total, completed, percentage, latest = _run_workflow(
        workflow_service.get_user_progress, db, user.maNguoiDung, course_id
    )
    return LearningProgressResponse(
        maKhoaHoc=course_id,
        tongBaiHoc=total,
        baiHocHoanThanh=completed,
        tienDo=percentage,
        ngayHoatDongGanNhat=latest,
    )


@router.post("/learning/courses/{course_id}/lessons/{lesson_id}/complete", response_model=LearningProgressResponse)
def complete_learning_lesson(
    course_id: int,
    lesson_id: int,
    user: Annotated[NguoiDung, Depends(require_roles("USER"))],
    db: Annotated[Session, Depends(get_db)],
) -> LearningProgressResponse:
    _run_workflow(
        workflow_service.complete_user_lesson,
        db,
        user.maNguoiDung,
        course_id,
        lesson_id,
    )
    total, completed, percentage, latest = _run_workflow(
        workflow_service.get_user_progress, db, user.maNguoiDung, course_id
    )
    return LearningProgressResponse(
        maKhoaHoc=course_id,
        tongBaiHoc=total,
        baiHocHoanThanh=completed,
        tienDo=percentage,
        ngayHoatDongGanNhat=latest,
    )


@router.get("/learning/history", response_model=list[LearningHistoryResponse])
def get_learning_history(
    user: Annotated[NguoiDung, Depends(require_roles("USER"))],
    db: Annotated[Session, Depends(get_db)],
) -> list[LearningHistoryResponse]:
    history = workflow_service.get_user_learning_history(db, user.maNguoiDung)
    return [
        LearningHistoryResponse(
            maLichSu=item.maLichSu,
            maKhoaHoc=item.maKhoaHoc,
            maBaiHoc=item.maBaiHoc,
            tienDo=item.tienDo,
            thoiGianXem=item.thoiGianXem,
            ngayTao=item.ngayTao,
            khoaHoc=CourseResponse.model_validate(item.khoaHoc),
            baiHoc=LessonResponse.model_validate(item.baiHoc),
        )
        for item in history
        if item.khoaHoc is not None and item.baiHoc is not None
        and item.maKhoaHoc is not None and item.maBaiHoc is not None
    ]
