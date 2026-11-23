from collections.abc import Generator

from sqlalchemy import create_engine, text
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from config.config import get_settings

settings = get_settings()
engine = create_engine(
    settings.database_url.get_secret_value(),
    pool_pre_ping=True,
    hide_parameters=True,
)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


class Base(DeclarativeBase):
    pass


def get_db() -> Generator[Session, None, None]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def check_database_connection() -> bool:
    with engine.connect() as connection:
        connection.execute(text("SELECT 1"))
    return True


def connect_to_database() -> bool:
    return check_database_connection()


def close_database_connection() -> None:
    engine.dispose()
