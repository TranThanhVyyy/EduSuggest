"""Unit test matrix (25+ scenarios) for pure Decimal Weighted Scoring & Ranking (GĐ3.2)."""
from __future__ import annotations

from datetime import datetime, timedelta
from decimal import Decimal

import pytest

from schemas.assignment import (
    AssignmentConfigurationError,
    CandidateInput,
    MatchedSpecialtyInfo,
)
from service.assignment_scoring import (
    SCORING_VERSION,
    compute_candidate_score,
    rank_candidates_pure,
)

NOW = datetime(2026, 11, 25, 12, 0, 0)


def _cand(
    expert_id: int = 1,
    *,
    user_id: int | None = None,
    match_type: str = "PRIMARY",
    spec_id: int = 10,
    spec_name: str = "Python",
    extra_specs: tuple[MatchedSpecialtyInfo, ...] = (),
    active: int = 0,
    max_assign: int = 5,
    years: int | None = 5,
    last_assigned: datetime | None = None,
) -> CandidateInput:
    rep = MatchedSpecialtyInfo(
        maChuyenMon=spec_id,
        tenChuyenMon=spec_name,
        laChuyenMonChinh=(match_type == "PRIMARY"),
    )
    return CandidateInput(
        maChuyenGia=expert_id,
        maNguoiDung=user_id if user_id is not None else expert_id + 100,
        matchType=match_type,  # type: ignore[arg-type]
        matchedSpecialtyId=spec_id,
        matchedSpecialtyName=spec_name,
        allMatchedSpecialties=(rep, *extra_specs),
        activeAssignments=active,
        maxAssignments=max_assign,
        yearsExperience=years,
        lastAssignedAt=last_assigned,
    )


def test_01_primary_match_receives_50_points():
    s = compute_candidate_score(_cand(match_type="PRIMARY"), evaluated_at=NOW)
    assert s.specialtyScore == Decimal("50.00")


def test_02_secondary_match_receives_35_points():
    s = compute_candidate_score(_cand(match_type="SECONDARY"), evaluated_at=NOW)
    assert s.specialtyScore == Decimal("35.00")


def test_03_no_specialty_stacking_even_with_multiple_matches():
    extras = (
        MatchedSpecialtyInfo(11, "FastAPI", False),
        MatchedSpecialtyInfo(12, "SQL", False),
        MatchedSpecialtyInfo(13, "Docker", False),
    )
    s = compute_candidate_score(
        _cand(match_type="PRIMARY", extra_specs=extras), evaluated_at=NOW
    )
    assert s.specialtyScore == Decimal("50.00")
    assert len(s.allMatchedSpecialtyIds) == 4


def test_04_workload_zero_receives_full_30_points():
    s = compute_candidate_score(_cand(active=0, max_assign=5), evaluated_at=NOW)
    assert s.workloadScore == Decimal("30.00")


def test_05_workload_mid_level_exact_decimal():
    s = compute_candidate_score(_cand(active=2, max_assign=5), evaluated_at=NOW)
    assert s.workloadScore == Decimal("18.00")


def test_06_workload_at_limit_receives_0_points():
    s = compute_candidate_score(_cand(active=5, max_assign=5), evaluated_at=NOW)
    assert s.workloadScore == Decimal("0.00")


def test_07_workload_above_limit_clamped_to_0_never_negative():
    s = compute_candidate_score(_cand(active=8, max_assign=5), evaluated_at=NOW)
    assert s.workloadScore == Decimal("0.00")
    assert s.totalScore >= Decimal("0.00")


def test_08_invalid_max_assignments_fails_closed():
    with pytest.raises(AssignmentConfigurationError):
        compute_candidate_score(_cand(active=0, max_assign=0), evaluated_at=NOW)
    with pytest.raises(AssignmentConfigurationError):
        compute_candidate_score(_cand(active=0, max_assign=-3), evaluated_at=NOW)


def test_09_experience_null_treated_as_0():
    s = compute_candidate_score(_cand(years=None), evaluated_at=NOW)
    assert s.experienceScore == Decimal("0.00")
    assert s.yearsExperience == 0
    assert s.rawYearsExperience is None


def test_10_experience_zero_receives_0():
    s = compute_candidate_score(_cand(years=0), evaluated_at=NOW)
    assert s.experienceScore == Decimal("0.00")


def test_11_experience_above_10_capped_at_10():
    s = compute_candidate_score(_cand(years=25), evaluated_at=NOW)
    assert s.experienceScore == Decimal("10.00")


def test_12_experience_invalid_negative_or_extreme_handled_safely_with_anomaly():
    s_neg = compute_candidate_score(_cand(years=-4), evaluated_at=NOW)
    assert s_neg.experienceScore == Decimal("0.00")
    assert any("NEGATIVE_EXPERIENCE_YEARS" in a for a in s_neg.anomalies)

    s_high = compute_candidate_score(_cand(years=99), evaluated_at=NOW)
    assert s_high.experienceScore == Decimal("10.00")
    assert any("OUT_OF_RANGE_EXPERIENCE_YEARS" in a for a in s_high.anomalies)


def test_13_fairness_never_assigned_receives_10():
    s = compute_candidate_score(_cand(last_assigned=None), evaluated_at=NOW)
    assert s.fairnessScore == Decimal("10.00")
    assert s.hoursSinceLastAssignment is None


def test_14_fairness_just_assigned_receives_0():
    s = compute_candidate_score(_cand(last_assigned=NOW), evaluated_at=NOW)
    assert s.fairnessScore == Decimal("0.00")
    assert s.hoursSinceLastAssignment == Decimal("0.00")


def test_15_fairness_at_and_beyond_168_hours_capped_at_10():
    s_exact = compute_candidate_score(
        _cand(last_assigned=NOW - timedelta(hours=168)), evaluated_at=NOW
    )
    s_more = compute_candidate_score(
        _cand(last_assigned=NOW - timedelta(hours=500)), evaluated_at=NOW
    )
    assert s_exact.fairnessScore == Decimal("10.00")
    assert s_more.fairnessScore == Decimal("10.00")


def test_16_fairness_future_timestamp_clamped_to_0_with_anomaly():
    s = compute_candidate_score(
        _cand(last_assigned=NOW + timedelta(hours=5)), evaluated_at=NOW
    )
    assert s.fairnessScore == Decimal("0.00")
    assert "FUTURE_LAST_ASSIGNED_AT" in s.anomalies


def test_17_and_18_total_score_bounded_0_to_100():
    s_max = compute_candidate_score(
        _cand(match_type="PRIMARY", active=0, max_assign=5, years=15, last_assigned=None),
        evaluated_at=NOW,
    )
    assert s_max.totalScore == Decimal("100.00")

    s_min = compute_candidate_score(
        _cand(match_type="SECONDARY", active=5, max_assign=5, years=0, last_assigned=NOW),
        evaluated_at=NOW,
    )
    assert s_min.totalScore == Decimal("35.00")
    assert Decimal("0.00") <= s_min.totalScore <= Decimal("100.00")


def test_19_and_20_consistent_rounding_and_explanation_matches_total():
    # Active=2/5 -> 18.00; years=8 -> 8.00; 96h/168h -> 5.714285 -> 5.71; total = 81.71
    s = compute_candidate_score(
        _cand(
            match_type="PRIMARY",
            active=2,
            max_assign=5,
            years=8,
            last_assigned=NOW - timedelta(hours=96),
        ),
        evaluated_at=NOW,
    )
    assert s.specialtyScore == Decimal("50.00")
    assert s.workloadScore == Decimal("18.00")
    assert s.experienceScore == Decimal("8.00")
    assert s.fairnessScore == Decimal("5.71")
    assert s.totalScore == Decimal("81.71")
    assert (
        s.specialtyScore + s.workloadScore + s.experienceScore + s.fairnessScore
        == s.totalScore
    )
    assert "81.71/100" in s.explanationText
    assert "2/5" in s.explanationText
    jsonb = s.to_jsonb()
    assert jsonb["scoringVersion"] == SCORING_VERSION
    assert jsonb["totalScore"] == 81.71


def test_21_secondary_beats_primary_when_default_mode_and_total_higher():
    primary_busy = _cand(
        expert_id=1, match_type="PRIMARY", active=4, max_assign=5, years=2, last_assigned=NOW
    )  # 50 + 6 + 2 + 0 = 58.00
    secondary_free = _cand(
        expert_id=2, match_type="SECONDARY", active=0, max_assign=5, years=10, last_assigned=None
    )  # 35 + 30 + 10 + 10 = 85.00

    ranked = rank_candidates_pure(
        [primary_busy, secondary_free],
        evaluated_at=NOW,
        absolute_primary_priority=False,
    )
    assert [r.maChuyenGia for r in ranked] == [2, 1]
    assert ranked[0].score.totalScore == Decimal("85.00")
    assert ranked[1].score.totalScore == Decimal("58.00")


def test_22_absolute_primary_priority_ranks_primary_first_without_changing_score():
    primary_busy = _cand(
        expert_id=1, match_type="PRIMARY", active=4, max_assign=5, years=2, last_assigned=NOW
    )
    secondary_free = _cand(
        expert_id=2, match_type="SECONDARY", active=0, max_assign=5, years=10, last_assigned=None
    )

    ranked = rank_candidates_pure(
        [secondary_free, primary_busy],
        evaluated_at=NOW,
        absolute_primary_priority=True,
    )
    assert [r.maChuyenGia for r in ranked] == [1, 2]
    assert ranked[0].score.totalScore == Decimal("58.00")
    assert ranked[1].score.totalScore == Decimal("85.00")


def test_23_deterministic_tie_breaker_all_levels():
    # Same totalScore = 78.00:
    # A (id=10): PRIMARY (50), active=2/5 (18), years=0 (0), never assigned (10) -> 78.00
    # B (id=11): PRIMARY (50), active=1/5 (24), years=4 (4), just assigned (0)   -> 78.00 (lower workload wins!)
    a = _cand(expert_id=10, match_type="PRIMARY", active=2, years=0, last_assigned=None)
    b = _cand(expert_id=11, match_type="PRIMARY", active=1, years=4, last_assigned=NOW)
    r1 = rank_candidates_pure([a, b], evaluated_at=NOW)
    assert [r.maChuyenGia for r in r1] == [11, 10]

    # Same totalScore AND same workload -> never-assigned beats recently-assigned; older beats newer; lower id beats higher id
    c1 = _cand(expert_id=20, match_type="PRIMARY", active=1, years=5, last_assigned=NOW - timedelta(hours=24))
    c2 = _cand(expert_id=15, match_type="PRIMARY", active=1, years=5, last_assigned=NOW - timedelta(hours=24))
    r2 = rank_candidates_pure([c1, c2], evaluated_at=NOW)
    assert [r.maChuyenGia for r in r2] == [15, 20]


def test_24_ranking_independent_of_query_order():
    cands = [
        _cand(expert_id=30, match_type="PRIMARY", active=2, years=5, last_assigned=NOW - timedelta(hours=48)),
        _cand(expert_id=10, match_type="SECONDARY", active=0, years=9, last_assigned=None),
        _cand(expert_id=20, match_type="PRIMARY", active=2, years=5, last_assigned=NOW - timedelta(hours=48)),
    ]
    r_fwd = [r.maChuyenGia for r in rank_candidates_pure(cands, evaluated_at=NOW)]
    r_rev = [r.maChuyenGia for r in rank_candidates_pure(list(reversed(cands)), evaluated_at=NOW)]
    assert r_fwd == r_rev == [10, 20, 30]


def test_25_empty_candidate_list_returns_empty():
    assert rank_candidates_pure([], evaluated_at=NOW) == []
