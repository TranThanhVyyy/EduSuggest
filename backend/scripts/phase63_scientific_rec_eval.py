"""GĐ6.3D Reproducible Scientific Recommendation Evaluation Pipeline (READ ONLY on Official Dataset V2).

Computes Precision@K, Recall@K, Hit Rate@K, NDCG@K, MRR@K (K=5, 10), Catalog Coverage,
and Category Diversity for Course & Material Recommendation across 8 Official Personas,
comparing TF-IDF + Cosine Similarity against Random (20 seeds), Latest, and Popularity baselines.
"""
from __future__ import annotations

import csv
import json
import math
import os
import platform
import random
import statistics
import sys
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

ROOT = Path(r"D:\đồ án\EduSuggest")
BACKEND = ROOT / "backend"
REPORTS_DIR = ROOT / "docs" / "reports"
CHARTS_DIR = REPORTS_DIR / "charts"
CHARTS_DIR.mkdir(parents=True, exist_ok=True)
sys.path.insert(0, str(BACKEND))

for raw_line in (BACKEND / ".env").read_text(encoding="utf-8").splitlines():
    line = raw_line.strip()
    if line and not line.startswith("#") and "=" in line:
        k, v = line.split("=", 1)
        os.environ.setdefault(k.strip(), v.strip())

from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from service import recommendation_service as rs

# Independent domain-grounded relevance mapping (defined strictly from curriculum taxonomy,
# NEVER derived from TF-IDF output). Maps each persona to relevant category IDs.
PERSONA_DOMAIN_CATEGORIES: dict[str, dict] = {
    "official_persona_frontend": {
        "track": "Web Frontend & UI/UX",
        "primary_category_ids": [4, 41],       # Web Frontend, Thiết kế UI/UX
        "secondary_category_ids": [29, 28],    # Fullstack Development, Lập trình căn bản
    },
    "official_persona_backend": {
        "track": "Web Backend, DB & Software Architecture",
        "primary_category_ids": [5, 6, 40],    # Web Backend, CSDL & SQL, Kiến trúc phần mềm
        "secondary_category_ids": [10, 11],    # An toàn thông tin, Kiểm thử phần mềm & QA
    },
    "official_persona_fullstack": {
        "track": "Fullstack Web Development",
        "primary_category_ids": [29, 4, 5],    # Fullstack, Web Frontend, Web Backend
        "secondary_category_ids": [6, 40],     # CSDL & SQL, Kiến trúc phần mềm
    },
    "official_persona_ai": {
        "track": "AI, Machine Learning, Deep Learning & NLP",
        "primary_category_ids": [33, 34, 35],  # ML, Deep Learning & CV, GenAI & NLP
        "secondary_category_ids": [8, 39],     # Khoa học dữ liệu, CTDL & Giải thuật
    },
    "official_persona_data": {
        "track": "Data Science, Analytics & Databases",
        "primary_category_ids": [8, 32, 6],    # Khoa học dữ liệu, Phân tích dữ liệu, CSDL & SQL
        "secondary_category_ids": [33],        # Machine Learning
    },
    "official_persona_devops": {
        "track": "DevOps, Cloud, Linux & Networking",
        "primary_category_ids": [9, 36, 38],   # DevOps & CI/CD, Điện toán đám mây, Hệ điều hành & Linux
        "secondary_category_ids": [37, 10],    # Mạng máy tính, An toàn thông tin
    },
    "official_persona_mobile": {
        "track": "Mobile App Development",
        "primary_category_ids": [7],           # Lập trình Mobile
        "secondary_category_ids": [41, 4, 40], # Thiết kế UI/UX, Web Frontend, Kiến trúc phần mềm
    },
    "official_persona_new": {
        "track": "Cold-start Beginner (Foundational CS & Intro Courses)",
        "primary_category_ids": [28, 39],      # Lập trình căn bản, CTDL & Giải thuật
        "secondary_category_ids": [4, 5, 6],   # Web Frontend, Web Backend, CSDL & SQL
    },
}

RANDOM_SEEDS = list(range(42, 62))  # 20 fixed seeds


def compute_metrics_at_k(ranked_ids: list[int], relevant_set: set[int], k: int) -> dict[str, float]:
    top_k = ranked_ids[:k]
    if not top_k or not relevant_set:
        return {"precision": 0.0, "recall": 0.0, "hit_rate": 0.0, "ndcg": 0.0, "mrr": 0.0}
    hits = [1 if item_id in relevant_set else 0 for item_id in top_k]
    precision = sum(hits) / k
    recall = sum(hits) / len(relevant_set)
    hit_rate = 1.0 if any(hits) else 0.0
    mrr = next((1.0 / (idx + 1) for idx, h in enumerate(hits) if h), 0.0)
    dcg = sum(h / math.log2(idx + 2) for idx, h in enumerate(hits))
    idcg = sum(1.0 / math.log2(idx + 2) for idx in range(min(len(relevant_set), k)))
    ndcg = (dcg / idcg) if idcg > 0 else 0.0
    return {
        "precision": precision,
        "recall": recall,
        "hit_rate": hit_rate,
        "ndcg": ndcg,
        "mrr": mrr,
    }


def category_diversity(ranked_ids: list[int], cat_by_id: dict[int, int | None], k: int) -> float:
    top_k = ranked_ids[:k]
    if not top_k:
        return 0.0
    cats = {cat_by_id.get(i) for i in top_k if cat_by_id.get(i) is not None}
    return len(cats) / len(top_k)


def main():
    eng = create_engine(os.environ["DATABASE_URL"], pool_pre_ping=True)
    SessionLocal = sessionmaker(bind=eng, autocommit=False, autoflush=False)

    with SessionLocal() as db:
        db_name = db.execute(text("SELECT current_database()")).scalar_one()
        assert db_name == "EduSuggest", f"Expected read-only EduSuggest, got {db_name}"

        # Load eligible public courses & standalone materials (READ ONLY)
        course_rows = db.execute(
            text(
                'SELECT k."maKhoaHoc", k."tieuDe", k."maDanhMuc", d."tenDanhMuc", k."trinhDo", k."ngayTao", '
                '(SELECT count(*) FROM "DangKyKhoaHoc" dk WHERE dk."maKhoaHoc" = k."maKhoaHoc" AND dk."trangThaiQuyenHoc" = \'ACTIVE\') AS pop '
                'FROM "KhoaHoc" k LEFT JOIN "DanhMuc" d ON d."maDanhMuc" = k."maDanhMuc" '
                'WHERE k."trangThaiDuyet" = \'APPROVED\' AND k."trangThaiHienThi" = \'VISIBLE\' '
                'ORDER BY k."maKhoaHoc"'
            )
        ).mappings().all()

        material_rows = db.execute(
            text(
                'SELECT t."maTaiLieu", t."tieuDe", t."maDanhMuc", d."tenDanhMuc", t."loai", t."ngayTao" '
                'FROM "TaiLieu" t LEFT JOIN "DanhMuc" d ON d."maDanhMuc" = t."maDanhMuc" '
                'WHERE t."trangThaiDuyet" = \'APPROVED\' AND t."trangThaiHienThi" = \'VISIBLE\' '
                'ORDER BY t."maTaiLieu"'
            )
        ).mappings().all()

        course_cat = {int(r["maKhoaHoc"]): r["maDanhMuc"] for r in course_rows}
        course_title = {int(r["maKhoaHoc"]): r["tieuDe"] for r in course_rows}
        course_cat_name = {int(r["maKhoaHoc"]): r["tenDanhMuc"] for r in course_rows}
        course_pop = {int(r["maKhoaHoc"]): int(r["pop"]) for r in course_rows}
        course_created = {int(r["maKhoaHoc"]): (r["ngayTao"].isoformat() if r["ngayTao"] else "") for r in course_rows}

        mat_cat = {int(r["maTaiLieu"]): r["maDanhMuc"] for r in material_rows}
        mat_title = {int(r["maTaiLieu"]): r["tieuDe"] for r in material_rows}
        mat_cat_name = {int(r["maTaiLieu"]): r["tenDanhMuc"] for r in material_rows}
        mat_created = {int(r["maTaiLieu"]): (r["ngayTao"].isoformat() if r["ngayTao"] else "") for r in material_rows}

        all_course_ids = [int(r["maKhoaHoc"]) for r in course_rows]
        all_mat_ids = [int(r["maTaiLieu"]) for r in material_rows]

        # Build independent relevance labels per persona (excluding already-enrolled courses for course eval)
        relevance_labels = {}
        persona_profiles = {}
        eval_rows = []
        case_studies = []

        # Aggregate trackers per algorithm
        algos_course = ["tfidf_cosine", "latest", "popularity", "random_20seeds"]
        algos_mat = ["tfidf_cosine", "latest", "random_20seeds"]
        course_results_by_algo: dict[str, list[dict]] = {a: [] for a in algos_course}
        mat_results_by_algo: dict[str, list[dict]] = {a: [] for a in algos_mat}
        course_recommended_union: dict[str, set[int]] = {a: set() for a in algos_course}
        mat_recommended_union: dict[str, set[int]] = {a: set() for a in algos_mat}

        for username, spec in PERSONA_DOMAIN_CATEGORIES.items():
            u_row = db.execute(
                text('SELECT "maNguoiDung", "hoTen" FROM "NguoiDung" WHERE "tenTaiKhoan" = :u'),
                {"u": username},
            ).mappings().first()
            if not u_row:
                continue
            uid = int(u_row["maNguoiDung"])

            enrolled_ids = {
                int(r[0])
                for r in db.execute(
                    text('SELECT "maKhoaHoc" FROM "DangKyKhoaHoc" WHERE "maNguoiDung" = :u AND "trangThaiQuyenHoc" = \'ACTIVE\''),
                    {"u": uid},
                ).all()
            }
            history_rows = db.execute(
                text(
                    'SELECT h."maKhoaHoc", k."tieuDe", h."tienDo", h."danhGia" '
                    'FROM "LichSuHocTap" h JOIN "KhoaHoc" k ON k."maKhoaHoc" = h."maKhoaHoc" '
                    'WHERE h."maNguoiDung" = :u ORDER BY h."ngayTao" DESC'
                ),
                {"u": uid},
            ).mappings().all()

            eligible_courses = [cid for cid in all_course_ids if cid not in enrolled_ids]
            rel_cat_ids = set(spec["primary_category_ids"] + spec["secondary_category_ids"])
            relevant_courses = {cid for cid in eligible_courses if course_cat.get(cid) in rel_cat_ids}
            relevant_materials = {mid for mid in all_mat_ids if mat_cat.get(mid) in rel_cat_ids}

            relevance_labels[username] = {
                "user_id": uid,
                "track": spec["track"],
                "primary_category_ids": spec["primary_category_ids"],
                "secondary_category_ids": spec["secondary_category_ids"],
                "enrolled_course_ids_excluded": sorted(enrolled_ids),
                "eligible_course_count": len(eligible_courses),
                "relevant_course_ids": sorted(relevant_courses),
                "relevant_material_ids": sorted(relevant_materials),
            }

            # 1. Production TF-IDF + Cosine Similarity
            c_rec = rs.recommend_courses(db, uid, limit=10)
            m_rec = rs.recommend_standalone_materials(db, uid, limit=10)
            tfidf_c_ids = [int(i.maKhoaHoc) for i in c_rec.items]
            tfidf_m_ids = [int(i.maTaiLieu) for i in m_rec.items]

            # 2. Latest baseline (exact same eligible pool)
            latest_c_ids = sorted(eligible_courses, key=lambda cid: (course_created[cid], cid), reverse=True)[:10]
            latest_m_ids = sorted(all_mat_ids, key=lambda mid: (mat_created[mid], mid), reverse=True)[:10]

            # 3. Popularity baseline (enrollment count DESC, tie-break course_id DESC)
            pop_c_ids = sorted(eligible_courses, key=lambda cid: (course_pop[cid], cid), reverse=True)[:10]

            # 4. Random baseline (20 fixed seeds -> mean & std)
            rand_c_k5, rand_c_k10, rand_c_div = [], [], []
            rand_m_k5, rand_m_k10 = [], []
            for seed in RANDOM_SEEDS:
                rng = random.Random(seed + uid)
                rc = rng.sample(eligible_courses, min(10, len(eligible_courses)))
                rm = rng.sample(all_mat_ids, min(10, len(all_mat_ids)))
                rand_c_k5.append(compute_metrics_at_k(rc, relevant_courses, 5))
                rand_c_k10.append(compute_metrics_at_k(rc, relevant_courses, 10))
                rand_c_div.append(category_diversity(rc, course_cat, 10))
                rand_m_k5.append(compute_metrics_at_k(rm, relevant_materials, 5))
                rand_m_k10.append(compute_metrics_at_k(rm, relevant_materials, 10))
                course_recommended_union["random_20seeds"].update(rc[:10])
                mat_recommended_union["random_20seeds"].update(rm[:10])

            def avg_metric_list(mlist: list[dict[str, float]]) -> dict[str, float]:
                keys = mlist[0].keys()
                return {k: round(statistics.mean([m[k] for m in mlist]), 4) for k in keys}

            def std_metric_list(mlist: list[dict[str, float]]) -> dict[str, float]:
                keys = mlist[0].keys()
                return {k: round(statistics.stdev([m[k] for m in mlist]), 4) for k in keys}

            for algo, ranked in [
                ("tfidf_cosine", tfidf_c_ids),
                ("latest", latest_c_ids),
                ("popularity", pop_c_ids),
            ]:
                m5 = compute_metrics_at_k(ranked, relevant_courses, 5)
                m10 = compute_metrics_at_k(ranked, relevant_courses, 10)
                div10 = category_diversity(ranked, course_cat, 10)
                course_recommended_union[algo].update(ranked[:10])
                rec_entry = {
                    "persona": username,
                    "strategy": c_rec.strategy if algo == "tfidf_cosine" else algo,
                    "k5": {k: round(v, 4) for k, v in m5.items()},
                    "k10": {k: round(v, 4) for k, v in m10.items()},
                    "diversity_at_10": round(div10, 4),
                }
                course_results_by_algo[algo].append(rec_entry)
                eval_rows.append({
                    "domain": "course",
                    "algorithm": algo,
                    "persona": username,
                    "strategy": rec_entry["strategy"],
                    "p_at_5": rec_entry["k5"]["precision"],
                    "r_at_5": rec_entry["k5"]["recall"],
                    "hr_at_5": rec_entry["k5"]["hit_rate"],
                    "ndcg_at_5": rec_entry["k5"]["ndcg"],
                    "mrr_at_5": rec_entry["k5"]["mrr"],
                    "p_at_10": rec_entry["k10"]["precision"],
                    "r_at_10": rec_entry["k10"]["recall"],
                    "hr_at_10": rec_entry["k10"]["hit_rate"],
                    "ndcg_at_10": rec_entry["k10"]["ndcg"],
                    "mrr_at_10": rec_entry["k10"]["mrr"],
                    "diversity_at_10": rec_entry["diversity_at_10"],
                })

            # Random course aggregate for this persona
            rand_entry = {
                "persona": username,
                "strategy": "random_20seeds",
                "k5": avg_metric_list(rand_c_k5),
                "k5_std": std_metric_list(rand_c_k5),
                "k10": avg_metric_list(rand_c_k10),
                "k10_std": std_metric_list(rand_c_k10),
                "diversity_at_10": round(statistics.mean(rand_c_div), 4),
            }
            course_results_by_algo["random_20seeds"].append(rand_entry)
            eval_rows.append({
                "domain": "course",
                "algorithm": "random_20seeds",
                "persona": username,
                "strategy": "random_20seeds",
                "p_at_5": rand_entry["k5"]["precision"],
                "r_at_5": rand_entry["k5"]["recall"],
                "hr_at_5": rand_entry["k5"]["hit_rate"],
                "ndcg_at_5": rand_entry["k5"]["ndcg"],
                "mrr_at_5": rand_entry["k5"]["mrr"],
                "p_at_10": rand_entry["k10"]["precision"],
                "r_at_10": rand_entry["k10"]["recall"],
                "hr_at_10": rand_entry["k10"]["hit_rate"],
                "ndcg_at_10": rand_entry["k10"]["ndcg"],
                "mrr_at_10": rand_entry["k10"]["mrr"],
                "diversity_at_10": rand_entry["diversity_at_10"],
            })

            # Materials
            for algo, ranked in [("tfidf_cosine", tfidf_m_ids), ("latest", latest_m_ids)]:
                m5 = compute_metrics_at_k(ranked, relevant_materials, 5)
                m10 = compute_metrics_at_k(ranked, relevant_materials, 10)
                div10 = category_diversity(ranked, mat_cat, 10)
                mat_recommended_union[algo].update(ranked[:10])
                rec_entry = {
                    "persona": username,
                    "strategy": m_rec.strategy if algo == "tfidf_cosine" else algo,
                    "k5": {k: round(v, 4) for k, v in m5.items()},
                    "k10": {k: round(v, 4) for k, v in m10.items()},
                    "diversity_at_10": round(div10, 4),
                }
                mat_results_by_algo[algo].append(rec_entry)
                eval_rows.append({
                    "domain": "material",
                    "algorithm": algo,
                    "persona": username,
                    "strategy": rec_entry["strategy"],
                    "p_at_5": rec_entry["k5"]["precision"],
                    "r_at_5": rec_entry["k5"]["recall"],
                    "hr_at_5": rec_entry["k5"]["hit_rate"],
                    "ndcg_at_5": rec_entry["k5"]["ndcg"],
                    "mrr_at_5": rec_entry["k5"]["mrr"],
                    "p_at_10": rec_entry["k10"]["precision"],
                    "r_at_10": rec_entry["k10"]["recall"],
                    "hr_at_10": rec_entry["k10"]["hit_rate"],
                    "ndcg_at_10": rec_entry["k10"]["ndcg"],
                    "mrr_at_10": rec_entry["k10"]["mrr"],
                    "diversity_at_10": rec_entry["diversity_at_10"],
                })

            mat_rand_entry = {
                "persona": username,
                "strategy": "random_20seeds",
                "k5": avg_metric_list(rand_m_k5),
                "k10": avg_metric_list(rand_m_k10),
                "diversity_at_10": 0.0,
            }
            mat_results_by_algo["random_20seeds"].append(mat_rand_entry)

            # Case study payload
            case_studies.append({
                "persona": username,
                "user_id": uid,
                "full_name": u_row["hoTen"],
                "track": spec["track"],
                "course_strategy": c_rec.strategy,
                "material_strategy": m_rec.strategy,
                "enrolled_courses": [{"id": cid, "title": course_title.get(cid), "category": course_cat_name.get(cid)} for cid in sorted(enrolled_ids)],
                "history_count": len(history_rows),
                "top5_courses": [
                    {
                        "rank": idx + 1,
                        "id": int(item.maKhoaHoc),
                        "title": item.tieuDe,
                        "category": course_cat_name.get(int(item.maKhoaHoc)),
                        "score": round(float(item.score or 0.0), 4),
                        "reason_codes": list(item.reasonCodes or []),
                        "is_domain_relevant": int(item.maKhoaHoc) in relevant_courses,
                    }
                    for idx, item in enumerate(c_rec.items[:5])
                ],
                "top5_materials": [
                    {
                        "rank": idx + 1,
                        "id": int(item.maTaiLieu),
                        "title": item.tieuDe,
                        "category": mat_cat_name.get(int(item.maTaiLieu)),
                        "score": round(float(item.score or 0.0), 4),
                        "reason_codes": list(item.reasonCodes or []),
                        "is_domain_relevant": int(item.maTaiLieu) in relevant_materials,
                    }
                    for idx, item in enumerate(m_rec.items[:5])
                ],
            })

    # Macro-averages (All 8 personas + Personalized 7 personas excluding cold-start)
    def macro_summary(entries: list[dict], union_set: set[int], catalog_size: int, exclude_cold: bool = False) -> dict:
        subset = [e for e in entries if not (exclude_cold and e["persona"] == "official_persona_new")]
        res = {}
        for k_key in ("k5", "k10"):
            res[k_key] = {
                m: round(statistics.mean([e[k_key][m] for e in subset]), 4)
                for m in ("precision", "recall", "hit_rate", "ndcg", "mrr")
            }
        res["diversity_at_10"] = round(statistics.mean([e["diversity_at_10"] for e in subset]), 4)
        res["catalog_coverage_at_10"] = round(len(union_set) / max(1, catalog_size), 4)
        return res

    summary_courses_all8 = {a: macro_summary(course_results_by_algo[a], course_recommended_union[a], len(all_course_ids), False) for a in algos_course}
    summary_courses_pers7 = {a: macro_summary(course_results_by_algo[a], course_recommended_union[a], len(all_course_ids), True) for a in algos_course}
    summary_materials_all8 = {a: macro_summary(mat_results_by_algo[a], mat_recommended_union[a], len(all_mat_ids), False) for a in algos_mat}

    config_doc = {
        "evaluation_date": datetime.now(timezone.utc).isoformat(),
        "dataset": "edusuggest-official-v2 (EduSuggest READ ONLY)",
        "python_version": platform.python_version(),
        "eligible_courses_count": len(all_course_ids),
        "eligible_standalone_materials_count": len(all_mat_ids),
        "personas_evaluated": len(PERSONA_DOMAIN_CATEGORIES),
        "k_values": [5, 10],
        "random_seeds": RANDOM_SEEDS,
        "ground_truth_methodology": "Independent domain-category relevance labels mapped from the 24 EduSuggest taxonomy categories prior to evaluation; already-enrolled courses are excluded from each persona's eligible candidate pool.",
        "limitations": [
            "8 Official Personas with simulated learning histories (3-4 enrollments each) represent structured domain archetypes rather than real production student clickstreams.",
            "Category-level relevance labels evaluate domain alignment rather than fine-grained user satisfaction or completion rate.",
            "Results should be presented in thesis defense as offline simulation evaluation on Official Dataset V2, NOT as a live human user survey.",
        ],
    }

    results_doc = {
        "config": config_doc,
        "macro_courses_all_8_personas": summary_courses_all8,
        "macro_courses_personalized_7_personas": summary_courses_pers7,
        "macro_materials_all_8_personas": summary_materials_all8,
        "per_persona_courses": course_results_by_algo,
        "per_persona_materials": mat_results_by_algo,
        "case_studies": case_studies,
    }

    # Save JSON & CSV artifacts
    (REPORTS_DIR / "recommendation-evaluation-config.json").write_text(json.dumps(config_doc, ensure_ascii=False, indent=2), encoding="utf-8")
    (REPORTS_DIR / "recommendation-relevance-labels.json").write_text(json.dumps(relevance_labels, ensure_ascii=False, indent=2), encoding="utf-8")
    (REPORTS_DIR / "recommendation-evaluation-results.json").write_text(json.dumps(results_doc, ensure_ascii=False, indent=2), encoding="utf-8")

    csv_path = REPORTS_DIR / "recommendation-evaluation-results.csv"
    with csv_path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=list(eval_rows[0].keys()))
        writer.writeheader()
        writer.writerows(eval_rows)

    # Generate 4 real matplotlib charts
    plt.rcParams["font.sans-serif"] = ["DejaVu Sans"]
    navy, teal, amber, slate = "#0f172a", "#0d9488", "#d97706", "#64748b"

    # Chart 1: Baseline Comparison (Personalized 7 Personas - Course Recommendation @5 & @10)
    labels = ["TF-IDF +\nCosine", "Latest", "Popularity", "Random\n(20 seeds)"]
    keys = ["tfidf_cosine", "latest", "popularity", "random_20seeds"]
    p5 = [summary_courses_pers7[k]["k5"]["precision"] for k in keys]
    r5 = [summary_courses_pers7[k]["k5"]["recall"] for k in keys]
    ndcg5 = [summary_courses_pers7[k]["k5"]["ndcg"] for k in keys]
    hr5 = [summary_courses_pers7[k]["k5"]["hit_rate"] for k in keys]

    x = range(len(labels))
    w = 0.2
    fig, ax = plt.subplots(figsize=(9, 5), dpi=150)
    ax.bar([i - 1.5*w for i in x], p5, width=w, label="Precision@5", color=navy)
    ax.bar([i - 0.5*w for i in x], r5, width=w, label="Recall@5", color=teal)
    ax.bar([i + 0.5*w for i in x], ndcg5, width=w, label="NDCG@5", color=amber)
    ax.bar([i + 1.5*w for i in x], hr5, width=w, label="Hit Rate@5", color=slate)
    ax.set_xticks(list(x))
    ax.set_xticklabels(labels)
    ax.set_ylim(0, 1.15)
    ax.set_ylabel("Score (0.0 – 1.0)")
    ax.set_title("Course Recommendation Baseline Comparison (7 Personalized Personas, K=5)")
    ax.legend(frameon=False, ncol=4, loc="upper center")
    ax.grid(axis="y", linestyle="--", alpha=0.4)
    fig.tight_layout()
    fig.savefig(CHARTS_DIR / "baseline_comparison_courses_k5.png")
    plt.close(fig)

    # Chart 2: Precision, Recall, NDCG @5 vs @10 (TF-IDF Courses vs Materials, All 8 Personas)
    m_names = ["Precision", "Recall", "NDCG", "Hit Rate", "MRR"]
    m_keys = ["precision", "recall", "ndcg", "hit_rate", "mrr"]
    c_k5 = [summary_courses_all8["tfidf_cosine"]["k5"][k] for k in m_keys]
    c_k10 = [summary_courses_all8["tfidf_cosine"]["k10"][k] for k in m_keys]
    mt_k5 = [summary_materials_all8["tfidf_cosine"]["k5"][k] for k in m_keys]
    mt_k10 = [summary_materials_all8["tfidf_cosine"]["k10"][k] for k in m_keys]

    x = range(len(m_names))
    fig, ax = plt.subplots(figsize=(9.5, 5), dpi=150)
    ax.bar([i - 1.5*w for i in x], c_k5, width=w, label="Courses @5", color=navy)
    ax.bar([i - 0.5*w for i in x], c_k10, width=w, label="Courses @10", color="#334155")
    ax.bar([i + 0.5*w for i in x], mt_k5, width=w, label="Materials @5", color=teal)
    ax.bar([i + 1.5*w for i in x], mt_k10, width=w, label="Materials @10", color="#5eead4")
    ax.set_xticks(list(x))
    ax.set_xticklabels(m_names)
    ax.set_ylim(0, 1.15)
    ax.set_ylabel("Macro-Average Score (8 Personas)")
    ax.set_title("TF-IDF + Cosine Similarity: Courses vs. Materials at K=5 and K=10")
    ax.legend(frameon=False, ncol=4, loc="upper center")
    ax.grid(axis="y", linestyle="--", alpha=0.4)
    fig.tight_layout()
    fig.savefig(CHARTS_DIR / "precision_recall_ndcg_k5_k10.png")
    plt.close(fig)

    # Chart 3: Catalog Coverage @10 across Baselines
    cov_vals = [summary_courses_all8[k]["catalog_coverage_at_10"] * 100 for k in keys]
    fig, ax = plt.subplots(figsize=(7.5, 4.5), dpi=150)
    bars = ax.bar(labels, cov_vals, color=[teal, slate, amber, "#94a3b8"], width=0.5)
    for b, v in zip(bars, cov_vals):
        ax.text(b.get_x() + b.get_width()/2, v + 1.5, f"{v:.1f}%", ha="center", fontweight="bold", fontsize=9)
    ax.set_ylim(0, max(cov_vals) + 15)
    ax.set_ylabel("Catalog Coverage@10 (%)")
    ax.set_title("Course Catalog Coverage@10 Across Algorithms (8 Personas)")
    ax.grid(axis="y", linestyle="--", alpha=0.4)
    fig.tight_layout()
    fig.savefig(CHARTS_DIR / "catalog_coverage_comparison.png")
    plt.close(fig)

    # Chart 4: Latency Before (GĐ6.1) vs After (GĐ6.2/6.3)
    lat_labels = ["GĐ6.1 Before\n(p50)", "GĐ6.1 Before\n(Max)", "GĐ6.3 Cold\n(p50)", "GĐ6.3 HTTP Warm\n(p95)", "GĐ6.3 HTTP Warm\n(p50)"]
    lat_vals = [15232.0, 18277.0, 1166.32, 278.01, 141.29]
    fig, ax = plt.subplots(figsize=(8.5, 4.5), dpi=150)
    bars = ax.bar(lat_labels, lat_vals, color=["#dc2626", "#991b1b", amber, "#0284c7", teal], width=0.55)
    ax.set_yscale("log")
    for b, v in zip(bars, lat_vals):
        ax.text(b.get_x() + b.get_width()/2, v * 1.15, f"{v:,.0f} ms", ha="center", fontweight="bold", fontsize=8.5)
    ax.set_ylabel("Latency (ms, log scale)")
    ax.set_title("Recommendation Engine Latency: Before vs. After Optimization (108x–134x Speedup)")
    ax.grid(axis="y", linestyle="--", alpha=0.4)
    fig.tight_layout()
    fig.savefig(CHARTS_DIR / "latency_before_after_optimization.png")
    plt.close(fig)

    print(json.dumps({
        "courses_pers7_tfidf": summary_courses_pers7["tfidf_cosine"],
        "courses_pers7_latest": summary_courses_pers7["latest"],
        "courses_pers7_popularity": summary_courses_pers7["popularity"],
        "courses_pers7_random": summary_courses_pers7["random_20seeds"],
        "materials_all8_tfidf": summary_materials_all8["tfidf_cosine"],
        "materials_all8_latest": summary_materials_all8["latest"],
    }, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
