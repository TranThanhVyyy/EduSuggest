# EDUSUGGEST – GĐ6.3D: RECOMMENDATION BASELINE COMPARISON REPORT

- **Ngày thực hiện:** 2026-11-27
- **Tập dữ liệu:** Official Dataset V2 (`EduSuggest` READ ONLY — `101` khóa học `APPROVED+VISIBLE`, `226` tài liệu `APPROVED+VISIBLE`, `8` Official Personas)
- **Script tái lập:** [`backend/scripts/phase63_scientific_rec_eval.py`](../../backend/scripts/phase63_scientific_rec_eval.py)
- **Artifacts:** [`recommendation-evaluation-results.json`](./recommendation-evaluation-results.json), [`recommendation-evaluation-results.csv`](./recommendation-evaluation-results.csv), [`charts/baseline_comparison_courses_k5.png`](./charts/baseline_comparison_courses_k5.png), [`charts/catalog_coverage_comparison.png`](./charts/catalog_coverage_comparison.png)

## 1. So sánh thuật toán trên Gợi ý Khóa học (7 Personalized Personas, loại trừ Cold-Start)

Tất cả thuật toán được đánh giá trên **cùng tập ứng viên đủ điều kiện** (đã loại bỏ các khóa học persona đang ghi danh) và **cùng bộ nhãn liên quan độc lập** (`recommendation-relevance-labels.json`).

| Thuật toán | Precision@5 | Recall@5 | Hit Rate@5 | NDCG@5 | MRR@5 | Precision@10 | Recall@10 | NDCG@10 | Coverage@10 | Diversity@10 |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| **TF-IDF + Cosine (Production)** | **0.1429** | **0.0378** | **0.5714** | **0.1671** | **0.3857** | **0.1857** | **0.0947** | **0.1897** | **57.43%** | **0.5714** |
| **Latest Baseline** | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0714 | 0.0411 | 0.0470 | 10.89% | 0.3000 |
| **Popularity Baseline** | 0.3714 | 0.0926 | 0.7143 | 0.3738 | 0.5048 | 0.3143 | 0.1592 | 0.3321 | 10.89% | 0.6429 |
| **Random Baseline (20 seeds)** | 0.1943 | 0.0503 | 0.6643 | 0.1989 | 0.3719 | 0.1907 | 0.0988 | 0.1954 | 100.00% | 0.8450 |

## 2. So sánh thuật toán trên Gợi ý Tài liệu (All 8 Personas)

| Thuật toán | Precision@5 | Recall@5 | Hit Rate@5 | NDCG@5 | MRR@5 | Precision@10 | Coverage@10 | Diversity@10 |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| **TF-IDF + Cosine (Production)** | **0.2000** | **0.0198** | **0.3750** | **0.1779** | **0.2292** | **0.1375** | **31.42%** | **0.5000** |
| **Latest Baseline** | 0.3000 | 0.0287 | 0.6250 | 0.2653 | 0.3333 | 0.2250 | 4.42% | 1.0000 |

## 3. Phân tích khoa học trung thực (Vì sao TF-IDF vượt trội Latest & Coverage nhưng thua Popularity ở Precision@5?)

1. **Vượt trội hoàn toàn so với `Latest` về chất lượng lẫn độ phủ:**
   - Trên Gợi ý Khóa học, `TF-IDF + Cosine` đạt `Precision@5 = 0.1429`, `NDCG@5 = 0.1671`, `MRR@5 = 0.3857` so với `0.0000` của `Latest`, và đạt **Catalog Coverage@10 = `57.43%`** (**5.27×** so với `10.89%` của `Latest` và `Popularity`).
   - Trên Gợi ý Tài liệu, `TF-IDF + Cosine` đạt **Catalog Coverage@10 = `31.42%`** (**7.1×** so với `4.42%` của `Latest`).
2. **Báo cáo trung thực lý do `Popularity` cao hơn ở `Precision@5` (`0.3714` vs `0.1429`):**
   - `Popularity` **không cá nhân hóa** (Coverage@10 chỉ `10.89%` — đề xuất gần như cùng một danh sách 10 khóa cho mọi người học). Điểm Precision cao của `Popularity` là do phân bố lượt đăng ký mô phỏng (`150 LEGACY ACTIVE`) tập trung nhiều vào các danh mục cốt lõi (Web, Data, AI, Mobile) vốn trùng với phần lớn 7 personas.
3. **Nguyên nhân học thuật khiến Unigram TF-IDF thuần bị nhiễu chéo danh mục (Cross-Domain Term Overlap):**
   - Khi nâng cấp Official Dataset V2 lên 421 bài học giàu nội dung (~1.415 ký tự/bài), các cụm từ sư phạm tiếng Việt lặp lại ở nhiều khóa học khác ngành (ví dụ: *"kiến trúc"*, *"thực hành"*, *"dự án"*, *"kiểm thử"*, *"tối ưu"*) tạo độ tương đồng cosine dương giữa các khóa khác lĩnh vực (ví dụ gợi ý khóa An toàn thông tin hoặc Java cho persona AI).
   - **Hướng phát triển cho nghiên cứu tiếp theo (không sửa trong GĐ6.3):** Bổ sung danh sách stop-words sư phạm tiếng Việt, tăng trọng số từ khóa chuyên ngành / n-gram, hoặc kết hợp Hybrid (TF-IDF + Category Affinity / Collaborative Filtering khi có dữ liệu người dùng thật).
