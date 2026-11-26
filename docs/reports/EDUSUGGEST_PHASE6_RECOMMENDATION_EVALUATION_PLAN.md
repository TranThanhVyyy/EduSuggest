# EDUSUGGEST — GĐ6.1: KẾ HOẠCH ĐÁNH GIÁ KHOA HỌC HỆ THỐNG GỢI Ý (CHO GĐ6.3)

**Nguyên tắc:** Giữ nguyên thuật toán **TF-IDF + Cosine Similarity** (`backend/service/content_recommendation.py`, `recommendation_service.py`), không bịa số liệu, phân biệt rõ đánh giá trên dữ liệu mô phỏng (`edusuggest-official-v2`) với dữ liệu người dùng thật.

---

## 1. Kiến trúc & Điểm kiểm toán hiện tại
- **Tiền xử lý văn bản:** Chuẩn hóa tiếng Việt + tách token kỹ thuật, kết hợp `tieuDe`, `moTa`, `tenDanhMuc`, nội dung bài học và tín hiệu trình độ/thời lượng/học phí.
- **Lọc điều kiện (`Eligibility Filtering`):** Chỉ gợi ý khóa học `APPROVED + VISIBLE` (đã xác minh **`0` rò rỉ** khóa `#31` và tài liệu `#132`).
- **Quy tắc loại trừ (`Exclusion Rules`):** Loại trừ khóa học người dùng đã đăng ký (`ACTIVE`/`LEGACY`).
- **Cold-start:** Chuyển tự động sang chiến lược `latest` cho người học mới (`official_persona_new`).

---

## 2. Phương pháp đánh giá khoa học đề xuất cho GĐ6.3 (Chống rò rỉ dữ liệu)

### 2.1. Tách dữ liệu Holdout (Zero Data Leakage)
- Đối với mỗi người dùng có `>= 3` khóa học trong `DangKyKhoaHoc` / `LichSuHocTap`:
  - **Train/Profile Split (70–80%):** Dùng để xây dựng vector hồ sơ người dùng.
  - **Test/Holdout Split (20–30% — tối thiểu 1 khóa ẩn):** Tạm loại khỏi đầu vào tạo hồ sơ và dùng làm tập ground truth để chấm điểm ranking; tuyệt đối không dùng tương tác đầu vào làm nhãn đánh giá.
- **Song song đánh giá 8 Official Personas theo chuyên gia gán nhãn (`Domain Relevance Ground Truth`):** Với mỗi persona (AI, Backend, Data, DevOps, Frontend, Fullstack, Mobile), xác định tập khóa học/tài liệu mục tiêu theo danh mục + bộ kỹ năng cốt lõi có thể giải trình minh bạch.

### 2.2. Bộ chỉ số đo lường (`K ∈ {5, 10}`)
- **Precision@K** & **Recall@K**: Độ chính xác và độ phủ trên Top-5, Top-10.
- **Hit Rate@K**: Tỷ lệ người dùng có ít nhất 1 mục phù hợp trong Top-K.
- **NDCG@K**: Chất lượng thứ hạng (ưu tiên mục liên quan cao ở vị trí đầu).
- **Catalog Coverage**: Tỷ lệ khóa học/tài liệu công khai được xuất hiện trong gợi ý trên toàn tập người dùng.
- **Intra-List Diversity**: Độ đa dạng chủ đề trong Top-K (`1 - avg pairwise cosine similarity`).
- **Cold-start Effectiveness & Response Time (`p50`, `p95` ms)**: Đo trước và sau khi tối ưu cache ở GĐ6.6.
