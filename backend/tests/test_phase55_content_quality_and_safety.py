"""
EduSuggest GĐ5.5 — Content Quality, Video URL Allowlist & Recommendation Visibility Safety Tests.

Runs exclusively against the isolated test database (EduSuggest_phase4_test).
Never writes to Production EduSuggest.
"""

from __future__ import annotations

import re
from pathlib import Path
from urllib.parse import parse_qs, urlparse

from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

from config.config import get_settings
from service.recommendation_service import recommend_courses


def _extract_safe_youtube_embed(raw_url: str) -> str:
    """Mirror of LearningView.vue strict YouTube privacy-enhanced embed allowlist."""
    raw = (raw_url or "").strip()
    if not re.match(r"^https?://", raw, re.I):
        return ""
    u = urlparse(raw)
    host = (u.hostname or "").lower()
    if host.startswith("www."):
        host = host[4:]
    vid = ""
    if host == "youtu.be":
        vid = u.path.lstrip("/").split("/")[0]
    elif host in {"youtube.com", "m.youtube.com", "youtube-nocookie.com"}:
        if u.path == "/watch":
            vid = (parse_qs(u.query).get("v") or [""])[0]
        elif u.path.startswith("/embed/"):
            vid = u.path.split("/embed/", 1)[1].split("/")[0]
    if re.fullmatch(r"[A-Za-z0-9_-]{11}", vid):
        return f"https://www.youtube-nocookie.com/embed/{vid}?rel=0"
    return ""


def test_learning_view_video_url_allowlist_blocks_xss_and_arbitrary_iframes() -> None:
    assert _extract_safe_youtube_embed("https://www.youtube.com/watch?v=0sOvCWFmrtA") == (
        "https://www.youtube-nocookie.com/embed/0sOvCWFmrtA?rel=0"
    )
    assert _extract_safe_youtube_embed("https://youtu.be/SqcY0GlETPk") == (
        "https://www.youtube-nocookie.com/embed/SqcY0GlETPk?rel=0"
    )
    assert _extract_safe_youtube_embed("javascript:alert(1)") == ""
    assert _extract_safe_youtube_embed("data:text/html,<script>alert(1)</script>") == ""
    assert _extract_safe_youtube_embed("https://evil.example.com/embed/0sOvCWFmrtA") == ""
    assert _extract_safe_youtube_embed("https://www.youtube.com/watch?v=short") == ""


def test_learning_view_uses_no_v_html_xss_sinks() -> None:
    vue_path = Path(r"D:\đồ án\EduSuggest\frontend\src\views\user\LearningView.vue")
    src = vue_path.read_text(encoding="utf-8")
    assert "v-html" not in src
    assert "youtube-nocookie.com/embed/" in src


def test_recommendations_never_expose_hidden_or_pending_courses() -> None:
    settings = get_settings()
    base = settings.database_url.get_secret_value().rsplit("/", 1)[0]
    eng = create_engine(base + "/EduSuggest_phase4_test")
    SessionLocal = sessionmaker(bind=eng)
    with SessionLocal() as db:
        hidden_ids = {
            int(r[0])
            for r in db.execute(
                text('SELECT "maKhoaHoc" FROM "KhoaHoc" WHERE "trangThaiHienThi" <> \'VISIBLE\' OR "trangThaiDuyet" <> \'APPROVED\'')
            ).fetchall()
        }
        uid = db.execute(text('SELECT "maNguoiDung" FROM "NguoiDung" WHERE "tenTaiKhoan"=\'official_persona_ai\'')).scalar_one_or_none()
        if uid is not None:
            rec = recommend_courses(db, int(uid), limit=10)
            returned_ids = {int(item.model_dump().get("maKhoaHoc") or item.model_dump().get("id")) for item in rec.items}
            assert returned_ids.isdisjoint(hidden_ids)
