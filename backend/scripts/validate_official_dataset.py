"""Validate database integrity, assets and real recommendation outputs."""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parents[1]
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

from sqlalchemy import func, select, text
from sqlalchemy.orm import Session

from models import (
    BaiHoc,
    ChuyenGia,
    ChuyenMon,
    DangKyKhoaHoc,
    DanhMuc,
    KhoaHoc,
    LichSuHocTap,
    NguoiDung,
    NhaCungCapKhoaHoc,
    TaiLieu,
)
from scripts.official_dataset_common import (
    DATASET_STAGING_DATABASE,
    PRODUCTION_DATABASE,
    REPORT_DIR,
    assert_database_target,
    create_database_engine,
    write_json,
)
from scripts.import_official_dataset import DEFAULT_MEDIA_DIR, DEFAULT_PRIVATE_ROOT
from service.recommendation_service import (
    recommend_courses,
    recommend_standalone_materials,
)

OUTPUT = REPORT_DIR / "dataset-validation.json"


def _duplicate_count(db: Session, table: str, column: str) -> int:
    statement = text(
        f'SELECT count(*) FROM (SELECT "{column}" FROM "{table}" '
        f'WHERE "{column}" IS NOT NULL GROUP BY "{column}" HAVING count(*) > 1) duplicate_rows'
    )
    return int(db.execute(statement).scalar_one())


def validate(db: Session, media_dir: Path, private_root: Path, target_database: str = DATASET_STAGING_DATABASE) -> dict:
    assert_database_target(db.connection(), expected_database=target_database)
    checks: dict[str, object] = {}
    failures: list[str] = []

    model_counts = {
        model.__tablename__: int(db.scalar(select(func.count()).select_from(model)) or 0)
        for model in (
            NguoiDung,
            NhaCungCapKhoaHoc,
            DanhMuc,
            KhoaHoc,
            BaiHoc,
            TaiLieu,
            ChuyenMon,
            ChuyenGia,
            DangKyKhoaHoc,
            LichSuHocTap,
        )
    }
    checks["record_counts"] = model_counts
    minimums = {
        "DanhMuc": 24,
        "KhoaHoc": 120,
        "ChuyenMon": 30,
        "ChuyenGia": 20,
        "NhaCungCapKhoaHoc": 8,
        "DangKyKhoaHoc": 150,
        "LichSuHocTap": 300,
    }
    for table, minimum in minimums.items():
        if model_counts[table] < minimum:
            failures.append(f"{table} has {model_counts[table]}, expected at least {minimum}")

    duplicates = {
        "usernames": _duplicate_count(db, "NguoiDung", "tenTaiKhoan"),
        "category_names": _duplicate_count(db, "DanhMuc", "tenDanhMuc"),
        "course_titles": _duplicate_count(db, "KhoaHoc", "tieuDe"),
        "specialty_names": _duplicate_count(db, "ChuyenMon", "tenChuyenMon"),
    }
    checks["duplicates"] = duplicates
    for name, count in duplicates.items():
        if count:
            failures.append(f"Duplicate {name}: {count}")

    # PostgreSQL itself validates all declared FKs; these targeted orphan checks
    # make the report explicit for the entities central to this dataset.
    orphan_queries = {
        "courses_without_category": 'SELECT count(*) FROM "KhoaHoc" c LEFT JOIN "DanhMuc" d ON d."maDanhMuc"=c."maDanhMuc" WHERE c."maDanhMuc" IS NOT NULL AND d."maDanhMuc" IS NULL',
        "courses_without_provider": 'SELECT count(*) FROM "KhoaHoc" c LEFT JOIN "NhaCungCapKhoaHoc" p ON p."maNhaCungCap"=c."maNhaCungCap" WHERE c."maNhaCungCap" IS NOT NULL AND p."maNhaCungCap" IS NULL',
        "lessons_without_course": 'SELECT count(*) FROM "BaiHoc" l LEFT JOIN "KhoaHoc" c ON c."maKhoaHoc"=l."maKhoaHoc" WHERE l."maKhoaHoc" IS NOT NULL AND c."maKhoaHoc" IS NULL',
        "materials_without_course": 'SELECT count(*) FROM "TaiLieu" m LEFT JOIN "KhoaHoc" c ON c."maKhoaHoc"=m."maKhoaHoc" WHERE m."maKhoaHoc" IS NOT NULL AND c."maKhoaHoc" IS NULL',
        "enrollments_without_user_or_course": 'SELECT count(*) FROM "DangKyKhoaHoc" e LEFT JOIN "NguoiDung" u ON u."maNguoiDung"=e."maNguoiDung" LEFT JOIN "KhoaHoc" c ON c."maKhoaHoc"=e."maKhoaHoc" WHERE u."maNguoiDung" IS NULL OR c."maKhoaHoc" IS NULL',
        "history_without_user_or_course": 'SELECT count(*) FROM "LichSuHocTap" h LEFT JOIN "NguoiDung" u ON u."maNguoiDung"=h."maNguoiDung" LEFT JOIN "KhoaHoc" c ON c."maKhoaHoc"=h."maKhoaHoc" WHERE u."maNguoiDung" IS NULL OR c."maKhoaHoc" IS NULL',
    }
    orphans = {name: int(db.execute(text(query)).scalar_one()) for name, query in orphan_queries.items()}
    checks["orphans"] = orphans
    for name, count in orphans.items():
        if count:
            failures.append(f"{name}: {count}")

    courses = db.scalars(select(KhoaHoc)).all()
    missing_cover_reference = [course.maKhoaHoc for course in courses if not course.hinhAnh]
    missing_cover_files = []
    external_cover_urls = []
    for course in courses:
        if not course.hinhAnh:
            continue
        if course.hinhAnh.startswith("/media/courses/"):
            candidate = media_dir / Path(course.hinhAnh).name
            if not candidate.is_file() or candidate.stat().st_size == 0:
                missing_cover_files.append(course.maKhoaHoc)
        else:
            external_cover_urls.append(course.maKhoaHoc)
    checks["covers"] = {
        "total_courses": len(courses),
        "missing_reference": missing_cover_reference,
        "missing_local_file": missing_cover_files,
        "external_reference_count": len(external_cover_urls),
    }
    if missing_cover_reference or missing_cover_files:
        failures.append("One or more course covers are missing")

    materials = db.scalars(select(TaiLieu)).all()
    missing_private_files = []
    invalid_references = []
    objects_dir = private_root / target_database / "materials"
    for material in materials:
        reference = material.duongDanTep or ""
        if reference.startswith("private://materials/"):
            object_id = reference.removeprefix("private://materials/")
            if not (objects_dir / f"{object_id}.bin").is_file() or not (objects_dir / f"{object_id}.json").is_file():
                missing_private_files.append(material.maTaiLieu)
        elif reference and not reference.lower().startswith(("http://", "https://")):
            invalid_references.append(material.maTaiLieu)
    checks["materials"] = {
        "total": len(materials),
        "missing_private_files": missing_private_files,
        "invalid_references": invalid_references,
    }
    if missing_private_files or invalid_references:
        failures.append("One or more material references are invalid")

    recommendation_results = {}
    persona_users = db.scalars(select(NguoiDung).where(NguoiDung.tenTaiKhoan.like("official_persona_%")).order_by(NguoiDung.tenTaiKhoan)).all()
    for user in persona_users:
        response = recommend_courses(db, user.maNguoiDung, 5)
        materials_response = recommend_standalone_materials(db, user.maNguoiDung, 5)
        recommendation_results[user.tenTaiKhoan] = {
            "strategy": response.strategy,
            "personalized": response.personalized,
            "courses": [item.model_dump(mode="json") for item in response.items],
            "materials": [item.model_dump(mode="json") for item in materials_response.items],
        }
        enrolled_ids = set(db.scalars(select(DangKyKhoaHoc.maKhoaHoc).where(DangKyKhoaHoc.maNguoiDung == user.maNguoiDung)).all())
        if enrolled_ids.intersection({item.maKhoaHoc for item in response.items}):
            failures.append(f"Recommendation leaked an enrolled course for {user.tenTaiKhoan}")
        if any(not item.hinhAnh for item in response.items):
            failures.append(f"Recommendation omitted a cover for {user.tenTaiKhoan}")
    checks["recommendations"] = recommendation_results
    if len(recommendation_results) < 8:
        failures.append(f"Only {len(recommendation_results)} recommendation personas were found")
    personalized_sets = {
        tuple(item["maKhoaHoc"] for item in result["courses"])
        for username, result in recommendation_results.items()
        if username != "official_persona_new"
    }
    if len(personalized_sets) < 3:
        failures.append("Persona recommendations are insufficiently differentiated")

    checks["failures"] = failures
    checks["status"] = "PASS" if not failures else "FAIL"
    return checks


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--database", default=DATASET_STAGING_DATABASE)
    parser.add_argument("--course-media-dir", type=Path, default=DEFAULT_MEDIA_DIR)
    parser.add_argument("--private-storage-root", type=Path, default=DEFAULT_PRIVATE_ROOT)
    parser.add_argument("--output", type=Path, default=OUTPUT)
    args = parser.parse_args()
    if args.database not in (DATASET_STAGING_DATABASE, PRODUCTION_DATABASE):
        raise SystemExit("Validation is restricted to EduSuggest_dataset_staging or EduSuggest")
    engine = create_database_engine(args.database)
    try:
        with Session(engine) as db:
            result = validate(db, args.course_media_dir.resolve(), args.private_storage_root.resolve(), args.database)
    finally:
        engine.dispose()
    write_json(args.output, result)
    print(json.dumps({"status": result["status"], "failures": result["failures"], "record_counts": result["record_counts"]}, ensure_ascii=False, indent=2))
    print(f"Full validation report: {args.output}")
    if result["status"] != "PASS":
        raise SystemExit(1)


if __name__ == "__main__":
    main()
