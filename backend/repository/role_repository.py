from sqlalchemy import func, select
from sqlalchemy.orm import Session

from models import VaiTro


def get_by_name(db: Session, name: str) -> VaiTro | None:
    statement = select(VaiTro).where(func.upper(VaiTro.tenVaiTro) == name.upper())
    return db.scalars(statement).first()
