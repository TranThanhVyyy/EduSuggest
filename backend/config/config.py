from functools import lru_cache
from pathlib import Path

from pydantic import Field, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict

BACKEND_DIR = Path(__file__).resolve().parents[1]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=BACKEND_DIR / ".env",
        env_file_encoding="utf-8",
        extra="ignore",
        populate_by_name=True,
    )

    app_name: str = Field(default="EduSuggest", alias="APP_NAME")
    app_env: str = Field(default="development", alias="APP_ENV")
    debug: bool = Field(default=False, alias="DEBUG")
    api_prefix: str = Field(default="/api", alias="API_PREFIX")

    database_host: str = Field(default="localhost", alias="DATABASE_HOST")
    database_port: int = Field(default=5432, alias="DATABASE_PORT")
    database_name: str | None = Field(default=None, alias="DATABASE_NAME")
    database_user: str | None = Field(default=None, alias="DATABASE_USER")
    database_password: SecretStr | None = Field(default=None, alias="DATABASE_PASSWORD")
    database_url: SecretStr = Field(..., alias="DATABASE_URL")

    log_level: str = Field(default="INFO", alias="LOG_LEVEL")
    system_log_file: str = Field(default="logs/system.log", alias="SYSTEM_LOG_FILE")
    secret_key: SecretStr = Field(..., alias="SECRET_KEY")

    minio_url: str | None = Field(default=None, alias="MINIO_URL")
    minio_access_key: SecretStr | None = Field(default=None, alias="MINIO_ACCESS_KEY")
    minio_secret_key: SecretStr | None = Field(default=None, alias="MINIO_SECRET_KEY")
    minio_bucket: str | None = Field(default=None, alias="MINIO_BUCKET")
    port_image: str | None = Field(default=None, alias="PORT_IMAGE")
    minio_secure: bool = Field(default=False, alias="MINIO_SECURE")
    access_token_expire_seconds: int = Field(
        default=900, gt=0, alias="ACCESS_TOKEN_EXPIRE_SECONDS"
    )
    bucket_name: str | None = Field(default=None, alias="BUCKET_NAME")
    google_client_id: str | None = Field(default=None, alias="GOOGLE_CLIENT_ID")
    google_client_secret: SecretStr | None = Field(
        default=None, alias="GOOGLE_CLIENT_SECRET"
    )
    frontend_url: str | None = Field(default=None, alias="FRONTEND_URL")
    backend_url: str | None = Field(default=None, alias="BACKEND_URL")
    server_metadata_url: str | None = Field(
        default=None, alias="GOOGLE_SERVER_METADATA_URL"
    )
    google_scope: str = Field(default="openid email profile", alias="GOOGLE_SCOPE")
    google_access_type: str = Field(default="offline", alias="GOOGLE_ACCESS_TYPE")
    google_prompt: str = Field(default="consent", alias="GOOGLE_PROMPT")
    facebook_app_id: str | None = Field(default=None, alias="FACEBOOK_APP_ID")
    facebook_app_secret: SecretStr | None = Field(
        default=None, alias="FACEBOOK_APP_SECRET"
    )
    mongodb_url: SecretStr | None = Field(default=None, alias="MONGODB_URL")
    redis_host: str | None = Field(default=None, alias="REDIS_HOST")
    redis_port: int | None = Field(default=None, alias="REDIS_PORT")
    redis_db: int | None = Field(default=None, alias="REDIS_DB")
    smtp_host: str | None = Field(default=None, alias="SMTP_HOST")
    smtp_port: int | None = Field(default=None, alias="SMTP_PORT")
    smtp_username: str | None = Field(default=None, alias="SMTP_USERNAME")
    smtp_password: SecretStr | None = Field(default=None, alias="SMTP_PASSWORD")
    smtp_from_email: str | None = Field(default=None, alias="SMTP_FROM_EMAIL")
    smtp_use_tls: bool = Field(default=True, alias="SMTP_USE_TLS")
    momo_partner_code: str | None = Field(default=None, alias="MOMO_PARTNER_CODE")
    momo_access_key: SecretStr | None = Field(default=None, alias="MOMO_ACCESS_KEY")
    momo_secret_key: SecretStr | None = Field(default=None, alias="MOMO_SECRET_KEY")
    momo_api_url: str | None = Field(
        default="https://test-payment.momo.vn/v2/gateway/api/create",
        alias="MOMO_API_URL",
    )
    momo_ipn_url: str | None = Field(default=None, alias="MOMO_IPN_URL")
    momo_redirect_url: str | None = Field(default=None, alias="MOMO_REDIRECT_URL")
    momo_environment: str = Field(default="sandbox", alias="MOMO_ENVIRONMENT")
    momo_demo_mode: bool = Field(default=False, alias="MOMO_DEMO_MODE")

    @property
    def client_kwargs(self) -> dict:
        return {
            "scope": self.google_scope,
            "access_type": self.google_access_type,
            "prompt": self.google_prompt,
        }

    @property
    def backend_api_base(self) -> str:
        return self.backend_url or "http://127.0.0.1:8000"


@lru_cache
def get_settings() -> Settings:
    return Settings()
