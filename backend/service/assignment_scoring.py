"""Pure, deterministic, Decimal-based Weighted Scoring & Ranking module for GĐ3.2.

Zero database dependencies — designed for exact arithmetic, deterministic tie-breaking,
and exhaustive unit testing.
"""
from __future__ import annotations

from datetime import datetime
from decimal import Decimal, ROUND_HALF_UP
from typing import Iterable

from schemas.assignment import (
    AssignmentConfigurationError,
    CandidateInput,
    RankedCandidate,
    ScoreBreakdown,
)

SCORING_VERSION = "3.2.0"

# Fairness horizon (168 hours = 7 days) is an independent algorithm constant,
# intentionally decoupled from CauHinhPhanCong.khoangThongKeGio (accountability window).
FAIRNESS_HORIZON_HOURS = Decimal("168")

PRIMARY_SPECIALTY_POINTS = Decimal("50.00")
SECONDARY_SPECIALTY_POINTS = Decimal("35.00")
WORKLOAD_MAX_POINTS = Decimal("30.00")
EXPERIENCE_MAX_POINTS = Decimal("10.00")
FAIRNESS_MAX_POINTS = Decimal("10.00")

ZERO = Decimal("0.00")
ONE = Decimal("1")
HUNDRED = Decimal("100.00")
TWO_DP = Decimal("0.01")


def _q2(val: Decimal) -> Decimal:
    return val.quantize(TWO_DP, rounding=ROUND_HALF_UP)


def compute_candidate_score(
    candidate: CandidateInput,
    *,
    evaluated_at: datetime,
    absolute_primary_priority: bool = False,
) -> ScoreBreakdown:
    """Compute exact, deterministic Weighted Score (0.00..100.00) using Decimal arithmetic.

    Formula:
      TotalScore = SpecialtyScore + WorkloadScore + ExperienceScore + FairnessScore
    where:
      - SpecialtyScore  : 50.00 (PRIMARY) or 35.00 (SECONDARY) — never stacked
      - WorkloadScore   : 30 * max(0, 1 - ActiveAssignments / MaxAssignments)
      - ExperienceScore : min(max(soNamKinhNghiem or 0, 0), 10)
      - FairnessScore   : 10.00 if never assigned; else 10 * min(max(hours / 168, 0), 1)
    """
    if candidate.maxAssignments <= 0:
        raise AssignmentConfigurationError(
            f"Invalid gioiHanTaiToiDa={candidate.maxAssignments}; must be >= 1."
        )

    anomalies: list[str] = []

    # 1. SpecialtyScore (50 or 35, never stacked)
    if candidate.matchType == "PRIMARY":
        specialty_score = PRIMARY_SPECIALTY_POINTS
    elif candidate.matchType == "SECONDARY":
        specialty_score = SECONDARY_SPECIALTY_POINTS
    else:
        raise ValueError(f"Unsupported matchType: {candidate.matchType!r}")

    # 2. WorkloadScore: 30 * max(0, 1 - active / max)
    active = candidate.activeAssignments
    if active < 0:
        anomalies.append(f"NEGATIVE_ACTIVE_WORKLOAD:{active}")
        active = 0
    ratio = Decimal(active) / Decimal(candidate.maxAssignments)
    workload_factor = max(Decimal("0"), ONE - ratio)
    workload_score = _q2(WORKLOAD_MAX_POINTS * workload_factor)

    # 3. ExperienceScore: min(max(years, 0), 10); NULL -> 0
    raw_years = candidate.yearsExperience
    if raw_years is None:
        normalized_years = 0
    elif raw_years < 0:
        anomalies.append(f"NEGATIVE_EXPERIENCE_YEARS:{raw_years}")
        normalized_years = 0
    elif raw_years > 60:
        anomalies.append(f"OUT_OF_RANGE_EXPERIENCE_YEARS:{raw_years}")
        normalized_years = 60
    else:
        normalized_years = int(raw_years)
    experience_score = _q2(Decimal(min(normalized_years, 10)))

    # 4. FairnessScore: 10 * min(max(hours / 168, 0), 1); never assigned -> 10.00
    if candidate.lastAssignedAt is None:
        hours_since: Decimal | None = None
        fairness_score = FAIRNESS_MAX_POINTS
    else:
        delta_seconds = (evaluated_at - candidate.lastAssignedAt).total_seconds()
        raw_hours = Decimal(str(delta_seconds)) / Decimal("3600")
        if raw_hours < Decimal("0"):
            anomalies.append("FUTURE_LAST_ASSIGNED_AT")
            clamped_hours = Decimal("0")
        else:
            clamped_hours = raw_hours
        hours_since = _q2(clamped_hours)
        fairness_ratio = min(max(clamped_hours / FAIRNESS_HORIZON_HOURS, Decimal("0")), ONE)
        fairness_score = _q2(FAIRNESS_MAX_POINTS * fairness_ratio)

    # TotalScore = exact sum of normalized 2-dp components, bounded [0.00, 100.00]
    total_score = specialty_score + workload_score + experience_score + fairness_score
    if total_score < ZERO:
        total_score = ZERO
    elif total_score > HUNDRED:
        total_score = HUNDRED
    total_score = _q2(total_score)

    match_label = (
        "chuyên môn chính" if candidate.matchType == "PRIMARY" else "chuyên môn phụ"
    )
    explanation = (
        f"Chuyên gia phù hợp {match_label} ({candidate.matchedSpecialtyName}) "
        f"với danh mục nội dung, đang xử lý {active}/{candidate.maxAssignments} nhiệm vụ, "
        f"có {normalized_years} năm kinh nghiệm và nhận tổng điểm {total_score:.2f}/100."
    )

    return ScoreBreakdown(
        scoringVersion=SCORING_VERSION,
        specialtyScore=specialty_score,
        workloadScore=workload_score,
        experienceScore=experience_score,
        fairnessScore=fairness_score,
        totalScore=total_score,
        matchType=candidate.matchType,
        matchedSpecialtyId=candidate.matchedSpecialtyId,
        matchedSpecialtyName=candidate.matchedSpecialtyName,
        allMatchedSpecialtyIds=tuple(
            s.maChuyenMon for s in candidate.allMatchedSpecialties
        ),
        activeAssignments=active,
        maxAssignments=candidate.maxAssignments,
        yearsExperience=normalized_years,
        rawYearsExperience=raw_years,
        lastAssignedAt=candidate.lastAssignedAt,
        hoursSinceLastAssignment=hours_since,
        absolutePrimaryPriority=absolute_primary_priority,
        evaluatedAt=evaluated_at,
        anomalies=tuple(anomalies),
        explanationText=explanation,
    )


def ranking_sort_key(
    candidate: CandidateInput,
    breakdown: ScoreBreakdown,
    *,
    absolute_primary_priority: bool,
) -> tuple:
    """Deterministic multi-criteria ranking & tie-breaker key.

    Order:
      0. (Optional, if absolute_primary_priority=True) PRIMARY before SECONDARY.
      1. Higher TotalScore first.
      2. Lower ActiveAssignments first.
      3. Never-assigned first; otherwise older lastAssignedAt first.
      4. Higher SpecialtyScore first.
      5. Lower maChuyenGia ascending (final deterministic tie-breaker).
    """
    primary_group = (
        (0 if breakdown.matchType == "PRIMARY" else 1)
        if absolute_primary_priority
        else 0
    )
    if breakdown.lastAssignedAt is None:
        fairness_tie = (0, datetime.min)
    else:
        fairness_tie = (1, breakdown.lastAssignedAt)

    return (
        primary_group,
        -breakdown.totalScore,
        breakdown.activeAssignments,
        fairness_tie,
        -breakdown.specialtyScore,
        candidate.maChuyenGia,
    )


def rank_candidates_pure(
    candidates: Iterable[CandidateInput],
    *,
    evaluated_at: datetime,
    absolute_primary_priority: bool = False,
) -> list[RankedCandidate]:
    """Score and deterministically rank a collection of eligible candidates."""
    scored: list[tuple[CandidateInput, ScoreBreakdown]] = [
        (
            cand,
            compute_candidate_score(
                cand,
                evaluated_at=evaluated_at,
                absolute_primary_priority=absolute_primary_priority,
            ),
        )
        for cand in candidates
    ]
    scored.sort(
        key=lambda pair: ranking_sort_key(
            pair[0],
            pair[1],
            absolute_primary_priority=absolute_primary_priority,
        )
    )
    return [
        RankedCandidate(
            rank=idx,
            maChuyenGia=cand.maChuyenGia,
            maNguoiDung=cand.maNguoiDung,
            score=breakdown,
        )
        for idx, (cand, breakdown) in enumerate(scored, start=1)
    ]
