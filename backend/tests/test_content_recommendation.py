import unittest

from service.content_recommendation import (
    CourseFeatures,
    CourseSignal,
    MaterialFeatures,
    build_preference_profile,
    normalize_text,
    rank_materials,
    rank_personalized_courses,
    rank_similar_courses,
    tokenize,
)


def course(
    course_id: int,
    title: str | None,
    *,
    description: str | None = None,
    category_id: int | None = None,
    level: str | None = None,
    public: bool = True,
) -> CourseFeatures:
    return CourseFeatures(
        course_id=course_id,
        title=title,
        description=description,
        category_id=category_id,
        level=level,
        review_status="APPROVED" if public else "PENDING",
        visibility="VISIBLE" if public else "HIDDEN",
    )


class ContentRecommendationTests(unittest.TestCase):
    def test_normalizes_html_urls_and_vietnamese_text(self):
        self.assertEqual(
            normalize_text("<p>LẬP  trình</p> https://example.com/file"),
            "lập trình",
        )
        self.assertIn("trình", tokenize("Lập trình Python"))

    def test_empty_and_null_text_do_not_create_features(self):
        self.assertEqual(tokenize(None), ())
        self.assertEqual(tokenize("<p> </p> https://example.com"), ())

    def test_common_single_word_does_not_make_courses_similar(self):
        source = course(1, "Khóa học Python")
        candidate = course(2, "Học Python trực tuyến")
        self.assertEqual(rank_similar_courses(source, [candidate]), [])

    def test_content_similarity_ranks_related_course_first(self):
        source = course(
            1,
            "Lập trình Python cơ bản",
            description="Viết chương trình xử lý dữ liệu và tự động hóa công việc.",
            category_id=10,
        )
        related = course(
            2,
            "Lập trình Python nâng cao",
            description="Thực hành xử lý dữ liệu bằng Python, xây dựng chương trình tự động.",
            category_id=10,
        )
        unrelated = course(
            3,
            "Nấu ăn món chay",
            description="Chế biến thực đơn dinh dưỡng từ rau củ.",
            category_id=20,
        )
        ranked = rank_similar_courses(source, [unrelated, related])
        self.assertEqual([item.item.course_id for item in ranked], [2])
        self.assertGreater(ranked[0].score, 0)
        self.assertIn("CONTENT_SIMILARITY", ranked[0].reason_codes)

    def test_similar_courses_filter_private_source_duplicates_and_limit(self):
        source = course(1, "Lập trình Python dữ liệu", category_id=10)
        candidates = [
            source,
            course(2, "Python lập trình dữ liệu", category_id=10),
            course(2, "Python lập trình dữ liệu nâng cao", category_id=10),
            course(3, "Python lập trình dữ liệu nâng cao", category_id=10, public=False),
            course(4, "Dữ liệu Python lập trình", category_id=10),
        ]
        ranked = rank_similar_courses(source, candidates, limit=1)
        self.assertEqual(len(ranked), 1)
        self.assertNotEqual(ranked[0].item.course_id, 1)
        self.assertEqual(ranked[0].item.course_id, 2)

    def test_personalized_courses_exclude_enrolled_and_private_items(self):
        history = course(
            1,
            "Lập trình Python xử lý dữ liệu",
            description="Tự động hóa và phân tích dữ liệu.",
            category_id=10,
        )
        candidates = [
            course(1, history.title, category_id=10),
            course(2, "Phân tích dữ liệu Python", description="Lập trình và tự động hóa dữ liệu", category_id=10),
            course(3, "Thiết kế nội thất", description="Bố cục màu sắc không gian", category_id=30, public=False),
        ]
        profile = build_preference_profile([CourseSignal(history, 2)], candidates)
        ranked = rank_personalized_courses(profile, candidates, excluded_course_ids={1})
        self.assertEqual([item.item.course_id for item in ranked], [2])

    def test_new_user_has_no_content_profile(self):
        candidate = course(2, "Python phân tích dữ liệu")
        self.assertIsNone(build_preference_profile([], [candidate]))
        self.assertEqual(rank_personalized_courses(None, [candidate]), [])

    def test_material_recommendations_use_lesson_context_and_limit(self):
        materials = [
            MaterialFeatures(
                material_id=1,
                course_id=10,
                lesson_id=100,
                title="Python xử lý dữ liệu",
                description="Thực hành phân tích dữ liệu bằng chương trình.",
                lesson_title="Lập trình Python dữ liệu",
            ),
            MaterialFeatures(
                material_id=2,
                course_id=10,
                lesson_id=101,
                title="Thiết kế phối cảnh",
                description="Không gian và màu sắc nội thất.",
                lesson_title="Thiết kế nội thất",
            ),
        ]
        ranked = rank_materials(
            {"title": ("Lập trình Python dữ liệu",), "description": ("Phân tích dữ liệu",)},
            materials,
            lesson_id=100,
            limit=1,
        )
        self.assertEqual([item.item.material_id for item in ranked], [1])
        self.assertIn("SAME_LESSON", ranked[0].reason_codes)

    def test_materials_without_context_or_metadata_return_empty(self):
        material = MaterialFeatures(material_id=1, course_id=1, lesson_id=1)
        self.assertEqual(rank_materials({}, [material]), [])


if __name__ == "__main__":
    unittest.main()
