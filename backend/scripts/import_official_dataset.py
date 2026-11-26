"""Idempotently import the reviewed official dataset into dataset staging only.

The command cannot target EduSuggest or EduSuggest_phase3_test.  It verifies
``current_database()`` and Alembic revision on the same connection immediately
before every transaction.  ``--dry-run`` executes all ORM work then rolls back
and never writes media/private files.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import secrets
import shutil
import stat
import sys
from datetime import UTC, datetime
from decimal import Decimal
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parents[1]
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))
os.environ["DEBUG"] = "False"
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from models import (
    BaiHoc,
    ChuyenGia,
    ChuyenGiaChuyenMon,
    ChuyenMon,
    ChuyenMonDanhMuc,
    DangKyKhoaHoc,
    DanhMuc,
    KhoaHoc,
    LichSuHocTap,
    NguoiDung,
    NhaCungCapKhoaHoc,
    TaiLieu,
    ThongBao,
    VaiTro,
)
from scripts.official_dataset_common import (
    COVER_DIR,
    DATASET_MANIFEST,
    DATASET_STAGING_DATABASE,
    MATERIAL_DIR,
    PRODUCTION_DATABASE,
    PROJECT_DIR,
    assert_database_target,
    create_database_engine,
    write_json,
)
from scripts.prepare_official_dataset import make_svg
from utils.security import hash_password

RUNTIME_DIR = BACKEND_DIR / "logs" / "official-dataset"
CREDENTIALS_FILE = RUNTIME_DIR / "demo-credentials.json"
IMPORT_REPORT = RUNTIME_DIR / "last-import.json"
DEFAULT_MEDIA_DIR = PROJECT_DIR / "media" / "dataset-staging" / "courses"
DEFAULT_PRIVATE_ROOT = BACKEND_DIR / "private_storage"
INTERNAL_SCHEME = "private://materials/"

CATEGORY_ALIASES = {
    "Lập trình Web Frontend": "Web Frontend",
    "Lập trình Web Backend": "Web Backend",
    "Phát triển ứng dụng Di động": "Lập trình Mobile",
    "Khoa học dữ liệu & Machine Learning": "Khoa học dữ liệu",
    "DevOps & Điện toán đám mây": "DevOps & CI/CD",
    "An toàn thông tin & Bảo mật ứng dụng": "An toàn thông tin",
    "Công nghệ phần mềm & Đảm bảo chất lượng": "Kiểm thử phần mềm & QA",
}


def load_dataset(path: Path) -> dict:
    data = json.loads(path.read_text(encoding="utf-8"))
    if data.get("dataset_id") != "edusuggest-official-v1":
        raise RuntimeError("Unsupported or missing official dataset_id")
    return data


def _demo_password(dry_run: bool) -> str:
    if CREDENTIALS_FILE.exists():
        return json.loads(CREDENTIALS_FILE.read_text(encoding="utf-8"))[
            "shared_password"
        ]
    if dry_run:
        return "DryRun-Only!2026"
    RUNTIME_DIR.mkdir(parents=True, exist_ok=True)
    password = "Edu-" + secrets.token_urlsafe(15) + "!"
    write_json(
        CREDENTIALS_FILE,
        {
            "warning": "LOCAL SECRET - do not commit or publish",
            "database": DATASET_STAGING_DATABASE,
            "shared_password": password,
            "created_at": datetime.now(UTC).isoformat(),
        },
    )
    try:
        CREDENTIALS_FILE.chmod(stat.S_IREAD | stat.S_IWRITE)
    except OSError:
        pass
    return password


def _role_map(db: Session) -> dict[str, VaiTro]:
    roles = {str(row.tenVaiTro): row for row in db.scalars(select(VaiTro)).all()}
    missing = {"ADMIN", "PROVIDER", "EXPERT", "USER"} - roles.keys()
    if missing:
        raise RuntimeError(f"Missing required roles: {sorted(missing)}")
    return roles


def _ensure_user(
    db: Session,
    *,
    username: str,
    display_name: str,
    role: VaiTro,
    password_hash: str,
) -> tuple[NguoiDung, bool]:
    user = db.scalar(
        select(NguoiDung).where(NguoiDung.tenTaiKhoan == username).limit(1)
    )
    if user:
        return user, False
    user = NguoiDung(
        tenTaiKhoan=username,
        hoTen=display_name,
        email=f"{username}@dataset.example.com",
        matKhau=password_hash,
        maVaiTro=role.maVaiTro,
        trangThai="ACTIVE",
        batBuocDoiMatKhau=False,
    )
    db.add(user)
    db.flush()
    return user, True


def _prepare_private_file(
    *,
    key: str,
    source: Path,
    private_root: Path,
    target_database: str,
    dry_run: bool,
    created_files: list[Path],
) -> str:
    object_id = hashlib.sha256(f"edusuggest-official-v1:{key}".encode()).hexdigest()[
        :32
    ]
    reference = f"{INTERNAL_SCHEME}{object_id}"
    if dry_run:
        if not source.is_file() or source.stat().st_size == 0:
            raise RuntimeError(f"Material source is missing or empty: {source}")
        return reference
    objects_dir = (private_root / target_database / "materials").resolve()
    objects_dir.mkdir(parents=True, exist_ok=True)
    data_path = objects_dir / f"{object_id}.bin"
    metadata_path = objects_dir / f"{object_id}.json"
    if not data_path.exists():
        shutil.copyfile(source, data_path)
        created_files.append(data_path)
    expected_size = source.stat().st_size
    metadata = {
        "object_id": object_id,
        "original_name": source.name,
        "content_type": "text/plain",
        "size": expected_size,
    }
    if not metadata_path.exists():
        write_json(metadata_path, metadata)
        created_files.append(metadata_path)
    if data_path.stat().st_size != expected_size:
        raise RuntimeError(f"Private object collision for {key}")
    return reference


def _copy_cover(
    source: Path,
    destination: Path,
    *,
    dry_run: bool,
    created_files: list[Path],
) -> None:
    if not source.is_file():
        raise RuntimeError(f"Cover source is missing: {source}")
    if dry_run:
        return
    destination.parent.mkdir(parents=True, exist_ok=True)
    if not destination.exists():
        shutil.copyfile(source, destination)
        created_files.append(destination)


def _ensure_categories(db: Session, dataset: dict, stats: dict) -> dict[str, DanhMuc]:
    existing = db.scalars(select(DanhMuc).order_by(DanhMuc.maDanhMuc)).all()
    by_name = {str(row.tenDanhMuc): row for row in existing}
    for legacy, canonical in CATEGORY_ALIASES.items():
        row = by_name.get(legacy)
        canonical_row = by_name.get(canonical)
        if row and not canonical_row:
            del by_name[legacy]
            row.tenDanhMuc = canonical
            by_name[canonical] = row
            stats["categories_renamed"] += 1
    for item in dataset["categories"]:
        row = by_name.get(item["name"])
        if not row:
            row = DanhMuc(tenDanhMuc=item["name"], moTa=item["description"])
            db.add(row)
            db.flush()
            by_name[item["name"]] = row
            stats["categories_created"] += 1
        elif not row.moTa:
            row.moTa = item["description"]
    return {item["key"]: by_name[item["name"]] for item in dataset["categories"]}


def _ensure_accounts(db: Session, dataset: dict, password: str, stats: dict):
    roles = _role_map(db)
    password_hash = hash_password(password)
    providers = db.scalars(
        select(NhaCungCapKhoaHoc).order_by(NhaCungCapKhoaHoc.maNhaCungCap)
    ).all()
    for item in dataset["providers"]:
        if len(providers) >= dataset["targets"]["providers"]:
            break
        user, created = _ensure_user(
            db,
            username=item["username"],
            display_name=item["display_name"],
            role=roles["PROVIDER"],
            password_hash=password_hash,
        )
        provider = db.scalar(
            select(NhaCungCapKhoaHoc)
            .where(NhaCungCapKhoaHoc.maNguoiDung == user.maNguoiDung)
            .limit(1)
        )
        if not provider:
            provider = NhaCungCapKhoaHoc(
                maNguoiDung=user.maNguoiDung,
                tieuSu="Hồ sơ nhà cung cấp tổng hợp thuộc official dataset EduSuggest.",
                chuyenMon="Đào tạo công nghệ thông tin",
            )
            db.add(provider)
            db.flush()
            providers.append(provider)
            stats["providers_created"] += 1
        if created:
            stats["users_created"] += 1

    learners = db.scalars(
        select(NguoiDung)
        .where(NguoiDung.maVaiTro == roles["USER"].maVaiTro)
        .order_by(NguoiDung.maNguoiDung)
    ).all()
    official_learners = []
    for item in dataset["learners"]:
        existing = db.scalar(
            select(NguoiDung).where(NguoiDung.tenTaiKhoan == item["username"]).limit(1)
        )
        if existing:
            official_learners.append(existing)
            continue
        if len(learners) >= dataset["targets"]["learners"]:
            continue
        user, created = _ensure_user(
            db,
            username=item["username"],
            display_name=item["display_name"],
            role=roles["USER"],
            password_hash=password_hash,
        )
        learners.append(user)
        official_learners.append(user)
        if created:
            stats["users_created"] += 1

    experts = db.scalars(select(ChuyenGia).order_by(ChuyenGia.maChuyenGia)).all()
    official_experts = []
    admin = db.scalar(
        select(NguoiDung)
        .where(NguoiDung.maVaiTro == roles["ADMIN"].maVaiTro)
        .order_by(NguoiDung.maNguoiDung)
        .limit(1)
    )
    for item in dataset["experts"]:
        existing_user = db.scalar(
            select(NguoiDung).where(NguoiDung.tenTaiKhoan == item["username"]).limit(1)
        )
        existing_expert = (
            None
            if not existing_user
            else db.scalar(
                select(ChuyenGia)
                .where(ChuyenGia.maNguoiDung == existing_user.maNguoiDung)
                .limit(1)
            )
        )
        if existing_expert:
            official_experts.append(existing_expert)
            continue
        if len(experts) >= dataset["targets"]["experts"]:
            continue
        user, created = _ensure_user(
            db,
            username=item["username"],
            display_name=item["display_name"],
            role=roles["EXPERT"],
            password_hash=password_hash,
        )
        expert = ChuyenGia(
            maNguoiDung=user.maNguoiDung,
            chuyenMon=", ".join(item["specialties"]),
            tieuSu=item["bio"],
            soNamKinhNghiem=item["years_experience"],
            trangThaiHoSo=item["profile_status"],
            ghiChuXacMinh="Hồ sơ mô phỏng thuộc official dataset"
            if item["profile_status"] == "VERIFIED"
            else None,
            maNguoiXacMinh=admin.maNguoiDung
            if admin and item["profile_status"] == "VERIFIED"
            else None,
            ngayXacMinh=datetime.now(UTC).replace(tzinfo=None)
            if admin and item["profile_status"] == "VERIFIED"
            else None,
            ngayCapNhat=datetime.now(UTC).replace(tzinfo=None),
        )
        db.add(expert)
        db.flush()
        experts.append(expert)
        official_experts.append(expert)
        stats["experts_created"] += 1
        if created:
            stats["users_created"] += 1
    return roles, providers, official_learners, official_experts


def _ensure_specialties(
    db: Session, dataset: dict, categories: dict, experts: list[ChuyenGia], stats: dict
) -> dict[str, ChuyenMon]:
    existing = db.scalars(select(ChuyenMon).order_by(ChuyenMon.maChuyenMon)).all()
    by_name = {row.tenChuyenMon: row for row in existing}
    specialty_by_key = {}
    for item in dataset["specialties"]:
        specialty = by_name.get(item["name"])
        if not specialty and len(existing) < dataset["targets"]["specialties"]:
            specialty = ChuyenMon(
                tenChuyenMon=item["name"],
                nhomChuyenMon="OFFICIAL_DATASET",
                moTa=f"Chuyên môn tổng hợp: {item['name']}.",
                trangThai="ACTIVE",
                ngayTao=datetime.now(UTC).replace(tzinfo=None),
            )
            db.add(specialty)
            db.flush()
            existing.append(specialty)
            by_name[item["name"]] = specialty
            stats["specialties_created"] += 1
        if not specialty:
            specialty = existing[len(specialty_by_key) % len(existing)]
        specialty_by_key[item["key"]] = specialty
        for category_key in item["category_keys"]:
            category = categories[category_key]
            link = db.get(ChuyenMonDanhMuc, (specialty.maChuyenMon, category.maDanhMuc))
            if not link:
                db.add(
                    ChuyenMonDanhMuc(
                        maChuyenMon=specialty.maChuyenMon,
                        maDanhMuc=category.maDanhMuc,
                        ngayTao=datetime.now(UTC).replace(tzinfo=None),
                    )
                )
                stats["specialty_category_links_created"] += 1
    specialty_rows = list(dict.fromkeys(specialty_by_key.values()))
    for index, expert in enumerate(experts):
        for offset in (0, 7):
            specialty = specialty_rows[(index + offset) % len(specialty_rows)]
            link = db.get(
                ChuyenGiaChuyenMon, (expert.maChuyenGia, specialty.maChuyenMon)
            )
            if not link:
                db.add(
                    ChuyenGiaChuyenMon(
                        maChuyenGia=expert.maChuyenGia,
                        maChuyenMon=specialty.maChuyenMon,
                        laChuyenMonChinh=offset == 0,
                        ngayTao=datetime.now(UTC).replace(tzinfo=None),
                    )
                )
                stats["expert_specialty_links_created"] += 1
    return specialty_by_key


def _ensure_courses(
    db: Session,
    dataset: dict,
    categories: dict,
    providers: list[NhaCungCapKhoaHoc],
    media_dir: Path,
    dry_run: bool,
    created_files: list[Path],
    stats: dict,
) -> tuple[dict[str, KhoaHoc], dict[str, BaiHoc]]:
    now = datetime.now(UTC).replace(tzinfo=None)
    course_by_title = {
        str(row.tieuDe): row for row in db.scalars(select(KhoaHoc)).all()
    }
    manifest_course_map: dict[str, KhoaHoc] = {}
    lesson_map: dict[str, BaiHoc] = {}
    courses_by_category = {}
    for category_key, category in categories.items():
        courses_by_category[category_key] = list(
            db.scalars(
                select(KhoaHoc).where(KhoaHoc.maDanhMuc == category.maDanhMuc)
            ).all()
        )
    items_by_category = {}
    for item in dataset["courses"]:
        items_by_category.setdefault(item["category_key"], []).append(item)
    lesson_items = {}
    for item in dataset["lessons"]:
        lesson_items.setdefault(item["course_key"], []).append(item)

    for category_key, items in items_by_category.items():
        category = categories[category_key]
        current = courses_by_category[category_key]
        for item in items:
            course = course_by_title.get(item["title"])
            if not course and len(current) < 5:
                provider = providers[len(course_by_title) % len(providers)]
                course = KhoaHoc(
                    maNhaCungCap=provider.maNhaCungCap,
                    maDanhMuc=category.maDanhMuc,
                    tieuDe=item["title"],
                    moTa=item["description"],
                    hinhAnh=item["cover"],
                    gia=Decimal(str(item["price"])),
                    trinhDo=item["level"],
                    thoiLuong=item["duration_minutes"],
                    trangThaiDuyet=item["approval_status"],
                    trangThaiHienThi=item["visibility_status"],
                    ngayTao=now,
                    ngayCapNhat=now,
                    soVongKiemDuyetHienTai=1
                    if item["approval_status"] != "APPROVED"
                    else 0,
                )
                db.add(course)
                db.flush()
                current.append(course)
                course_by_title[item["title"]] = course
                stats["courses_created"] += 1
                cover_name = Path(item["cover"]).name
                _copy_cover(
                    COVER_DIR / cover_name,
                    media_dir / cover_name,
                    dry_run=dry_run,
                    created_files=created_files,
                )
                for lesson_item in lesson_items[item["key"]]:
                    lesson = BaiHoc(
                        maKhoaHoc=course.maKhoaHoc,
                        tieuDe=lesson_item["title"],
                        noiDung=lesson_item["content"],
                        duongDanVideo=None,
                        thoiLuong=lesson_item["duration_minutes"],
                        thuTu=lesson_item["order"],
                        ngayTao=now,
                    )
                    db.add(lesson)
                    db.flush()
                    lesson_map[lesson_item["key"]] = lesson
                    stats["lessons_created"] += 1
            if course:
                manifest_course_map[item["key"]] = course

    # Existing quality courses remain untouched except for a missing cover.  A
    # deterministic original cover is generated; no remote hotlink is introduced.
    for index, course in enumerate(
        db.scalars(select(KhoaHoc).order_by(KhoaHoc.maKhoaHoc)).all()
    ):
        if course.hinhAnh:
            continue
        filename = f"official-existing-{course.maKhoaHoc:04d}.svg"
        source = media_dir / filename
        if not dry_run and not source.exists():
            make_svg(
                1000 + index,
                course.tieuDe or "Khóa học EduSuggest",
                "EDUSUGGEST",
                source,
            )
            created_files.append(source)
        course.hinhAnh = f"/media/courses/{filename}"
        stats["existing_course_covers_created"] += 1
    return manifest_course_map, lesson_map


def _ensure_materials(
    db: Session,
    dataset: dict,
    categories: dict,
    providers: list[NhaCungCapKhoaHoc],
    courses: dict[str, KhoaHoc],
    lessons: dict[str, BaiHoc],
    private_root: Path,
    target_database: str,
    dry_run: bool,
    created_files: list[Path],
    stats: dict,
) -> None:
    now = datetime.now(UTC).replace(tzinfo=None)
    existing_titles = {str(row.tieuDe) for row in db.scalars(select(TaiLieu)).all()}
    standalone_count = (
        db.scalar(
            select(func.count(TaiLieu.maTaiLieu)).where(TaiLieu.maKhoaHoc.is_(None))
        )
        or 0
    )
    for item in dataset["materials"]:
        if item["title"] in existing_titles:
            continue
        course = courses.get(item["course_key"]) if item["course_key"] else None
        if item["course_key"] and not course:
            continue
        if not item["course_key"] and standalone_count >= 30:
            continue
        category = categories[item["category_key"]]
        provider = providers[len(existing_titles) % len(providers)]
        lesson = lessons.get(item["lesson_key"]) if item["lesson_key"] else None
        reference = _prepare_private_file(
            key=item["key"],
            source=MATERIAL_DIR / item["file"],
            private_root=private_root,
            target_database=target_database,
            dry_run=dry_run,
            created_files=created_files,
        )
        db.add(
            TaiLieu(
                maNhaCungCap=provider.maNhaCungCap,
                maKhoaHoc=course.maKhoaHoc if course else None,
                maBaiHoc=lesson.maBaiHoc if lesson else None,
                maDanhMuc=category.maDanhMuc,
                tieuDe=item["title"],
                duongDanTep=reference,
                loai=item["kind"],
                moTa=item["description"],
                trangThaiDuyet=item["approval_status"],
                trangThaiHienThi=item["visibility_status"],
                ngayTao=now,
                ngayCapNhat=now,
                soVongKiemDuyetHienTai=0
                if item["approval_status"] == "APPROVED"
                else 1,
            )
        )
        existing_titles.add(item["title"])
        if not item["course_key"]:
            standalone_count += 1
        stats["materials_created"] += 1


def _ensure_interactions(
    db: Session, dataset: dict, learners: list[NguoiDung], categories: dict, stats: dict
) -> None:
    if not learners:
        return
    cold_start = db.scalar(
        select(NguoiDung)
        .where(NguoiDung.tenTaiKhoan == "official_persona_new")
        .limit(1)
    )
    active_learners = [
        user
        for user in learners
        if not cold_start or user.maNguoiDung != cold_start.maNguoiDung
    ]
    courses = db.scalars(
        select(KhoaHoc)
        .where(
            KhoaHoc.trangThaiDuyet == "APPROVED", KhoaHoc.trangThaiHienThi == "VISIBLE"
        )
        .order_by(KhoaHoc.maDanhMuc, KhoaHoc.maKhoaHoc)
    ).all()
    existing_pairs = set(
        db.execute(select(DangKyKhoaHoc.maNguoiDung, DangKyKhoaHoc.maKhoaHoc)).all()
    )
    enrollment_total = db.scalar(select(func.count(DangKyKhoaHoc.maDangKy))) or 0
    cursor = 0
    while (
        enrollment_total < dataset["targets"]["enrollments"]
        and active_learners
        and courses
    ):
        user = active_learners[cursor % len(active_learners)]
        preferred = courses[(cursor * 7 + user.maNguoiDung) % len(courses)]
        pair = (user.maNguoiDung, preferred.maKhoaHoc)
        cursor += 1
        if pair in existing_pairs:
            if cursor > len(active_learners) * len(courses) * 2:
                break
            continue
        db.add(
            DangKyKhoaHoc(
                maNguoiDung=user.maNguoiDung,
                maKhoaHoc=preferred.maKhoaHoc,
                ngayDangKy=datetime.now(UTC).replace(tzinfo=None),
                tienDo=Decimal(0),
            )
        )
        existing_pairs.add(pair)
        enrollment_total += 1
        stats["enrollments_created"] += 1

    db.flush()
    existing_history = set(
        db.execute(
            select(LichSuHocTap.maNguoiDung, LichSuHocTap.maBaiHoc).where(
                LichSuHocTap.maBaiHoc.is_not(None)
            )
        ).all()
    )
    history_total = db.scalar(select(func.count(LichSuHocTap.maLichSu))) or 0
    enrollments = db.scalars(
        select(DangKyKhoaHoc)
        .where(DangKyKhoaHoc.maNguoiDung.in_([u.maNguoiDung for u in active_learners]))
        .order_by(DangKyKhoaHoc.maDangKy)
    ).all()
    for enrollment in enrollments:
        if history_total >= dataset["targets"]["history"]:
            break
        lessons = db.scalars(
            select(BaiHoc)
            .where(BaiHoc.maKhoaHoc == enrollment.maKhoaHoc)
            .order_by(BaiHoc.thuTu, BaiHoc.maBaiHoc)
            .limit(2)
        ).all()
        completed = 0
        for lesson in lessons:
            pair = (enrollment.maNguoiDung, lesson.maBaiHoc)
            if (
                pair in existing_history
                or history_total >= dataset["targets"]["history"]
            ):
                continue
            db.add(
                LichSuHocTap(
                    maNguoiDung=enrollment.maNguoiDung,
                    maKhoaHoc=enrollment.maKhoaHoc,
                    maBaiHoc=lesson.maBaiHoc,
                    tienDo="COMPLETED",
                    thoiGianXem=lesson.thoiLuong or 30,
                    ngayTao=datetime.now(UTC).replace(tzinfo=None),
                )
            )
            existing_history.add(pair)
            history_total += 1
            completed += 1
            stats["history_created"] += 1
        if completed:
            total_lessons = (
                db.scalar(
                    select(func.count(BaiHoc.maBaiHoc)).where(
                        BaiHoc.maKhoaHoc == enrollment.maKhoaHoc
                    )
                )
                or 1
            )
            done = (
                db.scalar(
                    select(func.count(LichSuHocTap.maLichSu)).where(
                        LichSuHocTap.maNguoiDung == enrollment.maNguoiDung,
                        LichSuHocTap.maKhoaHoc == enrollment.maKhoaHoc,
                        LichSuHocTap.tienDo == "COMPLETED",
                    )
                )
                or 0
            )
            enrollment.tienDo = Decimal(
                str(round(min(100, done * 100 / total_lessons), 2))
            )


def _ensure_notifications(
    db: Session, learners: list[NguoiDung], experts: list[ChuyenGia], stats: dict
) -> None:
    recipients = list(learners[:8])
    for expert in experts[:4]:
        if expert.nguoiDung:
            recipients.append(expert.nguoiDung)
    for index, user in enumerate(recipients):
        key = f"official-dataset-welcome-{user.maNguoiDung}"
        if db.scalar(select(ThongBao).where(ThongBao.khoaChongTrung == key).limit(1)):
            continue
        db.add(
            ThongBao(
                maNguoiNhan=user.maNguoiDung,
                loaiThongBao="SYSTEM",
                tieuDe="Dữ liệu học tập EduSuggest đã sẵn sàng",
                noiDung="Thông báo mô phỏng thuộc official dataset phục vụ trình diễn chức năng.",
                duLieuLienKet={"dataset": "edusuggest-official-v1", "synthetic": True},
                daDoc=index % 2 == 0,
                khoaChongTrung=key,
                ngayTao=datetime.now(UTC).replace(tzinfo=None),
                ngayDoc=datetime.now(UTC).replace(tzinfo=None)
                if index % 2 == 0
                else None,
            )
        )
        stats["notifications_created"] += 1


def _counts(db: Session) -> dict[str, int]:
    models = [
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
        ThongBao,
    ]
    return {
        model.__tablename__: int(
            db.scalar(select(func.count()).select_from(model)) or 0
        )
        for model in models
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", type=Path, default=DATASET_MANIFEST)
    parser.add_argument("--database", default=DATASET_STAGING_DATABASE)
    parser.add_argument("--course-media-dir", type=Path, default=DEFAULT_MEDIA_DIR)
    parser.add_argument(
        "--private-storage-root", type=Path, default=DEFAULT_PRIVATE_ROOT
    )
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--confirm-import", action="store_true")
    parser.add_argument("--confirm-production-import", action="store_true")
    args = parser.parse_args()
    if args.database == DATASET_STAGING_DATABASE:
        if not args.dry_run and not args.confirm_import:
            raise SystemExit("Use --dry-run or explicitly pass --confirm-import")
    elif args.database == PRODUCTION_DATABASE:
        if not args.dry_run and not args.confirm_production_import:
            raise SystemExit(
                "Production database EduSuggest requires --dry-run or explicit --confirm-production-import"
            )
    else:
        raise SystemExit(
            f"Refusing database {args.database!r}; only {DATASET_STAGING_DATABASE!r} or approved {PRODUCTION_DATABASE!r} is allowed"
        )
    dataset = load_dataset(args.manifest)
    password = _demo_password(args.dry_run)
    stats = {
        key: 0
        for key in (
            "categories_renamed",
            "categories_created",
            "users_created",
            "providers_created",
            "experts_created",
            "specialties_created",
            "specialty_category_links_created",
            "expert_specialty_links_created",
            "courses_created",
            "lessons_created",
            "existing_course_covers_created",
            "materials_created",
            "enrollments_created",
            "history_created",
            "notifications_created",
        )
    }
    created_files: list[Path] = []
    engine = create_database_engine(args.database)
    try:
        with Session(engine) as db:
            try:
                assert_database_target(db.connection(), expected_database=args.database)
                before = _counts(db)
                categories = _ensure_categories(db, dataset, stats)
                _roles, providers, learners, experts = _ensure_accounts(
                    db, dataset, password, stats
                )
                _ensure_specialties(db, dataset, categories, experts, stats)
                courses, lessons = _ensure_courses(
                    db,
                    dataset,
                    categories,
                    providers,
                    args.course_media_dir.resolve(),
                    args.dry_run,
                    created_files,
                    stats,
                )
                _ensure_materials(
                    db,
                    dataset,
                    categories,
                    providers,
                    courses,
                    lessons,
                    args.private_storage_root.resolve(),
                    args.database,
                    args.dry_run,
                    created_files,
                    stats,
                )
                _ensure_interactions(db, dataset, learners, categories, stats)
                _ensure_notifications(db, learners, experts, stats)
                db.flush()
                after = _counts(db)
                if args.dry_run:
                    db.rollback()
                else:
                    assert_database_target(db.connection(), expected_database=args.database)
                    db.commit()
                report = {
                    "dataset_id": dataset["dataset_id"],
                    "database": args.database,
                    "mode": "DRY_RUN" if args.dry_run else "IMPORT",
                    "completed_at": datetime.now(UTC).isoformat(),
                    "stats": stats,
                    "counts_before": before,
                    "counts_after_transaction": after,
                    "created_file_count": len(created_files),
                }
                if not args.dry_run:
                    write_json(IMPORT_REPORT, report)
                print(f"{report['mode']} completed on guarded database {args.database}")
                print(json.dumps(report, ensure_ascii=False, indent=2))
            except Exception:
                db.rollback()
                for path in reversed(created_files):
                    path.unlink(missing_ok=True)
                raise
    finally:
        engine.dispose()


if __name__ == "__main__":
    main()
