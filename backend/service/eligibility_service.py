"""ACC-15 serialization and current-eligibility checks for expert write paths."""
from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy import select, text
from sqlalchemy.orm import Session

from models import ChuyenGia, ChuyenGiaChuyenMon
from repository import assignment_repository
from schemas.assignment import TargetType

_ACC15_LOCK_NAMESPACE = 83415


def lock_expert_eligibility(db: Session, expert_id: int) -> None:
    db.execute(
        text("SELECT pg_advisory_xact_lock(:namespace, :expert_id)"),
        {"namespace": _ACC15_LOCK_NAMESPACE, "expert_id": int(expert_id)},
    )


def lock_experts_eligibility(db: Session, expert_ids: list[int]) -> None:
    """Acquire ACC-15 locks in a deterministic order to avoid lock inversion."""
    for expert_id in sorted({int(value) for value in expert_ids}):
        lock_expert_eligibility(db, expert_id)


def lock_specialty_experts(db: Session, specialty_id: int) -> list[int]:
    expert_ids = sorted(
        {
            int(value)
            for value in db.scalars(
                select(ChuyenGiaChuyenMon.maChuyenGia).where(
                    ChuyenGiaChuyenMon.maChuyenMon == specialty_id
                )
            ).all()
        }
    )
    lock_experts_eligibility(db, expert_ids)
    return expert_ids


def current_assignment_ineligibility_reasons(
    db: Session,
    *,
    expert_id: int,
    target_type: TargetType,
    target_id: int,
    category_id: int,
    now: datetime | None = None,
) -> list[str]:
    """Recheck mutable gates while preserving an already-valid active assignment.

    Active workload includes the current assignment, hence only values above the
    configured maximum invalidate an existing assignment.
    """
    evaluated_at = now or datetime.now(UTC).replace(tzinfo=None)
    reasons: list[str] = []
    target, owner_user_id = assignment_repository.get_target(
        db, target_type, target_id
    )
    if target is None:
        return ["TARGET_NOT_FOUND"]
    has_any_active, matched = assignment_repository.get_expert_matched_specialties_fresh(
        db, expert_id=expert_id, category_id=category_id
    )
    if not has_any_active:
        reasons.append("NO_ACTIVE_SPECIALTY")
    elif not matched:
        reasons.append("SPECIALTY_NOT_MATCHED")
    if assignment_repository.is_expert_paused_fresh(
        db, expert_id=expert_id, now=evaluated_at
    ):
        reasons.append("AVAILABILITY_PAUSED")
    workload, _ = assignment_repository.get_expert_workload_and_last_assigned_fresh(
        db, expert_id=expert_id
    )
    config = assignment_repository.get_singleton_config(db)
    if int(workload) > int(config.gioiHanTaiToiDa):
        reasons.append("WORKLOAD_LIMIT_EXCEEDED")
    expert_user_id = db.scalar(
        select(ChuyenGia.maNguoiDung).where(ChuyenGia.maChuyenGia == expert_id)
    )
    if owner_user_id is not None and expert_user_id == owner_user_id:
        reasons.append("CONFLICT_OF_INTEREST")
    return reasons
