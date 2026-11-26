"""Seed script for EduSuggest recommendation test dataset.

SAFETY GUARDRAILS:
1. Rejects execution if current database matches the production or primary database ('EduSuggest').
2. Requires explicit test database: EDUSUGGEST_TEST_DB_NAME or --target-db (e.g. 'EduSuggest_test').
3. Requires explicit command-line confirmation flag: --confirm-seed-test-data or --dry-run.
4. Fully idempotent: checks existing entities by unique keys before insertion.
5. Atomic transaction: rolls back completely on any unexpected error.
"""

from __future__ import annotations

import argparse
import os
import sys
from datetime import UTC, datetime
from decimal import Decimal

from sqlalchemy import create_engine, select, text
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session, sessionmaker

# Add backend directory to sys.path if not present
BACKEND_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if BACKEND_DIR not in sys.path:
    sys.path.insert(0, BACKEND_DIR)

from config.config import get_settings
from models import (
    BaiHoc,
    ChuyenGia,
    DangKyKhoaHoc,
    DanhMuc,
    KhoaHoc,
    LichSuHocTap,
    NguoiDung,
    NhaCungCapKhoaHoc,
    TaiLieu,
    VaiTro,
)
from utils.security import hash_password

PROD_DATABASE_NAMES = frozenset({"edusuggest", "production", "postgres", "defaultdb"})

DEFAULT_ROLES = [
    ("ADMIN", "Quản trị viên hệ thống"),
    ("USER", "Người học / Người dùng thông thường"),
    ("PROVIDER", "Nhà cung cấp nội dung khóa học"),
    ("EXPERT", "Chuyên gia kiểm duyệt nội dung"),
]

# ---------------------------------------------------------------------------
# Dataset Definitions
# ---------------------------------------------------------------------------

CATEGORIES_DATA = [
    {
        "id": 1,
        "ten": "Lập trình Web Frontend",
        "mota": "Phát triển giao diện web hiện đại với HTML5, CSS3, JavaScript, TypeScript, Vue.js, React và tối ưu hóa trải nghiệm người dùng UI/UX.",
    },
    {
        "id": 2,
        "ten": "Lập trình Web Backend",
        "mota": "Xây dựng hệ thống máy chủ, RESTful API, kiến trúc Microservices hiệu năng cao với Python FastAPI, Node.js, Go và xử lý dữ liệu backend.",
    },
    {
        "id": 3,
        "ten": "Cơ sở dữ liệu & SQL",
        "mota": "Thiết kế, quản trị, tối ưu hóa truy vấn cơ sở dữ liệu quan hệ PostgreSQL, MySQL và giải pháp lưu trữ NoSQL.",
    },
    {
        "id": 4,
        "ten": "Phát triển ứng dụng Di động",
        "mota": "Lập trình ứng dụng di động đa nền tảng cho iOS và Android sử dụng Flutter, React Native và Swift/Kotlin Native.",
    },
    {
        "id": 5,
        "ten": "Khoa học dữ liệu & Machine Learning",
        "mota": "Phân tích dữ liệu, trực quan hóa, học máy Machine Learning, xử lý ngôn ngữ tự nhiên NLP và thuật toán trí tuệ nhân tạo với Python.",
    },
    {
        "id": 6,
        "ten": "DevOps & Điện toán đám mây",
        "mota": "Quy trình CI/CD tự động, ảo hóa container Docker, điều phối Kubernetes, triển khai Cloud GCP/AWS và quản lý hạ tầng.",
    },
]

USERS_DATA = [
    {
        "username": "provider_demo",
        "fullname": "Giảng Viên Kỹ Thuật Demo",
        "email": "provider_demo@edusuggest.edu.vn",
        "role": "PROVIDER",
        "bio": "Chuyên gia đào tạo kỹ thuật công nghệ phần mềm và kiến trúc phân tán.",
        "specialty": "Full-stack Web & Cloud Architecture",
    },
    {
        "username": "expert_demo",
        "fullname": "Chuyên Gia Kiểm Duyệt Demo",
        "email": "expert_demo@edusuggest.edu.vn",
        "role": "EXPERT",
        "bio": "Hội đồng kiểm duyệt chất lượng nội dung học thuật đại học.",
        "specialty": "Curriculum Quality Assurance",
    },
    {
        "username": "learner_frontend_newbie",
        "fullname": "Học Viên Mới Chưa Có Lịch Sử",
        "email": "newbie@edusuggest.edu.vn",
        "role": "USER",
    },
    {
        "username": "learner_vue_specialist",
        "fullname": "Học Viên Chuyên Sâu Vue Frontend",
        "email": "vue_specialist@edusuggest.edu.vn",
        "role": "USER",
    },
    {
        "username": "learner_fullstack_hybrid",
        "fullname": "Học Viên Full-Stack Đa Sở Thích",
        "email": "fullstack_hybrid@edusuggest.edu.vn",
        "role": "USER",
    },
]

COURSES_DATA = [
    {
        "key": "c1",
        "category_idx": 1,
        "title": "Lập trình Vue.js 3 và Tailwind CSS từ Cơ bản đến Nâng cao",
        "description": "Khóa học toàn diện hướng dẫn phát triển ứng dụng Single Page Application với Vue 3, Vite, Tailwind CSS, Component thiết kế giao diện hiện đại.",
        "level": "Beginner",
        "duration": 1200,
        "price": Decimal(599000),
        "review_status": "APPROVED",
        "visibility": "VISIBLE",
        "lessons": [
            {
                "title": "Giới thiệu Kiến trúc Vue 3 và Thiết lập Dự án Vite",
                "content": "Tổng quan về Vue 3, cấu trúc thư mục Vite, làm quen với Single File Component và cú pháp template declarative.",
                "duration": 45,
                "order": 1,
                "materials": [
                    {
                        "title": "Slide Tổng quan Kiến trúc Vue 3 và Vite",
                        "type": "SLIDE",
                        "desc": "Tài liệu trình chiếu bài giảng kiến trúc Vue 3.",
                    },
                    {
                        "title": "Cheatsheet Phím tắt và Cú pháp Vue 3",
                        "type": "CHEATSHEET",
                        "desc": "Bảng tra cứu nhanh cú pháp template và reactivity.",
                    },
                ],
            },
            {
                "title": "Reactivity Core: Ref, Reactive và Computed Properties",
                "content": "Hiểu sâu về cơ chế phản ứng hai chiều trong Vue 3, quản lý trạng thái component cục bộ với ref và computed tối ưu hiệu năng.",
                "duration": 60,
                "order": 2,
                "materials": [
                    {
                        "title": "Source Code Mẫu Thực hành Reactivity",
                        "type": "CODE",
                        "desc": "Mã nguồn bài tập thực hành ref và reactive.",
                    },
                    {
                        "title": "Bài tập Thực hành Reactivity State",
                        "type": "PDF",
                        "desc": "Đề bài và hướng dẫn tự giải bài tập phản ứng dữ liệu.",
                    },
                ],
            },
            {
                "title": "Tạo Component Tái sử dụng và Tích hợp Tailwind CSS",
                "content": "Xây dựng hệ thống UI kit gồm Button, Modal, Card tái sử dụng cao, áp dụng Utility-first CSS với Tailwind CSS chuẩn responsive.",
                "duration": 75,
                "order": 3,
                "materials": [
                    {
                        "title": "Hướng dẫn Cấu hình Tailwind CSS trong Vite",
                        "type": "DOCX",
                        "desc": "Tài liệu các bước thiết lập và tùy biến theme Tailwind.",
                    },
                ],
            },
        ],
    },
    {
        "key": "c2",
        "category_idx": 1,
        "title": "Xây dựng Single Page App với Vue 3 Composition API và Pinia State Management",
        "description": "Làm chủ Composition API, kiến trúc module, quản lý trạng thái tập trung với Pinia, tối ưu hóa định tuyến Vue Router và xác thực người dùng frontend.",
        "level": "Intermediate",
        "duration": 1500,
        "price": Decimal(799000),
        "review_status": "APPROVED",
        "visibility": "VISIBLE",
        "lessons": [
            {
                "title": "Kiến trúc State Management với Pinia Store",
                "content": "Thiết kế state, getters, actions trong Pinia, đồng bộ hóa trạng thái ứng dụng lớn và tích hợp devtools kiểm thử.",
                "duration": 90,
                "order": 1,
                "materials": [
                    {
                        "title": "Pinia Architecture Pattern Guide",
                        "type": "PDF",
                        "desc": "Sổ tay thiết kế kiến trúc Pinia Store cho ứng dụng doanh nghiệp.",
                    },
                ],
            },
        ],
    },
    {
        "key": "c3",
        "category_idx": 1,
        "title": "Thiết kế Giao diện UI/UX Hiện đại với React và Next.js",
        "description": "Học React 18 hooks, Server Components, server-side rendering với Next.js App Router và thư viện giao diện Tailwind CSS.",
        "level": "Beginner",
        "duration": 1080,
        "price": Decimal(650000),
        "review_status": "APPROVED",
        "visibility": "VISIBLE",
        "lessons": [
            {
                "title": "Khởi tạo Ứng dụng Next.js với Server Components",
                "content": "Cơ chế Render phía máy chủ SSR, Client Components, cấu trúc định tuyến thư mục app router hiện đại.",
                "duration": 60,
                "order": 1,
                "materials": [
                    {
                        "title": "Next.js App Router Cheatsheet",
                        "type": "CHEATSHEET",
                        "desc": "Bảng tổng hợp routing và server actions Next.js.",
                    },
                ],
            },
        ],
    },
    {
        "key": "c4",
        "category_idx": 2,
        "title": "Lập trình Web Backend Hiện đại với Python FastAPI và SQLAlchemy",
        "description": "Xây dựng Backend RESTful API tốc độ cao bằng Python FastAPI, tích hợp SQLAlchemy 2.0 ORM, PostgreSQL connection pooling và Alembic migration.",
        "level": "Intermediate",
        "duration": 1800,
        "price": Decimal(899000),
        "review_status": "APPROVED",
        "visibility": "VISIBLE",
        "lessons": [
            {
                "title": "Tổng quan FastAPI, Pydantic V2 và Asynchronous Python",
                "content": "Nguyên lý lập trình bất đồng bộ async await, validation dữ liệu tự động với Pydantic model và tự động sinh Swagger OpenAPI docs.",
                "duration": 60,
                "order": 1,
                "materials": [
                    {
                        "title": "FastAPI Architecture Blueprint",
                        "type": "PDF",
                        "desc": "Tài liệu kiến trúc phân tầng Controller - Service - Repository trong FastAPI.",
                    },
                    {
                        "title": "Source Code Starter Template FastAPI",
                        "type": "CODE",
                        "desc": "Mã nguồn khung dự án chuẩn kiến trúc sạch.",
                    },
                ],
            },
            {
                "title": "Tích hợp SQLAlchemy 2.0 ORM và PostgreSQL Connection Pool",
                "content": "Thiết lập engine, session management, tối ưu hóa câu truy vấn N+1, eager loading relations và database transaction rollback an toàn.",
                "duration": 80,
                "order": 2,
                "materials": [
                    {
                        "title": "SQLAlchemy 2.0 Query Patterns",
                        "type": "PDF",
                        "desc": "Hướng dẫn viết truy vấn select hiện đại và quan hệ 1-N, N-N.",
                    },
                    {
                        "title": "Database Migration Script Template",
                        "type": "CODE",
                        "desc": "Kịch bản mẫu tích hợp Alembic cho PostgreSQL.",
                    },
                ],
            },
            {
                "title": "Xác thực JWT Token và Phân quyền Role-based Access Control",
                "content": "Triển khai cơ chế cấp phát Access Token, Refresh Token, blacklist token đã thu hồi và bảo mật endpoint theo vai trò người dùng.",
                "duration": 75,
                "order": 3,
                "materials": [
                    {
                        "title": "Security & JWT Checklist",
                        "type": "PDF",
                        "desc": "Danh sách kiểm tra an toàn bảo mật cho API doanh nghiệp.",
                    },
                ],
            },
        ],
    },
    {
        "key": "c5",
        "category_idx": 2,
        "title": "Xây dựng RESTful API và Microservices Hiệu năng cao với FastAPI",
        "description": "Nâng cao kỹ năng kiến trúc Microservices với Python FastAPI, message broker RabbitMQ, caching Redis và container hóa Docker.",
        "level": "Advanced",
        "duration": 2100,
        "price": Decimal(1200000),
        "review_status": "APPROVED",
        "visibility": "VISIBLE",
        "lessons": [
            {
                "title": "Kiến trúc Hướng sự kiện Event-Driven với Redis Stream",
                "content": "Thiết kế hệ thống giao tiếp bất đồng bộ giữa các service, xử lý background task và message queue tin cậy.",
                "duration": 90,
                "order": 1,
                "materials": [
                    {
                        "title": "Microservices Communication Diagram",
                        "type": "SLIDE",
                        "desc": "Sơ đồ kiến trúc luồng dữ liệu microservices.",
                    },
                ],
            },
        ],
    },
    {
        "key": "c6",
        "category_idx": 3,
        "title": "Quản trị và Tối ưu hóa Cơ sở dữ liệu PostgreSQL Chuyên sâu",
        "description": "Khóa học quản trị cơ sở dữ liệu quan hệ PostgreSQL, thiết kế index B-Tree, GIN, phân tích câu lệnh EXPLAIN ANALYZE và partition bảng lớn.",
        "level": "Advanced",
        "duration": 1440,
        "price": Decimal(950000),
        "review_status": "APPROVED",
        "visibility": "VISIBLE",
        "lessons": [
            {
                "title": "Chiến lược Đánh chỉ mục Indexing và Đọc Execution Plan",
                "content": "Phân tích chi tiết chi phí truy vấn, phân biệt Sequential Scan và Index Scan, kỹ thuật tối ưu hóa câu truy vấn chậm.",
                "duration": 90,
                "order": 1,
                "materials": [
                    {
                        "title": "PostgreSQL Indexing Mastery Guide",
                        "type": "PDF",
                        "desc": "Cẩm nang chuyên sâu về các loại index trong PostgreSQL.",
                    },
                ],
            },
        ],
    },
    {
        "key": "c7",
        "category_idx": 4,
        "title": "Lập trình Ứng dụng Di động Đa nền tảng với Flutter và Dart",
        "description": "Học lập trình ứng dụng di động iOS và Android bằng Flutter framework, ngôn ngữ Dart, state management Bloc và xuất bản ứng dụng.",
        "level": "Beginner",
        "duration": 1600,
        "price": Decimal(699000),
        "review_status": "APPROVED",
        "visibility": "VISIBLE",
        "lessons": [
            {
                "title": "Xây dựng Giao diện Widget và Điều hướng Màn hình",
                "content": "Các khái niệm StatelessWidget, StatefulWidget, xây dựng layout thích ứng trên nhiều kích thước màn hình smartphone.",
                "duration": 60,
                "order": 1,
                "materials": [
                    {
                        "title": "Flutter Widget Cheatsheet",
                        "type": "CHEATSHEET",
                        "desc": "Bảng tra cứu nhanh các layout widget phổ biến nhất.",
                    },
                ],
            },
        ],
    },
    {
        "key": "c8",
        "category_idx": 5,
        "title": "Nhập môn Khoa học Dữ liệu và Phân tích Dữ liệu với Python Pandas",
        "description": "Nhập môn khoa học dữ liệu Data Science cho người mới bắt đầu, thao tác dữ liệu với Pandas DataFrame, NumPy và làm sạch dữ liệu thực tế.",
        "level": "Beginner",
        "duration": 1350,
        "price": Decimal(750000),
        "review_status": "APPROVED",
        "visibility": "VISIBLE",
        "lessons": [
            {
                "title": "Làm sạch và Tiền xử lý Dữ liệu Khuyết thiếu với Pandas",
                "content": "Xử lý giá trị null, lọc dữ liệu trùng lặp, chuẩn hóa kiểu dữ liệu số và xử lý chuỗi ký tự trong tập dữ liệu lớn.",
                "duration": 70,
                "order": 1,
                "materials": [
                    {
                        "title": "Jupyter Notebook Thực hành Làm sạch Dữ liệu",
                        "type": "CODE",
                        "desc": "File thực hành notebook kèm bộ dữ liệu CSV mẫu.",
                    },
                    {
                        "title": "Pandas Data Wrangling Cheatsheet",
                        "type": "CHEATSHEET",
                        "desc": "Bảng tóm tắt các hàm biến đổi dữ liệu Pandas.",
                    },
                ],
            },
            {
                "title": "Trực quan hóa Dữ liệu Khoa học với Matplotlib và Seaborn",
                "content": "Vẽ biểu đồ phân bố histogram, biểu đồ tương quan scatter plot, heatmap ma trận tương quan và định dạng báo cáo phân tích.",
                "duration": 65,
                "order": 2,
                "materials": [
                    {
                        "title": "Visualization Best Practices",
                        "type": "PDF",
                        "desc": "Nguyên tắc chọn loại biểu đồ phù hợp cho từng loại biến số.",
                    },
                ],
            },
            {
                "title": "Quy trình Phân tích Dữ liệu Khám phá EDA Toàn diện",
                "content": "Thực hiện đồ án EDA trên dữ liệu thực tế, rút ra các insight kinh doanh và chuẩn bị dữ liệu đầu vào cho mô hình học máy.",
                "duration": 80,
                "order": 3,
                "materials": [
                    {
                        "title": "Bộ Dataset Mẫu Khảo sát Giáo dục",
                        "type": "DATASET",
                        "desc": "Tập dữ liệu CSV phục vụ phân tích dự án cuối khóa.",
                    },
                ],
            },
        ],
    },
    {
        "key": "c9",
        "category_idx": 5,
        "title": "Machine Learning Cơ bản và Ứng dụng Thuật toán Học máy với Scikit-Learn",
        "description": "Hiểu và áp dụng các thuật toán học máy giám sát và không giám sát: Hồi quy tuyến tính, Phân loại Logistic Regression, Cây quyết định và K-Means.",
        "level": "Intermediate",
        "duration": 1900,
        "price": Decimal(1100000),
        "review_status": "APPROVED",
        "visibility": "VISIBLE",
        "lessons": [
            {
                "title": "Thuật toán Phân loại Classification và Đánh giá Mô hình",
                "content": "Đo lường độ chính xác Accuracy, Precision, Recall, F1-Score, vẽ ma trận nhầm lẫn Confusion Matrix với thư viện Scikit-Learn.",
                "duration": 85,
                "order": 1,
                "materials": [
                    {
                        "title": "Machine Learning Evaluation Metrics Guide",
                        "type": "PDF",
                        "desc": "Tài liệu giải thích trực quan các chỉ số đánh giá mô hình học máy.",
                    },
                ],
            },
        ],
    },
    {
        "key": "c10",
        "category_idx": 6,
        "title": "Triển khai CI/CD và Tự động hóa Hạ tầng với Docker và Kubernetes",
        "description": "Tự động hóa chu trình phát hành phần mềm với GitHub Actions, đóng gói ứng dụng container Docker và điều phối cụm Kubernetes.",
        "level": "Intermediate",
        "duration": 1650,
        "price": Decimal(850000),
        "review_status": "APPROVED",
        "visibility": "VISIBLE",
        "lessons": [
            {
                "title": "Tối ưu hóa Dockerfile Đa tầng Multi-stage Build",
                "content": "Kỹ thuật giảm kích thước image Docker, quản lý biến môi trường an toàn và cấu hình container chạy quyền non-root.",
                "duration": 70,
                "order": 1,
                "materials": [
                    {
                        "title": "Docker Best Practices Cheatsheet",
                        "type": "CHEATSHEET",
                        "desc": "Hướng dẫn viết Dockerfile chuẩn công nghiệp.",
                    },
                ],
            },
        ],
    },
    {
        "key": "c11_hidden",
        "category_idx": 1,
        "title": "Bí quyết Lập trình Web Full-Stack Nâng cao (Khóa học đang biên soạn)",
        "description": "Nội dung nâng cao tích hợp Frontend và Backend đang trong giai đoạn hoàn thiện giao diện, ẩn tạm thời với học viên.",
        "level": "Advanced",
        "duration": 900,
        "price": Decimal(450000),
        "review_status": "APPROVED",
        "visibility": "HIDDEN",  # MUST NOT BE RECOMMENDED
        "lessons": [],
    },
    {
        "key": "c12_pending",
        "category_idx": 2,
        "title": "Lập trình Hệ thống với Rust và WebAssembly (Bản nháp chờ kiểm duyệt)",
        "description": "Khóa học Rust hiệu năng cao đang gửi lên hội đồng kiểm duyệt nội dung, chưa có quyết định phê duyệt chính thức.",
        "level": "Advanced",
        "duration": 1200,
        "price": Decimal(990000),
        "review_status": "PENDING",  # MUST NOT BE RECOMMENDED
        "visibility": "VISIBLE",
        "lessons": [],
    },
    {
        "key": "c13_rejected",
        "category_idx": 6,
        "title": "Hacker Mũ Trắng và Tấn công Thử nghiệm Web (Bị từ chối kiểm duyệt)",
        "description": "Nội dung vi phạm tiêu chuẩn chính sách bảo mật của nền tảng, đã bị chuyên gia từ chối phê duyệt.",
        "level": "Beginner",
        "duration": 600,
        "price": Decimal(300000),
        "review_status": "REJECTED",  # MUST NOT BE RECOMMENDED
        "visibility": "HIDDEN",
        "lessons": [],
    },
]


def check_target_database_safety(
    db: Session, allowed_db_name: str | None = None
) -> str:
    """Verify that we are not targeting the primary/production database.

    Raises RuntimeError if database name is unsafe. Returns confirmed database name.
    """
    current_db = db.execute(text("SELECT current_database();")).scalar()
    if not current_db:
        raise RuntimeError("Unable to determine current connected database.")

    current_db_lower = current_db.lower().strip()

    # Safety Check 1: Deny known production databases
    if current_db_lower in PROD_DATABASE_NAMES:
        raise RuntimeError(
            f"SECURITY GUARDRAIL VIOLATION: Current database is '{current_db}', which is "
            "designated as primary/production. Seeding is strictly forbidden."
        )

    # Safety Check 2: If an explicit test database name was configured, require exact match
    if allowed_db_name:
        if current_db_lower != allowed_db_name.lower().strip():
            raise RuntimeError(
                f"SECURITY GUARDRAIL VIOLATION: Current database '{current_db}' does not match "
                f"the explicitly required test database '{allowed_db_name}'."
            )
    else:
        # Default policy: must contain 'test' in the name
        if "test" not in current_db_lower:
            raise RuntimeError(
                f"SECURITY GUARDRAIL VIOLATION: Current database '{current_db}' does not contain "
                "'test' in its name. Aborting seed operation."
            )

    return current_db


def seed_test_dataset(db: Session, dry_run: bool = False) -> dict[str, int]:
    """Populate recommendation test dataset safely and idempotently.

    Returns a summary of created or reused entities.
    """
    stats = {
        "roles_initialized": 0,
        "categories_created": 0,
        "users_created": 0,
        "courses_created": 0,
        "lessons_created": 0,
        "materials_created": 0,
        "enrollments_created": 0,
        "history_created": 0,
    }

    # 1. Initialize default roles if missing
    for r_name, r_desc in DEFAULT_ROLES:
        existing_role = db.scalar(
            select(VaiTro).where(VaiTro.tenVaiTro == r_name).limit(1)
        )
        if not existing_role:
            db.add(VaiTro(tenVaiTro=r_name, moTa=r_desc))
            stats["roles_initialized"] += 1
    db.flush()

    # Fetch role mapping
    roles = {
        r.tenVaiTro.upper(): r.maVaiTro
        for r in db.scalars(select(VaiTro)).all()
        if r.tenVaiTro
    }
    for role_name in ("ADMIN", "USER", "PROVIDER", "EXPERT"):
        if role_name not in roles:
            raise RuntimeError(f"Missing required role '{role_name}' in VaiTro table.")

    # 2. Seed Categories
    category_map: dict[int, DanhMuc] = {}
    for cat_data in CATEGORIES_DATA:
        existing = db.scalar(
            select(DanhMuc).where(DanhMuc.tenDanhMuc == cat_data["ten"]).limit(1)
        )
        if existing:
            category_map[cat_data["id"]] = existing
        else:
            cat = DanhMuc(tenDanhMuc=cat_data["ten"], moTa=cat_data["mota"])
            db.add(cat)
            db.flush()
            category_map[cat_data["id"]] = cat
            stats["categories_created"] += 1

    # 3. Seed Users
    user_map: dict[str, NguoiDung] = {}
    now = datetime.now(UTC)
    for u_data in USERS_DATA:
        username = u_data["username"].lower()
        existing_user = db.scalar(
            select(NguoiDung).where(NguoiDung.tenTaiKhoan == username).limit(1)
        )
        if existing_user:
            user_map[username] = existing_user
        else:
            new_user = NguoiDung(
                tenTaiKhoan=username,
                hoTen=u_data["fullname"],
                email=u_data["email"],
                matKhau=hash_password("TestPassword123!"),
                maVaiTro=roles[u_data["role"]],
            )
            db.add(new_user)
            db.flush()
            user_map[username] = new_user
            stats["users_created"] += 1

            if u_data["role"] == "PROVIDER":
                prov = db.scalar(
                    select(NhaCungCapKhoaHoc)
                    .where(NhaCungCapKhoaHoc.maNguoiDung == new_user.maNguoiDung)
                    .limit(1)
                )
                if not prov:
                    db.add(
                        NhaCungCapKhoaHoc(
                            maNguoiDung=new_user.maNguoiDung,
                            tieuSu=u_data.get("bio"),
                            chuyenMon=u_data.get("specialty"),
                        )
                    )
            elif u_data["role"] == "EXPERT":
                exp = db.scalar(
                    select(ChuyenGia)
                    .where(ChuyenGia.maNguoiDung == new_user.maNguoiDung)
                    .limit(1)
                )
                if not exp:
                    db.add(
                        ChuyenGia(
                            maNguoiDung=new_user.maNguoiDung,
                            tieuSu=u_data.get("bio"),
                            chuyenMon=u_data.get("specialty"),
                        )
                    )

    # Fetch provider & expert records
    provider_user = user_map.get("provider_demo")
    provider_record = None
    if provider_user:
        provider_record = db.scalar(
            select(NhaCungCapKhoaHoc)
            .where(NhaCungCapKhoaHoc.maNguoiDung == provider_user.maNguoiDung)
            .limit(1)
        )
    expert_user = user_map.get("expert_demo")

    # 4. Seed Courses, Lessons, Materials
    course_map: dict[str, KhoaHoc] = {}
    for c_data in COURSES_DATA:
        existing_course = db.scalar(
            select(KhoaHoc).where(KhoaHoc.tieuDe == c_data["title"]).limit(1)
        )
        cat = category_map.get(c_data["category_idx"])
        if existing_course:
            course_map[c_data["key"]] = existing_course
        else:
            course = KhoaHoc(
                maNhaCungCap=provider_record.maNhaCungCap if provider_record else None,
                maDanhMuc=cat.maDanhMuc if cat else None,
                maNguoiDuyet=expert_user.maNguoiDung
                if (expert_user and c_data["review_status"] == "APPROVED")
                else None,
                tieuDe=c_data["title"],
                moTa=c_data["description"],
                gia=c_data["price"],
                trinhDo=c_data["level"],
                thoiLuong=c_data["duration"],
                trangThaiDuyet=c_data["review_status"],
                trangThaiHienThi=c_data["visibility"],
                ngayDuyet=now if c_data["review_status"] == "APPROVED" else None,
                ngayTao=now,
                ngayCapNhat=now,
            )
            db.add(course)
            db.flush()
            course_map[c_data["key"]] = course
            stats["courses_created"] += 1

            # Seed lessons and materials
            for lesson_data in c_data.get("lessons", []):
                lesson = BaiHoc(
                    maKhoaHoc=course.maKhoaHoc,
                    tieuDe=lesson_data["title"],
                    noiDung=lesson_data["content"],
                    thoiLuong=lesson_data["duration"],
                    thuTu=lesson_data["order"],
                    ngayTao=now,
                )
                db.add(lesson)
                db.flush()
                stats["lessons_created"] += 1

                for mat_data in lesson_data.get("materials", []):
                    mat = TaiLieu(
                        maBaiHoc=lesson.maBaiHoc,
                        tieuDe=mat_data["title"],
                        loai=mat_data["type"],
                        moTa=mat_data["desc"],
                        duongDanTep=f"documents/{course.maKhoaHoc}/{lesson.maBaiHoc}/{mat_data['title'].lower().replace(' ', '_')}.pdf",
                        ngayTao=now,
                    )
                    db.add(mat)
                    stats["materials_created"] += 1

    # 5. Seed Interactions (Enrollment & Learning History)
    # Persona B: learner_vue_specialist -> Enrolled in C1 (100% progress)
    user_vue = user_map.get("learner_vue_specialist")
    c1 = course_map.get("c1")
    if user_vue and c1:
        enr_b = db.scalar(
            select(DangKyKhoaHoc)
            .where(
                DangKyKhoaHoc.maNguoiDung == user_vue.maNguoiDung,
                DangKyKhoaHoc.maKhoaHoc == c1.maKhoaHoc,
            )
            .limit(1)
        )
        if not enr_b:
            db.add(
                DangKyKhoaHoc(
                    maNguoiDung=user_vue.maNguoiDung,
                    maKhoaHoc=c1.maKhoaHoc,
                    ngayDangKy=now,
                    tienDo=Decimal("100.0"),
                    ngayHoanThanh=now,
                )
            )
            stats["enrollments_created"] += 1

            # Mark all lessons of C1 completed in history
            c1_lessons = db.scalars(
                select(BaiHoc).where(BaiHoc.maKhoaHoc == c1.maKhoaHoc)
            ).all()
            for lsn in c1_lessons:
                db.add(
                    LichSuHocTap(
                        maNguoiDung=user_vue.maNguoiDung,
                        maKhoaHoc=c1.maKhoaHoc,
                        maBaiHoc=lsn.maBaiHoc,
                        tienDo="COMPLETED",
                        thoiGianXem=lsn.thoiLuong or 60,
                        ngayTao=now,
                    )
                )
                stats["history_created"] += 1

    # Persona C: learner_fullstack_hybrid -> Enrolled in C1 (50%) and C4 (80%)
    user_hybrid = user_map.get("learner_fullstack_hybrid")
    c4 = course_map.get("c4")
    if user_hybrid and c1 and c4:
        enr_c1 = db.scalar(
            select(DangKyKhoaHoc)
            .where(
                DangKyKhoaHoc.maNguoiDung == user_hybrid.maNguoiDung,
                DangKyKhoaHoc.maKhoaHoc == c1.maKhoaHoc,
            )
            .limit(1)
        )
        if not enr_c1:
            db.add(
                DangKyKhoaHoc(
                    maNguoiDung=user_hybrid.maNguoiDung,
                    maKhoaHoc=c1.maKhoaHoc,
                    ngayDangKy=now,
                    tienDo=Decimal("50.0"),
                )
            )
            stats["enrollments_created"] += 1

        enr_c4 = db.scalar(
            select(DangKyKhoaHoc)
            .where(
                DangKyKhoaHoc.maNguoiDung == user_hybrid.maNguoiDung,
                DangKyKhoaHoc.maKhoaHoc == c4.maKhoaHoc,
            )
            .limit(1)
        )
        if not enr_c4:
            db.add(
                DangKyKhoaHoc(
                    maNguoiDung=user_hybrid.maNguoiDung,
                    maKhoaHoc=c4.maKhoaHoc,
                    ngayDangKy=now,
                    tienDo=Decimal("80.0"),
                )
            )
            stats["enrollments_created"] += 1

            # Mark 2 lessons of C4 completed
            c4_lessons = db.scalars(
                select(BaiHoc).where(BaiHoc.maKhoaHoc == c4.maKhoaHoc).limit(2)
            ).all()
            for lsn in c4_lessons:
                db.add(
                    LichSuHocTap(
                        maNguoiDung=user_hybrid.maNguoiDung,
                        maKhoaHoc=c4.maKhoaHoc,
                        maBaiHoc=lsn.maBaiHoc,
                        tienDo="COMPLETED",
                        thoiGianXem=lsn.thoiLuong or 60,
                        ngayTao=now,
                    )
                )
                stats["history_created"] += 1

    if dry_run:
        db.rollback()
        print(
            "[DRY-RUN] Verification passed. All entities verified and rolled back cleanly."
        )
    else:
        db.commit()

    return stats


def get_target_engine(target_db_name: str | None, custom_url: str | None = None):
    settings = get_settings()
    if custom_url:
        return create_engine(custom_url, pool_pre_ping=True)

    base_url = settings.database_url.get_secret_value()
    if target_db_name:
        parts = base_url.rsplit("/", 1)
        target_url = f"{parts[0]}/{target_db_name}"
        return create_engine(target_url, pool_pre_ping=True)

    return create_engine(base_url, pool_pre_ping=True)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="EduSuggest Recommendation Test Data Seeder with Safety Guardrails."
    )
    parser.add_argument(
        "--confirm-seed-test-data",
        action="store_true",
        help="Explicit confirmation required to execute seeding.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Perform all operations within a rolled-back transaction without saving.",
    )
    parser.add_argument(
        "--target-db",
        type=str,
        default=os.getenv("EDUSUGGEST_TEST_DB_NAME", "EduSuggest_test"),
        help="Explicit test database name (cannot be 'EduSuggest').",
    )
    parser.add_argument(
        "--db-url",
        type=str,
        default=None,
        help="Optional direct connection URL for the test database.",
    )

    args = parser.parse_args()

    if not args.confirm_seed_test_data and not args.dry_run:
        print(
            "ERROR: Missing explicit confirmation flag '--confirm-seed-test-data' or '--dry-run'.\n"
            "This script is strictly protected against accidental execution.",
            file=sys.stderr,
        )
        sys.exit(1)

    engine = get_target_engine(args.target_db, args.db_url)
    session_factory = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    db: Session = session_factory()

    try:
        # Strict Safety Inspection
        confirmed_db = check_target_database_safety(db, allowed_db_name=args.target_db)
        print(
            f"[GUARDRAIL PASSED] Connected to verified test database: '{confirmed_db}'"
        )

        stats = seed_test_dataset(db, dry_run=args.dry_run)
        print(f"[{'DRY-RUN' if args.dry_run else 'SEED'} COMPLETED] Summary:")
        for k, v in stats.items():
            print(f"  - {k}: {v}")
    except (RuntimeError, SQLAlchemyError) as exc:
        db.rollback()
        print(f"[SEED STOPPED/FAILED] {exc}", file=sys.stderr)
        sys.exit(1)
    finally:
        db.close()
        engine.dispose()


if __name__ == "__main__":
    main()
