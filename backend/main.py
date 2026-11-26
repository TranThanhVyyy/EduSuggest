import asyncio
import mimetypes
import time
import uuid
from contextlib import asynccontextmanager

# Ensure Windows StaticFiles serves .webp with standard MIME type image/webp
mimetypes.add_type("image/webp", ".webp")

from fastapi import FastAPI, HTTPException, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from sqlalchemy.exc import SQLAlchemyError

from api.accountability import router as accountability_router
from api.assignments import router as assignments_router
from api.auth import router as auth_router
from api.availability_notifications import router as availability_notifications_router
from api.commerce import router as commerce_router
from api.commerce_admin import router as commerce_admin_router
from api.recommendations import router as recommendations_router
from api.users import router as users_router
from api.workflows import router as workflows_router
from config.config import get_settings
from config.context import request_id
from config.storage import course_media_directory
from config.database import (
    check_database_connection,
    close_database_connection,
    connect_to_database,
    engine as db_engine,
    get_db,
)
from config.schema_guard import SchemaCompatibilityError, verify_database_schema_compatibility
from utils.logger import log_success, logger
from utils.token_cleanup import cleanup_expired_tokens_periodically

settings = get_settings()


@asynccontextmanager
async def lifespan(_: FastAPI):
    logger.info("=" * 60)
    logger.info("Starting %s", settings.app_name)
    logger.info("Environment: %s", settings.app_env)
    logger.info("Connecting to PostgreSQL")
    try:
        await asyncio.to_thread(connect_to_database)
        log_success("PostgreSQL connection established")
        if get_db not in app.dependency_overrides:
            await asyncio.to_thread(
                verify_database_schema_compatibility,
                db_engine,
                require_marketplace_tables=bool(settings.commerce_enrollment_gate_enabled),
            )
            log_success("PostgreSQL schema compatibility verified (fail-closed guard PASS)")
    except SchemaCompatibilityError as exc:
        logger.error("STARTUP BLOCKED — %s", exc)
        raise
    except SQLAlchemyError as exc:
        logger.error("PostgreSQL connection failed (%s)", type(exc).__name__)

    cleanup_task = asyncio.create_task(cleanup_expired_tokens_periodically())
    base_url = settings.backend_api_base.rstrip("/")
    logger.info("Swagger UI: %s/docs", base_url)
    logger.info("ReDoc: %s/redoc", base_url)
    logger.info("Health check: %s%s/health", base_url, settings.api_prefix.rstrip("/"))
    try:
        yield
    finally:
        logger.info("Stopping %s", settings.app_name)
        cleanup_task.cancel()
        try:
            await cleanup_task
        except asyncio.CancelledError:
            pass
        await asyncio.to_thread(close_database_connection)
        logger.info("%s stopped", settings.app_name)


app = FastAPI(
    title="EduSuggest API",
    description="Course and Learning Material Recommendation System",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan,
)
allowed_frontend_origins = {
    "http://localhost:5173",
    "http://127.0.0.1:5173",
}
if settings.frontend_url:
    allowed_frontend_origins.add(settings.frontend_url.rstrip("/"))
app.add_middleware(
    CORSMiddleware,
    allow_origins=sorted(allowed_frontend_origins),
    allow_methods=["*"],
    allow_headers=["Authorization", "Content-Type", "Idempotency-Key"],
)
app.include_router(auth_router, prefix=settings.api_prefix)
app.include_router(users_router, prefix=settings.api_prefix)
app.include_router(workflows_router, prefix=settings.api_prefix)
app.include_router(assignments_router, prefix=settings.api_prefix)
app.include_router(accountability_router, prefix=settings.api_prefix)
app.include_router(availability_notifications_router, prefix=settings.api_prefix)
app.include_router(recommendations_router, prefix=settings.api_prefix)
app.include_router(commerce_router, prefix=settings.api_prefix)
app.include_router(commerce_admin_router, prefix=settings.api_prefix)

_course_media_dir = course_media_directory()
_course_media_dir.mkdir(parents=True, exist_ok=True)
app.mount(
    "/media/courses",
    StaticFiles(directory=str(_course_media_dir)),
    name="course-media",
)


@app.middleware("http")
async def request_middleware(request: Request, call_next):
    token = request_id.set(str(uuid.uuid4()))
    started_at = time.perf_counter()
    status_code = status.HTTP_500_INTERNAL_SERVER_ERROR
    logger.info("Request started: %s %s", request.method, request.url.path)
    try:
        response = await call_next(request)
        status_code = response.status_code
        return response
    except Exception:
        logger.exception("Request failed: %s %s", request.method, request.url.path)
        raise
    finally:
        elapsed_ms = (time.perf_counter() - started_at) * 1000
        logger.info(
            "Response %s - %.1fms - %s %s",
            status_code,
            elapsed_ms,
            request.method,
            request.url.path,
        )
        request_id.reset(token)


@app.get("/")
def read_root():
    return {"message": "EduSuggest API đang chạy"}


@app.get(f"{settings.api_prefix.rstrip('/')}/health", tags=["health"])
def health_check():
    try:
        check_database_connection()
    except SQLAlchemyError as exc:
        logger.error("PostgreSQL health check failed (%s)", type(exc).__name__)
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail={
                "status": "error",
                "application": settings.app_name,
                "database": "disconnected",
            },
        ) from exc

    return {
        "status": "ok",
        "application": settings.app_name,
        "database": "connected",
    }
