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
    course_id: int
    lesson_id: int
    title: str | None = None
    description: str | None = None
    material_type: str | None = None
    lesson_title: str | None = None
    lesson_content: str | None = None
    course_title: str | None = None
    category_text: str | None = None


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
) -> float:
    shared_words = {
        term for term in left.keys() & right.keys() if not term.startswith("__bigram__")
    }
    if len(shared_words) < minimum_shared_terms:
        return 0.0
    inverse_document_frequency = _idf(corpus)
    return _cosine(
        _vector(left, inverse_document_frequency),
        _vector(right, inverse_document_frequency),
    )


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
) -> tuple[float, tuple[str, ...]]:
    left_terms = _course_terms(left)
    right_terms = _course_terms(right)
    text_score = (
        _text_similarity(left_terms, right_terms, corpus)
        if left_terms and right_terms
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
) -> list[RankedItem]:
    if not source.is_public or not _has_course_content(source):
        return []
    unique_candidates: dict[int, CourseFeatures] = {}
    for candidate in candidates:
        if (
            candidate.course_id != source.course_id
            and candidate.is_public
            and _has_course_content(candidate)
        ):
            unique_candidates.setdefault(candidate.course_id, candidate)
    corpus_courses = [source, *unique_candidates.values()]
    corpus = [_course_terms(course) for course in corpus_courses]
    ranked: list[RankedItem] = []
    for candidate in unique_candidates.values():
        score, reasons = _course_pair_score(
            source, candidate, corpus
        )
        if score > 0:
            ranked.append(RankedItem(candidate, score, reasons))
    ranked.sort(key=lambda item: (-item.score, item.item.course_id))
    return ranked[: max(0, limit)]


def build_preference_profile(
    signals: Sequence[CourseSignal],
    candidate_courses: Sequence[CourseFeatures],
) -> PreferenceProfile | None:
    usable_signals = [
        signal
        for signal in signals
        if signal.weight > 0 and _has_course_content(signal.course)
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
        for term, value in _course_terms(course).items():
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
) -> tuple[float, tuple[str, ...]]:
    candidate_terms = _course_terms(candidate)
    corpus_terms = [_course_terms(course) for course in profile.corpus]
    if profile.text_counts and candidate_terms:
        text_score: float | None = _text_similarity(
            profile.text_counts, candidate_terms, corpus_terms
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
) -> list[RankedItem]:
    if profile is None:
        return []
    excluded = excluded_course_ids or set()
    unique_candidates: dict[int, CourseFeatures] = {}
    for candidate in candidates:
        if (
            candidate.course_id not in excluded
            and candidate.is_public
            and _has_course_content(candidate)
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
    ranked: list[RankedItem] = []
    for candidate in unique_candidates.values():
        score, reasons = _profile_pair_score(scoring_profile, candidate)
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
