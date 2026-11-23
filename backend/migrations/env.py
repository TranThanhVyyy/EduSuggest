from logging.config import fileConfig

from alembic import context
from sqlalchemy import engine_from_config, pool

import models
from config.config import get_settings
from config.database import Base

# Lấy cấu hình từ .env
settings = get_settings()

# Cấu hình Alembic
config = context.config

# Cấu hình logging
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# Đưa DATABASE_URL vào Alembic
database_url = settings.database_url.get_secret_value()

# Tránh lỗi ký tự % khi sử dụng ConfigParser
config.set_main_option("sqlalchemy.url", database_url.replace("%", "%%"))

# Metadata của SQLAlchemy
if models.NguoiDung.metadata is not Base.metadata:
    raise RuntimeError("Models must use config.database.Base")
target_metadata = Base.metadata


def run_migrations_offline() -> None:
    """Chạy migration ở chế độ offline."""

    url = settings.database_url.get_secret_value()

    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        compare_type=True,
        compare_server_default=True,
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """Chạy migration ở chế độ online."""

    connectable = engine_from_config(
        config.get_section(config.config_ini_section) or {},
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            compare_type=True,
            compare_server_default=True,
        )

        with context.begin_transaction():
            context.run_migrations()

    connectable.dispose()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
