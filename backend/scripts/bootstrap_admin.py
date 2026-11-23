from getpass import getpass

from pydantic import EmailStr, TypeAdapter, ValidationError
from sqlalchemy import func, select
from sqlalchemy.exc import SQLAlchemyError

from config.database import SessionLocal
from models import NguoiDung, VaiTro
from repository import role_repository, user_repository
from utils.security import hash_password
from utils.usernames import normalize_username


def main() -> None:
    db = SessionLocal()
    try:
        admin_role = role_repository.get_by_name(db, "ADMIN")
        if admin_role is None:
            raise SystemExit("ADMIN role is missing; seed the four roles first.")
        admin_exists = db.scalar(
            select(NguoiDung.maNguoiDung)
            .join(NguoiDung.vaiTro)
            .where(func.upper(VaiTro.tenVaiTro) == "ADMIN")
            .limit(1)
        )
        if admin_exists is not None:
            raise SystemExit("An ADMIN account already exists; bootstrap stopped.")

        full_name = input("Admin full name: ").strip()
        if not full_name:
            raise SystemExit("Full name cannot be blank.")
        raw_username = input("Admin username: ")
        try:
            username = normalize_username(raw_username)
        except ValueError as exc:
            raise SystemExit(str(exc)) from exc
        if user_repository.get_by_username(db, username) is not None:
            raise SystemExit("That username already belongs to an account; bootstrap stopped.")

        raw_email = input("Admin email: ").strip()
        try:
            email = str(TypeAdapter(EmailStr).validate_python(raw_email)).lower()
        except ValidationError as exc:
            raise SystemExit("Enter a valid email address.") from exc
        if user_repository.get_by_email(db, email) is not None:
            raise SystemExit("That email already belongs to an account; bootstrap stopped.")

        password = getpass("Admin password (8-128 characters): ")
        if not 8 <= len(password) <= 128:
            raise SystemExit("Password must contain 8-128 characters.")
        confirmation = getpass("Confirm admin password: ")
        if password != confirmation:
            raise SystemExit("Password confirmation did not match.")

        db.add(
            NguoiDung(
                maVaiTro=admin_role.maVaiTro,
                tenTaiKhoan=username,
                hoTen=full_name,
                email=email,
                matKhau=hash_password(password),
            )
        )
        db.commit()
        print(f"Created the first ADMIN account with username {username}.")
    except SQLAlchemyError:
        db.rollback()
        raise
    finally:
        db.close()


if __name__ == "__main__":
    main()
