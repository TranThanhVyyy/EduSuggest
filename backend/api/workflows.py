from collections.abc import Callable
from typing import Annotated, ParamSpec, TypeVar

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from sqlalchemy.orm import Session

from api.dependencies import require_roles
from config.database import get_db
from models import KhoaHoc, NguoiDung
from schemas.workflow import (
    AdminProviderApplicationResponse,
    AdminUserResponse,
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
    MaterialResponse,
    MaterialUpdateRequest,
    ProviderApplicationCreate,
    ProviderApplicationResponse,
    ProviderProfileResponse,
    ProviderProfileUpdateRequest,
    RejectProviderApplicationRequest,
    VisibilityUpdateRequest,
)
from service import workflow_service
from service.workflow_service import (
    WorkflowConflictError,
    WorkflowForbiddenError,
    WorkflowNotFoundError,
)

router = APIRouter(tags=["workflow"])

P = ParamSpec("P")
T = TypeVar("T")


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


def _course_detail(course: KhoaHoc, *, include_learning_content: bool = True) -> CourseDetailResponse:
    return CourseDetailResponse(
        **CourseResponse.model_validate(course).model_dump(),
        baiHocs=[
            CourseLessonDetailResponse(
                **LessonResponse.model_validate(lesson).model_dump(),
                taiLieus=[
                    MaterialResponse.model_validate(material)
                    for material in lesson.taiLieus
                ],
            )
            for lesson in course.baiHocs
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
    "/admin/users",
    response_model=list[AdminUserResponse],
    dependencies=[Depends(require_roles("ADMIN"))],
)
def list_admin_users(
    db: Annotated[Session, Depends(get_db)],
) -> list[AdminUserResponse]:
    users = workflow_service.list_admin_users(db)
    return [
        AdminUserResponse(
            maNguoiDung=item.maNguoiDung,
            hoTen=item.hoTen,
            email=item.email,
            soDienThoai=item.soDienThoai,
            tenVaiTro=item.vaiTro.tenVaiTro if item.vaiTro else None,
        )
        for item in users
    ]


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
    return AdminUserResponse(
        maNguoiDung=expert.maNguoiDung,
        hoTen=expert.hoTen,
        email=expert.email,
        soDienThoai=expert.soDienThoai,
        tenVaiTro=expert.vaiTro.tenVaiTro if expert.vaiTro else None,
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


@router.get("/expert/profile", response_model=ExpertProfileResponse)
def get_expert_profile(
    user: Annotated[NguoiDung, Depends(require_roles("EXPERT"))],
    db: Annotated[Session, Depends(get_db)],
) -> ExpertProfileResponse:
    profile = _run_workflow(workflow_service.get_expert_profile, db, user.maNguoiDung)
    return ExpertProfileResponse(
        maChuyenGia=profile.maChuyenGia,
        maNguoiDung=profile.maNguoiDung,
        tieuSu=profile.tieuSu,
        chuyenMon=profile.chuyenMon,
    )


@router.put("/expert/profile", response_model=ExpertProfileResponse)
def update_expert_profile(
    payload: ExpertProfileUpdateRequest,
    user: Annotated[NguoiDung, Depends(require_roles("EXPERT"))],
    db: Annotated[Session, Depends(get_db)],
) -> ExpertProfileResponse:
    profile = _run_workflow(
        workflow_service.update_expert_profile, db, user.maNguoiDung, payload
    )
    return ExpertProfileResponse(
        maChuyenGia=profile.maChuyenGia,
        maNguoiDung=profile.maNguoiDung,
        tieuSu=profile.tieuSu,
        chuyenMon=profile.chuyenMon,
    )


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


@router.get("/expert/reviews/history", response_model=list[ExpertReviewResponse])
def get_expert_review_history(
    user: Annotated[NguoiDung, Depends(require_roles("EXPERT"))],
    db: Annotated[Session, Depends(get_db)],
) -> list[ExpertReviewResponse]:
    reviews = _run_workflow(
        workflow_service.list_expert_review_history, db, user.maNguoiDung
    )
    return [ExpertReviewResponse.model_validate(item) for item in reviews]


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
    return [ExpertReviewResponse.model_validate(item) for item in reviews]


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
    material = _run_workflow(
        workflow_service.update_provider_material,
        db,
        user.maNguoiDung,
        course_id,
        lesson_id,
        material_id,
        payload,
    )
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
    _run_workflow(
        workflow_service.delete_provider_material,
        db,
        user.maNguoiDung,
        course_id,
        lesson_id,
        material_id,
    )
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get(
    "/courses",
    response_model=list[CourseResponse],
    dependencies=[Depends(require_roles("USER"))],
)
def get_visible_course_catalog(
    db: Annotated[Session, Depends(get_db)],
    query: str | None = Query(default=None, max_length=255),
    category_id: int | None = Query(default=None, gt=0),
    limit: int = Query(default=50, ge=1, le=100),
) -> list[CourseResponse]:
    courses = workflow_service.list_user_catalog(
        db, query=query, category_id=category_id, limit=limit
    )
    return [CourseResponse.model_validate(item) for item in courses]


@router.get(
    "/categories",
    response_model=list[CategoryResponse],
    dependencies=[Depends(require_roles("USER"))],
)
def get_user_categories(
    db: Annotated[Session, Depends(get_db)],
) -> list[CategoryResponse]:
    return [
        CategoryResponse.model_validate(item)
        for item in workflow_service.list_categories(db)
    ]


@router.get(
    "/courses/{course_id}",
    response_model=CourseDetailResponse,
    dependencies=[Depends(require_roles("USER"))],
)
def get_visible_course(
    course_id: int,
    user: Annotated[NguoiDung, Depends(require_roles("USER"))],
    db: Annotated[Session, Depends(get_db)],
) -> CourseDetailResponse:
    course = _run_workflow(workflow_service.get_user_course, db, course_id)
    enrolled = workflow_service.user_is_enrolled(db, user.maNguoiDung, course_id)
    return _course_detail(course, include_learning_content=enrolled)


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
                taiLieus=[MaterialResponse.model_validate(item) for item in lesson.taiLieus],
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
