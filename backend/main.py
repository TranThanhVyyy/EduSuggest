import asyncio
import time
import uuid
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, Request, status
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.exc import SQLAlchemyError

from api.auth import router as auth_router
from api.recommendations import router as recommendations_router
from api.users import router as users_router
from api.workflows import router as workflows_router
from config.config import get_settings
from config.context import request_id
from config.database import (
    check_database_connection,
    close_database_connection,
    connect_to_database,
)
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
    allow_headers=["Authorization", "Content-Type"],
)
app.include_router(auth_router, prefix=settings.api_prefix)
app.include_router(users_router, prefix=settings.api_prefix)
app.include_router(workflows_router, prefix=settings.api_prefix)
app.include_router(recommendations_router, prefix=settings.api_prefix)


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
