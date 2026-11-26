"""add expert specialties, category mapping, profile verification, and forced password change

Revision ID: b2c3d4e5f6a7
Revises: e5b72183d29a
Create Date: 2026-11-25 05:30:00.000000

NOTE:
- Additive migration branched cleanly from current live DB revision `e5b72183d29a`
  so unapproved integrity migration `f1a2b3c4d5e6` is not applied automatically.
- Preserves legacy `ChuyenGia.chuyenMon` column and leaves existing experts in `DRAFT`.
- Leaves `NguoiDung.batBuocDoiMatKhau = false` for all existing accounts.
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "b2c3d4e5f6a7"
down_revision: str | Sequence[str] | None = "e5b72183d29a"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


_INITIAL_SPECIALTIES: list[tuple[str, str, str, list[str]]] = [
    (
        "React",
        "Frontend",
        "Phát triển giao diện web hiện đại với React, Hooks, State Management và hệ sinh thái Next.js.",
        ["Lập trình Web Frontend"],
    ),
    (
        "Vue.js",
        "Frontend",
        "Xây dựng ứng dụng SPA/SSR với Vue 3, Composition API, Pinia và Vite.",
        ["Lập trình Web Frontend"],
    ),
    (
        "JavaScript & TypeScript",
        "Lập trình",
        "Ngôn ngữ JavaScript ES6+, TypeScript nâng cao cho cả Frontend và Backend.",
        ["Lập trình Web Frontend", "Lập trình Web Backend"],
    ),
    (
        "Python",
        "Backend",
        "Phát triển Backend với FastAPI, Django, Flask và xử lý dữ liệu bằng Python.",
        ["Lập trình Web Backend", "Khoa học dữ liệu & Machine Learning"],
    ),
    (
        "Java & Spring Boot",
        "Backend",
        "Thiết kế hệ thống doanh nghiệp, REST API và Microservices với Java & Spring Boot.",
        ["Lập trình Web Backend", "Công nghệ phần mềm & Đảm bảo chất lượng"],
    ),
    (
        "Node.js & Express",
        "Backend",
        "Xây dựng dịch vụ web thời gian thực, API hiệu năng cao trên nền tảng Node.js.",
        ["Lập trình Web Backend"],
    ),
    (
        "SQL & PostgreSQL",
        "Cơ sở dữ liệu",
        "Thiết kế lược đồ quan hệ, tối ưu truy vấn SQL, đánh chỉ mục và quản trị PostgreSQL.",
        ["Cơ sở dữ liệu & SQL", "Lập trình Web Backend"],
    ),
    (
        "NoSQL & Data Modeling",
        "Cơ sở dữ liệu",
        "Mô hình hóa dữ liệu phi quan hệ với MongoDB, Redis và kiến trúc lưu trữ phân tán.",
        ["Cơ sở dữ liệu & SQL"],
    ),
    (
        "Machine Learning & AI",
        "AI và khoa học dữ liệu",
        "Học máy có giám sát/không giám sát, Deep Learning, NLP và triển khai mô hình AI.",
        ["Khoa học dữ liệu & Machine Learning"],
    ),
    (
        "Data Analytics & Visualization",
        "AI và khoa học dữ liệu",
        "Phân tích dữ liệu, trực quan hóa số liệu, thống kê ứng dụng và BI.",
        ["Khoa học dữ liệu & Machine Learning", "Cơ sở dữ liệu & SQL"],
    ),
    (
        "An toàn thông tin & OWASP",
        "Mạng máy tính và bảo mật",
        "Kiểm thử bảo mật ứng dụng web, OWASP Top 10, mã hóa và quản trị rủi ro an ninh mạng.",
        ["An toàn thông tin & Bảo mật ứng dụng"],
    ),
    (
        "DevOps & Cloud Infrastructure",
        "DevOps & Cloud",
        "CI/CD, Docker, Kubernetes, hạ tầng đám mây AWS/GCP và giám sát hệ thống.",
        ["DevOps & Điện toán đám mây"],
    ),
    (
        "Thiết kế UI/UX",
        "Thiết kế UI/UX",
        "Nghiên cứu trải nghiệm người dùng, wireframe, design system và thiết kế giao diện trên Figma.",
        ["Lập trình Web Frontend", "Phát triển ứng dụng Di động"],
    ),
    (
        "Flutter & React Native",
        "Phát triển ứng dụng di động",
        "Phát triển ứng dụng di động đa nền tảng iOS/Android với Flutter và React Native.",
        ["Phát triển ứng dụng Di động"],
    ),
    (
        "Kiểm thử phần mềm & QA",
        "Kiểm thử & QA",
        "Kiểm thử tự động, kiểm thử hiệu năng, đảm bảo chất lượng phần mềm và quy trình CI.",
        ["Công nghệ phần mềm & Đảm bảo chất lượng"],
    ),
]


def upgrade() -> None:
    # 1. NguoiDung.batBuocDoiMatKhau (default false for all existing users)
    op.add_column(
        "NguoiDung",
        sa.Column(
            "batBuocDoiMatKhau",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("false"),
        ),
    )

    # 2. Independent specialty catalog table: ChuyenMon
    op.create_table(
        "ChuyenMon",
        sa.Column("maChuyenMon", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("tenChuyenMon", sa.String(length=255), nullable=False),
        sa.Column("nhomChuyenMon", sa.String(length=100), nullable=False),
        sa.Column("moTa", sa.Text(), nullable=True),
        sa.Column(
            "trangThai",
            sa.String(length=20),
            nullable=False,
            server_default=sa.text("'ACTIVE'"),
        ),
        sa.Column(
            "maNguoiTao",
            sa.Integer(),
            sa.ForeignKey("NguoiDung.maNguoiDung", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column(
            "ngayTao",
            sa.DateTime(),
            nullable=False,
            server_default=sa.text("CURRENT_TIMESTAMP"),
        ),
        sa.Column("ngayCapNhat", sa.DateTime(), nullable=True),
        sa.CheckConstraint(
            "\"trangThai\" IN ('ACTIVE', 'INACTIVE')",
            name="ck_ChuyenMon_trangThai",
        ),
    )
    op.execute(
        'CREATE UNIQUE INDEX uq_chuyenmon_ten_normalized '
        'ON "ChuyenMon" (lower(btrim("tenChuyenMon")))'
    )
    op.create_index("ix_ChuyenMon_nhomChuyenMon", "ChuyenMon", ["nhomChuyenMon"])
    op.create_index("ix_ChuyenMon_trangThai", "ChuyenMon", ["trangThai"])

    # 3. N-N Specialty <-> Category mapping table: ChuyenMonDanhMuc
    op.create_table(
        "ChuyenMonDanhMuc",
        sa.Column(
            "maChuyenMon",
            sa.Integer(),
            sa.ForeignKey("ChuyenMon.maChuyenMon", ondelete="CASCADE"),
            primary_key=True,
        ),
        sa.Column(
            "maDanhMuc",
            sa.Integer(),
            sa.ForeignKey("DanhMuc.maDanhMuc", ondelete="CASCADE"),
            primary_key=True,
        ),
        sa.Column(
            "ngayTao",
            sa.DateTime(),
            nullable=False,
            server_default=sa.text("CURRENT_TIMESTAMP"),
        ),
    )
    op.create_index("ix_ChuyenMonDanhMuc_maDanhMuc", "ChuyenMonDanhMuc", ["maDanhMuc"])

    # 4. N-N Expert <-> Specialty table: ChuyenGiaChuyenMon
    op.create_table(
        "ChuyenGiaChuyenMon",
        sa.Column(
            "maChuyenGia",
            sa.Integer(),
            sa.ForeignKey("ChuyenGia.maChuyenGia", ondelete="CASCADE"),
            primary_key=True,
        ),
        sa.Column(
            "maChuyenMon",
            sa.Integer(),
            sa.ForeignKey("ChuyenMon.maChuyenMon", ondelete="RESTRICT"),
            primary_key=True,
        ),
        sa.Column(
            "laChuyenMonChinh",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("false"),
        ),
        sa.Column(
            "ngayTao",
            sa.DateTime(),
            nullable=False,
            server_default=sa.text("CURRENT_TIMESTAMP"),
        ),
    )
    op.execute(
        'CREATE UNIQUE INDEX uq_chuyengia_chuyenmon_chinh '
        'ON "ChuyenGiaChuyenMon" ("maChuyenGia") '
        'WHERE "laChuyenMonChinh" = true'
    )
    op.create_index(
        "ix_ChuyenGiaChuyenMon_maChuyenMon", "ChuyenGiaChuyenMon", ["maChuyenMon"]
    )

    # 5. Additive profile & verification columns on ChuyenGia (legacy chuyenMon kept intact)
    op.add_column(
        "ChuyenGia",
        sa.Column("soNamKinhNghiem", sa.Integer(), nullable=True),
    )
    op.add_column(
        "ChuyenGia",
        sa.Column(
            "trangThaiHoSo",
            sa.String(length=30),
            nullable=False,
            server_default=sa.text("'DRAFT'"),
        ),
    )
    op.add_column(
        "ChuyenGia",
        sa.Column("ghiChuXacMinh", sa.Text(), nullable=True),
    )
    op.add_column(
        "ChuyenGia",
        sa.Column(
            "maNguoiXacMinh",
            sa.Integer(),
            sa.ForeignKey("NguoiDung.maNguoiDung", ondelete="SET NULL"),
            nullable=True,
        ),
    )
    op.add_column(
        "ChuyenGia",
        sa.Column("ngayXacMinh", sa.DateTime(), nullable=True),
    )
    op.add_column(
        "ChuyenGia",
        sa.Column("ngayCapNhat", sa.DateTime(), nullable=True),
    )
    op.create_check_constraint(
        "ck_ChuyenGia_trangThaiHoSo",
        "ChuyenGia",
        "\"trangThaiHoSo\" IN ('DRAFT', 'PENDING_VERIFICATION', 'VERIFIED', 'NEEDS_UPDATE')",
    )
    op.create_check_constraint(
        "ck_ChuyenGia_soNamKinhNghiem",
        "ChuyenGia",
        '"soNamKinhNghiem" IS NULL OR ("soNamKinhNghiem" >= 0 AND "soNamKinhNghiem" <= 60)',
    )
    op.create_index("ix_ChuyenGia_trangThaiHoSo", "ChuyenGia", ["trangThaiHoSo"])

    # 6. Idempotently seed initial specialties & N-N category mappings
    conn = op.get_bind()
    category_rows = conn.execute(
        sa.text('SELECT "maDanhMuc", "tenDanhMuc" FROM "DanhMuc"')
    ).fetchall()
    category_by_name = {
        (row[1] or "").strip().lower(): row[0] for row in category_rows if row[1]
    }

    for ten, nhom, mota, cat_names in _INITIAL_SPECIALTIES:
        conn.execute(
            sa.text(
                'INSERT INTO "ChuyenMon" ("tenChuyenMon", "nhomChuyenMon", "moTa", "trangThai") '
                "VALUES (:ten, :nhom, :mota, 'ACTIVE') "
                'ON CONFLICT DO NOTHING'
            ),
            {"ten": ten, "nhom": nhom, "mota": mota},
        )
        spec_id = conn.execute(
            sa.text(
                'SELECT "maChuyenMon" FROM "ChuyenMon" '
                'WHERE lower(btrim("tenChuyenMon")) = lower(btrim(:ten))'
            ),
            {"ten": ten},
        ).scalar()
        if spec_id is None:
            continue
        for cat_name in cat_names:
            cat_id = category_by_name.get(cat_name.strip().lower())
            if cat_id is not None:
                conn.execute(
                    sa.text(
                        'INSERT INTO "ChuyenMonDanhMuc" ("maChuyenMon", "maDanhMuc") '
                        "VALUES (:spec_id, :cat_id) "
                        "ON CONFLICT DO NOTHING"
                    ),
                    {"spec_id": spec_id, "cat_id": cat_id},
                )


def downgrade() -> None:
    op.drop_index("ix_ChuyenGia_trangThaiHoSo", table_name="ChuyenGia")
    op.drop_constraint("ck_ChuyenGia_soNamKinhNghiem", "ChuyenGia", type_="check")
    op.drop_constraint("ck_ChuyenGia_trangThaiHoSo", "ChuyenGia", type_="check")
    op.drop_column("ChuyenGia", "ngayCapNhat")
    op.drop_column("ChuyenGia", "ngayXacMinh")
    op.drop_column("ChuyenGia", "maNguoiXacMinh")
    op.drop_column("ChuyenGia", "ghiChuXacMinh")
    op.drop_column("ChuyenGia", "trangThaiHoSo")
    op.drop_column("ChuyenGia", "soNamKinhNghiem")

    op.drop_index("ix_ChuyenGiaChuyenMon_maChuyenMon", table_name="ChuyenGiaChuyenMon")
    op.execute("DROP INDEX IF EXISTS uq_chuyengia_chuyenmon_chinh")
    op.drop_table("ChuyenGiaChuyenMon")

    op.drop_index("ix_ChuyenMonDanhMuc_maDanhMuc", table_name="ChuyenMonDanhMuc")
    op.drop_table("ChuyenMonDanhMuc")

    op.drop_index("ix_ChuyenMon_trangThai", table_name="ChuyenMon")
    op.drop_index("ix_ChuyenMon_nhomChuyenMon", table_name="ChuyenMon")
    op.execute("DROP INDEX IF EXISTS uq_chuyenmon_ten_normalized")
    op.drop_table("ChuyenMon")

    op.drop_column("NguoiDung", "batBuocDoiMatKhau")
