from datetime import UTC, datetime

from sqlalchemy import delete, select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import Session

from models import TokenBiThuHoi


def is_revoked(db: Session, jti: str) -> bool:
    statement = select(TokenBiThuHoi.maToken).where(TokenBiThuHoi.jti == jti)
    return db.scalar(statement) is not None


def revoke(
    db: Session,
    jti: str,
    expires_at: datetime,
) -> None:
    now = datetime.now(UTC).replace(tzinfo=None)
    statement = (
        insert(TokenBiThuHoi)
        .values(jti=jti, thoiGianHetHan=expires_at, ngayTao=now)
        .on_conflict_do_nothing(index_elements=[TokenBiThuHoi.jti])
    )
    db.execute(statement)
    db.commit()


def delete_expired(db: Session) -> int:
    now = datetime.now(UTC).replace(tzinfo=None)
    result = db.execute(
        delete(TokenBiThuHoi).where(TokenBiThuHoi.thoiGianHetHan <= now)
    )
    return result.rowcount or 0
