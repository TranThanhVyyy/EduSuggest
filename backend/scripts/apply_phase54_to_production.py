"""
EduSuggest GĐ5.5 — Official Production Apply for Verified GĐ5.4 Learning Content.

SAFETY:
- Verifies current_database() == 'EduSuggest', 35 tables, revision e5f6a7b8c9d0.
- Checks OLD value on Production BEFORE every single lesson update (conflict guard).
- Updates ONLY BaiHoc.noiDung and BaiHoc.duongDanVideo for the 346 verified lessons
  from edusuggest_phase54_staging in a single atomic transaction.
- Never changes Course IDs, Lesson IDs, Material IDs, approval/visibility flags,
  enrollments, learning history, or financial tables.
- Supports --dry-run, --confirm-apply, and --rollback.
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

from sqlalchemy import create_engine, text

PROJECT_ROOT = Path(r"D:\đồ án\EduSuggest")
BACKEND_ROOT = PROJECT_ROOT / "backend"
BACKUP_ROLLBACK_PATH = PROJECT_ROOT / "backend" / "database" / "backups" / "phase55-content-deploy" / "20261127" / "prod-phase54-rollback.json"

sys.path.insert(0, str(BACKEND_ROOT))
from config.config import get_settings  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(description="Apply verified GĐ5.4 learning content to Production EduSuggest.")
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--dry-run", action="store_true")
    mode.add_argument("--confirm-apply", action="store_true")
    mode.add_argument("--rollback", action="store_true")
    args = parser.parse_args()

    prod_url = get_settings().database_url.get_secret_value()
    stg_url = prod_url.rsplit("/", 1)[0] + "/edusuggest_phase54_staging"
    prod_eng = create_engine(prod_url)
    stg_eng = create_engine(stg_url)

    with prod_eng.connect() as conn:
        cur_db = str(conn.execute(text("SELECT current_database()")).scalar_one())
        rev = str(conn.execute(text("SELECT version_num FROM alembic_version")).scalar_one())
        tbls = int(conn.execute(text("SELECT count(*) FROM information_schema.tables WHERE table_schema='public'")).scalar_one())
        if cur_db != "EduSuggest" or rev != "e5f6a7b8c9d0" or tbls != 35:
            print(f"ABORT: unexpected Production state db={cur_db} rev={rev} tables={tbls}")
            return 1

    if args.rollback:
        rb = json.loads(BACKUP_ROLLBACK_PATH.read_text(encoding="utf-8"))
        with prod_eng.begin() as conn:
            for item in rb["lessons"]:
                conn.execute(
                    text('UPDATE "BaiHoc" SET "noiDung"=:c, "duongDanVideo"=:v WHERE "maBaiHoc"=:id'),
                    {"c": item["old_content"], "v": item["old_video_url"], "id": item["lesson_id"]},
                )
        print(f"PRODUCTION ROLLBACK COMPLETE: restored {len(rb['lessons'])} lessons.")
        return 0

    diff_meta = json.loads((PROJECT_ROOT / "docs" / "reports" / "learning-content-diff.json").read_text(encoding="utf-8"))
    rb_staging = json.loads((PROJECT_ROOT / "docs" / "reports" / "learning-content-rollback-manifest.json").read_text(encoding="utf-8"))
    expected_old = {int(x["lesson_id"]): (x["old_content"], x["old_video_url"]) for x in rb_staging["lessons"]}
    target_ids = sorted(expected_old.keys())

    with stg_eng.connect() as sconn:
        stg_rows = {
            int(r[0]): (r[1], r[2])
            for r in sconn.execute(text('SELECT "maBaiHoc", "noiDung", "duongDanVideo" FROM "BaiHoc"')).fetchall()
        }

    with prod_eng.connect() as pconn:
        prod_rows = {
            int(r[0]): ((r[1] or "").strip(), (r[2] or "").strip() or None)
            for r in pconn.execute(text('SELECT "maBaiHoc", "noiDung", "duongDanVideo" FROM "BaiHoc"')).fetchall()
        }

    conflicts = []
    to_apply = []
    for lid in target_ids:
        if lid not in prod_rows or lid not in stg_rows:
            conflicts.append({"lesson_id": lid, "reason": "MISSING_ROW"})
            continue
        p_content, p_vid = prod_rows[lid]
        exp_content, exp_vid = expected_old[lid]
        if p_content != (exp_content or "").strip() or p_vid != ((exp_vid or "").strip() or None):
            conflicts.append({"lesson_id": lid, "reason": "CONCURRENT_MODIFICATION"})
            continue
        new_content, new_vid = stg_rows[lid]
        to_apply.append({
            "lesson_id": lid,
            "old_content": p_content,
            "old_video_url": p_vid,
            "new_content": new_content,
            "new_video_url": new_vid,
        })

    if args.dry_run:
        print(json.dumps({
            "mode": "DRY_RUN_PRODUCTION",
            "db": cur_db,
            "rev": rev,
            "tables": tbls,
            "expected_changes": len(diff_meta["changes"]),
            "ready_to_apply": len(to_apply),
            "conflicts": len(conflicts),
        }, ensure_ascii=False, indent=2))
        return 0 if not conflicts else 2

    if conflicts:
        print(f"ABORT: {len(conflicts)} conflict(s) detected on Production! {conflicts[:5]}")
        return 2

    BACKUP_ROLLBACK_PATH.parent.mkdir(parents=True, exist_ok=True)
    BACKUP_ROLLBACK_PATH.write_text(json.dumps({
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "db": cur_db,
        "lessons": [
            {"lesson_id": x["lesson_id"], "old_content": x["old_content"], "old_video_url": x["old_video_url"]}
            for x in to_apply
        ],
    }, ensure_ascii=False, indent=2), encoding="utf-8")

    with prod_eng.begin() as conn:
        for item in to_apply:
            conn.execute(
                text('UPDATE "BaiHoc" SET "noiDung"=:c, "duongDanVideo"=:v WHERE "maBaiHoc"=:id'),
                {"c": item["new_content"], "v": item["new_video_url"], "id": item["lesson_id"]},
            )
        total_lessons = conn.execute(text('SELECT count(*) FROM "BaiHoc"')).scalar_one()
        valid_vids = conn.execute(text('SELECT count(*) FROM "BaiHoc" WHERE "duongDanVideo" IS NOT NULL AND "duongDanVideo" <> \'\'')).scalar_one()

    print(json.dumps({
        "status": "PRODUCTION_CONTENT_APPLIED_OK",
        "db": cur_db,
        "updated_lessons": len(to_apply),
        "total_lessons": total_lessons,
        "valid_video_lessons": valid_vids,
        "rollback_manifest": str(BACKUP_ROLLBACK_PATH),
    }, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
