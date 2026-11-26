# EDUSUGGEST — GĐ5.3: KẾ HOẠCH NÂNG CẤP NỘI DUNG HỌC TẬP (CHO GĐ5.4)

**Mục tiêu:** Lộ trình nâng cao chiều sâu học thuật cho 411 bài học hiện hữu (không tạo thêm Quiz Engine, không đổi schema, tận dụng trường `BaiHoc.noiDung` và `BaiHoc.duongDanVideo` hiện có).

---

## 1. Nhóm bài học cần bổ sung nội dung ưu tiên

| Nhóm ưu tiên | Số lượng | Thiếu hụt hiện tại | Phương án nâng cấp đề xuất (GĐ5.4) |
| :--- |---:|---|---|
| **P1 — 15 bài legacy nội dung ngắn (`< 120 ký tự`)** | `15` bài | Mô tả văn bản quá ngắn, chỉ dựa vào tiêu đề & video | Bổ sung 3 mục chuẩn trong `noiDung`: *Mục tiêu học tập*, *Tóm tắt kiến thức trọng tâm*, *Bài tập tự kiểm tra* |
| **P2 — 92 bài "Thực hành có hướng dẫn" (`official-v1`)** | `92` bài | Văn phong còn chung chung theo khuôn mẫu danh mục | Bổ sung đề bài thực hành cụ thể theo đúng công nghệ khóa học, từng bước gợi ý và đầu ra kỳ vọng |
| **P3 — 92 bài "Bài toán tích hợp và đánh giá" (`official-v1`)** | `92` bài | Thiếu câu hỏi ôn tập / tiêu chí nghiệm thu cụ thể | Bổ sung 3–5 câu hỏi trắc nghiệm/tự luận kèm hướng dẫn tự đánh giá và checklist tiêu chí hoàn thành dự án nhỏ (lưu dạng Markdown/text trong `noiDung`, không cần bảng Quiz mới) |
| **P4 — Video minh họa chọn lọc cho bài nền tảng** | `24` bài tiêu biểu (1 bài/danh mục) | 92 khóa `official-v1` hoàn toàn là bài học văn bản | Chỉ nhúng video có quyền nhúng hợp lệ từ kênh chính thức của công nghệ (Python, Vue, React, FastAPI, PostgreSQL, AWS, Docker, OWASP...) kèm ghi rõ nguồn kênh chính thức; giữ nguyên bản chất text/lab cho các bài đọc và thực hành |

---

## 2. Nguyên tắc triển khai GĐ5.4
1. Không ép mọi bài học phải có video; phân biệt rõ bài đọc, thực hành, kiểm tra và dự án.
2. Không tải lại trái phép video hoặc sao chép khóa học thương mại; mọi video bên thứ ba bắt buộc ghi rõ nguồn kênh chính thức.
3. Thực hiện trên Staging trước, kiểm chứng Recommendation 8 personas và chỉ cập nhật Production sau khi có phê duyệt từng bước.
