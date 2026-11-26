"""
EduSuggest GĐ5.1 — Automated Realistic Course Cover Discovery & Thumbnail Pipeline.

Features:
- Reads all 120 courses from PostgreSQL (READ ONLY) or exported snapshot JSON.
- Generates Vietnamese + English topic-aware search queries from title, category,
  description, tech keywords, level, and lesson titles.
- Discovers real, open-licensed photographs via Openverse API (modifiable licenses
  only: CC0/PDM/CC-BY/CC-BY-SA) and Wikimedia Commons API fallback.
- Enforces strict license verification, minimum resolution, watermark/clipart
  rejection, SHA-256 + 64-bit dHash perceptual deduplication across all 120 courses.
- Composites 6 distinct Editorial EdTech Modernism 1280x720 (16:9) WebP thumbnails
  using Python Pillow with native Vietnamese TrueType fonts.
- Supports --dry-run, --batch-size, --resume, --rebuild-thumbnails, --course-ids,
  disk request cache, rate limiting, exponential backoff retry, timeouts, structured
  JSONL logs, rollback manifest, provenance manifest, and attribution markdown.
"""

from __future__ import annotations

import argparse
import hashlib
import io
import json
import math
import os
import re
import sys
import time
import unicodedata
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from PIL import Image, ImageDraw, ImageEnhance, ImageFilter, ImageFont, ImageOps

# Paths
PROJECT_ROOT = Path(r"D:\đồ án\EduSuggest")
BACKEND_ROOT = PROJECT_ROOT / "backend"
STAGING_ROOT = PROJECT_ROOT / "media" / "phase5-covers-staging"
COVERS_DIR = STAGING_ROOT / "covers"
RAW_DIR = STAGING_ROOT / "raw"
CACHE_DIR = STAGING_ROOT / "cache"
REPORTS_DIR = PROJECT_ROOT / "docs" / "reports"
PROD_MEDIA_DIR = PROJECT_ROOT / "media" / "courses"

SNAPSHOT_PATH = STAGING_ROOT / "courses_120_snapshot.json"
CHECKPOINT_PATH = STAGING_ROOT / "checkpoint.json"
API_CACHE_PATH = CACHE_DIR / "api_cache.json"
LOG_PATH = STAGING_ROOT / "pipeline.jsonl"
MANIFEST_PATH = STAGING_ROOT / "course-cover-manifest.json"
ROLLBACK_PATH = STAGING_ROOT / "rollback-manifest.json"
DOCS_MANIFEST_PATH = REPORTS_DIR / "course-cover-manifest.json"
ATTRIBUTION_PATH = REPORTS_DIR / "COURSE_COVER_SOURCE_ATTRIBUTION.md"

USER_AGENT = "EduSuggestCoverPipeline/1.0 (Academic E-Learning Dataset; https://edusuggest.local)"

# Allowed modifiable open licenses (NO ND / NoDerivatives)
ALLOWED_OPENVERSE_LICENSES = {"cc0", "pdm", "by", "by-sa"}
WIKIMEDIA_ALLOWED_RE = re.compile(
    r"^(cc0|public domain|pd-|cc[- ]by(?:[- ]sa)?(?:\s+\d\.\d)?(?:\s+unported|\s+generic)?)$",
    re.I,
)
BANNED_TERMS_RE = re.compile(
    r"(shutterstock|istock|getty|dreamstime|123rf|alamy|watermark|clipart|"
    r"flag[ _]of|coat[ _]of[ _]arms|diagram|flowchart|screenshot|logo[ _]only|"
    r"signature|autograph|grave|cemetery|weapon|gun|war|military|nazi|confederate|"
    r"poster|symposium|conference|acrm|governor|senator|president|mayor|speech|"
    r"podium|hearing|committee|army|soldier|navy|police|hospital|clinical|"
    r"lighthouse|stable[ _-]?diffusion|midjourney|dall-?e|ai[ _-]?generated|"
    r"painting|illustration|vector|infographic|slide|chart[ _-]?table|roadmap|"
    r"scrum[ _-]?ritual|dummies|penguin|plush|radio|ad[ _-]?banner|sydney|"
    r"warning|floor[ _-]?tiles|bbc|7cups|flower|meadow|forest)",
    re.I,
)

# Font paths (Windows Vietnamese-safe TrueType fonts)
FONT_CANDIDATES_BOLD = [
    r"C:\Windows\Fonts\segoeuib.ttf",
    r"C:\Windows\Fonts\arialbd.ttf",
    r"C:\Windows\Fonts\calibrib.ttf",
]
FONT_CANDIDATES_SEMIBOLD = [
    r"C:\Windows\Fonts\seguisb.ttf",
    r"C:\Windows\Fonts\segoeui.ttf",
    r"C:\Windows\Fonts\arial.ttf",
]
FONT_CANDIDATES_REGULAR = [
    r"C:\Windows\Fonts\segoeui.ttf",
    r"C:\Windows\Fonts\arial.ttf",
]


def _pick_font(candidates: list[str], size: int) -> ImageFont.FreeTypeFont:
    for path in candidates:
        if os.path.isfile(path):
            return ImageFont.truetype(path, size=size)
    return ImageFont.load_default()


# 6 Distinct Editorial EdTech Visual Themes (diverse by domain cluster)
THEMES: dict[str, dict[str, Any]] = {
    "software_web": {
        "name": "Editorial Left Scrim (Navy + Teal)",
        "layout": "left_scrim",
        "bg": (15, 30, 48),
        "accent": (13, 148, 136),
        "pill_bg": (13, 148, 136, 230),
        "pill_fg": (255, 255, 255),
        "title_fg": (255, 255, 255),
        "sub_fg": (203, 213, 225),
    },
    "ai_data": {
        "name": "Bottom-Left Editorial Card (Slate + Copper)",
        "layout": "bottom_card",
        "bg": (17, 24, 39),
        "accent": (217, 119, 6),
        "pill_bg": (217, 119, 6, 235),
        "pill_fg": (255, 255, 255),
        "title_fg": (255, 255, 255),
        "sub_fg": (226, 232, 240),
    },
    "cloud_devops": {
        "name": "Diagonal Petrol Scrim (Petrol + Cyan)",
        "layout": "diagonal_scrim",
        "bg": (12, 35, 48),
        "accent": (14, 165, 164),
        "pill_bg": (14, 165, 164, 230),
        "pill_fg": (255, 255, 255),
        "title_fg": (255, 255, 255),
        "sub_fg": (207, 250, 254),
    },
    "security_iot": {
        "name": "Split Editorial Frame (Obsidian + Emerald)",
        "layout": "split_left",
        "bg": (20, 25, 35),
        "accent": (16, 185, 129),
        "pill_bg": (16, 185, 129, 230),
        "pill_fg": (15, 23, 42),
        "title_fg": (248, 250, 252),
        "sub_fg": (148, 163, 184),
    },
    "design_creative": {
        "name": "Full-Bleed Bottom Gradient (Charcoal + Terracotta)",
        "layout": "bottom_band",
        "bg": (28, 36, 48),
        "accent": (224, 109, 83),
        "pill_bg": (224, 109, 83, 235),
        "pill_fg": (255, 255, 255),
        "title_fg": (255, 255, 255),
        "sub_fg": (226, 232, 240),
    },
    "product_career": {
        "name": "Academic Lower-Third Band (Academic Navy + Gold)",
        "layout": "lower_third",
        "bg": (22, 38, 59),
        "accent": (200, 138, 46),
        "pill_bg": (200, 138, 46, 235),
        "pill_fg": (255, 255, 255),
        "title_fg": (255, 255, 255),
        "sub_fg": (219, 228, 240),
    },
}


# Clean real-photography queries (zero conference posters, zero AI-art lighthouses, zero slides)
TECH_QUERY_MAP: list[tuple[str, list[str]]] = [
    (r"\baws\b|amazon web|cloud|điện toán đám mây|azure|gcp", ["server room", "data center", "computer server", "modern office"]),
    (r"\bdocker\b|\bkubernetes\b|\bk8s\b|devops|ci/cd|terraform|ansible", ["server rack", "network cables", "computer hardware", "tech workspace"]),
    (r"\blinux\b|\bubuntu\b|bash|shell|hệ điều hành", ["coding laptop", "keyboard monitor", "computer desk", "developer workspace"]),
    (r"\bpython\b", ["coding laptop", "programming desk", "computer screen", "keyboard desk"]),
    (r"\bjava\b(?!script)", ["software developer", "coding monitor", "laptop desk", "office computer"]),
    (r"\bjavascript\b|\btypescript\b|\bnode\.?js\b", ["code monitor", "web developer", "laptop coding", "developer desk"]),
    (r"\breact\b|\bvue\b|\bnext\.?js\b|\bangular\b|frontend|html|css", ["laptop workspace", "modern desk", "computer monitor", "minimalist desk"]),
    (r"\bfastapi\b|\bspring\b|\bdjango\b|\bexpress\b|rest api|backend|microservice", ["coding monitor", "developer office", "workstation desk", "dual monitor"]),
    (r"\bsql\b|postgresql|mysql|mongodb|redis|cơ sở dữ liệu|database", ["server room", "laptop office", "computer desk", "tech monitor"]),
    (r"\bflutter\b|\bswift\b|\bkotlin\b|\bandroid\b|\bios\b|mobile|di động", ["smartphone desk", "mobile phone", "tablet laptop", "phone workspace"]),
    (r"machine learning|deep learning|pytorch|tensorflow|trí tuệ nhân tạo|\bai\b|llm|nlp|thị giác máy tính|computer vision", ["computer hardware", "microchip", "technology lab", "coding laptop", "server room"]),
    (r"data science|khoa học dữ liệu|phân tích dữ liệu|analytics|power bi|tableau|excel|big data|spark", ["laptop analytics", "office laptop", "business desk", "notebook laptop"]),
    (r"an toàn thông tin|bảo mật|cybersecurity|pentest|hacker|owasp|mạng máy tính|network|firewall", ["server room", "fiber optics", "network switch", "dark keyboard", "computer screen"]),
    (r"iot|arduino|raspberry|nhúng|embedded|robot|điện tử|vi điều khiển", ["circuit board", "microchip", "electronics", "motherboard"]),
    (r"figma|ui/ux|thiết kế giao diện|ux|đồ họa|photoshop|illustrator|thiết kế", ["creative desk", "sketchbook laptop", "studio desk", "minimalist workspace", "tablet pen"]),
    (r"game|unity|unreal|3d|blender|đồ họa máy tính", ["gaming keyboard", "computer monitor", "dark desk", "workstation"]),
    (r"blockchain|web3|solidity|smart contract|crypto", ["fiber optics", "circuit board", "dark laptop", "server lights"]),
    (r"kiểm thử|testing|qa|selenium|cypress|automation test|jira", ["office laptop", "developer desk", "modern workspace", "laptop notebook"]),
    (r"agile|scrum|quản trị dự án|product|sản phẩm|kinh doanh|khởi nghiệp", ["startup office", "team office", "meeting table", "notebook coffee"]),
    (r"\bgit\b|github|thuật toán|cấu trúc dữ liệu|c\+\+|\bc căn bản\b|giải thuật", ["coding laptop", "computer keyboard", "programming screen", "notebook desk"]),
    (r"tiếng anh|english|ielts|toeic|giao tiếp|kỹ năng mềm|phỏng vấn|cv", ["study desk", "library laptop", "coffee notebook", "desk workspace"]),
]

CATEGORY_THEME_MAP: list[tuple[str, str]] = [
    (r"ai|trí tuệ|machine learning|dữ liệu|data|analytics|cơ sở dữ liệu|database", "ai_data"),
    (r"đám mây|cloud|devops|hệ thống|linux|mạng", "cloud_devops"),
    (r"an toàn|bảo mật|security|iot|nhúng|phần cứng", "security_iot"),
    (r"ui/ux|thiết kế|design|game|đồ họa|sáng tạo", "design_creative"),
    (r"quản trị|sản phẩm|product|agile|kiểm thử|kỹ năng|nghề nghiệp|tiếng anh|kinh doanh", "product_career"),
]


def log_event(event: str, **kwargs: Any) -> None:
    STAGING_ROOT.mkdir(parents=True, exist_ok=True)
    record = {
        "ts": datetime.now(timezone.utc).isoformat(),
        "event": event,
        **kwargs,
    }
    with open(LOG_PATH, "a", encoding="utf-8") as f:
        f.write(json.dumps(record, ensure_ascii=False) + "\n")


def strip_accents(s: str) -> str:
    return "".join(c for c in unicodedata.normalize("NFD", s) if unicodedata.category(c) != "Mn")


def pick_theme(course: dict[str, Any]) -> str:
    hay = f"{course.get('tenDanhMuc', '')} {course.get('tieuDe', '')}".lower()
    for pattern, theme_key in CATEGORY_THEME_MAP:
        if re.search(pattern, hay, re.I):
            return theme_key
    return "software_web"


def generate_queries(course: dict[str, Any]) -> tuple[list[str], list[str]]:
    """Generate ranked 1-2 word English search queries + Vietnamese keyword list."""
    title = (course.get("tieuDe") or "").strip()
    cat = (course.get("tenDanhMuc") or "").strip()
    desc = (course.get("moTa") or "").strip()
    lessons = " ".join(course.get("lessons") or [])
    combined = f"{title} {cat} {desc} {lessons}".lower()

    en_queries: list[str] = []
    for pattern, q_list in TECH_QUERY_MAP:
        if re.search(pattern, combined, re.I):
            for q in q_list:
                if q not in en_queries:
                    en_queries.append(q)
        if len(en_queries) >= 4:
            break

    # Fallback broad 2-word photography queries (varied by course id)
    broad_pool = [
        "coding laptop",
        "computer desk",
        "software developer",
        "modern office",
        "tech workspace",
        "laptop coffee",
        "programmer screen",
        "workstation monitor",
        "startup desk",
        "digital office",
        "study laptop",
        "keyboard monitor",
    ]
    cid = int(course["maKhoaHoc"])
    offset = cid % len(broad_pool)
    for k in range(3):
        cand_q = broad_pool[(offset + k * 3) % len(broad_pool)]
        if cand_q not in en_queries:
            en_queries.append(cand_q)

    vi_keywords = [w for w in [cat, title[:48]] if w]
    return en_queries[:5], vi_keywords


def compute_dhash(img: Image.Image, hash_size: int = 8) -> str:
    """64-bit difference perceptual hash (dHash) for near-duplicate detection."""
    gray = img.convert("L").resize((hash_size + 1, hash_size), Image.Resampling.LANCZOS)
    pixels = list(gray.get_flattened_data())
    bits = 0
    for row in range(hash_size):
        row_start = row * (hash_size + 1)
        for col in range(hash_size):
            bits = (bits << 1) | (1 if pixels[row_start + col] > pixels[row_start + col + 1] else 0)
    return f"{bits:016x}"


def hamming_distance(hex_a: str, hex_b: str) -> int:
    return (int(hex_a, 16) ^ int(hex_b, 16)).bit_count()


class RateLimitedFetcher:
    def __init__(self, min_interval_sec: float = 0.25) -> None:
        self.min_interval = min_interval_sec
        self.last_call = 0.0
        self.api_cache: dict[str, Any] = {}
        CACHE_DIR.mkdir(parents=True, exist_ok=True)
        if API_CACHE_PATH.is_file():
            try:
                self.api_cache = json.loads(API_CACHE_PATH.read_text(encoding="utf-8"))
            except Exception:
                self.api_cache = {}

    def save_cache(self) -> None:
        API_CACHE_PATH.write_text(json.dumps(self.api_cache, ensure_ascii=False), encoding="utf-8")

    def _wait(self) -> None:
        elapsed = time.time() - self.last_call
        if elapsed < self.min_interval:
            time.sleep(self.min_interval - elapsed)
        self.last_call = time.time()

    def get_json(self, url: str, timeout: float = 12.0, retries: int = 3) -> dict[str, Any] | None:
        if url in self.api_cache:
            return self.api_cache[url]
        for attempt in range(retries):
            self._wait()
            try:
                req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT, "Accept": "application/json"})
                with urllib.request.urlopen(req, timeout=timeout) as resp:
                    data = json.loads(resp.read().decode("utf-8"))
                    self.api_cache[url] = data
                    return data
            except urllib.error.HTTPError as exc:
                if exc.code in (429, 500, 502, 503, 504):
                    time.sleep(1.2 * (2 ** attempt))
                    continue
                return None
            except Exception:
                time.sleep(0.8 * (2 ** attempt))
        return None

    def download_bytes(self, url: str, timeout: float = 15.0, retries: int = 2) -> bytes | None:
        for attempt in range(retries):
            self._wait()
            try:
                req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
                with urllib.request.urlopen(req, timeout=timeout) as resp:
                    if resp.status != 200:
                        return None
                    data = resp.read()
                    if len(data) < 8000:
                        return None
                    return data
            except urllib.error.HTTPError as exc:
                if exc.code in (429, 500, 502, 503, 504):
                    time.sleep(1.0 * (2 ** attempt))
                    continue
                return None
            except Exception:
                time.sleep(0.6 * (2 ** attempt))
        return None


def search_openverse(fetcher: RateLimitedFetcher, query: str, page: int = 1, curated_sources: bool = True) -> list[dict[str, Any]]:
    query_params: dict[str, Any] = {
        "q": query,
        "license_type": "modification",
        "category": "photograph",
        "aspect_ratio": "wide",
        "page_size": 20,
        "page": page,
    }
    if curated_sources:
        query_params["source"] = "stocksnap,rawpixel,wordpress"
    params = urllib.parse.urlencode(query_params)
    url = f"https://api.openverse.org/v1/images/?{params}"
    data = fetcher.get_json(url)
    if not data or not isinstance(data.get("results"), list):
        return []
    candidates: list[dict[str, Any]] = []
    for item in data["results"]:
        lic = str(item.get("license") or "").lower().strip()
        if lic not in ALLOWED_OPENVERSE_LICENSES:
            continue
        img_url = str(item.get("url") or "").strip()
        if not img_url or BANNED_TERMS_RE.search(img_url + " " + str(item.get("title") or "")):
            continue
        if img_url.lower().endswith((".svg", ".gif", ".tif", ".tiff", ".pdf")):
            continue
        w = int(item.get("width") or 0)
        h = int(item.get("height") or 0)
        if w and h and (w < 700 or h < 390 or (w / max(h, 1)) < 1.15):
            continue
        lic_ver = str(item.get("license_version") or "").strip()
        lic_label = f"CC {lic.upper()} {lic_ver}".strip() if lic != "pdm" else "Public Domain Mark 1.0"
        if lic == "cc0":
            lic_label = f"CC0 {lic_ver or '1.0'}".strip()
        candidates.append({
            "source_provider": "Openverse",
            "source_origin": str(item.get("source") or "openverse"),
            "source_url": str(item.get("foreign_landing_url") or img_url),
            "original_image_url": img_url,
            "thumbnail_url": str(item.get("thumbnail") or ""),
            "title": str(item.get("title") or "").strip(),
            "author": str(item.get("creator") or "Unknown").strip(),
            "author_url": str(item.get("creator_url") or ""),
            "license": lic_label,
            "license_url": str(item.get("license_url") or "https://creativecommons.org/licenses/"),
            "attribution_required": lic in {"by", "by-sa"},
            "share_alike": lic == "by-sa",
            "width": w,
            "height": h,
            "query": query,
        })
    return candidates


def search_wikimedia(fetcher: RateLimitedFetcher, query: str) -> list[dict[str, Any]]:
    params = urllib.parse.urlencode({
        "action": "query",
        "format": "json",
        "generator": "search",
        "gsrnamespace": 6,
        "gsrsearch": f"filetype:bitmap {query}",
        "gsrlimit": 30,
        "prop": "imageinfo",
        "iiprop": "url|size|mime|extmetadata",
        "iiurlwidth": 1280,
    })
    url = f"https://commons.wikimedia.org/w/api.php?{params}"
    data = fetcher.get_json(url)
    pages = (data or {}).get("query", {}).get("pages", {})
    if not isinstance(pages, dict):
        return []
    candidates: list[dict[str, Any]] = []
    for page_obj in pages.values():
        infos = page_obj.get("imageinfo") or []
        if not infos:
            continue
        info = infos[0]
        mime = str(info.get("mime") or "").lower()
        if mime not in {"image/jpeg", "image/png", "image/webp"}:
            continue
        w = int(info.get("width") or 0)
        h = int(info.get("height") or 0)
        if w < 700 or h < 390 or (w / max(h, 1)) < 1.15:
            continue
        meta = info.get("extmetadata") or {}
        lic_short = str((meta.get("LicenseShortName") or {}).get("value") or "").strip()
        if not lic_short or not WIKIMEDIA_ALLOWED_RE.match(lic_short):
            continue
        title = str(page_obj.get("title") or "").replace("File:", "")
        img_url = str(info.get("thumburl") or info.get("url") or "").strip()
        orig_url = str(info.get("url") or img_url).strip()
        if not img_url or BANNED_TERMS_RE.search(title + " " + orig_url):
            continue
        artist_raw = str((meta.get("Artist") or {}).get("value") or "Wikimedia Commons Contributor")
        artist_clean = re.sub(r"<[^>]+>", "", artist_raw).strip()[:120] or "Wikimedia Commons Contributor"
        lic_url = str((meta.get("LicenseUrl") or {}).get("value") or "https://commons.wikimedia.org/wiki/Commons:Licensing")
        candidates.append({
            "source_provider": "Wikimedia Commons",
            "source_origin": "wikimedia",
            "source_url": str(info.get("descriptionurl") or orig_url),
            "original_image_url": orig_url,
            "download_url": img_url,
            "title": title,
            "author": artist_clean,
            "author_url": "",
            "license": lic_short,
            "license_url": lic_url,
            "attribution_required": "by" in lic_short.lower(),
            "share_alike": "sa" in lic_short.lower(),
            "width": w,
            "height": h,
            "query": query,
        })
    return candidates


def wrap_vietnamese_title(draw: ImageDraw.ImageDraw, text: str, font: ImageFont.FreeTypeFont, max_width: int, max_lines: int = 3) -> list[str]:
    words = text.strip().split()
    lines: list[str] = []
    current = ""
    for word in words:
        trial = f"{current} {word}".strip()
        bbox = draw.textbbox((0, 0), trial, font=font)
        if bbox[2] - bbox[0] <= max_width:
            current = trial
        else:
            if current:
                lines.append(current)
            current = word
            if len(lines) == max_lines - 1:
                break
    if current and len(lines) < max_lines:
        lines.append(current)
    # Trim ellipsis if overflowed remaining words
    used_words = sum(len(l.split()) for l in lines)
    if used_words < len(words) and lines:
        last = lines[-1]
        while len(last) > 4:
            trial = last.rstrip(" ,.-:") + "…"
            bbox = draw.textbbox((0, 0), trial, font=font)
            if bbox[2] - bbox[0] <= max_width:
                lines[-1] = trial
                break
            last = last[:-1]
    return lines


def shorten_course_title(title: str) -> str:
    cleaned = re.sub(r"\s*\([^)]*kiểm duyệt[^)]*\)", "", title, flags=re.I).strip()
    if len(cleaned) > 66:
        cut = cleaned[:63].rsplit(" ", 1)[0]
        return cut.rstrip(" ,.-:") + "…"
    return cleaned


def compose_editorial_cover(
    raw_img: Image.Image,
    course: dict[str, Any],
    theme_key: str,
) -> tuple[Image.Image, dict[str, Any]]:
    """Render a crisp 1280x720 (16:9) Editorial EdTech Modernism course cover."""
    W, H = 1280, 720
    theme = THEMES[theme_key]
    layout = theme["layout"]
    bg_rgb = theme["bg"]
    accent_rgb = theme["accent"]

    # Smart 16:9 framing of real photo with subtle contrast/saturation polish
    photo = ImageOps.exif_transpose(raw_img).convert("RGB")
    photo = ImageEnhance.Contrast(photo).enhance(1.06)
    photo = ImageEnhance.Color(photo).enhance(1.04)

    canvas = Image.new("RGBA", (W, H), (*bg_rgb, 255))

    if layout == "split_left":
        # Left 45% clean dark editorial panel, right 55% crisp photograph
        split_x = 570
        right_photo = ImageOps.fit(photo, (W - split_x, H), method=Image.Resampling.LANCZOS)
        canvas.paste(right_photo.convert("RGBA"), (split_x, 0))
        # Soft feather seam
        seam = Image.new("RGBA", (90, H), (0, 0, 0, 0))
        sdraw = ImageDraw.Draw(seam)
        for x in range(90):
            alpha = int(255 * ((1 - x / 90) ** 1.6))
            sdraw.line([(x, 0), (x, H)], fill=(*bg_rgb, alpha))
        canvas.alpha_composite(seam, (split_x - 2, 0))
        # Vertical accent rule
        draw_acc = ImageDraw.Draw(canvas)
        draw_acc.rectangle([(0, 0), (10, H)], fill=(*accent_rgb, 255))
        text_x, text_y, max_w = 56, 150, 480
    else:
        fitted = ImageOps.fit(photo, (W, H), method=Image.Resampling.LANCZOS).convert("RGBA")
        canvas.alpha_composite(fitted)
        overlay = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        odraw = ImageDraw.Draw(overlay)

        if layout == "left_scrim":
            for x in range(W):
                t = max(0.0, 1.0 - (x / (W * 0.78)))
                alpha = int(238 * (t ** 1.35))
                odraw.line([(x, 0), (x, H)], fill=(*bg_rgb, alpha))
            odraw.rectangle([(56, 150), (62, 540)], fill=(*accent_rgb, 255))
            text_x, text_y, max_w = 88, 168, 690

        elif layout == "diagonal_scrim":
            for x in range(W):
                t = max(0.0, 1.0 - (x / (W * 0.82)))
                alpha = int(232 * (t ** 1.25))
                odraw.line([(x, 0), (x, H)], fill=(*bg_rgb, alpha))
            # Top-right subtle corner accent bar
            odraw.rectangle([(0, 0), (W, 8)], fill=(*accent_rgb, 255))
            text_x, text_y, max_w = 64, 178, 700

        elif layout == "bottom_card":
            # Gentle full vignette + crisp bottom-left editorial panel
            for y in range(H):
                t = max(0.0, (y - H * 0.30) / (H * 0.70))
                alpha = int(210 * (t ** 1.4))
                odraw.line([(0, y), (W, y)], fill=(*bg_rgb, alpha))
            odraw.rounded_rectangle([(48, 355), (860, 668)], radius=20, fill=(*bg_rgb, 224), outline=(*accent_rgb, 180), width=2)
            text_x, text_y, max_w = 82, 386, 740

        elif layout == "bottom_band":
            for y in range(H):
                t = max(0.0, (y - H * 0.25) / (H * 0.75))
                alpha = int(242 * (t ** 1.5))
                odraw.line([(0, y), (W, y)], fill=(*bg_rgb, alpha))
            odraw.rectangle([(64, 650), (240, 656)], fill=(*accent_rgb, 255))
            text_x, text_y, max_w = 64, 412, 920

        else:  # lower_third
            for y in range(H):
                t = max(0.0, (y - H * 0.32) / (H * 0.68))
                alpha = int(240 * (t ** 1.3))
                odraw.line([(0, y), (W, y)], fill=(*bg_rgb, alpha))
            odraw.rectangle([(0, H - 8), (W, H)], fill=(*accent_rgb, 255))
            text_x, text_y, max_w = 64, 422, 900

        canvas.alpha_composite(overlay)

    draw = ImageDraw.Draw(canvas)

    # Category pill (factual category only — zero fake badges/discounts)
    cat_text = (course.get("tenDanhMuc") or "Khóa học").upper()
    pill_font = _pick_font(FONT_CANDIDATES_SEMIBOLD, 20)
    pb = draw.textbbox((0, 0), cat_text, font=pill_font)
    pw = (pb[2] - pb[0]) + 28
    ph = 38
    draw.rounded_rectangle([(text_x, text_y), (text_x + pw, text_y + ph)], radius=8, fill=theme["pill_bg"])
    draw.text((text_x + 14, text_y + 6), cat_text, font=pill_font, fill=theme["pill_fg"])

    # Shortened crisp Vietnamese course title
    short_title = shorten_course_title(course.get("tieuDe") or f"Khóa học #{course['maKhoaHoc']}")
    title_size = 46 if layout != "split_left" else 40
    title_font = _pick_font(FONT_CANDIDATES_BOLD, title_size)
    lines = wrap_vietnamese_title(draw, short_title, title_font, max_w, max_lines=3)
    if len(lines) >= 3 and layout in {"bottom_card", "bottom_band", "lower_third"}:
        title_font = _pick_font(FONT_CANDIDATES_BOLD, 38)
        lines = wrap_vietnamese_title(draw, short_title, title_font, max_w, max_lines=3)

    ty = text_y + ph + 18
    line_step = int(title_font.size * 1.24)
    for line in lines:
        draw.text((text_x, ty), line, font=title_font, fill=theme["title_fg"])
        ty += line_step

    # Subtle understated brand signature in top-right (non-intrusive)
    brand_font = _pick_font(FONT_CANDIDATES_SEMIBOLD, 20)
    brand_txt = "EduSuggest"
    bb = draw.textbbox((0, 0), brand_txt, font=brand_font)
    bw = bb[2] - bb[0]
    bx = W - bw - 40
    by = 28
    draw.rounded_rectangle([(bx - 14, by - 6), (bx + bw + 14, by + 30)], radius=8, fill=(15, 23, 42, 165))
    draw.text((bx, by), brand_txt, font=brand_font, fill=(241, 245, 249))

    transform_meta = {
        "target_dimensions": "1280x720",
        "aspect_ratio": "16:9",
        "format": "WEBP",
        "theme_key": theme_key,
        "theme_layout": layout,
        "rendered_title": short_title,
        "rendered_category": cat_text,
        "operations": ["exif_transpose", "smart_16_9_center_crop", "editorial_scrim_overlay", "vietnamese_typography_pillow"],
    }
    return canvas.convert("RGB"), transform_meta


def load_courses() -> list[dict[str, Any]]:
    if SNAPSHOT_PATH.is_file():
        return json.loads(SNAPSHOT_PATH.read_text(encoding="utf-8"))
    # Fallback: read directly from Production PostgreSQL (READ ONLY)
    sys.path.insert(0, str(BACKEND_ROOT))
    from sqlalchemy import create_engine, text
    from config.config import get_settings

    eng = create_engine(get_settings().database_url.get_secret_value())
    with eng.connect() as conn:
        rows = conn.execute(text('''
            SELECT k."maKhoaHoc", k."tieuDe", k."moTa", d."tenDanhMuc", k."maDanhMuc",
                   k."trinhDo", k."gia", k."thoiLuong", k."hinhAnh"
            FROM "KhoaHoc" k
            LEFT JOIN "DanhMuc" d ON d."maDanhMuc" = k."maDanhMuc"
            ORDER BY k."maKhoaHoc"
        ''')).fetchall()
        lessons_rows = conn.execute(text('SELECT "maKhoaHoc", "tieuDe" FROM "BaiHoc" ORDER BY "maKhoaHoc", "thuTu"')).fetchall()
    by_c: dict[int, list[str]] = {}
    for cid, lt in lessons_rows:
        by_c.setdefault(cid, []).append(lt)
    result = []
    for r in rows:
        m = dict(r._mapping)
        m["gia"] = float(m["gia"] or 0)
        m["lessons"] = by_c.get(m["maKhoaHoc"], [])
        result.append(m)
    return result


def build_rollback_manifest(courses: list[dict[str, Any]]) -> dict[str, Any]:
    entries = []
    for c in courses:
        rel = c.get("hinhAnh") or ""
        fname = os.path.basename(rel)
        p = PROD_MEDIA_DIR / fname
        sha = hashlib.sha256(p.read_bytes()).hexdigest() if p.is_file() else ""
        size = p.stat().st_size if p.is_file() else 0
        entries.append({
            "course_id": c["maKhoaHoc"],
            "course_title": c["tieuDe"],
            "original_db_path": rel,
            "original_filename": fname,
            "original_size_bytes": size,
            "original_sha256": sha,
        })
    payload = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "total_courses": len(entries),
        "entries": entries,
    }
    ROLLBACK_PATH.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    return payload


def write_attribution_doc(manifest_entries: list[dict[str, Any]]) -> None:
    lines = [
        "# COURSE COVER SOURCE ATTRIBUTION — EDUSUGGEST (GĐ5.1)",
        "",
        f"**Ngày tạo:** {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}  ",
        f"**Tổng số khóa học đã gán ảnh bìa xác minh giấy phép:** `{len(manifest_entries)} / 120`",
        "",
        "Tất cả ảnh nền thực tế sử dụng để tạo ảnh bìa 1280×720 WebP đều được truy xuất hợp lệ qua API công khai (**Openverse API** với bộ lọc `license_type=modification` và **Wikimedia Commons API**), đảm bảo giấy phép mở cho phép chỉnh sửa (`CC0`, `PDM`, `CC BY`, `CC BY-SA`), không watermark và không sao chép thương hiệu nền tảng khác.",
        "",
        "| Course ID | Khóa học | Nguồn | Tác giả / Nhiếp ảnh gia | Giấy phép | Yêu cầu ghi nguồn | Tệp WebP |",
        "|---:|---|---|---|---|---|---|",
    ]
    for e in sorted(manifest_entries, key=lambda x: x["course_id"]):
        title = e["course_title"].replace("|", "/")
        author = (e.get("author") or "Unknown").replace("|", "/")
        src = f"[{e['source_provider']}]({e['source_url']})"
        lic = f"[{e['license']}]({e['license_url']})"
        attr = e.get("attribution_requirements") or "Không bắt buộc"
        lines.append(f"| {e['course_id']} | {title} | {src} | {author} | {lic} | {attr} | `{e['local_filename']}` |")

    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    ATTRIBUTION_PATH.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description="EduSuggest GĐ5.1 Automated Course Cover Pipeline")
    parser.add_argument("--dry-run", action="store_true", help="Plan queries & themes without downloading or writing covers")
    parser.add_argument("--resume", action="store_true", help="Resume from checkpoint and skip verified covers")
    parser.add_argument("--rebuild-thumbnails", action="store_true", help="Re-render WebP covers from cached raw photos")
    parser.add_argument("--batch-size", type=int, default=120, help="Batch size per progress flush")
    parser.add_argument("--limit", type=int, default=0, help="Optional limit on number of courses to process")
    parser.add_argument("--course-ids", type=str, default="", help="Comma-separated course IDs to (re)process")
    args = parser.parse_args()

    STAGING_ROOT.mkdir(parents=True, exist_ok=True)
    COVERS_DIR.mkdir(parents=True, exist_ok=True)
    RAW_DIR.mkdir(parents=True, exist_ok=True)
    CACHE_DIR.mkdir(parents=True, exist_ok=True)

    courses = load_courses()
    if not args.dry_run:
        build_rollback_manifest(courses)

    target_ids: set[int] | None = None
    if args.course_ids.strip():
        target_ids = {int(x.strip()) for x in args.course_ids.split(",") if x.strip()}

    checkpoint: dict[str, dict[str, Any]] = {}
    if CHECKPOINT_PATH.is_file() and (args.resume or args.rebuild_thumbnails or target_ids):
        try:
            checkpoint = json.loads(CHECKPOINT_PATH.read_text(encoding="utf-8"))
        except Exception:
            checkpoint = {}

    if args.dry_run:
        sample = courses[: args.limit] if args.limit else courses
        theme_counts: dict[str, int] = {}
        for c in sample:
            tk = pick_theme(c)
            theme_counts[tk] = theme_counts.get(tk, 0) + 1
        print(json.dumps({
            "mode": "DRY_RUN",
            "total_courses": len(sample),
            "themes_distribution": theme_counts,
            "sample_queries": [
                {"id": c["maKhoaHoc"], "title": c["tieuDe"], "theme": pick_theme(c), "queries": generate_queries(c)[0]}
                for c in sample[:6]
            ],
        }, ensure_ascii=False, indent=2))
        return 0

    fetcher = RateLimitedFetcher(min_interval_sec=0.18)

    # Track global deduplication sets from existing checkpoint (excluding target_ids being replaced)
    used_urls: set[str] = set()
    used_sha256: set[str] = set()
    used_dhashes: list[tuple[int, str]] = []
    for cid_str, rec in checkpoint.items():
        cid_int = int(cid_str)
        if rec.get("original_image_url"):
            used_urls.add(rec["original_image_url"])
        if target_ids and cid_int in target_ids:
            continue
        if rec.get("status") == "VERIFIED":
            if rec.get("raw_sha256"):
                used_sha256.add(rec["raw_sha256"])
            if rec.get("dhash"):
                used_dhashes.append((cid_int, rec["dhash"]))

    # Candidate pool cache per query to avoid redundant API calls across related courses
    query_candidates_cache: dict[str, list[dict[str, Any]]] = {}

    process_list = courses[: args.limit] if args.limit else courses
    processed = 0
    verified_count = 0
    failed_ids: list[int] = []

    for idx, course in enumerate(process_list, start=1):
        cid = int(course["maKhoaHoc"])
        cid_str = str(cid)
        if target_ids is not None and cid not in target_ids:
            continue

        existing = checkpoint.get(cid_str)
        out_filename = f"course-{cid:03d}.webp"
        out_path = COVERS_DIR / out_filename

        # Resume skip if already verified and file exists
        if args.resume and not args.rebuild_thumbnails and not target_ids and existing and existing.get("status") == "VERIFIED" and out_path.is_file():
            verified_count += 1
            continue

        theme_key = pick_theme(course)
        en_queries, vi_keywords = generate_queries(course)

        # Rebuild from cached raw photo
        if args.rebuild_thumbnails and existing and existing.get("raw_filename"):
            raw_path = RAW_DIR / existing["raw_filename"]
            if raw_path.is_file():
                with Image.open(raw_path) as raw_img:
                    composed, transform_meta = compose_editorial_cover(raw_img, course, theme_key)
                    composed.save(out_path, format="WEBP", quality=84, method=6)
                existing["local_filename"] = out_filename
                existing["output_size_bytes"] = out_path.stat().st_size
                existing["sha256"] = hashlib.sha256(out_path.read_bytes()).hexdigest()
                existing["transformation_details"] = transform_meta
                checkpoint[cid_str] = existing
                verified_count += 1
                processed += 1
                continue

        # Discover & download unique verified photograph
        chosen_meta: dict[str, Any] | None = None
        chosen_bytes: bytes | None = None
        chosen_img: Image.Image | None = None
        chosen_dhash = ""
        chosen_raw_sha = ""

        # Try curated clean photography sources (stocksnap/rawpixel/wordpress) first, then broad Openverse, then Wikimedia
        for source_pass in ("openverse_curated", "openverse_all", "wikimedia"):
            if chosen_meta is not None:
                break
            for q in en_queries:
                if chosen_meta is not None:
                    break
                cache_key = f"{source_pass}::{q}"
                if cache_key not in query_candidates_cache:
                    if source_pass == "openverse_curated":
                        cands = search_openverse(fetcher, q, page=1, curated_sources=True)
                        if len(cands) < 12:
                            cands.extend(search_openverse(fetcher, q, page=2, curated_sources=True))
                    elif source_pass == "openverse_all":
                        cands = search_openverse(fetcher, q, page=1, curated_sources=False)
                    else:
                        cands = search_wikimedia(fetcher, q)
                    query_candidates_cache[cache_key] = cands
                    fetcher.save_cache()

                for cand in query_candidates_cache[cache_key]:
                    orig_url = cand["original_image_url"]
                    if orig_url in used_urls:
                        continue
                    dl_url = cand.get("download_url") or orig_url
                    data = fetcher.download_bytes(dl_url)
                    if not data and cand.get("thumbnail_url"):
                        data = fetcher.download_bytes(cand["thumbnail_url"])
                    if not data:
                        continue

                    raw_sha = hashlib.sha256(data).hexdigest()
                    if raw_sha in used_sha256:
                        continue

                    try:
                        img = Image.open(io.BytesIO(data))
                        img.verify()
                        img = Image.open(io.BytesIO(data))
                        w, h = img.size
                        ratio = w / max(h, 1)
                        if w < 640 or h < 360 or ratio < 1.2 or ratio > 2.3:
                            continue
                        dh = compute_dhash(img)
                    except Exception:
                        continue

                    # Perceptual near-duplicate check across all selected courses
                    if any(hamming_distance(dh, prev_dh) <= 9 for _, prev_dh in used_dhashes):
                        continue

                    chosen_meta = cand
                    chosen_bytes = data
                    chosen_img = img
                    chosen_dhash = dh
                    chosen_raw_sha = raw_sha
                    break

        if chosen_meta is None or chosen_img is None or chosen_bytes is None:
            failed_ids.append(cid)
            log_event("course_cover_failed", course_id=cid, title=course["tieuDe"], queries=en_queries)
            continue

        # Save raw verified photo + render 1280x720 WebP editorial cover
        raw_ext = ".jpg" if (chosen_img.format or "").upper() in {"JPEG", "JPG"} else ".png"
        raw_filename = f"raw-{cid:03d}{raw_ext}"
        (RAW_DIR / raw_filename).write_bytes(chosen_bytes)

        composed, transform_meta = compose_editorial_cover(chosen_img, course, theme_key)
        composed.save(out_path, format="WEBP", quality=84, method=6)
        out_bytes = out_path.read_bytes()
        out_sha = hashlib.sha256(out_bytes).hexdigest()

        used_urls.add(chosen_meta["original_image_url"])
        used_sha256.add(chosen_raw_sha)
        used_dhashes.append((cid, chosen_dhash))

        attr_req = (
            f"Ghi nguồn tác giả '{chosen_meta['author']}' + giấy phép {chosen_meta['license']}"
            + (" (Share-Alike)" if chosen_meta.get("share_alike") else "")
            if chosen_meta.get("attribution_required")
            else f"Không bắt buộc ghi nguồn ({chosen_meta['license']}), vẫn lưu đầy đủ provenance"
        )

        record = {
            "course_id": cid,
            "course_title": course["tieuDe"],
            "category": course.get("tenDanhMuc") or "",
            "status": "VERIFIED",
            "source_provider": chosen_meta["source_provider"],
            "source_origin": chosen_meta["source_origin"],
            "source_url": chosen_meta["source_url"],
            "original_image_url": chosen_meta["original_image_url"],
            "author": chosen_meta["author"],
            "license": chosen_meta["license"],
            "license_url": chosen_meta["license_url"],
            "retrieved_at": datetime.now(timezone.utc).isoformat(),
            "search_keywords": {"en": en_queries, "vi": vi_keywords, "matched_query": chosen_meta["query"]},
            "raw_filename": raw_filename,
            "raw_sha256": chosen_raw_sha,
            "raw_dimensions": f"{chosen_img.size[0]}x{chosen_img.size[1]}",
            "dhash": chosen_dhash,
            "local_filename": out_filename,
            "sha256": out_sha,
            "output_size_bytes": len(out_bytes),
            "attribution_requirements": attr_req,
            "transformation_details": transform_meta,
            "previous_db_path": course.get("hinhAnh") or "",
        }
        checkpoint[cid_str] = record
        verified_count += 1
        processed += 1

        # Checkpoint after every course for crash resilience
        CHECKPOINT_PATH.write_text(json.dumps(checkpoint, ensure_ascii=False, indent=2), encoding="utf-8")
        log_event("course_cover_verified", course_id=cid, provider=chosen_meta["source_provider"], license=chosen_meta["license"], size=len(out_bytes))

        if processed % 10 == 0 or idx == len(process_list):
            print(f"[PROGRESS] {idx}/{len(process_list)} | verified={verified_count} | failed={len(failed_ids)}", flush=True)

    fetcher.save_cache()

    # Build final sorted manifest + attribution markdown
    all_entries = [checkpoint[str(c["maKhoaHoc"])] for c in courses if str(c["maKhoaHoc"]) in checkpoint]
    manifest_payload = {
        "schema_version": "1.0",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "total_courses": len(courses),
        "verified_covers": sum(1 for e in all_entries if e.get("status") == "VERIFIED"),
        "failed_course_ids": failed_ids,
        "entries": all_entries,
    }
    MANIFEST_PATH.write_text(json.dumps(manifest_payload, ensure_ascii=False, indent=2), encoding="utf-8")
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    DOCS_MANIFEST_PATH.write_text(json.dumps(manifest_payload, ensure_ascii=False, indent=2), encoding="utf-8")
    write_attribution_doc(all_entries)

    print(json.dumps({
        "status": "DONE",
        "total_courses": len(courses),
        "verified_covers": manifest_payload["verified_covers"],
        "failed_count": len(failed_ids),
        "failed_course_ids": failed_ids,
        "manifest_path": str(MANIFEST_PATH),
    }, ensure_ascii=False, indent=2))
    return 0 if not failed_ids else 2


if __name__ == "__main__":
    raise SystemExit(main())
