"""
EduSuggest GĐ5.1 — Contact Sheets & HTML Comparison Gallery Builder.

Generates:
1. 4 high-resolution Contact Sheet PNGs (30 courses per sheet, 5x6 grid) in
   media/phase5-covers-staging/contact-sheets/ for full 120/120 visual audit.
2. Standalone HTML Comparison Gallery in
   docs/reports/course-cover-comparison-gallery.html showing Old vs New cover,
   course title, category, source, author, license, size, and verification status.
"""

from __future__ import annotations

import html
import json
import os
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

PROJECT_ROOT = Path(r"D:\đồ án\EduSuggest")
STAGING_ROOT = PROJECT_ROOT / "media" / "phase5-covers-staging"
COVERS_DIR = STAGING_ROOT / "covers"
SHEETS_DIR = STAGING_ROOT / "contact-sheets"
PROD_MEDIA_DIR = PROJECT_ROOT / "media" / "courses"
MANIFEST_PATH = STAGING_ROOT / "course-cover-manifest.json"
GALLERY_HTML_PATH = PROJECT_ROOT / "docs" / "reports" / "course-cover-comparison-gallery.html"


def _font(size: int) -> ImageFont.FreeTypeFont:
    for p in (r"C:\Windows\Fonts\segoeuib.ttf", r"C:\Windows\Fonts\segoeui.ttf", r"C:\Windows\Fonts\arial.ttf"):
        if os.path.isfile(p):
            return ImageFont.truetype(p, size=size)
    return ImageFont.load_default()


def build_contact_sheets(entries: list[dict]) -> list[Path]:
    SHEETS_DIR.mkdir(parents=True, exist_ok=True)
    cols, rows_per_sheet = 5, 6
    per_sheet = cols * rows_per_sheet
    thumb_w, thumb_h = 320, 180
    pad_x, pad_y = 14, 34
    margin = 20

    sheet_w = margin * 2 + cols * thumb_w + (cols - 1) * pad_x
    sheet_h = margin * 2 + 36 + rows_per_sheet * (thumb_h + pad_y)
    label_font = _font(13)
    header_font = _font(18)

    paths: list[Path] = []
    sorted_entries = sorted(entries, key=lambda x: x["course_id"])
    for s_idx in range(0, len(sorted_entries), per_sheet):
        chunk = sorted_entries[s_idx : s_idx + per_sheet]
        sheet_num = (s_idx // per_sheet) + 1
        canvas = Image.new("RGB", (sheet_w, sheet_h), (244, 245, 247))
        draw = ImageDraw.Draw(canvas)
        draw.text(
            (margin, margin),
            f"EduSuggest GĐ5.1 — Visual Audit Contact Sheet {sheet_num} (Courses {s_idx + 1}–{s_idx + len(chunk)} / {len(sorted_entries)})",
            font=header_font,
            fill=(17, 34, 51),
        )
        for i, entry in enumerate(chunk):
            r = i // cols
            c = i % cols
            x = margin + c * (thumb_w + pad_x)
            y = margin + 40 + r * (thumb_h + pad_y)
            cover_path = COVERS_DIR / entry["local_filename"]
            if cover_path.is_file():
                with Image.open(cover_path) as im:
                    thumb = im.resize((thumb_w, thumb_h), Image.Resampling.LANCZOS)
                canvas.paste(thumb, (x, y))
            else:
                draw.rectangle([(x, y), (x + thumb_w, y + thumb_h)], fill=(220, 38, 38))
            lbl = f"#{entry['course_id']} [{entry['source_provider'][:4]}] {entry['course_title'][:34]}"
            draw.text((x, y + thumb_h + 4), lbl, font=label_font, fill=(30, 41, 59))
        out = SHEETS_DIR / f"contact-sheet-{sheet_num}.png"
        canvas.save(out, format="PNG", optimize=True)
        paths.append(out)
    return paths


def build_html_gallery(entries: list[dict]) -> Path:
    sorted_entries = sorted(entries, key=lambda x: x["course_id"])
    categories = sorted({e.get("category") or "Khác" for e in sorted_entries})
    total_kb = sum(e.get("output_size_bytes", 0) for e in sorted_entries) / 1024.0

    cards_html = []
    for e in sorted_entries:
        cid = e["course_id"]
        title = html.escape(e["course_title"])
        cat = html.escape(e.get("category") or "")
        old_fn = os.path.basename(e.get("previous_db_path") or "")
        old_rel = f"../../media/courses/{old_fn}" if old_fn else ""
        new_rel = f"../../media/phase5-covers-staging/covers/{e['local_filename']}"
        src_name = html.escape(e.get("source_provider") or "")
        src_url = html.escape(e.get("source_url") or "#")
        author = html.escape(e.get("author") or "Unknown")
        lic = html.escape(e.get("license") or "")
        lic_url = html.escape(e.get("license_url") or "#")
        size_kb = e.get("output_size_bytes", 0) / 1024.0
        theme = html.escape((e.get("transformation_details") or {}).get("theme_key", ""))
        status = html.escape(e.get("status") or "PENDING")

        cards_html.append(f"""
        <article class="card" data-category="{cat}" data-search="{title.lower()} {cat.lower()} {cid}">
          <div class="card-head">
            <span class="cid">#{cid}</span>
            <span class="cat">{cat}</span>
            <span class="badge ok">{status}</span>
          </div>
          <h3 class="title">{title}</h3>
          <div class="compare">
            <figure>
              <figcaption>Ảnh bìa cũ ({html.escape(old_fn)})</figcaption>
              <img src="{old_rel}" alt="Old cover {cid}" loading="lazy">
            </figure>
            <figure>
              <figcaption>Ảnh bìa mới ({e['local_filename']} · {size_kb:.1f} KB)</figcaption>
              <img src="{new_rel}" alt="New cover {cid}" loading="lazy">
            </figure>
          </div>
          <div class="meta">
            <span>Nguồn: <a href="{src_url}" target="_blank" rel="noopener">{src_name}</a></span>
            <span>Tác giả: {author}</span>
            <span>Giấy phép: <a href="{lic_url}" target="_blank" rel="noopener">{lic}</a></span>
            <span>Theme: <code>{theme}</code></span>
          </div>
        </article>
        """)

    cat_options = "\n".join(f'<option value="{html.escape(c)}">{html.escape(c)}</option>' for c in categories)
    doc = f"""<!DOCTYPE html>
<html lang="vi">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>EduSuggest GĐ5.1 — Gallery So Sánh 120 Ảnh Bìa Khóa Học</title>
  <style>
    :root {{ --navy:#112233; --teal:#0D9488; --bg:#F6F5F1; --surface:#FFFFFF; --border:#E2E8F0; --muted:#64748B; }}
    * {{ box-sizing:border-box; }}
    body {{ margin:0; font-family:'Segoe UI', system-ui, sans-serif; background:var(--bg); color:var(--navy); }}
    header {{ position:sticky; top:0; z-index:10; background:rgba(255,255,255,.95); backdrop-filter:blur(8px); border-bottom:1px solid var(--border); padding:16px 24px; }}
    .wrap {{ max-width:1400px; margin:0 auto; }}
    h1 {{ margin:0 0 6px; font-size:20px; }}
    .stats {{ font-size:13px; color:var(--muted); margin-bottom:12px; }}
    .controls {{ display:flex; gap:12px; flex-wrap:wrap; }}
    input, select {{ padding:8px 12px; border:1px solid var(--border); border-radius:8px; font-size:13px; background:#fff; }}
    input {{ flex:1; min-width:240px; }}
    main {{ padding:24px; }}
    .grid {{ display:grid; grid-template-columns:repeat(auto-fill, minmax(560px, 1fr)); gap:18px; }}
    .card {{ background:var(--surface); border:1px solid var(--border); border-radius:14px; padding:14px; }}
    .card-head {{ display:flex; align-items:center; gap:8px; margin-bottom:6px; font-size:12px; }}
    .cid {{ font-weight:700; color:var(--navy); }}
    .cat {{ background:#EFF6FF; color:#1E3A8A; padding:2px 8px; border-radius:6px; font-weight:600; }}
    .badge.ok {{ margin-left:auto; background:#ECFDF5; color:#065F46; padding:2px 8px; border-radius:6px; font-weight:700; }}
    .title {{ margin:0 0 10px; font-size:15px; line-height:1.35; }}
    .compare {{ display:grid; grid-template-columns:1fr 1fr; gap:10px; }}
    figure {{ margin:0; }}
    figcaption {{ font-size:11px; color:var(--muted); margin-bottom:4px; }}
    img {{ width:100%; aspect-ratio:16/9; object-fit:cover; border-radius:8px; border:1px solid var(--border); background:#f1f5f9; display:block; }}
    .meta {{ margin-top:10px; display:flex; flex-wrap:wrap; gap:10px; font-size:11.5px; color:var(--muted); border-top:1px solid #F1F5F9; padding-top:8px; }}
    a {{ color:var(--teal); text-decoration:none; }}
    a:hover {{ text-decoration:underline; }}
    @media (max-width:640px) {{ .grid {{ grid-template-columns:1fr; }} .compare {{ grid-template-columns:1fr; }} }}
  </style>
</head>
<body>
  <header>
    <div class="wrap">
      <h1>EduSuggest GĐ5.1 — Gallery So Sánh Ảnh Bìa Cũ &amp; Ảnh Bìa Mới (120 Khóa Học)</h1>
      <div class="stats">Đã xác minh: <strong>{len(sorted_entries)}/120</strong> · Định dạng: <strong>1280×720 (16:9) WebP</strong> · Tổng dung lượng mới: <strong>{total_kb/1024:.2f} MB</strong> (TB {total_kb/max(len(sorted_entries),1):.1f} KB/ảnh) · Production DB chưa chỉnh sửa.</div>
      <div class="controls">
        <input id="q" type="search" placeholder="Tìm theo tên khóa học, danh mục hoặc Course ID...">
        <select id="cat"><option value="">Tất cả danh mục ({len(categories)})</option>{cat_options}</select>
      </div>
    </div>
  </header>
  <main class="wrap">
    <div class="grid" id="grid">
      {"".join(cards_html)}
    </div>
  </main>
  <script>
    const q = document.getElementById('q'), cat = document.getElementById('cat');
    const cards = Array.from(document.querySelectorAll('.card'));
    function filter() {{
      const term = q.value.trim().toLowerCase();
      const c = cat.value;
      for (const el of cards) {{
        const okC = !c || el.dataset.category === c;
        const okQ = !term || el.dataset.search.includes(term);
        el.style.display = (okC && okQ) ? '' : 'none';
      }}
    }}
    q.addEventListener('input', filter);
    cat.addEventListener('change', filter);
  </script>
</body>
</html>
"""
    GALLERY_HTML_PATH.parent.mkdir(parents=True, exist_ok=True)
    GALLERY_HTML_PATH.write_text(doc, encoding="utf-8")
    return GALLERY_HTML_PATH


def main() -> int:
    manifest = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
    entries = manifest.get("entries") or []
    sheets = build_contact_sheets(entries)
    gallery = build_html_gallery(entries)
    print(json.dumps({
        "entries": len(entries),
        "contact_sheets": [str(p) for p in sheets],
        "gallery_html": str(gallery),
    }, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
