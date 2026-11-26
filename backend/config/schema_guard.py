"""GĐ4.7A.2 Fail-Closed Startup Schema Compatibility Guard.

Prevents the GĐ4 Backend from silently booting against an unmigrated database
(missing either the 5 DangKyKhoaHoc columns from d4e5f6a7b8c9 or the 5 financial
tables + 2 ThanhToan columns from e5f6a7b8c9d0).
"""
from __future__ import annotations

from sqlalchemy import text
from sqlalchemy.engine import Engine

REQUIRED_ORM_COLUMNS: tuple[tuple[str, str], ...] = (
    ("DangKyKhoaHoc", "maDonHang"),
    ("DangKyKhoaHoc", "nguonCapQuyen"),
    ("DangKyKhoaHoc", "trangThaiQuyenHoc"),
    ("DangKyKhoaHoc", "ngayThuHoi"),
    ("DangKyKhoaHoc", "lyDoThuHoi"),
    ("ThanhToan", "daThuTien"),
    ("ThanhToan", "soTienDaThuThucTe"),
)

REQUIRED_MARKETPLACE_TABLES: tuple[str, ...] = (
    "YeuThich",
    "GioHang",
    "ChiTietGioHang",
    "DonHang",
    "ChiTietDonHang",
    "ThanhToan",
)

REQUIRED_FINANCIAL_TABLES: tuple[str, ...] = (
    "HoanTienNgoaiLe",
    "LanThuHoanTien",
    "BaoCaoSuCoThanhToan",
    "SuKienThanhToan",
    "TacVuDoiSoatThanhToan",
)

REQUIRED_ALEMBIC_REVISION = "e5f6a7b8c9d0"


class SchemaCompatibilityError(RuntimeError):
    """Raised when the connected PostgreSQL database schema is incompatible with the Backend ORM."""


def verify_database_schema_compatibility(
    engine: Engine,
    *,
    require_marketplace_tables: bool = False,
) -> dict[str, object]:
    """Verify required ORM columns and financial tables exist.

    Raises SchemaCompatibilityError (fail-closed) if any required column/table is missing.
    """
    with engine.connect() as conn:
        current_db = str(conn.execute(text("SELECT current_database()")).scalar_one() or "")
        col_rows = conn.execute(
            text(
                """
                SELECT table_name, column_name
                FROM information_schema.columns
                WHERE table_schema = 'public'
                  AND table_name IN ('DangKyKhoaHoc', 'ThanhToan')
                """
            )
        ).fetchall()
        present_cols = {(str(r[0]), str(r[1])) for r in col_rows}

        tbl_rows = conn.execute(
            text(
                """
                SELECT table_name
                FROM information_schema.tables
                WHERE table_schema = 'public'
                  AND table_type = 'BASE TABLE'
                """
            )
        ).fetchall()
        present_tables = {str(r[0]) for r in tbl_rows}

    missing_cols = [
        f"{tbl}.{col}" for tbl, col in REQUIRED_ORM_COLUMNS if (tbl, col) not in present_cols
    ]
    missing_marketplace = [
        tbl for tbl in REQUIRED_MARKETPLACE_TABLES if tbl not in present_tables
    ]
    missing_financial = [
        tbl for tbl in REQUIRED_FINANCIAL_TABLES if tbl not in present_tables
    ]

    if missing_cols or missing_financial:
        raise SchemaCompatibilityError(
            f"Database '{current_db}' is incompatible with GĐ4.7A.2 Financial Integrity Backend "
            f"(required revision {REQUIRED_ALEMBIC_REVISION}). Missing columns: {missing_cols}; "
            f"missing financial tables: {missing_financial}. Run 'alembic upgrade head' BEFORE starting."
        )

    if require_marketplace_tables and missing_marketplace:
        raise SchemaCompatibilityError(
            f"Database '{current_db}' has COMMERCE_ENROLLMENT_GATE_ENABLED=True but is missing "
            f"Marketplace tables {missing_marketplace}."
        )

    return {
        "database": current_db,
        "compatible": True,
        "requiredRevision": REQUIRED_ALEMBIC_REVISION,
        "marketplaceTablesPresent": len(missing_marketplace) == 0,
        "financialTablesPresent": len(missing_financial) == 0,
    }
