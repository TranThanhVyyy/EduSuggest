from __future__ import annotations

import threading
from collections import Counter
from dataclasses import dataclass
from decimal import Decimal

from sqlalchemy import text

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
    _course_terms,
    _material_terms,
    build_preference_profile,
    has_course_content,
    rank_materials,
    rank_personalized_courses,
    rank_similar_courses,
    rank_similar_materials,
    rank_standalone_materials,
)
from service.workflow_service import WorkflowForbiddenError, WorkflowNotFoundError


@dataclass(frozen=True)
class _CourseCorpusCacheEntry:
    fingerprint: str
    candidates: tuple[CourseFeatures, ...]
    image_by_course_id: dict[int, str | None]
    terms_by_course_id: dict[int, Counter[str]]


@dataclass(frozen=True)
class _MaterialCorpusCacheEntry:
    fingerprint: str
    materials: tuple[MaterialFeatures, ...]
    terms_by_material_id: dict[int, Counter[str]]


_CACHE_LOCK = threading.RLock()
_MAX_CACHED_DATABASES = 8
_COURSE_CORPUS_CACHE: dict[str, _CourseCorpusCacheEntry] = {}
_MATERIAL_CORPUS_CACHE: dict[str, _MaterialCorpusCacheEntry] = {}
_CACHE_STATS: dict[str, int] = {
    "course_hits": 0,
    "course_misses": 0,
    "material_hits": 0,
    "material_misses": 0,
}


def get_recommendation_cache_stats() -> dict[str, int]:
    """Return thread-safe cache hit/miss counters and current entry counts."""
    with _CACHE_LOCK:
        return {
            **_CACHE_STATS,
            "course_entries": len(_COURSE_CORPUS_CACHE),
            "material_entries": len(_MATERIAL_CORPUS_CACHE),
        }


def invalidate_recommendation_cache(db_name: str | None = None) -> None:
    """Explicitly invalidate in-memory TF-IDF corpus caches (called on committed mutations or tests)."""
    with _CACHE_LOCK:
        if db_name is None:
            _COURSE_CORPUS_CACHE.clear()
            _MATERIAL_CORPUS_CACHE.clear()
        else:
            for key in list(_COURSE_CORPUS_CACHE.keys()):
                if key == db_name or key.endswith(f"/{db_name}"):
                    _COURSE_CORPUS_CACHE.pop(key, None)
            for key in list(_MATERIAL_CORPUS_CACHE.keys()):
                if key == db_name or key.endswith(f"/{db_name}"):
                    _MATERIAL_CORPUS_CACHE.pop(key, None)


def _current_db_key(db) -> str:
    try:
        bind = db.get_bind()
        if bind is not None and getattr(bind, "url", None) is not None:
            url = bind.url
            return f"{url.drivername}://{url.host or ''}:{url.port or ''}/{url.database or 'default'}"
    except Exception:
        pass
    return "default"


def _is_postgres(db) -> bool:
    try:
        bind = db.get_bind()
        return bind is not None and bind.dialect.name == "postgresql"
    except Exception:
        return False


def _course_corpus_fingerprint(db) -> str:
    """Content-accurate DB fingerprint covering every course, lesson, and category field used by TF-IDF."""
    if _is_postgres(db):
        row = db.execute(
            text(
                'SELECT '
                '('
                '  SELECT md5(coalesce(string_agg('
                '    concat_ws(\'|\', "maKhoaHoc", coalesce("tieuDe", \'\'), coalesce("moTa", \'\'), '
                '    coalesce("maDanhMuc"::text, \'\'), coalesce("trinhDo", \'\'), coalesce("thoiLuong"::text, \'\'), '
                '    coalesce("gia"::text, \'\'), coalesce("hinhAnh", \'\'), "trangThaiDuyet", "trangThaiHienThi", '
                '    coalesce("ngayTao"::text, \'\'), coalesce("ngayCapNhat"::text, \'\')), E\'\\n\' '
                '    ORDER BY "maKhoaHoc"'
                '  ), \'\')) '
                '  FROM "KhoaHoc" WHERE "trangThaiDuyet"=\'APPROVED\' AND "trangThaiHienThi"=\'VISIBLE\''
                '), '
                '('
                '  SELECT md5(coalesce(string_agg('
                '    concat_ws(\'|\', b."maBaiHoc", b."maKhoaHoc", coalesce(b."tieuDe", \'\'), md5(coalesce(b."noiDung", \'\'))), E\'\\n\' '
                '    ORDER BY b."maBaiHoc"'
                '  ), \'\')) '
                '  FROM "BaiHoc" b '
                '  JOIN "KhoaHoc" k ON k."maKhoaHoc" = b."maKhoaHoc" '
                '  WHERE k."trangThaiDuyet"=\'APPROVED\' AND k."trangThaiHienThi"=\'VISIBLE\''
                '), '
                '('
                '  SELECT md5(coalesce(string_agg('
                '    concat_ws(\'|\', "maDanhMuc", coalesce("tenDanhMuc", \'\'), coalesce("moTa", \'\')), E\'\\n\' '
                '    ORDER BY "maDanhMuc"'
                '  ), \'\')) '
                '  FROM "DanhMuc"'
                ')'
            )
        ).fetchone()
        return "|".join(str(x) for x in (row or ()))
    # Non-PostgreSQL fallback (e.g., SQLite unit tests): disable stale reuse across text edits
    row = db.execute(
        text(
            'SELECT '
            '(SELECT count(*) FROM "KhoaHoc" WHERE "trangThaiDuyet"=\'APPROVED\' AND "trangThaiHienThi"=\'VISIBLE\'), '
            '(SELECT coalesce(max("ngayCapNhat"), max("ngayTao")) FROM "KhoaHoc"), '
            '(SELECT count(*) FROM "BaiHoc"), '
            '(SELECT count(*) FROM "DanhMuc")'
        )
    ).fetchone()
    return "|".join(str(x) for x in (row or ()))


def _material_corpus_fingerprint(db) -> str:
    """Content-accurate DB fingerprint covering every standalone material and category field used by TF-IDF."""
    if _is_postgres(db):
        row = db.execute(
            text(
                'SELECT '
                '('
                '  SELECT md5(coalesce(string_agg('
                '    concat_ws(\'|\', "maTaiLieu", coalesce("tieuDe", \'\'), coalesce("moTa", \'\'), '
                '    coalesce("loai", \'\'), coalesce("maDanhMuc"::text, \'\'), coalesce("maBaiHoc"::text, \'\'), '
                '    coalesce("maKhoaHoc"::text, \'\'), "trangThaiDuyet", "trangThaiHienThi", '
                '    coalesce("ngayTao"::text, \'\'), coalesce("ngayCapNhat"::text, \'\')), E\'\\n\' '
                '    ORDER BY "maTaiLieu"'
                '  ), \'\')) '
                '  FROM "TaiLieu" WHERE "trangThaiDuyet"=\'APPROVED\' AND "trangThaiHienThi"=\'VISIBLE\''
                '), '
                '('
                '  SELECT md5(coalesce(string_agg('
                '    concat_ws(\'|\', "maDanhMuc", coalesce("tenDanhMuc", \'\'), coalesce("moTa", \'\')), E\'\\n\' '
                '    ORDER BY "maDanhMuc"'
                '  ), \'\')) '
                '  FROM "DanhMuc"'
                ')'
            )
        ).fetchone()
        return "|".join(str(x) for x in (row or ()))
    row = db.execute(
        text(
            'SELECT '
            '(SELECT count(*) FROM "TaiLieu" WHERE "trangThaiDuyet"=\'APPROVED\' AND "trangThaiHienThi"=\'VISIBLE\'), '
            '(SELECT coalesce(max("ngayCapNhat"), max("ngayTao")) FROM "TaiLieu"), '
            '(SELECT count(*) FROM "DanhMuc")'
        )
    ).fetchone()
    return "|".join(str(x) for x in (row or ()))


def _get_cached_course_corpus(db) -> _CourseCorpusCacheEntry:
    db_key = _current_db_key(db)
    fp = _course_corpus_fingerprint(db)
    with _CACHE_LOCK:
        entry = _COURSE_CORPUS_CACHE.get(db_key)
        if entry is not None and entry.fingerprint == fp:
            _CACHE_STATS["course_hits"] += 1
            return entry
        _CACHE_STATS["course_misses"] += 1
        course_rows = workflow_repository.list_recommendation_courses(db)
        image_by_course_id = {row.maKhoaHoc: row.hinhAnh for row in course_rows}
        candidates = tuple(_course_features(course) for course in course_rows)
        terms_by_course_id = {c.course_id: _course_terms(c) for c in candidates}
        entry = _CourseCorpusCacheEntry(
            fingerprint=fp,
            candidates=candidates,
            image_by_course_id=image_by_course_id,
            terms_by_course_id=terms_by_course_id,
        )
        if db_key not in _COURSE_CORPUS_CACHE and len(_COURSE_CORPUS_CACHE) >= _MAX_CACHED_DATABASES:
            _COURSE_CORPUS_CACHE.pop(next(iter(_COURSE_CORPUS_CACHE)))
        _COURSE_CORPUS_CACHE[db_key] = entry
        return entry


def _get_cached_material_corpus(db) -> _MaterialCorpusCacheEntry:
    db_key = _current_db_key(db)
    fp = _material_corpus_fingerprint(db)
    with _CACHE_LOCK:
        entry = _MATERIAL_CORPUS_CACHE.get(db_key)
        if entry is not None and entry.fingerprint == fp:
            _CACHE_STATS["material_hits"] += 1
            return entry
        _CACHE_STATS["material_misses"] += 1
        materials = workflow_repository.list_standalone_recommendation_materials(db)
        features = tuple(_material_feature(m) for m in materials)
        terms_by_id = {m.material_id: _material_terms(m) for m in features}
        entry = _MaterialCorpusCacheEntry(
            fingerprint=fp,
            materials=features,
            terms_by_material_id=terms_by_id,
        )
        if db_key not in _MATERIAL_CORPUS_CACHE and len(_MATERIAL_CORPUS_CACHE) >= _MAX_CACHED_DATABASES:
            _MATERIAL_CORPUS_CACHE.pop(next(iter(_MATERIAL_CORPUS_CACHE)))
        _MATERIAL_CORPUS_CACHE[db_key] = entry
        return entry


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
        material_text=(),
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
    ranked_item,
    *,
    latest: bool = False,
    image_by_course_id: dict[int, str | None] | None = None,
) -> RecommendedCourse:
    course = ranked_item.item
    return RecommendedCourse(
        maKhoaHoc=course.course_id,
        tieuDe=course.title,
        moTa=course.description,
        hinhAnh=(image_by_course_id or {}).get(course.course_id),
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
    corpus_entry = _get_cached_course_corpus(db)
    image_by_course_id = corpus_entry.image_by_course_id
    candidates = corpus_entry.candidates
    precomputed_terms = corpus_entry.terms_by_course_id
    enrollments = workflow_repository.list_user_recommendation_enrollments(db, user_id)
    history = workflow_repository.list_user_recommendation_history(db, user_id)
    signals, enrolled_ids = _user_signals(enrollments, history)
    profile = build_preference_profile(signals, candidates, precomputed_terms=precomputed_terms)

    if profile is None:
        dated = [
            course
            for course in candidates
            if course.course_id not in enrolled_ids
            and (course.category_id is not None or bool(precomputed_terms.get(course.course_id)))
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
                    RankedItem(course, 0.0, ("RECENT_COURSE",)),
                    latest=True,
                    image_by_course_id=image_by_course_id,
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
        precomputed_terms=precomputed_terms,
    )
    return CourseRecommendationResponse(
        items=[
            _safe_course_response(item, image_by_course_id=image_by_course_id)
            for item in ranked
        ],
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
    corpus_entry = _get_cached_course_corpus(db)
    ranked = rank_similar_courses(
        source,
        corpus_entry.candidates,
        limit,
        precomputed_terms=corpus_entry.terms_by_course_id,
    )
    return [
        _safe_course_response(item, image_by_course_id=corpus_entry.image_by_course_id)
        for item in ranked
    ]


def _material_feature(material: TaiLieu) -> MaterialFeatures:
    lesson: BaiHoc | None = material.baiHoc
    course = material.khoaHoc or (lesson.khoaHoc if lesson else None)
    category = material.danhMuc or (course.danhMuc if course else None)
    return MaterialFeatures(
        material_id=material.maTaiLieu,
        course_id=course.maKhoaHoc if course else None,
        lesson_id=lesson.maBaiHoc if lesson else None,
        category_id=category.maDanhMuc if category else None,
        title=material.tieuDe,
        description=material.moTa,
        material_type=material.loai,
        lesson_title=lesson.tieuDe if lesson else None,
        lesson_content=lesson.noiDung if lesson else None,
        course_title=course.tieuDe if course else None,
        category_text=(category.tenDanhMuc if category else None),
        review_status=material.trangThaiDuyet,
        visibility=material.trangThaiHienThi,
        created_at=material.ngayTao,
        updated_at=material.ngayCapNhat,
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
                maDanhMuc=item.item.category_id,
                tieuDe=item.item.title,
                moTa=item.item.description,
                loai=item.item.material_type,
                score=item.score,
                reasonCodes=list(item.reason_codes),
            )
            for item in ranked
        ],
        strategy="content_based",
        personalized=True,
    )


def recommend_standalone_materials(
    db, user_id: int, limit: int = 10
) -> MaterialRecommendationResponse:
    enrollments = workflow_repository.list_user_recommendation_enrollments(db, user_id)
    history = workflow_repository.list_user_recommendation_history(db, user_id)
    signals, _ = _user_signals(enrollments, history)

    course_corpus = _get_cached_course_corpus(db)
    profile = build_preference_profile(
        signals,
        course_corpus.candidates,
        precomputed_terms=course_corpus.terms_by_course_id,
    )

    mat_corpus = _get_cached_material_corpus(db)
    ranked, strategy, personalized = rank_standalone_materials(
        profile, mat_corpus.materials, limit=limit
    )

    return MaterialRecommendationResponse(
        items=[
            RecommendedMaterial(
                maTaiLieu=item.item.material_id,
                maBaiHoc=item.item.lesson_id,
                maKhoaHoc=item.item.course_id,
                maDanhMuc=item.item.category_id,
                tieuDe=item.item.title,
                moTa=item.item.description,
                loai=item.item.material_type,
                score=item.score,
                reasonCodes=list(item.reason_codes),
            )
            for item in ranked
        ],
        strategy=strategy,
        personalized=personalized,
    )


def recommend_similar_materials(
    db, material_id: int, limit: int = 10
) -> list[RecommendedMaterial]:
    target_material = workflow_repository.get_public_material(db, material_id)
    if target_material is None:
        raise WorkflowNotFoundError("Material was not found.")

    candidates = workflow_repository.list_standalone_recommendation_materials(db)
    ranked = rank_similar_materials(
        _material_feature(target_material),
        [_material_feature(m) for m in candidates],
        limit=limit,
    )
    return [
        RecommendedMaterial(
            maTaiLieu=item.item.material_id,
            maBaiHoc=item.item.lesson_id,
            maKhoaHoc=item.item.course_id,
            maDanhMuc=item.item.category_id,
            tieuDe=item.item.title,
            moTa=item.item.description,
            loai=item.item.material_type,
            score=item.score,
            reasonCodes=list(item.reason_codes),
        )
        for item in ranked
    ]
