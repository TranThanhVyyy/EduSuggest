"""Generate the deterministic, source-attributed EduSuggest official dataset.

This stage writes JSON/SVG/TXT assets only.  It never opens PostgreSQL.  The
result is intentionally reproducible and may be reviewed before import.
"""

from __future__ import annotations

import argparse
import html
import re
import sys
from datetime import UTC, datetime
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parents[1]
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

from scripts.official_dataset_common import (
    COVER_DIR,
    DATASET_MANIFEST,
    MATERIAL_DIR,
    SOURCE_MANIFEST,
    ensure_generated_directories,
    sha256_file,
    write_json,
)

PALETTES = [
    ("#112233", "#0D9488", "#F8FAF9"),
    ("#172554", "#2563EB", "#EFF6FF"),
    ("#3B1D2A", "#C2410C", "#FFF7ED"),
    ("#1F2937", "#7C3AED", "#F5F3FF"),
    ("#0F3D3E", "#D97706", "#FFFBEB"),
    ("#1E293B", "#0891B2", "#ECFEFF"),
]

# Five original course concepts per category.  Public sites informed topic
# coverage only; every Vietnamese title, description and lesson body below is
# generated as original EduSuggest editorial content.
CATEGORIES = [
    (
        "lap-trinh-can-ban",
        "Lập trình căn bản",
        "nền tảng tư duy lập trình, kiểu dữ liệu và kiểm soát luồng",
        [
            "Python nhập môn và tư duy giải quyết bài toán",
            "C căn bản: bộ nhớ, con trỏ và cấu trúc chương trình",
            "Java căn bản với lập trình hướng đối tượng",
            "JavaScript nền tảng cho người mới bắt đầu",
            "Git và kỹ năng làm việc với mã nguồn",
        ],
    ),
    (
        "web-frontend",
        "Web Frontend",
        "giao diện web truy cập được, hiệu năng tốt và dễ bảo trì",
        [
            "HTML, CSS và Responsive Web Design thực hành",
            "JavaScript hiện đại và DOM chuyên sâu",
            "Vue 3, Pinia và kiến trúc ứng dụng frontend",
            "React, Hooks và quản lý trạng thái",
            "TypeScript và kiểm thử giao diện web",
        ],
    ),
    (
        "web-backend",
        "Web Backend",
        "dịch vụ web an toàn, API rõ ràng và dữ liệu nhất quán",
        [
            "Xây dựng REST API với FastAPI và PostgreSQL",
            "Node.js, Express và TypeScript cho Backend",
            "Spring Boot và thiết kế dịch vụ Java",
            "ASP.NET Core Web API thực hành",
            "Bảo mật API với JWT, OAuth 2.0 và RBAC",
        ],
    ),
    (
        "fullstack-development",
        "Fullstack Development",
        "ứng dụng hoàn chỉnh từ giao diện, API đến triển khai",
        [
            "Fullstack Vue 3 và FastAPI",
            "Fullstack React và Node.js",
            "Next.js và PostgreSQL cho sản phẩm web",
            "Spring Boot kết hợp Vue cho hệ thống doanh nghiệp",
            "Xây dựng SaaS Fullstack từ thiết kế đến vận hành",
        ],
    ),
    (
        "lap-trinh-mobile",
        "Lập trình Mobile",
        "ứng dụng di động đa nền tảng, trải nghiệm tốt và quản lý trạng thái đúng",
        [
            "Flutter và Dart từ nền tảng đến ứng dụng",
            "React Native và TypeScript thực chiến",
            "Android hiện đại với Kotlin và Jetpack Compose",
            "iOS với SwiftUI và kiến trúc MVVM",
            "Kiểm thử và phát hành ứng dụng Mobile",
        ],
    ),
    (
        "lap-trinh-game",
        "Lập trình Game",
        "vòng lặp game, vật lý, đồ họa và thiết kế gameplay",
        [
            "Unity và C# cho Game 2D",
            "Unity 3D và hệ thống vật lý",
            "Unreal Engine và Blueprint căn bản",
            "Godot và GDScript cho Indie Game",
            "Thiết kế AI và hành vi nhân vật trong Game",
        ],
    ),
    (
        "lap-trinh-desktop",
        "Lập trình Desktop",
        "ứng dụng máy tính ổn định, kiến trúc rõ và đóng gói thuận tiện",
        [
            "Ứng dụng Desktop với C# và WPF",
            "JavaFX và kiến trúc ứng dụng Desktop",
            "Python, PySide và công cụ nội bộ",
            "Electron và TypeScript cho ứng dụng đa nền tảng",
            "Tauri và Rust cho Desktop nhẹ, an toàn",
        ],
    ),
    (
        "co-so-du-lieu-sql",
        "Cơ sở dữ liệu & SQL",
        "mô hình dữ liệu quan hệ, truy vấn chính xác và vận hành tin cậy",
        [
            "SQL nền tảng và mô hình dữ liệu quan hệ",
            "PostgreSQL từ thiết kế đến vận hành",
            "Tối ưu truy vấn, chỉ mục và EXPLAIN",
            "Transaction, khóa và kiểm soát đồng thời",
            "Backup, phục hồi và tính sẵn sàng dữ liệu",
        ],
    ),
    (
        "phan-tich-du-lieu",
        "Phân tích dữ liệu",
        "làm sạch, khám phá và truyền đạt thông tin từ dữ liệu",
        [
            "Phân tích dữ liệu với Excel và SQL",
            "Python Pandas cho phân tích dữ liệu",
            "Trực quan hóa dữ liệu với Power BI",
            "Thống kê ứng dụng cho Data Analyst",
            "Xây dựng báo cáo và Data Storytelling",
        ],
    ),
    (
        "khoa-hoc-du-lieu",
        "Khoa học dữ liệu",
        "quy trình dữ liệu có thể tái lập từ khảo sát đến mô hình",
        [
            "Quy trình Khoa học dữ liệu với Python",
            "Feature Engineering và chuẩn bị dữ liệu",
            "Thống kê suy luận cho Data Science",
            "Thiết kế thí nghiệm và A/B Testing",
            "Xây dựng Data Product có thể tái lập",
        ],
    ),
    (
        "machine-learning",
        "Machine Learning",
        "mô hình học máy được đánh giá đúng và triển khai có trách nhiệm",
        [
            "Machine Learning với Scikit-learn",
            "Hồi quy, phân loại và đánh giá mô hình",
            "Clustering và học không giám sát",
            "MLOps căn bản và theo dõi mô hình",
            "Hệ thống gợi ý với TF-IDF và Cosine Similarity",
        ],
    ),
    (
        "deep-learning-computer-vision",
        "Deep Learning & Computer Vision",
        "mạng nơ-ron, xử lý ảnh và đánh giá mô hình thị giác",
        [
            "Deep Learning với PyTorch",
            "Mạng CNN cho phân loại hình ảnh",
            "Object Detection và xử lý video",
            "Transfer Learning cho Computer Vision",
            "Triển khai mô hình thị giác hiệu quả",
        ],
    ),
    (
        "generative-ai-nlp",
        "Generative AI & NLP",
        "xử lý ngôn ngữ, embedding và ứng dụng mô hình sinh an toàn",
        [
            "NLP nền tảng với Python",
            "Transformer và Attention từ trực giác đến thực hành",
            "Xây dựng ứng dụng RAG có trích dẫn",
            "Prompt Engineering và đánh giá đầu ra",
            "Vận hành ứng dụng Generative AI an toàn",
        ],
    ),
    (
        "devops-cicd",
        "DevOps & CI/CD",
        "tự động hóa kiểm thử, đóng gói và phát hành phần mềm",
        [
            "Git workflow và CI/CD căn bản",
            "Docker từ image đến Compose",
            "Kubernetes cho ứng dụng thực tế",
            "Infrastructure as Code với Terraform",
            "Quan sát hệ thống với Metrics, Logs và Traces",
        ],
    ),
    (
        "dien-toan-dam-may",
        "Điện toán đám mây",
        "kiến trúc cloud co giãn, bảo mật và kiểm soát chi phí",
        [
            "Nền tảng Cloud và kiến trúc phân tán",
            "AWS cho Developer và Solution Architect",
            "Microsoft Azure căn bản thực hành",
            "Google Cloud cho ứng dụng dữ liệu",
            "FinOps và tối ưu chi phí Cloud",
        ],
    ),
    (
        "mang-may-tinh",
        "Mạng máy tính",
        "giao thức, định tuyến và chẩn đoán kết nối",
        [
            "Mạng máy tính từ TCP/IP đến HTTP",
            "Routing và Switching thực hành",
            "DNS, DHCP và dịch vụ mạng cốt lõi",
            "Thiết kế mạng doanh nghiệp an toàn",
            "Giám sát và xử lý sự cố mạng",
        ],
    ),
    (
        "he-dieu-hanh-linux",
        "Hệ điều hành & Linux",
        "tiến trình, hệ thống tệp và quản trị Linux",
        [
            "Linux cho Developer và SysAdmin",
            "Shell Script và tự động hóa công việc",
            "Tiến trình, bộ nhớ và hệ thống tệp",
            "Quản trị dịch vụ Linux với systemd",
            "Hardening và xử lý sự cố Linux",
        ],
    ),
    (
        "an-toan-thong-tin",
        "An toàn thông tin",
        "phòng thủ ứng dụng, hệ thống và dữ liệu theo nguyên tắc tối thiểu",
        [
            "Nhập môn An toàn thông tin",
            "Bảo mật Web theo OWASP Top 10",
            "Phân tích lỗ hổng và quản lý rủi ro",
            "Ứng cứu sự cố và điều tra số căn bản",
            "Mật mã ứng dụng và quản lý bí mật",
        ],
    ),
    (
        "cau-truc-du-lieu-giai-thuat",
        "Cấu trúc dữ liệu & Giải thuật",
        "lựa chọn cấu trúc và phân tích độ phức tạp",
        [
            "Cấu trúc dữ liệu với Python",
            "Giải thuật sắp xếp và tìm kiếm",
            "Cây, đồ thị và thuật toán duyệt",
            "Dynamic Programming từ cơ bản đến ứng dụng",
            "Luyện tư duy giải thuật và phân tích Big-O",
        ],
    ),
    (
        "kien-truc-thiet-ke-phan-mem",
        "Kiến trúc & Thiết kế phần mềm",
        "ranh giới hệ thống, khả năng thay đổi và quyết định kiến trúc",
        [
            "SOLID và Design Patterns thực hành",
            "Clean Architecture cho ứng dụng Backend",
            "Domain-Driven Design căn bản",
            "Microservices và giao tiếp phân tán",
            "Event-Driven Architecture và tính nhất quán",
        ],
    ),
    (
        "kiem-thu-phan-mem-qa",
        "Kiểm thử phần mềm & QA",
        "chiến lược chất lượng từ yêu cầu đến kiểm thử tự động",
        [
            "Manual Testing và thiết kế Test Case",
            "API Testing với Postman và Pytest",
            "Web E2E với Playwright",
            "Performance Testing và phân tích tải",
            "Xây dựng chiến lược QA trong CI/CD",
        ],
    ),
    (
        "thiet-ke-ui-ux",
        "Thiết kế UI/UX",
        "nghiên cứu người dùng, hệ thống giao diện và khả năng tiếp cận",
        [
            "Nền tảng UI/UX và tư duy thiết kế",
            "Figma từ Wireframe đến Prototype",
            "Design System và quản lý component",
            "UX Research và kiểm thử khả dụng",
            "Thiết kế giao diện Web dễ tiếp cận",
        ],
    ),
    (
        "iot-he-thong-nhung",
        "IoT & Hệ thống nhúng",
        "thiết bị, cảm biến và luồng dữ liệu đáng tin cậy",
        [
            "Arduino và điện tử căn bản",
            "ESP32 và giao tiếp cảm biến",
            "Embedded C cho vi điều khiển",
            "MQTT và kiến trúc nền tảng IoT",
            "Bảo mật và quản lý thiết bị IoT",
        ],
    ),
    (
        "blockchain-web3",
        "Blockchain & Web3",
        "sổ cái phân tán, hợp đồng thông minh và rủi ro bảo mật",
        [
            "Blockchain từ nguyên lý đến ứng dụng",
            "Smart Contract với Solidity",
            "Phát triển DApp với Ethereum",
            "Kiểm thử và bảo mật Smart Contract",
            "Thiết kế sản phẩm Web3 có trách nhiệm",
        ],
    ),
]

SPECIALTY_NAMES = [
    "Python và lập trình nền tảng",
    "Java và hệ sinh thái JVM",
    "JavaScript và TypeScript",
    "Vue và Nuxt",
    "React và Next.js",
    "Backend API và FastAPI",
    "Node.js Backend",
    "Mobile đa nền tảng",
    "Game Development",
    "Ứng dụng Desktop",
    "SQL và PostgreSQL",
    "Data Analytics",
    "Data Science",
    "Machine Learning",
    "Deep Learning",
    "NLP và Generative AI",
    "DevOps và CI/CD",
    "Cloud Architecture",
    "Mạng máy tính",
    "Linux và hệ điều hành",
    "Application Security",
    "Cấu trúc dữ liệu và giải thuật",
    "Software Architecture",
    "Quality Assurance",
    "UI/UX Design",
    "IoT và Embedded",
    "Blockchain và Smart Contract",
    "MLOps",
    "Data Engineering",
    "Distributed Systems",
]

PERSONAS = [
    ("official_persona_new", "Người học mới", []),
    ("official_persona_frontend", "Frontend Developer", [1, 2, 3, 21]),
    ("official_persona_backend", "Backend Developer", [0, 2, 7, 19]),
    ("official_persona_fullstack", "Fullstack Developer", [1, 2, 3, 13]),
    ("official_persona_ai", "AI và Machine Learning", [9, 10, 11, 12]),
    ("official_persona_data", "Data Science và Database", [7, 8, 9, 10]),
    ("official_persona_devops", "DevOps và Cloud", [13, 14, 16, 17]),
    ("official_persona_mobile", "Mobile Developer", [0, 4, 18, 20]),
]

PROVIDERS = [
    ("official_provider_foundations", "EduSuggest Learning Lab"),
    ("official_provider_web", "EduSuggest Web Studio"),
    ("official_provider_data", "EduSuggest Data Lab"),
    ("official_provider_ai", "EduSuggest AI Lab"),
    ("official_provider_cloud", "EduSuggest Cloud Practice"),
    ("official_provider_security", "EduSuggest Security Lab"),
    ("official_provider_design", "EduSuggest Design Studio"),
    ("official_provider_systems", "EduSuggest Systems Lab"),
]


def slugify(value: str) -> str:
    value = value.lower()
    substitutions = str.maketrans(
        "àáạảãâầấậẩẫăằắặẳẵèéẹẻẽêềếệểễìíịỉĩòóọỏõôồốộổỗơờớợởỡùúụủũưừứựửữỳýỵỷỹđ",
        "aaaaaaaaaaaaaaaaaeeeeeeeeeeeiiiiiooooooooooooooooouuuuuuuuuuuyyyyyd",
    )
    value = value.translate(substitutions)
    return re.sub(r"[^a-z0-9]+", "-", value).strip("-")


def make_svg(index: int, title: str, category: str, path: Path) -> None:
    navy, accent, canvas = PALETTES[index % len(PALETTES)]
    safe_title = html.escape(title)
    safe_category = html.escape(category.upper())
    words = title.split()
    lines = []
    current = ""
    for word in words:
        candidate = f"{current} {word}".strip()
        if len(candidate) > 34 and current:
            lines.append(current)
            current = word
        else:
            current = candidate
    if current:
        lines.append(current)
    lines = lines[:3]
    text_nodes = "".join(
        f'<text x="76" y="{290 + offset * 64}" font-size="48" font-weight="700" fill="{canvas}">{html.escape(line)}</text>'
        for offset, line in enumerate(lines)
    )
    motif = (index % 6) + 3
    svg = f'''<svg xmlns="http://www.w3.org/2000/svg" width="1200" height="675" viewBox="0 0 1200 675" role="img" aria-labelledby="title desc">
<title id="title">{safe_title}</title><desc id="desc">Ảnh bìa nguyên bản cho chủ đề {html.escape(category)}</desc>
<rect width="1200" height="675" fill="{navy}"/><rect x="52" y="52" width="1096" height="571" rx="28" fill="none" stroke="{accent}" stroke-width="3"/>
<circle cx="1030" cy="120" r="190" fill="{accent}" opacity=".16"/><circle cx="1100" cy="570" r="260" fill="{accent}" opacity=".10"/>
<path d="M870 160 L1100 300 L930 520 L760 365 Z" fill="none" stroke="{accent}" stroke-width="16" opacity=".72"/>
<path d="M820 250 L1050 390 M805 350 L1000 510" stroke="{canvas}" stroke-width="4" opacity=".35"/>
<text x="76" y="118" font-size="22" font-weight="700" letter-spacing="3" fill="{accent}">{safe_category}</text>
<text x="76" y="184" font-size="20" fill="{canvas}" opacity=".72">EDUSUGGEST LEARNING SERIES · {index + 1:03d}</text>
{text_nodes}
<g transform="translate(78 560)"><rect width="56" height="8" rx="4" fill="{accent}"/><rect x="72" width="{motif * 18}" height="8" rx="4" fill="{canvas}" opacity=".38"/></g>
</svg>'''
    path.write_text(svg, encoding="utf-8")


def lesson_body(course_title: str, category: str, stage: int) -> str:
    stages = [
        (
            "Nền tảng và mô hình tư duy",
            "giải thích thuật ngữ cốt lõi, thiết lập môi trường và nhận diện các sai lầm thường gặp",
        ),
        (
            "Thực hành có hướng dẫn",
            "phân rã yêu cầu, xây dựng từng phần, kiểm tra đầu ra và sửa lỗi có hệ thống",
        ),
        (
            "Bài toán tích hợp",
            "hoàn thiện một sản phẩm nhỏ, đánh giá chất lượng và lập kế hoạch cải tiến",
        ),
    ]
    heading, action = stages[stage]
    return (
        f"{heading} của khóa “{course_title}”. Bài học tập trung vào {category.lower()} và giúp người học {action}.\n\n"
        "Sau phần khái niệm, người học thực hiện một tình huống gần với công việc thực tế. Mỗi bước đều nêu rõ dữ liệu đầu vào, "
        "kết quả mong đợi, cách tự kiểm tra và tiêu chí hoàn thành; không yêu cầu sử dụng dịch vụ trả phí.\n\n"
        "Cuối bài có câu hỏi phản tư, bài tập mở rộng và danh sách điểm cần kiểm tra. Nội dung do nhóm EduSuggest tự biên soạn "
        "từ kiến thức kỹ thuật phổ quát và tài liệu chính thức được ghi trong manifest nguồn."
    )


def material_text(title: str, category: str, course_title: str | None) -> str:
    context = f"khóa học “{course_title}”" if course_title else f"chủ đề {category}"
    return (
        f"{title}\n{'=' * len(title)}\n\n"
        f"Phạm vi: {context}.\n\n"
        "Mục tiêu sử dụng\n- Ôn lại thuật ngữ trọng tâm.\n- Chuẩn bị môi trường thực hành.\n"
        "- Tự đánh giá kết quả bằng checklist có thể kiểm chứng.\n\n"
        "Checklist thực hành\n1. Ghi lại giả định và đầu vào.\n2. Thực hiện từng bước nhỏ và lưu bằng chứng.\n"
        "3. Kiểm tra lỗi, trường hợp biên và quyền truy cập.\n4. Tóm tắt điều đã học và câu hỏi còn mở.\n\n"
        "Nguồn gốc: Nội dung nguyên bản do EduSuggest tự biên soạn. Các URL tài liệu chính thức liên quan "
        "được quản lý riêng trong sources.json; tài liệu này không sao chép nội dung khóa học trả phí.\n"
    )


def build_dataset() -> dict:
    ensure_generated_directories()
    if not SOURCE_MANIFEST.exists():
        raise RuntimeError(
            "sources.json is missing; run collect_course_catalog.py first"
        )

    categories = []
    courses = []
    lessons = []
    materials = []
    asset_manifest = []
    course_index = 0
    for category_index, (slug, name, summary, titles) in enumerate(CATEGORIES):
        categories.append(
            {"key": slug, "name": name, "description": f"Nhóm kiến thức về {summary}."}
        )
        for position, title in enumerate(titles):
            key = f"course-{slug}-{position + 1}"
            cover_name = f"official-{course_index + 1:03d}-{slugify(title)[:58]}.svg"
            cover_path = COVER_DIR / cover_name
            make_svg(course_index, title, name, cover_path)
            status_cycle = [
                ("APPROVED", "VISIBLE"),
                ("APPROVED", "VISIBLE"),
                ("APPROVED", "VISIBLE"),
                ("APPROVED", "VISIBLE"),
                (
                    ["PENDING", "NEEDS_REVISION", "REJECTED"][category_index % 3],
                    "HIDDEN",
                ),
            ]
            approval, visibility = status_cycle[position]
            level = [
                "BEGINNER",
                "INTERMEDIATE",
                "INTERMEDIATE",
                "ADVANCED",
                "ALL_LEVELS",
            ][position]
            courses.append(
                {
                    "key": key,
                    "title": title,
                    "description": (
                        f"Khóa học {title} cung cấp lộ trình có cấu trúc về {summary}. "
                        "Người học đi từ nguyên lý, thực hành có hướng dẫn đến một bài toán tích hợp; mỗi phần đều có tiêu chí tự kiểm tra. "
                        f"Nội dung nhấn mạnh khả năng áp dụng, tính an toàn và cách giải thích quyết định kỹ thuật trong lĩnh vực {name}."
                    ),
                    "category_key": slug,
                    "provider_key": PROVIDERS[course_index % len(PROVIDERS)][0],
                    "cover": f"/media/courses/{cover_name}",
                    "price": 0
                    if course_index % 7 == 0
                    else 199000 + (course_index % 6) * 100000,
                    "level": level,
                    "duration_minutes": 360 + (course_index % 7) * 90,
                    "approval_status": approval,
                    "visibility_status": visibility,
                    "keywords": list(
                        dict.fromkeys((title + " " + name).replace("&", " ").split())
                    )[:12],
                    "source_type": "original_editorial_content",
                }
            )
            asset_manifest.append(
                {
                    "type": "course_cover",
                    "key": key,
                    "path": str(cover_path.relative_to(COVER_DIR.parent)),
                    "sha256": sha256_file(cover_path),
                    "license": "Original EduSuggest asset",
                }
            )
            for stage in range(3):
                lessons.append(
                    {
                        "key": f"{key}-lesson-{stage + 1}",
                        "course_key": key,
                        "title": [
                            "Nền tảng và thiết lập",
                            "Thực hành có hướng dẫn",
                            "Bài toán tích hợp và đánh giá",
                        ][stage]
                        + f": {title}",
                        "content": lesson_body(title, name, stage),
                        "video_url": None,
                        "duration_minutes": 35 + stage * 15 + (course_index % 4) * 5,
                        "order": stage + 1,
                    }
                )
            material_key = f"material-{key}"
            material_name = f"{material_key}.txt"
            material_path = MATERIAL_DIR / material_name
            material_title = f"Sổ tay thực hành – {title}"
            material_path.write_text(
                material_text(material_title, name, title), encoding="utf-8"
            )
            materials.append(
                {
                    "key": material_key,
                    "title": material_title,
                    "description": f"Checklist và bài tập nguyên bản hỗ trợ khóa học {title}.",
                    "course_key": key,
                    "lesson_key": f"{key}-lesson-2",
                    "category_key": slug,
                    "provider_key": PROVIDERS[course_index % len(PROVIDERS)][0],
                    "file": material_name,
                    "content_type": "text/plain",
                    "kind": "TEXT",
                    "approval_status": approval,
                    "visibility_status": visibility,
                    "source_type": "original_editorial_content",
                }
            )
            asset_manifest.append(
                {
                    "type": "learning_material",
                    "key": material_key,
                    "path": str(material_path.relative_to(MATERIAL_DIR.parent)),
                    "sha256": sha256_file(material_path),
                    "license": "Original EduSuggest content",
                }
            )
            course_index += 1

    for index, specialty in enumerate(SPECIALTY_NAMES):
        category = CATEGORIES[index % len(CATEGORIES)]
        key = f"standalone-{index + 1:02d}-{slugify(specialty)}"
        filename = f"{key}.txt"
        path = MATERIAL_DIR / filename
        title = f"Phiếu tự học: {specialty}"
        path.write_text(material_text(title, category[1], None), encoding="utf-8")
        materials.append(
            {
                "key": key,
                "title": title,
                "description": f"Tài liệu độc lập tự biên soạn cho chuyên môn {specialty}.",
                "course_key": None,
                "lesson_key": None,
                "category_key": category[0],
                "provider_key": PROVIDERS[index % len(PROVIDERS)][0],
                "file": filename,
                "content_type": "text/plain",
                "kind": "TEXT",
                "approval_status": "APPROVED",
                "visibility_status": "VISIBLE",
                "source_type": "original_editorial_content",
            }
        )
        asset_manifest.append(
            {
                "type": "learning_material",
                "key": key,
                "path": str(path.relative_to(MATERIAL_DIR.parent)),
                "sha256": sha256_file(path),
                "license": "Original EduSuggest content",
            }
        )

    experts = []
    for index in range(20):
        experts.append(
            {
                "username": f"official_expert_{index + 1:02d}",
                "display_name": f"Chuyên gia mô phỏng {index + 1:02d}",
                "bio": "Hồ sơ tổng hợp phục vụ trình diễn và kiểm thử nghiệp vụ EduSuggest; không đại diện cho một cá nhân thật.",
                "years_experience": 3 + (index % 9),
                "profile_status": "VERIFIED" if index < 16 else "DRAFT",
                "specialties": [
                    SPECIALTY_NAMES[index % 30],
                    SPECIALTY_NAMES[(index + 7) % 30],
                ],
                "synthetic": True,
            }
        )

    learners = [
        {
            "username": username,
            "display_name": name,
            "persona_categories": category_indexes,
            "synthetic": True,
        }
        for username, name, category_indexes in PERSONAS
    ]
    for index in range(42):
        learners.append(
            {
                "username": f"official_learner_{index + 1:02d}",
                "display_name": f"Người học mô phỏng {index + 1:02d}",
                "persona_categories": [(index * 5) % 24, (index * 5 + 1) % 24],
                "synthetic": True,
            }
        )

    dataset = {
        "dataset_id": "edusuggest-official-v1",
        "generated_at": datetime.now(UTC).isoformat(),
        "provenance": {
            "course_metadata": "Original Vietnamese editorial content informed by public taxonomy references in sources.json",
            "lesson_content": "Original EduSuggest authored content",
            "covers": "Original deterministic SVG assets; no third-party logo or hotlink",
            "profiles": "Synthetic personas; not real identities or credentials",
            "interactions": "Simulated learning histories; not observed user behaviour",
        },
        "targets": {
            "categories": 24,
            "courses": 120,
            "covers": 120,
            "lessons": 360,
            "materials": 150,
            "specialties": 30,
            "experts": 20,
            "providers": 8,
            "learners": 50,
            "enrollments": 150,
            "history": 300,
        },
        "categories": categories,
        "providers": [
            {"username": username, "display_name": display_name, "synthetic": True}
            for username, display_name in PROVIDERS
        ],
        "specialties": [
            {
                "key": slugify(name),
                "name": name,
                "category_keys": [
                    CATEGORIES[index % 24][0],
                    CATEGORIES[(index + 1) % 24][0],
                ],
            }
            for index, name in enumerate(SPECIALTY_NAMES)
        ],
        "experts": experts,
        "learners": learners,
        "courses": courses,
        "lessons": lessons,
        "materials": materials,
        "assets": asset_manifest,
    }
    return dataset


def validate_generated(dataset: dict) -> list[str]:
    errors = []
    expected = dataset["targets"]
    checks = {
        "categories": len(dataset["categories"]),
        "courses": len(dataset["courses"]),
        "covers": sum(
            1 for item in dataset["assets"] if item["type"] == "course_cover"
        ),
        "lessons": len(dataset["lessons"]),
        "materials": len(dataset["materials"]),
        "specialties": len(dataset["specialties"]),
        "experts": len(dataset["experts"]),
        "providers": len(dataset["providers"]),
        "learners": len(dataset["learners"]),
    }
    for key, actual in checks.items():
        if actual != expected[key]:
            errors.append(f"{key}: expected {expected[key]}, got {actual}")
    keys = []
    for section in ("categories", "courses", "lessons", "materials"):
        section_keys = [item["key"] for item in dataset[section]]
        if len(section_keys) != len(set(section_keys)):
            errors.append(f"Duplicate keys in {section}")
        keys.extend(section_keys)
    for asset in dataset["assets"]:
        root = (
            COVER_DIR.parent if asset["type"] == "course_cover" else MATERIAL_DIR.parent
        )
        path = root / asset["path"]
        if not path.is_file() or sha256_file(path) != asset["sha256"]:
            errors.append(f"Missing or invalid asset: {path}")
    return errors


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=DATASET_MANIFEST)
    args = parser.parse_args()
    dataset = build_dataset()
    errors = validate_generated(dataset)
    if errors:
        raise SystemExit("Dataset preparation failed:\n- " + "\n- ".join(errors))
    write_json(args.output, dataset)
    print(f"Prepared official dataset manifest: {args.output}")
    for key in (
        "categories",
        "courses",
        "lessons",
        "materials",
        "specialties",
        "experts",
        "providers",
        "learners",
    ):
        print(f"  {key}: {len(dataset[key])}")
    print(f"  assets: {len(dataset['assets'])}; validation: PASS")


if __name__ == "__main__":
    main()
