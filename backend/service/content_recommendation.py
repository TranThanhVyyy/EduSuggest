"""Small, dependency-free content ranking helpers for EduSuggest."""

from __future__ import annotations

import html
import math
import re
import unicodedata
from collections import Counter
from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass
from decimal import Decimal

_TAG_RE = re.compile(r"<[^>]+>")
_URL_RE = re.compile(r"(?:https?://|www\.)\S+", re.IGNORECASE)
_TOKEN_RE = re.compile(r"[^\W_]+", re.UNICODE)
_STOP_WORDS = frozenset(
    ["a", "an", "and", "are", "as", "at", "be", "by", "for", "from", "in", "into", "is", "it", "of", "on", "or", "that", "the", "this", "to", "was", "with", "va", "và", "la", "là", "cua", "của", "cho", "trong", "các", "cac", "nhung", "những", "voi", "với", "duoc", "được", "co", "có", "mot", "một", "nhieu", "nhiều", "tren", "trên", "duoi", "dưới", "ve", "về", "tai", "tại", "khi", "den", "đến", "theo", "nhu", "như", "da", "đã", "dang", "đang", "se", "sẽ", "can", "cần", "hoc", "học", "khoa", "khóa", "bai", "bài", "mon", "môn", "noi", "nội", "dung", "co", "cơ", "ban", "bản", "nguoi", "người", "dung", "dùng", "he", "hệ", "thong", "thống"]
)
_FIELD_WEIGHTS = {
    "title": 0.40,
    "description": 0.30,
    "category": 0.10,
    "lessons": 0.15,
    "materials": 0.05,
}


@dataclass(frozen=True)
class CourseFeatures:
    course_id: int
    title: str | None = None
    description: str | None = None
    category_id: int | None = None
    category_text: str | None = None
    level: str | None = None
    duration: float | None = None
    price: float | Decimal | None = None
    lesson_text: tuple[str, ...] = ()
    material_text: tuple[str, ...] = ()
    review_status: str | None = None
    visibility: str | None = None
    created_at: object | None = None
    updated_at: object | None = None

    @property
    def is_public(self) -> bool:
        return (
            (self.review_status or "").upper() == "APPROVED"
            and (self.visibility or "").upper() == "VISIBLE"
        )


@dataclass(frozen=True)
class CourseSignal:
    course: CourseFeatures
    weight: float = 1.0


@dataclass(frozen=True)
class PreferenceProfile:
    text_counts: Mapping[str, float]
    category_weights: Mapping[int, float]
    level_weights: Mapping[str, float]
    duration: float | None
    price: float | None
    corpus: tuple[CourseFeatures, ...] = ()


@dataclass(frozen=True)
class MaterialFeatures:
    material_id: int
    course_id: int | None = None
    lesson_id: int | None = None
    category_id: int | None = None
    title: str | None = None
    description: str | None = None
    material_type: str | None = None
    lesson_title: str | None = None
    lesson_content: str | None = None
    course_title: str | None = None
    category_text: str | None = None
    review_status: str | None = None
    visibility: str | None = None
    created_at: object | None = None
    updated_at: object | None = None

    @property
    def is_public(self) -> bool:
        return (
            (self.review_status or "").upper() == "APPROVED"
            and (self.visibility or "").upper() == "VISIBLE"
        )


@dataclass(frozen=True)
class RankedItem:
    item: CourseFeatures | MaterialFeatures
    score: float
    reason_codes: tuple[str, ...]


def normalize_text(value: str | None) -> str:
    if not value:
        return ""
    value = html.unescape(value)
    value = _TAG_RE.sub(" ", value)
    value = _URL_RE.sub(" ", value)
    value = unicodedata.normalize("NFC", value).casefold()
    return " ".join(value.split())


def tokenize(value: str | None) -> tuple[str, ...]:
    normalized = normalize_text(value)
    return tuple(
        token
        for token in _TOKEN_RE.findall(normalized)
        if len(token) > 1 and token not in _STOP_WORDS
    )


def _course_fields(course: CourseFeatures) -> dict[str, tuple[str, ...]]:
    return {
        "title": (course.title or "",),
        "description": (course.description or "",),
        "category": (course.category_text or "",),
        "lessons": course.lesson_text,
        "materials": course.material_text,
    }


def _weighted_terms(fields: Mapping[str, Iterable[str]]) -> Counter[str]:
    terms: Counter[str] = Counter()
    for field_name, values in fields.items():
        tokens = [token for value in values for token in tokenize(value)]
        if not tokens:
            continue
        weight = _FIELD_WEIGHTS.get(field_name, 1.0)
        denominator = len(tokens)
        terms.update({token: weight * count / denominator for token, count in Counter(tokens).items()})
    return terms


def _course_terms(course: CourseFeatures) -> Counter[str]:
    return _weighted_terms(_course_fields(course))


def _idf(corpus: Sequence[Mapping[str, float]]) -> dict[str, float]:
    document_frequency: Counter[str] = Counter()
    for document in corpus:
        document_frequency.update(document.keys())
    size = max(len(corpus), 1)
    return {
        term: math.log(1 + (size + 1) / (frequency + 1))
        for term, frequency in document_frequency.items()
    }


def _vector(
    terms: Mapping[str, float], inverse_document_frequency: Mapping[str, float]
) -> dict[str, float]:
    result: dict[str, float] = {}
    for term, frequency in terms.items():
        if frequency <= 0:
            continue
        idf = inverse_document_frequency.get(term, 0.0)
        if idf <= 0:
            continue
        result[term] = (1 + math.log(frequency)) * idf if frequency >= 1 else frequency * idf
    return result


def _cosine(left: Mapping[str, float], right: Mapping[str, float]) -> float:
    if not left or not right:
        return 0.0
    shared = left.keys() & right.keys()
    if not shared:
        return 0.0
    dot = sum(left[key] * right[key] for key in shared)
    left_norm = math.sqrt(sum(value * value for value in left.values()))
    right_norm = math.sqrt(sum(value * value for value in right.values()))
    return dot / (left_norm * right_norm) if left_norm and right_norm else 0.0


def _text_similarity(
    left: Mapping[str, float],
    right: Mapping[str, float],
    corpus: Sequence[Mapping[str, float]],
    *,
    minimum_shared_terms: int = 2,
    idf_cache: Mapping[str, float] | None = None,
    left_vec_cache: tuple[Mapping[str, float], float] | None = None,
) -> float:
    shared_words = {
        term for term in left.keys() & right.keys() if not term.startswith("__bigram__")
    }
    if len(shared_words) < minimum_shared_terms:
        return 0.0
    inverse_document_frequency = idf_cache if idf_cache is not None else _idf(corpus)
    if left_vec_cache is not None:
        left_vec, left_norm = left_vec_cache
    else:
        left_vec = _vector(left, inverse_document_frequency)
        left_norm = math.sqrt(sum(v * v for v in left_vec.values()))
    right_vec = _vector(right, inverse_document_frequency)
    if not left_vec or not right_vec or not left_norm:
        return 0.0
    shared = left_vec.keys() & right_vec.keys()
    if not shared:
        return 0.0
    dot = sum(left_vec[k] * right_vec[k] for k in shared)
    right_norm = math.sqrt(sum(v * v for v in right_vec.values()))
    return dot / (left_norm * right_norm) if right_norm else 0.0


def _has_course_content(course: CourseFeatures) -> bool:
    return bool(
        course.category_id is not None
        or _course_terms(course)
        or (course.category_text and tokenize(course.category_text))
    )


def has_course_content(course: CourseFeatures) -> bool:
    """Whether an item contains at least one usable text or category feature."""
    return _has_course_content(course)


def _ratio_similarity(left: float | None, right: float | None) -> float | None:
    if left is None or right is None:
        return None
    left = max(float(left), 0.0)
    right = max(float(right), 0.0)
    difference = abs(math.log1p(left) - math.log1p(right))
    return 1 / (1 + difference)


def _combine(components: Sequence[tuple[float, float | None]]) -> float:
    present = [(weight, score) for weight, score in components if score is not None]
    denominator = sum(weight for weight, _ in present)
    if denominator <= 0:
        return 0.0
    return sum(weight * float(score) for weight, score in present) / denominator


def _course_pair_score(
    left: CourseFeatures,
    right: CourseFeatures,
    corpus: Sequence[Mapping[str, float]],
    *,
    left_terms: Mapping[str, float] | None = None,
    right_terms: Mapping[str, float] | None = None,
    idf_cache: Mapping[str, float] | None = None,
    left_vec_cache: tuple[Mapping[str, float], float] | None = None,
) -> tuple[float, tuple[str, ...]]:
    l_terms = left_terms if left_terms is not None else _course_terms(left)
    r_terms = right_terms if right_terms is not None else _course_terms(right)
    text_score = (
        _text_similarity(
            l_terms, r_terms, corpus, idf_cache=idf_cache, left_vec_cache=left_vec_cache
        )
        if l_terms and r_terms
        else None
    )
    category_score = (
        float(left.category_id == right.category_id)
        if left.category_id is not None and right.category_id is not None
        else None
    )
    level_score = (
        float(normalize_text(left.level) == normalize_text(right.level))
        if left.level and right.level
        else None
    )
    duration_score = _ratio_similarity(left.duration, right.duration)
    price_score = _ratio_similarity(left.price, right.price)
    components = (
        (0.60, text_score),
        (0.20, category_score),
        (0.08, level_score),
        (0.06, duration_score),
        (0.06, price_score),
    )
    reasons: list[str] = []
    if text_score is not None and text_score > 0:
        reasons.append("CONTENT_SIMILARITY")
    if category_score == 1:
        reasons.append("SAME_CATEGORY")
    if level_score == 1:
        reasons.append("SIMILAR_LEVEL")
    if duration_score is not None and duration_score >= 0.75:
        reasons.append("SIMILAR_DURATION")
    if price_score is not None and price_score >= 0.75:
        reasons.append("SIMILAR_PRICE")
    return _combine(components), tuple(reasons)


def rank_similar_courses(
    source: CourseFeatures,
    candidates: Sequence[CourseFeatures],
    limit: int = 10,
    *,
    precomputed_terms: Mapping[int, Counter[str]] | None = None,
) -> list[RankedItem]:
    terms_cache: dict[int, Counter[str]] = dict(precomputed_terms) if precomputed_terms else {}

    def get_terms(c: CourseFeatures) -> Counter[str]:
        t = terms_cache.get(c.course_id)
        if t is None:
            t = _course_terms(c)
            terms_cache[c.course_id] = t
        return t

    if not source.is_public or not (source.category_id is not None or get_terms(source)):
        return []
    unique_candidates: dict[int, CourseFeatures] = {}
    for candidate in candidates:
        if (
            candidate.course_id != source.course_id
            and candidate.is_public
            and (candidate.category_id is not None or get_terms(candidate))
        ):
            unique_candidates.setdefault(candidate.course_id, candidate)
    corpus_courses = [source, *unique_candidates.values()]
    corpus = [get_terms(course) for course in corpus_courses]
    idf_cache = _idf(corpus)
    src_terms = get_terms(source)
    src_vec = _vector(src_terms, idf_cache)
    src_norm = math.sqrt(sum(v * v for v in src_vec.values()))
    ranked: list[RankedItem] = []
    for candidate in unique_candidates.values():
        score, reasons = _course_pair_score(
            source,
            candidate,
            corpus,
            left_terms=src_terms,
            right_terms=get_terms(candidate),
            idf_cache=idf_cache,
            left_vec_cache=(src_vec, src_norm),
        )
        if score > 0:
            ranked.append(RankedItem(candidate, score, reasons))
    ranked.sort(key=lambda item: (-item.score, item.item.course_id))
    return ranked[: max(0, limit)]


def build_preference_profile(
    signals: Sequence[CourseSignal],
    candidate_courses: Sequence[CourseFeatures],
    *,
    precomputed_terms: Mapping[int, Counter[str]] | None = None,
) -> PreferenceProfile | None:
    terms_cache: dict[int, Counter[str]] = dict(precomputed_terms) if precomputed_terms else {}

    def get_terms(c: CourseFeatures) -> Counter[str]:
        t = terms_cache.get(c.course_id)
        if t is None:
            t = _course_terms(c)
            terms_cache[c.course_id] = t
        return t

    usable_signals = [
        signal
        for signal in signals
        if signal.weight > 0 and (signal.course.category_id is not None or get_terms(signal.course))
    ]
    if not usable_signals:
        return None

    text_counts: Counter[str] = Counter()
    category_weights: Counter[int] = Counter()
    level_weights: Counter[str] = Counter()
    duration_sum = duration_weight = 0.0
    price_sum = price_weight = 0.0
    corpus_courses: dict[int, CourseFeatures] = {
        course.course_id: course for course in candidate_courses
    }
    for signal in usable_signals:
        course = signal.course
        corpus_courses.setdefault(course.course_id, course)
        for term, value in get_terms(course).items():
            text_counts[term] += value * signal.weight
        if course.category_id is not None:
            category_weights[course.category_id] += signal.weight
        if course.level:
            level_weights[normalize_text(course.level)] += signal.weight
        if course.duration is not None:
            duration_sum += max(float(course.duration), 0) * signal.weight
            duration_weight += signal.weight
        if course.price is not None:
            price_sum += max(float(course.price), 0) * signal.weight
            price_weight += signal.weight

    return PreferenceProfile(
        text_counts=dict(text_counts),
        category_weights=dict(category_weights),
        level_weights=dict(level_weights),
        duration=duration_sum / duration_weight if duration_weight else None,
        price=price_sum / price_weight if price_weight else None,
        corpus=tuple(corpus_courses.values()),
    )


def _profile_pair_score(
    profile: PreferenceProfile,
    candidate: CourseFeatures,
    *,
    candidate_terms: Mapping[str, float] | None = None,
    corpus_terms: Sequence[Mapping[str, float]] | None = None,
    idf_cache: Mapping[str, float] | None = None,
    profile_vec_cache: tuple[Mapping[str, float], float] | None = None,
) -> tuple[float, tuple[str, ...]]:
    c_terms = candidate_terms if candidate_terms is not None else _course_terms(candidate)
    all_corpus_terms = corpus_terms if corpus_terms is not None else [_course_terms(course) for course in profile.corpus]
    if profile.text_counts and c_terms:
        text_score: float | None = _text_similarity(
            profile.text_counts,
            c_terms,
            all_corpus_terms,
            idf_cache=idf_cache,
            left_vec_cache=profile_vec_cache,
        )
    else:
        text_score = None

    category_total = sum(profile.category_weights.values())
    category_score = (
        profile.category_weights.get(candidate.category_id, 0.0) / category_total
        if candidate.category_id is not None and category_total
        else None
    )
    level_total = sum(profile.level_weights.values())
    level_score = (
        profile.level_weights.get(normalize_text(candidate.level), 0.0) / level_total
        if candidate.level and level_total
        else None
    )
    duration_score = _ratio_similarity(profile.duration, candidate.duration)
    price_score = _ratio_similarity(profile.price, candidate.price)
    components = (
        (0.60, text_score),
        (0.20, category_score),
        (0.08, level_score),
        (0.06, duration_score),
        (0.06, price_score),
    )
    reasons: list[str] = []
    if text_score is not None and text_score > 0:
        reasons.append("CONTENT_SIMILARITY")
    if category_score is not None and category_score > 0:
        reasons.append("SAME_CATEGORY")
    if level_score is not None and level_score > 0:
        reasons.append("SIMILAR_LEVEL")
    if duration_score is not None and duration_score >= 0.75:
        reasons.append("SIMILAR_DURATION")
    if price_score is not None and price_score >= 0.75:
        reasons.append("SIMILAR_PRICE")
    return _combine(components), tuple(reasons)


def rank_personalized_courses(
    profile: PreferenceProfile | None,
    candidates: Sequence[CourseFeatures],
    *,
    excluded_course_ids: set[int] | None = None,
    limit: int = 10,
    precomputed_terms: Mapping[int, Counter[str]] | None = None,
) -> list[RankedItem]:
    if profile is None:
        return []
    terms_cache: dict[int, Counter[str]] = dict(precomputed_terms) if precomputed_terms else {}

    def get_terms(c: CourseFeatures) -> Counter[str]:
        t = terms_cache.get(c.course_id)
        if t is None:
            t = _course_terms(c)
            terms_cache[c.course_id] = t
        return t

    excluded = excluded_course_ids or set()
    unique_candidates: dict[int, CourseFeatures] = {}
    for candidate in candidates:
        if (
            candidate.course_id not in excluded
            and candidate.is_public
            and (candidate.category_id is not None or get_terms(candidate))
        ):
            unique_candidates.setdefault(candidate.course_id, candidate)
    usable_corpus = {
        course.course_id: course for course in (*profile.corpus, *unique_candidates.values())
    }
    scoring_profile = PreferenceProfile(
        text_counts=profile.text_counts,
        category_weights=profile.category_weights,
        level_weights=profile.level_weights,
        duration=profile.duration,
        price=profile.price,
        corpus=tuple(usable_corpus.values()),
    )
    # Precompute corpus terms, IDF, and profile TF-IDF vector ONCE (O(N) instead of O(N^2))
    corpus_terms = [get_terms(course) for course in scoring_profile.corpus]
    idf_cache = _idf(corpus_terms)
    prof_vec = _vector(scoring_profile.text_counts, idf_cache) if scoring_profile.text_counts else {}
    prof_norm = math.sqrt(sum(v * v for v in prof_vec.values()))

    ranked: list[RankedItem] = []
    for candidate in unique_candidates.values():
        score, reasons = _profile_pair_score(
            scoring_profile,
            candidate,
            candidate_terms=get_terms(candidate),
            corpus_terms=corpus_terms,
            idf_cache=idf_cache,
            profile_vec_cache=(prof_vec, prof_norm),
        )
        if score > 0:
            ranked.append(RankedItem(candidate, score, reasons))
    ranked.sort(key=lambda item: (-item.score, item.item.course_id))
    return ranked[: max(0, limit)]


def rank_materials(
    context_fields: Mapping[str, Iterable[str]],
    materials: Sequence[MaterialFeatures],
    *,
    lesson_id: int | None = None,
    limit: int = 10,
) -> list[RankedItem]:
    context_terms = _weighted_terms(context_fields)
    usable: dict[int, MaterialFeatures] = {}
    material_terms: dict[int, Counter[str]] = {}
    for material in materials:
        if (
            material.review_status is not None or material.visibility is not None
        ) and not material.is_public:
            continue
        terms = _weighted_terms(
            {
                "title": (material.title or "",),
                "description": (material.description or "",),
                "category": (material.material_type or "",),
                "lessons": (material.lesson_title or "", material.lesson_content or ""),
                "materials": (material.course_title or "", material.category_text or ""),
            }
        )
        if terms:
            usable.setdefault(material.material_id, material)
            material_terms.setdefault(material.material_id, terms)
    if not context_terms or not usable:
        return []

    corpus = [context_terms, *material_terms.values()]
    ranked: list[RankedItem] = []
    for material_id, material in usable.items():
        text_score = _text_similarity(
            context_terms,
            material_terms[material_id],
            corpus,
            minimum_shared_terms=1,
        )
        same_lesson = lesson_id is not None and material.lesson_id == lesson_id
        score = 0.65 * text_score + (0.35 if same_lesson else 0.0)
        reasons: list[str] = []
        if text_score > 0:
            reasons.append("CONTENT_SIMILARITY")
        if same_lesson:
            reasons.append("SAME_LESSON")
        if score > 0:
            ranked.append(RankedItem(material, score, tuple(reasons)))
    ranked.sort(key=lambda item: (-item.score, item.item.material_id))
    return ranked[: max(0, limit)]


def _material_fields(material: MaterialFeatures) -> dict[str, tuple[str, ...]]:
    return {
        "title": (material.title or "",),
        "description": (material.description or "",),
        "category": (material.category_text or "", material.material_type or ""),
        "lessons": (material.lesson_title or "", material.lesson_content or ""),
        "materials": (material.course_title or "",),
    }


def _material_terms(material: MaterialFeatures) -> Counter[str]:
    return _weighted_terms(_material_fields(material))


def rank_standalone_materials(
    profile: PreferenceProfile | None,
    materials: Sequence[MaterialFeatures],
    *,
    limit: int = 10,
) -> tuple[list[RankedItem], str, bool]:
    public_materials = [m for m in materials if m.is_public]
    if not public_materials:
        return [], "none", False

    usable_materials: dict[int, MaterialFeatures] = {}
    material_terms: dict[int, Counter[str]] = {}
    for material in public_materials:
        terms = _material_terms(material)
        if terms:
            usable_materials[material.material_id] = material
            material_terms[material.material_id] = terms

    if not profile or not profile.text_counts or not usable_materials:
        sorted_latest = sorted(
            public_materials,
            key=lambda m: (str(m.created_at or ""), m.material_id),
            reverse=True,
        )
        items = [
            RankedItem(item=m, score=0.0, reason_codes=("RECENT_MATERIAL",))
            for m in sorted_latest[: max(0, limit)]
        ]
        return items, "latest", False

    corpus = [profile.text_counts, *material_terms.values()]
    idf_cache = _idf(corpus)
    prof_vec = _vector(profile.text_counts, idf_cache)
    prof_norm = math.sqrt(sum(v * v for v in prof_vec.values()))
    ranked: list[RankedItem] = []
    category_total = sum(profile.category_weights.values())

    for material_id, material in usable_materials.items():
        terms = material_terms[material_id]
        text_score = _text_similarity(
            profile.text_counts,
            terms,
            corpus,
            minimum_shared_terms=1,
            idf_cache=idf_cache,
            left_vec_cache=(prof_vec, prof_norm),
        )
        category_score = (
            profile.category_weights.get(material.category_id, 0.0) / category_total
            if material.category_id is not None and category_total
            else 0.0
        )
        combined_score = 0.70 * text_score + 0.30 * category_score
        reasons: list[str] = []
        if text_score > 0:
            reasons.append("CONTENT_SIMILARITY")
        if category_score > 0:
            reasons.append("SAME_CATEGORY")
        if material.material_type:
            reasons.append("RECOMMENDED_TYPE")

        if combined_score > 0:
            ranked.append(RankedItem(material, round(combined_score, 4), tuple(reasons)))

    if not ranked:
        sorted_latest = sorted(
            public_materials,
            key=lambda m: (str(m.created_at or ""), m.material_id),
            reverse=True,
        )
        items = [
            RankedItem(item=m, score=0.0, reason_codes=("RECENT_MATERIAL",))
            for m in sorted_latest[: max(0, limit)]
        ]
        return items, "latest", False

    ranked.sort(key=lambda item: (-item.score, item.item.material_id))
    return ranked[: max(0, limit)], "content_based", True


def rank_similar_materials(
    source: MaterialFeatures,
    candidates: Sequence[MaterialFeatures],
    *,
    limit: int = 10,
) -> list[RankedItem]:
    source_terms = _material_terms(source)
    if not source_terms:
        return []

    unique_candidates: dict[int, MaterialFeatures] = {}
    material_terms: dict[int, Counter[str]] = {}
    for c in candidates:
        if c.material_id != source.material_id and c.is_public:
            terms = _material_terms(c)
            if terms:
                unique_candidates[c.material_id] = c
                material_terms[c.material_id] = terms

    if not unique_candidates:
        return []

    corpus = [source_terms, *material_terms.values()]
    ranked: list[RankedItem] = []
    for material_id, candidate in unique_candidates.items():
        terms = material_terms[material_id]
        text_score = _text_similarity(
            source_terms,
            terms,
            corpus,
            minimum_shared_terms=1,
        )
        same_cat = source.category_id is not None and source.category_id == candidate.category_id
        same_type = bool(source.material_type and source.material_type == candidate.material_type)
        same_course = source.course_id is not None and source.course_id == candidate.course_id

        score = (
            0.60 * text_score
            + (0.20 if same_cat else 0.0)
            + (0.10 if same_type else 0.0)
            + (0.10 if same_course else 0.0)
        )
        reasons: list[str] = []
        if text_score > 0:
            reasons.append("CONTENT_SIMILARITY")
        if same_cat:
            reasons.append("SAME_CATEGORY")
        if same_type:
            reasons.append("SAME_TYPE")
        if same_course:
            reasons.append("SAME_COURSE")

        if score > 0:
            ranked.append(RankedItem(candidate, round(score, 4), tuple(reasons)))

    ranked.sort(key=lambda item: (-item.score, item.item.material_id))
    return ranked[: max(0, limit)]
