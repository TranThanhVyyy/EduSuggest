from sqlalchemy import func, select
from sqlalchemy.orm import Session, joinedload

from models import NguoiDung


def get_by_email(db: Session, email: str) -> NguoiDung | None:
    statement = (
        select(NguoiDung)
        .options(joinedload(NguoiDung.vaiTro))
        .where(func.lower(NguoiDung.email) == email.lower())
    )
    return db.scalars(statement).first()


def get_by_username(db: Session, username: str) -> NguoiDung | None:
    statement = (
        select(NguoiDung)
        .options(joinedload(NguoiDung.vaiTro))
        .where(NguoiDung.tenTaiKhoan == username)
    )
    return db.scalars(statement).first()


def get_by_id(db: Session, user_id: int) -> NguoiDung | None:
    statement = (
        select(NguoiDung)
        .options(joinedload(NguoiDung.vaiTro))
        .where(NguoiDung.maNguoiDung == user_id)
    )
    return db.scalars(statement).first()
