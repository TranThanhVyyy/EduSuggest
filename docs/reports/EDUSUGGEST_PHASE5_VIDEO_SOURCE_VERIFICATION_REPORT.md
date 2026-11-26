# EDUSUGGEST — GĐ5.4: BÁO CÁO XÁC MINH NGUỒN VIDEO BÀI GIẢNG (135 BÀI)

**Ngày kiểm tra:** 2026-11-26  
**Phương pháp:** Kiểm tra trực tiếp toàn bộ `15` URL YouTube duy nhất (tương ứng `135` bài học video) bằng **YouTube oEmbed API** (`https://www.youtube.com/oembed?format=json&url=...`) — không vượt chống bot, không bịa video ID.

---

## 1. Kết quả xác minh 15 URL YouTube duy nhất (`135` bài học)

| Trạng thái xác minh | Số URL duy nhất | Số bài học | Chi tiết |
| :--- |---:|---:|---|
| **Hợp lệ, công khai, được phép nhúng & đúng chủ đề (`VALID_EMBEDDABLE`)** | `10` | **`65`** | Giữ nguyên trên Staging (nguồn: `freeCodeCamp.org`, `Programming with Mosh`, `Traversy Media`, `TechWorld with Nana`) |
| **Video YouTube sống nhưng gán NHẦM chủ đề (SQL gán lên 10 khóa khác)** | `1` (`7S_tz1z_5bA`) | **`50`** | Gỡ khỏi 10 khóa `#20–#29` (Terraform, OWASP, Pentest, Malware, QA, Selenium, JMeter, Fullstack, Rust, White-hat) trên Staging, giữ nguyên cho khóa `#11` (MySQL) |
| **Video chết / đã bị xóa hoặc chuyển riêng tư (`YOUTUBE_HTTP_404`)** | `4` | **`20`** | `9gBC9Ar4Ssg` (`#17`), `bzlFvdnC11E` (`#3`), `u0BqPd_rC1E` (`#4`), `sWbGOq-JrIQ` (`#19`) — đã gỡ khỏi Staging & bổ sung nội dung bài đọc/thực hành |

---

## 2. Danh sách 10 nguồn video hợp lệ được giữ lại (65 bài học)

| Video URL | Kênh phát hành | Tiêu đề xác minh qua oEmbed | Khóa học áp dụng |
|---|---|---|---|
| `youtube.com/watch?v=0sOvCWFmrtA` | freeCodeCamp.org | Python API Development - Comprehensive Course | `#6`, `#7` (FastAPI) |
| `youtube.com/watch?v=Oe421EPjeBE` | freeCodeCamp.org | Node.js and Express.js - Full Course | `#8` (Node.js/Express) |
| `youtube.com/watch?v=qw--VYLpxG4` | freeCodeCamp.org | PostgreSQL Tutorial Full Course | `#9` (PostgreSQL) |
| `youtube.com/watch?v=HXV3zeQKqGY` | freeCodeCamp.org | SQL Tutorial - Full Database Course | `#10` (SQL) |
| `youtube.com/watch?v=7S_tz1z_5bA` | Programming with Mosh | SQL Course for Beginners [Full Course] | `#11` (MySQL — chỉ giữ đúng khóa SQL!) |
| `youtube.com/watch?v=1gDhl4leEzA` | Traversy Media | Flutter Crash Course | `#12`, `#14` (Flutter) |
| `youtube.com/watch?v=0-S5a0eXPoc` | Programming with Mosh | React Native Tutorial for Beginners | `#13` (React Native) |
| `youtube.com/watch?v=vmEHCJofslg` | Keith Galli | Complete Python Pandas Data Science Tutorial | `#15` (Python Pandas) |
| `youtube.com/watch?v=0B5eIE_1vpU` | freeCodeCamp.org | Scikit-learn Crash Course | `#16` (Machine Learning) |
| `youtube.com/watch?v=3c-iBn73dDE` | TechWorld with Nana | Docker Tutorial for Beginners | `#18` (Docker/K8s) |
| `youtube.com/watch?v=SqcY0GlETPk` | Programming with Mosh | React Tutorial for Beginners | `#5` (React/Next.js) |

*(Ghi chú: Tổng 11 URL sống nếu tính `7S_tz1z_5bA` được giữ riêng cho `#11` → `65` bài học video hợp lệ, `0` video chết, `0` video lệch chủ đề trên `edusuggest_phase54_staging`.)*
