"""
EduSuggest GĐ5.1 — Safe Production Cover Apply & Rollback Tool.

DO NOT RUN WITH --confirm-apply UNTIL USER EXPLICITLY APPROVES THE NEW COVER SET!
- Copies verified 1280x720 WebP covers into media/courses/ (NEVER deletes old covers).
- Updates ONLY KhoaHoc.hinhAnh in the target database using course-cover-manifest.json.
- Supports --dry-run, --confirm-apply, and --rollback (using rollback-manifest.json).
"""

from __future__ import annotations

import argparse
import json
import shutil
import sys
from pathlib import Path

from sqlalchemy import create_engine, text

PROJECT_ROOT = Path(r"D:\đồ án\EduSuggest")
BACKEND_ROOT = PROJECT_ROOT / "backend"
STAGING_ROOT = PROJECT_ROOT / "media" / "phase5-covers-staging"
COVERS_DIR = STAGING_ROOT / "covers"
PROD_MEDIA_DIR = PROJECT_ROOT / "media" / "courses"
VERSIONED_SUBDIR = "v5-realistic"
PROD_VERSIONED_DIR = PROD_MEDIA_DIR / VERSIONED_SUBDIR
MANIFEST_PATH = STAGING_ROOT / "course-cover-manifest.json"
ROLLBACK_PATH = STAGING_ROOT / "rollback-manifest.json"

sys.path.insert(0, str(BACKEND_ROOT))
from config.config import get_settings  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(description="Apply or rollback GĐ5.1 course covers safely.")
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--dry-run", action="store_true", help="Verify files & print planned DB updates without writing")
    mode.add_argument("--confirm-apply", action="store_true", help="Copy WebP covers (keeping old covers) and update DB")
    mode.add_argument("--rollback", action="store_true", help="Restore original KhoaHoc.hinhAnh paths from rollback-manifest.json")
    args = parser.parse_args()

    eng = create_engine(get_settings().database_url.get_secret_value())

    if args.rollback:
        rb = json.loads(ROLLBACK_PATH.read_text(encoding="utf-8"))
        entries = rb["entries"]
        with eng.begin() as conn:
            db_name = conn.execute(text("SELECT current_database()")).scalar_one()
            for e in entries:
                conn.execute(
                    text('UPDATE "KhoaHoc" SET "hinhAnh" = :p WHERE "maKhoaHoc" = :cid'),
                    {"p": e["original_db_path"], "cid": e["course_id"]},
                )
        print(f"ROLLBACK COMPLETE on '{db_name}': restored {len(entries)} original cover paths.")
        return 0

    manifest = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
    entries = [e for e in manifest["entries"] if e.get("status") == "VERIFIED"]
    missing = [e["local_filename"] for e in entries if not (COVERS_DIR / e["local_filename"]).is_file()]
    if missing:
        print(f"ABORT: {len(missing)} cover files missing: {missing[:5]}")
        return 1

    if args.dry_run:
        with eng.connect() as conn:
            db_name = conn.execute(text("SELECT current_database()")).scalar_one()
        print(f"DRY RUN on '{db_name}': {len(entries)} verified WebP covers ready to apply (0 missing). Old covers preserved.")
        return 0

    # --confirm-apply: copy to versioned directory (NEVER overwrite or delete old SVG/JPG covers!)
    PROD_VERSIONED_DIR.mkdir(parents=True, exist_ok=True)
    for e in entries:
        dst = PROD_VERSIONED_DIR / e["local_filename"]
        shutil.copy2(COVERS_DIR / e["local_filename"], dst)

    # Verify all 120 physical files exist before touching DB transaction
    missing_dst = [e["local_filename"] for e in entries if not (PROD_VERSIONED_DIR / e["local_filename"]).is_file()]
    if missing_dst:
        print(f"ABORT BEFORE DB COMMIT: {len(missing_dst)} versioned files missing.")
        return 1

    with eng.begin() as conn:
        db_name = conn.execute(text("SELECT current_database()")).scalar_one()
        for e in entries:
            conn.execute(
                text('UPDATE "KhoaHoc" SET "hinhAnh" = :p WHERE "maKhoaHoc" = :cid'),
                {"p": f"/media/courses/{VERSIONED_SUBDIR}/{e['local_filename']}", "cid": e["course_id"]},
            )
    print(f"APPLY COMPLETE on '{db_name}': updated {len(entries)} courses -> /media/courses/{VERSIONED_SUBDIR}/*.webp (old 119 SVG + 1 JPG preserved).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
