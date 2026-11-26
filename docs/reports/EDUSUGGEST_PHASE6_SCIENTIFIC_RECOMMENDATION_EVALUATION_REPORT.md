# EDUSUGGEST – GĐ6.3D: SCIENTIFIC RECOMMENDATION EVALUATION REPORT

- **Ngày thực hiện:** 2026-11-27
- **Môi trường & Dữ liệu:** Official Dataset V2 (`EduSuggest` READ ONLY — `101` khóa học `APPROVED+VISIBLE`, `226` tài liệu `APPROVED+VISIBLE`, `8` Official Personas), Python 3.11, `matplotlib`.
- **Pipeline tái lập:** [`backend/scripts/phase63_scientific_rec_eval.py`](../../backend/scripts/phase63_scientific_rec_eval.py)
- **Artifacts:** [`recommendation-evaluation-config.json`](./recommendation-evaluation-config.json), [`recommendation-relevance-labels.json`](./recommendation-relevance-labels.json), [`recommendation-evaluation-results.json`](./recommendation-evaluation-results.json), [`recommendation-evaluation-results.csv`](./recommendation-evaluation-results.csv)
- **Biểu đồ thực nghiệm:**
  - [`charts/precision_recall_ndcg_k5_k10.png`](./charts/precision_recall_ndcg_k5_k10.png)
  - [`charts/baseline_comparison_courses_k5.png`](./charts/baseline_comparison_courses_k5.png)
  - [`charts/catalog_coverage_comparison.png`](./charts/catalog_coverage_comparison.png)
  - [`charts/latency_before_after_optimization.png`](./charts/latency_before_after_optimization.png)

## 1. Thiết kế thí nghiệm & Ground Truth độc lập

- **Thuật toán đánh giá:** Giữ nguyên **TF-IDF + Cosine Similarity** đang chạy trên Production (không chỉnh công thức hay trọng số).
- **Xây dựng Ground Truth (`recommendation-relevance-labels.json`):**
  - Ánh xạ **độc lập trước khi chạy thuật toán** từ 24 danh mục chuẩn của EduSuggest sang 8 định hướng học tập (`primary_category_ids` + `secondary_category_ids`).
  - **Không** dùng kết quả của thuật toán làm ground truth; **loại bỏ hoàn toàn** các khóa học đã đăng ký khỏi tập ứng viên đánh giá của từng persona để tránh data leakage.
- **Phân loại dữ liệu:** Đây là **đánh giá ngoại tuyến bằng bộ nhãn liên quan theo miền (Domain Relevance Labels)** trên dữ liệu mô phỏng **Official Dataset V2** (`8` Official Personas) — **không phải** khảo sát người dùng thật ngoài thực tế.

## 2. Định nghĩa & Công thức các chỉ số (`K = 5, 10`)

- **Precision@K:** $P@K = \frac{1}{K}\sum_{i=1}^{K} rel(i)$ — Tỷ lệ mục phù hợp trong Top-K.
- **Recall@K:** $R@K = \frac{\sum_{i=1}^{K} rel(i)}{|R_u|}$ — Tỷ lệ mục phù hợp tìm thấy trên tổng số mục liên quan $|R_u|$.
- **Hit Rate@K:** $HR@K = \mathbb{I}(\sum_{i=1}^{K} rel(i) > 0)$ — Tỷ lệ người dùng có ít nhất 1 gợi ý trúng miền trong Top-K.
- **NDCG@K:** $NDCG@K = \frac{DCG@K}{IDCG@K}$, với $DCG@K = \sum_{i=1}^{K}\frac{rel(i)}{\log_2(i+1)}$ — Đánh giá chất lượng xếp hạng có trọng số vị trí.
- **MRR@K:** $MRR@K = \frac{1}{\text{rank}_1}$ (hoặc $0$ nếu không trúng) — Độ ưu tiên của kết quả đúng đầu tiên.
- **Catalog Coverage@10:** $\frac{|\bigcup_{u} \text{Rec}_{10}(u)|}{|I|}$ — Tỷ lệ phần trăm danh mục hệ thống được khám phá.
- **Category Diversity@10:** Số danh mục khác nhau chia cho $K$ trong danh sách Top-10.

## 3. Kết quả tổng hợp (Macro-Average)

| Miền & Nhóm đánh giá | P@5 | R@5 | HR@5 | NDCG@5 | MRR@5 | P@10 | R@10 | HR@10 | NDCG@10 | Coverage@10 | Diversity@10 |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| **Courses – 7 Personalized Personas** | **0.1429** | **0.0378** | **0.5714** | **0.1671** | **0.3857** | **0.1857** | **0.0947** | **0.7143** | **0.1897** | **57.43%** | **0.5714** |
| **Materials – All 8 Personas** | **0.2000** | **0.0198** | **0.3750** | **0.1779** | **0.2292** | **0.1375** | **0.0274** | **0.5000** | **0.1426** | **31.42%** | **0.5000** |
| **Production Warm Latency (`8000`)** | — | — | — | — | — | — | — | — | — | **`101.71 ms` p50** | **`144.50 ms` p95** |

## 4. Hạn chế khoa học & Ý nghĩa bảo vệ đồ án

1. **Quy mô mẫu mô phỏng:** 8 Official Personas với 3–4 lượt ghi danh/người đại diện cho các hình mẫu chuyên ngành chuẩn nhưng chưa đủ để khái quát hóa như nhật ký tương tác của hàng nghìn người học thực tế.
2. **Hạn chế của Unigram TF-IDF trên văn bản sư phạm tiếng Việt:** Nội dung 421 bài học giàu chữ chứa nhiều thuật ngữ học thuật chung (*"kiến trúc"*, *"thực hành"*, *"dự án"*) gây chồng lấn cosine chéo danh mục (giải thích chi tiết trong [`EDUSUGGEST_PHASE6_RECOMMENDATION_BASELINE_COMPARISON_REPORT.md`](./EDUSUGGEST_PHASE6_RECOMMENDATION_BASELINE_COMPARISON_REPORT.md) và [`EDUSUGGEST_PHASE6_RECOMMENDATION_CASE_STUDIES.md`](./EDUSUGGEST_PHASE6_RECOMMENDATION_CASE_STUDIES.md)).
3. **Giá trị thực tiễn:** Thuật toán hiện tại chạy ổn định ở `101.71 ms` p50, đạt **Catalog Coverage@10 = `57.43%`** (gấp `5.27×` so với `Latest`/`Popularity`), giải thích được lý do gợi ý (`reasonCodes`), và hỗ trợ fallback Cold-start (`official_persona_new` → chiến lược `latest`) rõ ràng.
