from sqlalchemy import select, text
from sqlalchemy.orm import Session

from config.database import SessionLocal
from models import VaiTro

DEFAULT_ROLES = (
    (1, "ADMIN", "Quản trị viên."),
    (2, "USER", "Người học."),
    (3, "PROVIDER", "Nhà cung cấp khóa học."),
    (4, "EXPERT", "Chuyên gia đánh giá khóa học."),
)


def seed_default_roles(db: Session) -> None:
    existing_roles = db.scalars(select(VaiTro)).all()
    existing_names = {
        role.tenVaiTro.casefold()
        for role in existing_roles
        if role.tenVaiTro is not None
    }
    used_ids = {role.maVaiTro for role in existing_roles}
    next_id = max(used_ids, default=0) + 1

    for preferred_id, name, description in DEFAULT_ROLES:
        if name.casefold() in existing_names:
            continue

        if preferred_id in used_ids:
            while next_id in used_ids:
                next_id += 1
            role_id = next_id
            next_id += 1
        else:
            role_id = preferred_id

        db.add(
            VaiTro(
                maVaiTro=role_id,
                tenVaiTro=name,
                moTa=description,
            )
        )
        used_ids.add(role_id)
        existing_names.add(name.casefold())

    db.flush()
    sequence_value = db.execute(
        text(
            """
            SELECT setval(
                pg_get_serial_sequence('"VaiTro"', 'maVaiTro'),
                COALESCE(MAX("maVaiTro"), 1),
                MAX("maVaiTro") IS NOT NULL
            )
            FROM "VaiTro"
            """
        )
    ).scalar_one_or_none()
    if sequence_value is None:
        raise RuntimeError("Could not synchronize the VaiTro primary-key sequence.")


def main() -> None:
    with SessionLocal.begin() as db:
        seed_default_roles(db)
    print("Default roles seeded; VaiTro sequence synchronized.")


if __name__ == "__main__":
    main()
