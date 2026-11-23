from __future__ import annotations

from decimal import Decimal

from models import BaiHoc, KhoaHoc, LichSuHocTap, TaiLieu
from repository import workflow_repository
from schemas.recommendation import (
    CourseRecommendationResponse,
    MaterialRecommendationResponse,
    RecommendedCourse,
    RecommendedMaterial,
)
from service.content_recommendation import (
    CourseFeatures,
    CourseSignal,
    MaterialFeatures,
    RankedItem,
    build_preference_profile,
    has_course_content,
    rank_materials,
    rank_personalized_courses,
    rank_similar_courses,
)
from service.workflow_service import WorkflowForbiddenError, WorkflowNotFoundError


def _course_features(course: KhoaHoc) -> CourseFeatures:
    lessons = tuple(course.baiHocs or [])
    return CourseFeatures(
        course_id=course.maKhoaHoc,
        title=course.tieuDe,
        description=course.moTa,
        category_id=course.maDanhMuc,
        category_text=(
            " ".join(
                part for part in (course.danhMuc.tenDanhMuc, course.danhMuc.moTa) if part
            )
            if course.danhMuc
            else None
        ),
        level=course.trinhDo,
        duration=float(course.thoiLuong) if course.thoiLuong is not None else None,
        price=course.gia,
        lesson_text=tuple(
            " ".join(part for part in (lesson.tieuDe, lesson.noiDung) if part)
            for lesson in lessons
        ),
        material_text=tuple(
            " ".join(part for part in (material.tieuDe, material.moTa, material.loai) if part)
            for lesson in lessons
            for material in (lesson.taiLieus or [])
        ),
        review_status=course.trangThaiDuyet,
        visibility=course.trangThaiHienThi,
        created_at=course.ngayTao,
        updated_at=course.ngayCapNhat,
    )


def _completed_lesson_counts(history: list[LichSuHocTap]) -> dict[int, set[int]]:
    completed: dict[int, set[int]] = {}
    for record in history:
        if (
            record.tienDo == "COMPLETED"
            and record.maKhoaHoc is not None
            and record.maBaiHoc is not None
        ):
            completed.setdefault(record.maKhoaHoc, set()).add(record.maBaiHoc)
    return completed


def _user_signals(
    enrollments, history: list[LichSuHocTap]
) -> tuple[list[CourseSignal], set[int]]:
    signals: dict[int, CourseSignal] = {}
    enrolled_ids: set[int] = set()
    for enrollment in enrollments:
        course = enrollment.khoaHoc
        if course is None or enrollment.maKhoaHoc is None:
            continue
        enrolled_ids.add(enrollment.maKhoaHoc)
        progress = min(max(float(enrollment.tienDo or 0), 0), 100) / 100
        weight = 1 + progress + (1 if enrollment.ngayHoanThanh else 0)
        current = signals.get(course.maKhoaHoc)
        if current is None or weight > current.weight:
            signals[course.maKhoaHoc] = CourseSignal(_course_features(course), weight)

    completed = _completed_lesson_counts(history)
    history_courses: dict[int, KhoaHoc] = {}
    for record in history:
        if record.khoaHoc is not None and record.maKhoaHoc is not None:
            history_courses.setdefault(record.maKhoaHoc, record.khoaHoc)
    for course_id, course in history_courses.items():
        if course_id in signals:
            continue
        lesson_count = len(completed.get(course_id, set()))
        if lesson_count:
            weight = 0.5 + 0.25 * min(lesson_count, 4)
            signals[course_id] = CourseSignal(_course_features(course), weight)
    return list(signals.values()), enrolled_ids


def _safe_course_response(
    ranked_item, *, latest: bool = False
) -> RecommendedCourse:
    course = ranked_item.item
    return RecommendedCourse(
        maKhoaHoc=course.course_id,
        tieuDe=course.title,
        moTa=course.description,
        maDanhMuc=course.category_id,
        trinhDo=course.level,
        thoiLuong=int(course.duration) if course.duration is not None else None,
        gia=(
            course.price
            if isinstance(course.price, Decimal)
            else Decimal(str(course.price)) if course.price is not None else None
        ),
        score=None if latest else ranked_item.score,
        reasonCodes=list(ranked_item.reason_codes),
    )


def recommend_courses(db, user_id: int, limit: int) -> CourseRecommendationResponse:
    course_rows = workflow_repository.list_recommendation_courses(db)
    candidates = [_course_features(course) for course in course_rows]
    enrollments = workflow_repository.list_user_recommendation_enrollments(db, user_id)
    history = workflow_repository.list_user_recommendation_history(db, user_id)
    signals, enrolled_ids = _user_signals(enrollments, history)
    profile = build_preference_profile(signals, candidates)

    if profile is None:
        dated = [
            course
            for course in candidates
            if course.course_id not in enrolled_ids
            and has_course_content(course)
            and (course.created_at is not None or course.updated_at is not None)
        ]
        dated.sort(
            key=lambda course: (
                max(
                    str(date)
                    for date in (course.created_at, course.updated_at)
                    if date is not None
                ),
                -course.course_id,
            ),
            reverse=True,
        )
        return CourseRecommendationResponse(
            items=[
                _safe_course_response(
                    RankedItem(course, 0.0, ("RECENT_COURSE",)), latest=True
                )
                for course in dated[:limit]
            ],
            strategy="latest" if dated else "none",
            personalized=False,
        )

    ranked = rank_personalized_courses(
        profile,
        candidates,
        excluded_course_ids=enrolled_ids,
        limit=limit,
    )
    return CourseRecommendationResponse(
        items=[_safe_course_response(item) for item in ranked],
        strategy="content_based" if ranked else "none",
        personalized=bool(ranked),
    )


def recommend_similar_courses(
    db, course_id: int, limit: int
) -> list[RecommendedCourse]:
    source_row = workflow_repository.get_recommendation_course(db, course_id)
    if source_row is None:
        raise WorkflowNotFoundError("Course was not found.")
    source = _course_features(source_row)
    candidates = [
        _course_features(course)
        for course in workflow_repository.list_recommendation_courses(db)
    ]
    ranked = rank_similar_courses(source, candidates, limit)
    return [_safe_course_response(item) for item in ranked]


def _material_feature(material: TaiLieu) -> MaterialFeatures:
    lesson: BaiHoc | None = material.baiHoc
    course = lesson.khoaHoc if lesson else None
    category = course.danhMuc if course else None
    return MaterialFeatures(
        material_id=material.maTaiLieu,
        course_id=course.maKhoaHoc if course else 0,
        lesson_id=lesson.maBaiHoc if lesson else 0,
        title=material.tieuDe,
        description=material.moTa,
        material_type=material.loai,
        lesson_title=lesson.tieuDe if lesson else None,
        lesson_content=lesson.noiDung if lesson else None,
        course_title=course.tieuDe if course else None,
        category_text=(category.tenDanhMuc if category else None),
    )


def recommend_materials(
    db, user_id: int, course_id: int, lesson_id: int | None, limit: int
) -> MaterialRecommendationResponse:
    course = workflow_repository.get_recommendation_course(db, course_id)
    if course is None:
        raise WorkflowNotFoundError("Course was not found.")
    if workflow_repository.get_enrollment(db, user_id, course_id) is None:
        raise WorkflowForbiddenError("Enroll in this course before requesting its materials.")

    source_lesson = None
    if lesson_id is not None:
        source_lesson = workflow_repository.get_owned_lesson(db, course, lesson_id)
        if source_lesson is None:
            raise WorkflowNotFoundError("Lesson was not found in this course.")

    materials = workflow_repository.list_recommendation_materials_for_enrolled_course(
        db, user_id, course_id
    )
    if source_lesson is not None:
        context = {
            "title": (source_lesson.tieuDe or "",),
            "description": (source_lesson.noiDung or "", course.moTa or ""),
            "category": (
                course.danhMuc.tenDanhMuc if course.danhMuc else "",
            ),
        }
    else:
        context = {
            "title": (course.tieuDe or "",),
            "description": (course.moTa or "",),
            "category": (
                course.danhMuc.tenDanhMuc if course.danhMuc else "",
            ),
            "lessons": tuple(
                " ".join(part for part in (lesson.tieuDe, lesson.noiDung) if part)
                for lesson in course.baiHocs or []
            ),
        }
    ranked = rank_materials(
        context,
        [_material_feature(material) for material in materials],
        lesson_id=lesson_id,
        limit=limit,
    )
    return MaterialRecommendationResponse(
        items=[
            RecommendedMaterial(
                maTaiLieu=item.item.material_id,
                maBaiHoc=item.item.lesson_id,
                maKhoaHoc=item.item.course_id,
                tieuDe=item.item.title,
                moTa=item.item.description,
                loai=item.item.material_type,
                score=item.score,
                reasonCodes=list(item.reason_codes),
            )
            for item in ranked
        ]
    )
