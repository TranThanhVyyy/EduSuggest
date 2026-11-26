from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from api.dependencies import require_roles
from config.database import get_db
from models import NguoiDung
from schemas.recommendation import (
    CourseRecommendationResponse,
    MaterialRecommendationResponse,
    RecommendedCourse,
    RecommendedMaterial,
)
from service import recommendation_service
from service.workflow_service import (
    WorkflowForbiddenError,
    WorkflowNotFoundError,
)

router = APIRouter(tags=["recommendations"])


def _run(operation, *args):
    try:
        return operation(*args)
    except WorkflowNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)
        ) from exc
    except WorkflowForbiddenError as exc:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail=str(exc)
        ) from exc


@router.get("/recommendations/courses", response_model=CourseRecommendationResponse)
def get_course_recommendations(
    user: Annotated[NguoiDung, Depends(require_roles("USER"))],
    db: Annotated[Session, Depends(get_db)],
    limit: int = Query(default=10, ge=1, le=20),
) -> CourseRecommendationResponse:
    return recommendation_service.recommend_courses(db, user.maNguoiDung, limit)


@router.get(
    "/courses/{course_id}/similar",
    response_model=list[RecommendedCourse],
)
def get_similar_course_recommendations(
    course_id: int,
    user: Annotated[NguoiDung, Depends(require_roles("USER"))],
    db: Annotated[Session, Depends(get_db)],
    limit: int = Query(default=10, ge=1, le=20),
) -> list[RecommendedCourse]:
    _ = user.maNguoiDung
    return _run(recommendation_service.recommend_similar_courses, db, course_id, limit)


@router.get("/recommendations/materials", response_model=MaterialRecommendationResponse)
def get_material_recommendations(
    user: Annotated[NguoiDung, Depends(require_roles("USER"))],
    db: Annotated[Session, Depends(get_db)],
    course_id: int | None = Query(default=None, gt=0),
    lesson_id: int | None = Query(default=None, gt=0),
    limit: int = Query(default=10, ge=1, le=20),
) -> MaterialRecommendationResponse:
    if course_id is None:
        return _run(
            recommendation_service.recommend_standalone_materials,
            db,
            user.maNguoiDung,
            limit,
        )
    return _run(
        recommendation_service.recommend_materials,
        db,
        user.maNguoiDung,
        course_id,
        lesson_id,
        limit,
    )


@router.get(
    "/materials/{material_id}/similar",
    response_model=list[RecommendedMaterial],
)
def get_similar_material_recommendations(
    material_id: int,
    user: Annotated[NguoiDung, Depends(require_roles("USER"))],
    db: Annotated[Session, Depends(get_db)],
    limit: int = Query(default=10, ge=1, le=20),
) -> list[RecommendedMaterial]:
    _ = user.maNguoiDung
    return _run(
        recommendation_service.recommend_similar_materials,
        db,
        material_id,
        limit,
    )
