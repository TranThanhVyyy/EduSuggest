"""add TaiLieu check constraints and restrict DanhGiaChuyenGia delete

Revision ID: f1a2b3c4d5e6
Revises: e5b72183d29a
Create Date: 2026-11-24 23:33:00.000000

NOTE: Additive integrity migration prepared for M-03 & M-06.
DO NOT run automatically without explicit business/operator confirmation.
"""

from collections.abc import Sequence

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "f1a2b3c4d5e6"
down_revision: str | Sequence[str] | None = "e5b72183d29a"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # 1. Enforce valid review and visibility statuses on TaiLieu
    op.create_check_constraint(
        "ck_TaiLieu_trangThaiDuyet",
        "TaiLieu",
        "\"trangThaiDuyet\" IN ('DRAFT', 'PENDING', 'APPROVED', 'REJECTED', 'NEEDS_REVISION')",
    )
    op.create_check_constraint(
        "ck_TaiLieu_trangThaiHienThi",
        "TaiLieu",
        "\"trangThaiHienThi\" IN ('VISIBLE', 'HIDDEN')",
    )

    # 2. Enforce 3-level linking integrity:
    #    - Standalone: (maKhoaHoc IS NULL AND maBaiHoc IS NULL) -> allowed
    #    - Course-level: (maKhoaHoc IS NOT NULL AND maBaiHoc IS NULL) -> allowed
    #    - Lesson-level: (maKhoaHoc IS NOT NULL AND maBaiHoc IS NOT NULL) -> allowed
    #    - Orphan lesson without course: (maKhoaHoc IS NULL AND maBaiHoc IS NOT NULL) -> forbidden
    op.create_check_constraint(
        "ck_TaiLieu_lesson_requires_course",
        "TaiLieu",
        '"maBaiHoc" IS NULL OR "maKhoaHoc" IS NOT NULL',
    )

    # 3. Enforce maBaiHoc belongs to maKhoaHoc via composite UNIQUE + composite FK (MATCH SIMPLE)
    op.create_unique_constraint(
        "uq_BaiHoc_maKhoaHoc_maBaiHoc",
        "BaiHoc",
        ["maKhoaHoc", "maBaiHoc"],
    )
    op.create_foreign_key(
        "fk_TaiLieu_maKhoaHoc_maBaiHoc",
        "TaiLieu",
        "BaiHoc",
        ["maKhoaHoc", "maBaiHoc"],
        ["maKhoaHoc", "maBaiHoc"],
    )

    # 4. Prevent cascade-deletion of expert review history (M-06)
    op.drop_constraint(
        "fk_DanhGiaChuyenGia_maTaiLieu",
        "DanhGiaChuyenGia",
        type_="foreignkey",
    )
    op.create_foreign_key(
        "fk_DanhGiaChuyenGia_maTaiLieu",
        "DanhGiaChuyenGia",
        "TaiLieu",
        ["maTaiLieu"],
        ["maTaiLieu"],
        ondelete="RESTRICT",
    )


def downgrade() -> None:
    op.drop_constraint(
        "fk_DanhGiaChuyenGia_maTaiLieu",
        "DanhGiaChuyenGia",
        type_="foreignkey",
    )
    op.create_foreign_key(
        "fk_DanhGiaChuyenGia_maTaiLieu",
        "DanhGiaChuyenGia",
        "TaiLieu",
        ["maTaiLieu"],
        ["maTaiLieu"],
        ondelete="CASCADE",
    )

    op.drop_constraint(
        "fk_TaiLieu_maKhoaHoc_maBaiHoc",
        "TaiLieu",
        type_="foreignkey",
    )
    op.drop_constraint(
        "uq_BaiHoc_maKhoaHoc_maBaiHoc",
        "BaiHoc",
        type_="unique",
    )
    op.drop_constraint(
        "ck_TaiLieu_lesson_requires_course",
        "TaiLieu",
        type_="check",
    )
    op.drop_constraint(
        "ck_TaiLieu_trangThaiHienThi",
        "TaiLieu",
        type_="check",
    )
    op.drop_constraint(
        "ck_TaiLieu_trangThaiDuyet",
        "TaiLieu",
        type_="check",
    )
