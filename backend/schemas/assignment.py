"""Internal schemas, enums, and result contracts for GĐ3.2 Automatic Expert Assignment Engine.

These types are strictly internal to the Backend service layer (NOT exposed on public APIs).
"""
from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import datetime
from decimal import Decimal
from enum import Enum
from typing import Any, Literal

TargetType = Literal["COURSE", "MATERIAL"]
MatchType = Literal["PRIMARY", "SECONDARY"]


class EligibilityReasonCode(str, Enum):
    ROLE_NOT_EXPERT = "ROLE_NOT_EXPERT"
    ACCOUNT_NOT_ACTIVE = "ACCOUNT_NOT_ACTIVE"
    PASSWORD_CHANGE_REQUIRED = "PASSWORD_CHANGE_REQUIRED"
    EXPERT_PROFILE_NOT_FOUND = "EXPERT_PROFILE_NOT_FOUND"
    PROFILE_NOT_VERIFIED = "PROFILE_NOT_VERIFIED"
    NO_ACTIVE_SPECIALTY = "NO_ACTIVE_SPECIALTY"
    SPECIALTY_NOT_MATCHED = "SPECIALTY_NOT_MATCHED"
    WORKLOAD_LIMIT_REACHED = "WORKLOAD_LIMIT_REACHED"
    AVAILABILITY_PAUSED = "AVAILABILITY_PAUSED"
    DECLINED_IN_CURRENT_ROUND = "DECLINED_IN_CURRENT_ROUND"
    EXPIRED_IN_CURRENT_ROUND = "EXPIRED_IN_CURRENT_ROUND"
    CONFLICT_OF_INTEREST = "CONFLICT_OF_INTEREST"
    TARGET_CATEGORY_MISSING = "TARGET_CATEGORY_MISSING"
    TARGET_NOT_PENDING = "TARGET_NOT_PENDING"
    TARGET_ROUND_INVALID = "TARGET_ROUND_INVALID"
    TARGET_NOT_FOUND = "TARGET_NOT_FOUND"
    TARGET_NOT_STANDALONE_MATERIAL = "TARGET_NOT_STANDALONE_MATERIAL"
    ACTIVE_ASSIGNMENT_EXISTS = "ACTIVE_ASSIGNMENT_EXISTS"
    NO_ELIGIBLE_EXPERT = "NO_ELIGIBLE_EXPERT"


class AssignmentStatusCode(str, Enum):
    ASSIGNED = "ASSIGNED"
    NO_ELIGIBLE_EXPERT = "NO_ELIGIBLE_EXPERT"
    ALREADY_ASSIGNED = "ALREADY_ASSIGNED"
    STALE_REVIEW_ROUND = "STALE_REVIEW_ROUND"
    INVALID_TARGET = "INVALID_TARGET"
    REASSIGNMENT_LIMIT_REACHED = "REASSIGNMENT_LIMIT_REACHED"
    RETRYABLE_CONFLICT = "RETRYABLE_CONFLICT"
    CONFIGURATION_ERROR = "CONFIGURATION_ERROR"


class AssignmentConfigurationError(RuntimeError):
    """Raised when CauHinhPhanCong singleton is missing or invalid (fail-closed)."""


class AssignmentDatabaseGuardError(RuntimeError):
    """Raised when a test or guard detects an unintended database connection."""


@dataclass(frozen=True)
class WorkerJobContext:
    """ARCH-06 worker integration contract prepared for GĐ3.3 Durable Queue Worker."""

    maCongViec: int
    claimToken: uuid.UUID
    leaseGeneration: int
    maWorker: str
    loaiSuKien: str = "SUBMIT"
    maPhanCongNguon: int | None = None


@dataclass(frozen=True)
class MatchedSpecialtyInfo:
    maChuyenMon: int
    tenChuyenMon: str
    laChuyenMonChinh: bool


@dataclass(frozen=True)
class CandidateInput:
    maChuyenGia: int
    maNguoiDung: int
    matchType: MatchType
    matchedSpecialtyId: int
    matchedSpecialtyName: str
    allMatchedSpecialties: tuple[MatchedSpecialtyInfo, ...]
    activeAssignments: int
    maxAssignments: int
    yearsExperience: int | None
    lastAssignedAt: datetime | None


@dataclass(frozen=True)
class ScoreBreakdown:
    scoringVersion: str
    specialtyScore: Decimal
    workloadScore: Decimal
    experienceScore: Decimal
    fairnessScore: Decimal
    totalScore: Decimal
    matchType: MatchType
    matchedSpecialtyId: int
    matchedSpecialtyName: str
    allMatchedSpecialtyIds: tuple[int, ...]
    activeAssignments: int
    maxAssignments: int
    yearsExperience: int
    rawYearsExperience: int | None
    lastAssignedAt: datetime | None
    hoursSinceLastAssignment: Decimal | None
    absolutePrimaryPriority: bool
    evaluatedAt: datetime
    anomalies: tuple[str, ...] = ()
    explanationText: str = ""

    def to_jsonb(self) -> dict[str, Any]:
        """Serialize score breakdown to deterministic JSONB-safe dict."""
        return {
            "scoringVersion": self.scoringVersion,
            "specialtyScore": float(self.specialtyScore),
            "workloadScore": float(self.workloadScore),
            "experienceScore": float(self.experienceScore),
            "fairnessScore": float(self.fairnessScore),
            "totalScore": float(self.totalScore),
            "matchType": self.matchType,
            "matchedSpecialtyId": self.matchedSpecialtyId,
            "matchedSpecialtyName": self.matchedSpecialtyName,
            "allMatchedSpecialtyIds": list(self.allMatchedSpecialtyIds),
            "activeAssignments": self.activeAssignments,
            "maxAssignments": self.maxAssignments,
            "yearsExperience": self.yearsExperience,
            "rawYearsExperience": self.rawYearsExperience,
            "lastAssignedAt": (
                self.lastAssignedAt.isoformat() if self.lastAssignedAt else None
            ),
            "hoursSinceLastAssignment": (
                float(self.hoursSinceLastAssignment)
                if self.hoursSinceLastAssignment is not None
                else None
            ),
            "absolutePrimaryPriority": self.absolutePrimaryPriority,
            "evaluatedAt": self.evaluatedAt.isoformat(),
            "anomalies": list(self.anomalies),
        }


@dataclass(frozen=True)
class RankedCandidate:
    rank: int
    maChuyenGia: int
    maNguoiDung: int
    score: ScoreBreakdown


@dataclass(frozen=True)
class ExcludedCandidate:
    maChuyenGia: int
    maNguoiDung: int
    reasons: tuple[EligibilityReasonCode, ...]


@dataclass(frozen=True)
class RankingPreviewResult:
    targetType: TargetType
    targetId: int
    reviewRound: int | None
    categoryId: int | None
    isTargetValid: bool
    targetReason: EligibilityReasonCode | None
    rankedCandidates: tuple[RankedCandidate, ...] = ()
    excludedCandidates: tuple[ExcludedCandidate, ...] = ()
    noCandidateReason: EligibilityReasonCode | None = None
    evaluatedAt: datetime | None = None


@dataclass(frozen=True)
class AtomicAssignmentResult:
    status: AssignmentStatusCode
    targetType: TargetType
    targetId: int
    reviewRound: int | None = None
    assignmentId: int | None = None
    assignedExpertId: int | None = None
    assignedUserId: int | None = None
    score: ScoreBreakdown | None = None
    reasonCode: EligibilityReasonCode | None = None
    message: str = ""
    queueRecommendedStatus: str | None = None
    excludedCount: int = 0
    attempts: int = 0
    metadata: dict[str, Any] = field(default_factory=dict)
