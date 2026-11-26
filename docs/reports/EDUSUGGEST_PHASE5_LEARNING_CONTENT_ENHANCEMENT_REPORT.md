# EDUSUGGEST — GĐ5.4: BÁO CÁO NÂNG CẤP NỘI DUNG HỌC TẬP TRÊN STAGING

**Ngày thực hiện:** 2026-11-26  
**Môi trường thực thi:** Staging độc lập `edusuggest_phase54_staging` (nhân bản sạch từ Production `EduSuggest` sau GĐ5.3 với `421` bài học). **CHƯA ÁP DỤNG LÊN PRODUCTION — DỪNG CHỜ PHÊ DUYỆT GĐ5.5.**

---

## 1. Kết quả Batch Content Enhancement Pipeline (`phase54_enhance_content_staging.py`)

Pipeline tự động xử lý toàn bộ 421 bài học (hỗ trợ `--dry-run`, `--apply`, `--rollback`, checkpointing, quality validation, không xóa/đổi `maBaiHoc`):

| Chỉ số kiểm toán & cải thiện (trên `edusuggest_phase54_staging`) | Số lượng |
| :--- |---:|
| Tổng số bài học đã kiểm tra | **`421`** |
| Số bài giữ nguyên (đã đạt chuẩn: 10 bài khóa `#31` + 65 bài video hợp lệ nội dung đầy đủ) | **`75`** |
| **Số bài được cải thiện nội dung / làm sạch video trên Staging** | **`346`** |
| Phân loại thực tế sau cải thiện — Video Lecture hợp lệ (`oEmbed 200 OK`, đúng chủ đề) | **`65`** |
| Phân loại thực tế sau cải thiện — Bài đọc (`reading`) có đủ mục tiêu, khái niệm, ví dụ, tổng kết & nguồn chính thức | **`148`** |
| Phân loại thực tế sau cải thiện — Bài thực hành (`practical_exercise`) có đủ mục tiêu, chuẩn bị, hướng dẫn, kết quả & lỗi thường gặp | **`99`** |
| Phân loại thực tế sau cải thiện — Bài dự án + tự kiểm tra (`project_and_assessment`) có câu hỏi kèm đáp án gợi ý & đề bài dự án | **`94`** |
| Phân loại thực tế sau cải thiện — Bài kiểm tra (`assessment`) có câu hỏi kèm đáp án gợi ý (ghi rõ tự đánh giá, chưa có chấm điểm tự động) | **`15`** |
| Số video chết (`YOUTUBE_HTTP_404`) đã gỡ bỏ & chuyển sang bài đọc/thực hành | **`20`** |
| Số video SQL gán lệch chủ đề đã gỡ bỏ & bổ sung nội dung đúng chuyên ngành | **`50`** |

---

## 2. Gia cố `LearningView.vue` (Editorial EdTech Modernism & Bảo mật XSS)

Cập nhật [LearningView.vue](file:///D:/đồ%20án/EduSuggest/frontend/src/views/user/LearningView.vue):
- **Chống XSS tuyệt đối:** Giữ nguyên render văn bản thuần `{{ activeLesson.content }}` (không dùng `v-html`, không cho phép nhúng JavaScript tùy ý).
- **Allowlist iframe chặt chẽ:** Chỉ cho phép nhúng iframe privacy-enhanced `https://www.youtube-nocookie.com/embed/{11-char-id}?rel=0` đối với URL thuộc allowlist `youtube.com` / `youtu.be` / `youtube-nocookie.com` kèm liên kết ghi rõ nguồn phát hành YouTube; các URL hợp lệ khác (`https?://`) hiển thị nút mở trực tiếp tại nguồn (`rel="noopener noreferrer"`), chặn tuyệt đối `javascript:` / `data:`.

---

## 3. Recommendation Regression (8 Official Personas — Trước vs Sau GĐ5.4 trên Staging)

- **Chiến lược gợi ý:** `7/7` persona cá nhân hóa giữ nguyên `content_based → content_based`; `official_persona_new` (Cold-start) giữ nguyên `latest → latest` (Top-5 khóa học và tài liệu trùng khớp `100%`).
- **Phân tích thay đổi thứ hạng:** Do 346 bài học được bổ sung thuật ngữ công nghệ đúng chuyên ngành và tên tài liệu chính thức (MDN, Python, Vue, FastAPI, PostgreSQL, Docker, Kubernetes, AWS, OWASP...), vector TF-IDF khóa học giàu tín hiệu chuyên môn hơn khiến Top-5 khóa học ở 7 persona cá nhân hóa có điều chỉnh thứ hạng phù hợp hơn, trong khi 4/7 persona giữ nguyên Top-5 tài liệu. **Không sửa công thức TF-IDF + Cosine Similarity.**

---

## 4. Hồ sơ đối chiếu & Nghiệm thu Staging
- **Gallery HTML so sánh nội dung trước/sau:** [learning-content-comparison-gallery.html](learning-content-comparison-gallery.html)
- **Provenance đầy đủ:** [learning-content-provenance.json](learning-content-provenance.json)
- **Data Diff & Rollback Manifest:** [learning-content-diff.json](learning-content-diff.json) · [learning-content-rollback-manifest.json](learning-content-rollback-manifest.json)
- **Vấn đề chưa xử lý ở GĐ5.4 (chuyển GĐ5.5 nếu cần):** Chưa nhúng thêm video mới cho 70 bài vừa gỡ video chết/lệch chủ đề (tránh gắn video ngẫu nhiên chưa kiểm duyệt kỹ từng chương) và chưa xử lý tài liệu rác `#132` (`"hi"` / `"gsdfsd"`).
- **Trình duyệt tự động:** Chrome DevTools MCP vẫn `BLOCKED` (`DevToolsActivePort ENOENT`).
