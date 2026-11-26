"""GĐ3.2 Automatic Expert Assignment Engine, Eligibility, Specialty Matching & Atomic Load Balancing.

IMPORTANT SAFETY BOUNDARY (GĐ3.2):
- This service is NOT wired into Production submit/resubmit endpoints, startup hooks,
  background tasks, or public APIs. SEC-02 remains OPEN until GĐ3.3 closes open-pool access.
- Transaction ownership is explicit: `assign_best_expert(..., commit=False)` flushes inside
  the caller's transaction (ready for GĐ3.3 atomic queue+assignment+notification commits);
  pass `commit=True` when the engine owns the transaction boundary.
"""
from __future__ import annotations

from datetime import UTC, datetime, timedelta

from psycopg import errors as pg_errors
from sqlalchemy.exc import DBAPIError, IntegrityError, OperationalError
from sqlalchemy.orm import Session

from models import (
    CauHinhPhanCong,
    ChuyenGia,
    KhoaHoc,
    NguoiDung,
    PhanCongKiemDuyet,
    TaiLieu,
)
from repository import assignment_repository
from schemas.assignment import (
    AssignmentConfigurationError,
    AssignmentStatusCode,
    AtomicAssignmentResult,
    CandidateInput,
    EligibilityReasonCode,
    ExcludedCandidate,
    MatchType,
    MatchedSpecialtyInfo,
    RankingPreviewResult,
    TargetType,
    WorkerJobContext,
)
from service.assignment_scoring import compute_candidate_score, rank_candidates_pure

# Maximum retry attempts for candidate fallthrough when top candidate loses eligibility under lock
DEFAULT_MAX_CANDIDATE_ATTEMPTS = 10


def utc_now_naive() -> datetime:
    """Standard UTC naive timestamp matching PostgreSQL schema convention."""
    return datetime.now(UTC).replace(tzinfo=None)


def _select_matched_specialty(
    matched_specialties: list[MatchedSpecialtyInfo],
) -> tuple[MatchType, MatchedSpecialtyInfo]:
    """Deterministically select representative specialty (PRIMARY first, then min maChuyenMon)."""
    primaries = [s for s in matched_specialties if s.laChuyenMonChinh]
    if primaries:
        primaries.sort(key=lambda s: s.maChuyenMon)
        return "PRIMARY", primaries[0]
    secondaries = sorted(matched_specialties, key=lambda s: s.maChuyenMon)
    return "SECONDARY", secondaries[0]


def _validate_target(
    target_type: TargetType,
    target: KhoaHoc | TaiLieu | None,
    *,
    expected_review_round: int | None = None,
) -> tuple[bool, EligibilityReasonCode | None, int | None, int | None]:
    """Validate target eligibility for assignment.

    Returns: (is_valid, reason_code, category_id, current_review_round)
    """
    if target is None:
        return False, EligibilityReasonCode.TARGET_NOT_FOUND, None, None

    if target_type == "MATERIAL":
        assert isinstance(target, TaiLieu)
        if target.maKhoaHoc is not None or target.maBaiHoc is not None:
            return (
                False,
                EligibilityReasonCode.TARGET_NOT_STANDALONE_MATERIAL,
                target.maDanhMuc,
                target.soVongKiemDuyetHienTai,
            )

    if target.trangThaiDuyet != "PENDING":
        return (
            False,
            EligibilityReasonCode.TARGET_NOT_PENDING,
            target.maDanhMuc,
            target.soVongKiemDuyetHienTai,
        )

    if target.maDanhMuc is None:
        return (
            False,
            EligibilityReasonCode.TARGET_CATEGORY_MISSING,
            None,
            target.soVongKiemDuyetHienTai,
        )

    current_round = int(target.soVongKiemDuyetHienTai or 0)
    if current_round < 1:
        return (
            False,
            EligibilityReasonCode.TARGET_ROUND_INVALID,
            int(target.maDanhMuc),
            current_round,
        )

    if expected_review_round is not None and expected_review_round != current_round:
        return (
            False,
            EligibilityReasonCode.TARGET_ROUND_INVALID,
            int(target.maDanhMuc),
            current_round,
        )

    return True, None, int(target.maDanhMuc), current_round


def _evaluate_single_expert_eligibility(
    *,
    user: NguoiDung | None,
    expert: ChuyenGia | None,
    has_any_active_specialty: bool,
    matched_specialties: list[MatchedSpecialtyInfo],
    active_workload: int,
    max_assignments: int,
    is_paused: bool,
    round_exclusion_reasons: set[EligibilityReasonCode],
    target_owner_user_id: int | None,
) -> list[EligibilityReasonCode]:
    """Centralized expert eligibility rule evaluator (11 mandatory rules)."""
    reasons: list[EligibilityReasonCode] = []

    if user is None:
        reasons.append(EligibilityReasonCode.ROLE_NOT_EXPERT)
    else:
        role_name = user.vaiTro.tenVaiTro if user.vaiTro is not None else None
        if role_name != "EXPERT":
            reasons.append(EligibilityReasonCode.ROLE_NOT_EXPERT)
        if (user.trangThai or "").upper() != "ACTIVE":
            reasons.append(EligibilityReasonCode.ACCOUNT_NOT_ACTIVE)
        if bool(user.batBuocDoiMatKhau):
            reasons.append(EligibilityReasonCode.PASSWORD_CHANGE_REQUIRED)
        if target_owner_user_id is not None and user.maNguoiDung == target_owner_user_id:
            reasons.append(EligibilityReasonCode.CONFLICT_OF_INTEREST)

    if expert is None:
        reasons.append(EligibilityReasonCode.EXPERT_PROFILE_NOT_FOUND)
    else:
        if (expert.trangThaiHoSo or "DRAFT") != "VERIFIED":
            reasons.append(EligibilityReasonCode.PROFILE_NOT_VERIFIED)

    if not has_any_active_specialty:
        reasons.append(EligibilityReasonCode.NO_ACTIVE_SPECIALTY)
    elif not matched_specialties:
        reasons.append(EligibilityReasonCode.SPECIALTY_NOT_MATCHED)

    if active_workload >= max_assignments:
        reasons.append(EligibilityReasonCode.WORKLOAD_LIMIT_REACHED)

    if is_paused:
        reasons.append(EligibilityReasonCode.AVAILABILITY_PAUSED)

    for ex_code in sorted(round_exclusion_reasons, key=lambda c: c.value):
        reasons.append(ex_code)

    return reasons


def get_eligible_experts(
    db: Session,
    target_type: TargetType,
    target_id: int,
    *,
    review_round: int | None = None,
    now: datetime | None = None,
    config: CauHinhPhanCong | None = None,
) -> tuple[
    list[CandidateInput],
    list[ExcludedCandidate],
    EligibilityReasonCode | None,
    int | None,
    int | None,
]:
    """Centralized Expert Eligibility Engine (read-only).

    Returns:
      (eligible_inputs, excluded_candidates, target_error_reason, category_id, effective_round)
    """
    eval_now = now or utc_now_naive()
    cfg = config or assignment_repository.get_singleton_config(db)

    target, owner_uid = assignment_repository.get_target(db, target_type, target_id)
    is_valid, target_reason, category_id, current_round = _validate_target(
        target_type, target, expected_review_round=review_round
    )
    if not is_valid or category_id is None or current_round is None:
        return [], [], target_reason, category_id, current_round

    pool = assignment_repository.fetch_candidate_pool_bulk(
        db, category_id=category_id, now=eval_now
    )
    round_exclusions = assignment_repository.get_round_exclusions(
        db, target_type, target_id, current_round
    )

    eligible: list[CandidateInput] = []
    excluded: list[ExcludedCandidate] = []

    for expert in pool["experts"]:
        eid = int(expert.maChuyenGia)
        uid = int(expert.maNguoiDung) if expert.maNguoiDung is not None else -1
        matched_list = pool["matched_by_expert"].get(eid, [])
        active_load = pool["active_workload_by_expert"].get(eid, 0)
        is_paused = eid in pool["paused_expert_ids"]
        ex_reasons = round_exclusions.get(eid, set())

        reasons = _evaluate_single_expert_eligibility(
            user=expert.nguoiDung,
            expert=expert,
            has_any_active_specialty=eid in pool["experts_with_any_active_specialty"],
            matched_specialties=matched_list,
            active_workload=active_load,
            max_assignments=int(cfg.gioiHanTaiToiDa),
            is_paused=is_paused,
            round_exclusion_reasons=ex_reasons,
            target_owner_user_id=owner_uid,
        )
        if reasons:
            excluded.append(
                ExcludedCandidate(
                    maChuyenGia=eid,
                    maNguoiDung=uid,
                    reasons=tuple(reasons),
                )
            )
            continue

        match_type, representative = _select_matched_specialty(matched_list)
        eligible.append(
            CandidateInput(
                maChuyenGia=eid,
                maNguoiDung=uid,
                matchType=match_type,
                matchedSpecialtyId=representative.maChuyenMon,
                matchedSpecialtyName=representative.tenChuyenMon,
                allMatchedSpecialties=tuple(matched_list),
                activeAssignments=active_load,
                maxAssignments=int(cfg.gioiHanTaiToiDa),
                yearsExperience=expert.soNamKinhNghiem,
                lastAssignedAt=pool["last_assigned_by_expert"].get(eid),
            )
        )

    return eligible, excluded, None, category_id, current_round


def rank_candidates(
    db: Session,
    target_type: TargetType,
    target_id: int,
    *,
    review_round: int | None = None,
    now: datetime | None = None,
) -> RankingPreviewResult:
    """Read-only Ranking Preview. Never mutates database state."""
    eval_now = now or utc_now_naive()
    cfg = assignment_repository.get_singleton_config(db)

    eligible, excluded, target_reason, category_id, current_round = get_eligible_experts(
        db,
        target_type,
        target_id,
        review_round=review_round,
        now=eval_now,
        config=cfg,
    )
    if target_reason is not None:
        return RankingPreviewResult(
            targetType=target_type,
            targetId=target_id,
            reviewRound=current_round,
            categoryId=category_id,
            isTargetValid=False,
            targetReason=target_reason,
            rankedCandidates=(),
            excludedCandidates=tuple(excluded),
            noCandidateReason=target_reason,
            evaluatedAt=eval_now,
        )

    ranked = rank_candidates_pure(
        eligible,
        evaluated_at=eval_now,
        absolute_primary_priority=bool(cfg.uuTienTuyetDoiChuyenMonChinh),
    )
    return RankingPreviewResult(
        targetType=target_type,
        targetId=target_id,
        reviewRound=current_round,
        categoryId=category_id,
        isTargetValid=True,
        targetReason=None,
        rankedCandidates=tuple(ranked),
        excludedCandidates=tuple(excluded),
        noCandidateReason=(
            EligibilityReasonCode.NO_ELIGIBLE_EXPERT if not ranked else None
        ),
        evaluatedAt=eval_now,
    )


def _classify_db_error(exc: DBAPIError) -> tuple[str, str | None]:
    """ENG-03: Distinguish PostgreSQL errors by SQLSTATE AND constraint_name."""
    orig = getattr(exc, "orig", None)
    diag = getattr(orig, "diag", None)
    constraint_name = getattr(diag, "constraint_name", None)
    sqlstate = getattr(orig, "sqlstate", None)

    if isinstance(orig, pg_errors.UniqueViolation) or sqlstate == "23505":
        if constraint_name in ("uq_phancong_active_course", "uq_phancong_active_material"):
            return "ACTIVE_ASSIGNMENT_UNIQUE_VIOLATION", constraint_name
        if constraint_name in ("uq_hangdoi_open_course", "uq_hangdoi_open_material"):
            return "OPEN_QUEUE_UNIQUE_VIOLATION", constraint_name
        if constraint_name == "HangDoiPhanCong_khoaChongTrung_key":
            return "QUEUE_IDEMPOTENCY_UNIQUE_VIOLATION", constraint_name
        if constraint_name == "ThongBao_khoaChongTrung_key":
            return "NOTIFICATION_UNIQUE_VIOLATION", constraint_name
        return "OTHER_UNIQUE_VIOLATION", constraint_name
    if isinstance(orig, pg_errors.DeadlockDetected) or sqlstate == "40P01":
        return "DEADLOCK", constraint_name
    if isinstance(orig, pg_errors.SerializationFailure) or sqlstate == "40001":
        return "SERIALIZATION_FAILURE", constraint_name
    if isinstance(orig, pg_errors.LockNotAvailable) or sqlstate == "55P03":
        return "LOCK_NOT_AVAILABLE", constraint_name
    return "OTHER_DB_ERROR", constraint_name


def assign_best_expert(
    db: Session,
    target_type: TargetType,
    target_id: int,
    *,
    expected_review_round: int | None = None,
    now: datetime | None = None,
    worker_context: WorkerJobContext | None = None,
    commit: bool = False,
    max_candidate_attempts: int = DEFAULT_MAX_CANDIDATE_ATTEMPTS,
) -> AtomicAssignmentResult:
    """Atomic, concurrency-safe Automatic Expert Assignment Engine.

    ARCH-05 Lock Ordering enforced:
      (Optional HangDoiPhanCong by GĐ3.3 caller) -> KhoaHoc/TaiLieu -> NguoiDung -> ChuyenGia
      -> YeuCauTamNgungChuyenGia / PhanCongKiemDuyet.

    Transaction boundary:
      - commit=False (default): flushes within caller's transaction so GĐ3.3 can atomically
        commit assignment + queue status + notification together.
      - commit=True: commits on ASSIGNED, rolls back on conflict/error.
    """
    eval_now = now or utc_now_naive()

    try:
        cfg = assignment_repository.get_singleton_config(db)
    except AssignmentConfigurationError as exc:
        return AtomicAssignmentResult(
            status=AssignmentStatusCode.CONFIGURATION_ERROR,
            targetType=target_type,
            targetId=target_id,
            message=str(exc),
        )

    # Step 1 (ARCH-05): Lock target row first (KhoaHoc or TaiLieu)
    try:
        target, owner_uid = assignment_repository.get_target(
            db, target_type, target_id, for_update=True
        )
    except (OperationalError, DBAPIError) as exc:
        kind, _ = _classify_db_error(exc)
        if kind in ("DEADLOCK", "SERIALIZATION_FAILURE", "LOCK_NOT_AVAILABLE"):
            if commit:
                db.rollback()
            return AtomicAssignmentResult(
                status=AssignmentStatusCode.RETRYABLE_CONFLICT,
                targetType=target_type,
                targetId=target_id,
                message=f"Retryable PostgreSQL lock conflict ({kind}) while locking target.",
            )
        raise

    # Step 2: Validate target & review round under lock
    is_valid, target_reason, category_id, current_round = _validate_target(
        target_type, target, expected_review_round=expected_review_round
    )
    if not is_valid or category_id is None or current_round is None:
        if (
            expected_review_round is not None
            and current_round is not None
            and current_round >= 1
            and expected_review_round != current_round
        ):
            return AtomicAssignmentResult(
                status=AssignmentStatusCode.STALE_REVIEW_ROUND,
                targetType=target_type,
                targetId=target_id,
                reviewRound=current_round,
                reasonCode=EligibilityReasonCode.TARGET_ROUND_INVALID,
                message=(
                    f"Stale review round: expected {expected_review_round}, "
                    f"current is {current_round}."
                ),
            )
        return AtomicAssignmentResult(
            status=AssignmentStatusCode.INVALID_TARGET,
            targetType=target_type,
            targetId=target_id,
            reviewRound=current_round,
            reasonCode=target_reason,
            message=f"Target is not valid for assignment: {target_reason.value if target_reason else 'UNKNOWN'}.",
        )

    # Step 3: Idempotency check — active assignment already exists?
    existing_active = assignment_repository.get_active_assignment(
        db, target_type, target_id
    )
    if existing_active is not None:
        return AtomicAssignmentResult(
            status=AssignmentStatusCode.ALREADY_ASSIGNED,
            targetType=target_type,
            targetId=target_id,
            reviewRound=current_round,
            assignmentId=existing_active.maPhanCong,
            assignedExpertId=existing_active.maChuyenGia,
            reasonCode=EligibilityReasonCode.ACTIVE_ASSIGNMENT_EXISTS,
            message="Active assignment already exists for this target.",
        )

    # Step 4: Reassignment limit check (1 initial + soLanTaiPhanCongToiDa reassignments)
    max_attempts_in_round = 1 + int(cfg.soLanTaiPhanCongToiDa)
    round_count = assignment_repository.count_round_assignments(
        db, target_type, target_id, current_round
    )
    if round_count >= max_attempts_in_round:
        return AtomicAssignmentResult(
            status=AssignmentStatusCode.REASSIGNMENT_LIMIT_REACHED,
            targetType=target_type,
            targetId=target_id,
            reviewRound=current_round,
            message=(
                f"Reached maximum assignments in round {current_round} "
                f"({round_count}/{max_attempts_in_round})."
            ),
        )

    # Step 5: Compute initial ranked candidate list
    eligible, excluded, _, _, _ = get_eligible_experts(
        db,
        target_type,
        target_id,
        review_round=current_round,
        now=eval_now,
        config=cfg,
    )
    ranked = rank_candidates_pure(
        eligible,
        evaluated_at=eval_now,
        absolute_primary_priority=bool(cfg.uuTienTuyetDoiChuyenMonChinh),
    )

    if not ranked:
        return AtomicAssignmentResult(
            status=AssignmentStatusCode.NO_ELIGIBLE_EXPERT,
            targetType=target_type,
            targetId=target_id,
            reviewRound=current_round,
            reasonCode=EligibilityReasonCode.NO_ELIGIBLE_EXPERT,
            message="No eligible expert matches the target category and constraints.",
            queueRecommendedStatus="WAITING_ELIGIBLE",
            excludedCount=len(excluded),
        )

    # Step 6: Iterate ranked candidates with ARCH-05 lock ordering & full revalidation
    attempts = 0
    for ranked_cand in ranked[:max_candidate_attempts]:
        attempts += 1
        sp = db.begin_nested()
        try:
            # ARCH-05: Lock NguoiDung BEFORE ChuyenGia
            locked_user, locked_expert = (
                assignment_repository.lock_user_and_expert_in_order(
                    db,
                    user_id=ranked_cand.maNguoiDung,
                    expert_id=ranked_cand.maChuyenGia,
                )
            )

            # Fresh revalidation under lock (zero stale cache reliance)
            has_any_active_spec, fresh_matched = (
                assignment_repository.get_expert_matched_specialties_fresh(
                    db, expert_id=ranked_cand.maChuyenGia, category_id=category_id
                )
            )
            fresh_workload, fresh_last_assigned = (
                assignment_repository.get_expert_workload_and_last_assigned_fresh(
                    db, expert_id=ranked_cand.maChuyenGia
                )
            )
            fresh_paused = assignment_repository.is_expert_paused_fresh(
                db, expert_id=ranked_cand.maChuyenGia, now=eval_now
            )
            fresh_round_exclusions = assignment_repository.get_round_exclusions(
                db, target_type, target_id, current_round
            ).get(ranked_cand.maChuyenGia, set())

            reval_reasons = _evaluate_single_expert_eligibility(
                user=locked_user,
                expert=locked_expert,
                has_any_active_specialty=has_any_active_spec,
                matched_specialties=fresh_matched,
                active_workload=fresh_workload,
                max_assignments=int(cfg.gioiHanTaiToiDa),
                is_paused=fresh_paused,
                round_exclusion_reasons=fresh_round_exclusions,
                target_owner_user_id=owner_uid,
            )
            if reval_reasons:
                sp.rollback()
                continue

            # Recompute exact fresh score snapshot under lock (never persist stale snapshot)
            fresh_match_type, fresh_rep = _select_matched_specialty(fresh_matched)
            fresh_input = CandidateInput(
                maChuyenGia=ranked_cand.maChuyenGia,
                maNguoiDung=ranked_cand.maNguoiDung,
                matchType=fresh_match_type,
                matchedSpecialtyId=fresh_rep.maChuyenMon,
                matchedSpecialtyName=fresh_rep.tenChuyenMon,
                allMatchedSpecialties=tuple(fresh_matched),
                activeAssignments=fresh_workload,
                maxAssignments=int(cfg.gioiHanTaiToiDa),
                yearsExperience=locked_expert.soNamKinhNghiem if locked_expert else None,
                lastAssignedAt=fresh_last_assigned,
            )
            fresh_score = compute_candidate_score(
                fresh_input,
                evaluated_at=eval_now,
                absolute_primary_priority=bool(cfg.uuTienTuyetDoiChuyenMonChinh),
            )

            acceptance_deadline = eval_now + timedelta(hours=int(cfg.hanTiepNhanGio))
            assignment = PhanCongKiemDuyet(
                maKhoaHoc=target_id if target_type == "COURSE" else None,
                maTaiLieu=target_id if target_type == "MATERIAL" else None,
                maChuyenGia=ranked_cand.maChuyenGia,
                maDanhMuc=category_id,
                maChuyenMonKhop=fresh_score.matchedSpecialtyId,
                soVongKiemDuyet=current_round,
                phuongThucPhanCong="AUTO",
                maNguoiPhanCong=None,
                diemPhuHop=fresh_score.totalScore,
                chiTietDiem=fresh_score.to_jsonb(),
                lyDoPhanCong=fresh_score.explanationText,
                trangThai="ASSIGNED",
                ngayPhanCong=eval_now,
                hanTiepNhan=acceptance_deadline,
                hanKiemDuyet=None,
                ngayCapNhat=eval_now,
            )
            db.add(assignment)
            db.flush()
            sp.commit()

            if commit:
                db.commit()

            return AtomicAssignmentResult(
                status=AssignmentStatusCode.ASSIGNED,
                targetType=target_type,
                targetId=target_id,
                reviewRound=current_round,
                assignmentId=int(assignment.maPhanCong),
                assignedExpertId=int(assignment.maChuyenGia),
                assignedUserId=ranked_cand.maNguoiDung,
                score=fresh_score,
                message=fresh_score.explanationText,
                excludedCount=len(excluded),
                attempts=attempts,
                metadata={
                    "workerJobId": worker_context.maCongViec if worker_context else None,
                    "workerClaimToken": (
                        str(worker_context.claimToken) if worker_context else None
                    ),
                },
            )
        except IntegrityError as exc:
            sp.rollback()
            kind, cname = _classify_db_error(exc)
            if kind == "ACTIVE_ASSIGNMENT_UNIQUE_VIOLATION":
                existing = assignment_repository.get_active_assignment(
                    db, target_type, target_id
                )
                if existing is not None:
                    if commit:
                        db.rollback()
                    return AtomicAssignmentResult(
                        status=AssignmentStatusCode.ALREADY_ASSIGNED,
                        targetType=target_type,
                        targetId=target_id,
                        reviewRound=current_round,
                        assignmentId=int(existing.maPhanCong),
                        assignedExpertId=int(existing.maChuyenGia),
                        reasonCode=EligibilityReasonCode.ACTIVE_ASSIGNMENT_EXISTS,
                        message="Concurrent transaction already created an active assignment.",
                        attempts=attempts,
                        metadata={"constraint": cname},
                    )
            if commit:
                db.rollback()
            raise
        except (OperationalError, DBAPIError) as exc:
            sp.rollback()
            kind, _ = _classify_db_error(exc)
            if kind in ("DEADLOCK", "SERIALIZATION_FAILURE", "LOCK_NOT_AVAILABLE"):
                if commit:
                    db.rollback()
                return AtomicAssignmentResult(
                    status=AssignmentStatusCode.RETRYABLE_CONFLICT,
                    targetType=target_type,
                    targetId=target_id,
                    reviewRound=current_round,
                    message=f"Retryable PostgreSQL conflict ({kind}) during assignment.",
                    attempts=attempts,
                )
            if commit:
                db.rollback()
            raise

    # ENG-04: Distinguish truly no eligible candidates vs attempt budget exhausted with remaining candidates
    untested_remaining = max(0, len(ranked) - attempts)
    if untested_remaining > 0:
        return AtomicAssignmentResult(
            status=AssignmentStatusCode.RETRYABLE_CONFLICT,
            targetType=target_type,
            targetId=target_id,
            reviewRound=current_round,
            message=(
                f"Candidate attempt budget ({max_candidate_attempts}) exhausted while "
                f"{untested_remaining} ranked candidates remain untested."
            ),
            excludedCount=len(excluded) + attempts,
            attempts=attempts,
            metadata={"untestedCandidatesRemaining": untested_remaining},
        )

    # All candidates failed revalidation under lock
    return AtomicAssignmentResult(
        status=AssignmentStatusCode.NO_ELIGIBLE_EXPERT,
        targetType=target_type,
        targetId=target_id,
        reviewRound=current_round,
        reasonCode=EligibilityReasonCode.NO_ELIGIBLE_EXPERT,
        message="All initially eligible candidates became ineligible during lock revalidation.",
        queueRecommendedStatus="WAITING_ELIGIBLE",
        excludedCount=len(excluded) + attempts,
        attempts=attempts,
    )


# =====================================================================
# GĐ3.7 ADMIN Manual Exception Assignment (strict ARCH-05 + Eligibility)
# =====================================================================
def assign_expert_manually(
    db: Session,
    *,
    admin_user_id: int,
    target_type: TargetType,
    target_id: int,
    expert_id: int,
    reason: str,
    now: datetime | None = None,
) -> PhanCongKiemDuyet:
    """Exception-only ADMIN manual assignment enforcing 100% of Eligibility & ARCH-05 rules.

    - Locks target FOR UPDATE first, then NguoiDung FOR UPDATE -> ChuyenGia FOR UPDATE.
    - Reuses _validate_target, _evaluate_single_expert_eligibility, and compute_candidate_score.
    - Enforces no duplicate active assignment, round reassignment limit, specialty match,
      load cap, not paused, not previously excluded in round, no conflict of interest.
    - Cancels open PENDING/RETRYING/WAITING_ELIGIBLE queue jobs atomically (no worker race).
    - Sends recipient-scoped idempotent notification to assigned expert.
    """
    from sqlalchemy import select
    from models import HangDoiPhanCong
    from service import notification_service
    from service.workflow_service import WorkflowConflictError, WorkflowNotFoundError

    eval_now = now or utc_now_naive()
    clean_reason = (reason or "").strip()
    if len(clean_reason) < 5:
        raise WorkflowConflictError("Bắt buộc nhập lý do phân công thủ công (tối thiểu 5 ký tự).")

    cfg = assignment_repository.get_singleton_config(db)

    # ARCH-05 Step 1: Lock target first
    target, owner_uid = assignment_repository.get_target(
        db, target_type, target_id, for_update=True
    )
    if target is None:
        raise WorkflowNotFoundError("Không tìm thấy nội dung cần phân công.")

    is_valid, target_reason, category_id, current_round = _validate_target(target_type, target)
    if not is_valid or category_id is None or current_round is None:
        raise WorkflowConflictError(
            f"Nội dung không đủ điều kiện phân công ({target_reason.value if target_reason else 'INVALID'})."
        )

    # Check active assignment uniqueness
    existing_active = assignment_repository.get_active_assignment(db, target_type, target_id)
    if existing_active is not None:
        raise WorkflowConflictError(
            f"Nội dung đã có phân công đang hoạt động (#{existing_active.maPhanCong}). Hãy thu hồi trước nếu cần đổi chuyên gia."
        )

    # Check round reassignment limit
    max_attempts = 1 + int(cfg.soLanTaiPhanCongToiDa)
    round_count = assignment_repository.count_round_assignments(
        db, target_type, target_id, current_round
    )
    if round_count >= max_attempts:
        raise WorkflowConflictError(
            f"Nội dung đã đạt giới hạn tái phân công trong vòng {current_round} ({round_count}/{max_attempts})."
        )

    # Probe expert user_id, then lock NguoiDung -> ChuyenGia (ARCH-05)
    exp_probe = db.get(ChuyenGia, expert_id)
    if exp_probe is None or exp_probe.maNguoiDung is None:
        raise WorkflowNotFoundError("Không tìm thấy hồ sơ chuyên gia được chọn.")

    locked_user, locked_expert = assignment_repository.lock_user_and_expert_in_order(
        db, user_id=int(exp_probe.maNguoiDung), expert_id=expert_id
    )

    has_any_active_spec, fresh_matched = (
        assignment_repository.get_expert_matched_specialties_fresh(
            db, expert_id=expert_id, category_id=category_id
        )
    )
    fresh_workload, fresh_last_assigned = (
        assignment_repository.get_expert_workload_and_last_assigned_fresh(
            db, expert_id=expert_id
        )
    )
    fresh_paused = assignment_repository.is_expert_paused_fresh(
        db, expert_id=expert_id, now=eval_now
    )
    fresh_round_exclusions = assignment_repository.get_round_exclusions(
        db, target_type, target_id, current_round
    ).get(expert_id, set())

    ineligible_reasons = _evaluate_single_expert_eligibility(
        user=locked_user,
        expert=locked_expert,
        has_any_active_specialty=has_any_active_spec,
        matched_specialties=fresh_matched,
        active_workload=fresh_workload,
        max_assignments=int(cfg.gioiHanTaiToiDa),
        is_paused=fresh_paused,
        round_exclusion_reasons=fresh_round_exclusions,
        target_owner_user_id=owner_uid,
    )
    if ineligible_reasons:
        codes = ", ".join(r.value for r in ineligible_reasons)
        raise WorkflowConflictError(
            f"Chuyên gia #{expert_id} không đủ điều kiện kiểm duyệt nội dung này ({codes})."
        )

    fresh_match_type, fresh_rep = _select_matched_specialty(fresh_matched)
    fresh_input = CandidateInput(
        maChuyenGia=expert_id,
        maNguoiDung=int(locked_user.maNguoiDung),
        matchType=fresh_match_type,
        matchedSpecialtyId=fresh_rep.maChuyenMon,
        matchedSpecialtyName=fresh_rep.tenChuyenMon,
        allMatchedSpecialties=tuple(fresh_matched),
        activeAssignments=fresh_workload,
        maxAssignments=int(cfg.gioiHanTaiToiDa),
        yearsExperience=locked_expert.soNamKinhNghiem if locked_expert else None,
        lastAssignedAt=fresh_last_assigned,
    )
    fresh_score = compute_candidate_score(
        fresh_input,
        evaluated_at=eval_now,
        absolute_primary_priority=bool(cfg.uuTienTuyetDoiChuyenMonChinh),
    )

    acceptance_deadline = eval_now + timedelta(hours=int(cfg.hanTiepNhanGio))
    score_json = fresh_score.to_jsonb()
    score_json["manualAssignment"] = {
        "assignedByAdminId": admin_user_id,
        "reason": clean_reason,
        "assignedAt": eval_now.isoformat(),
    }
    assignment = PhanCongKiemDuyet(
        maKhoaHoc=target_id if target_type == "COURSE" else None,
        maTaiLieu=target_id if target_type == "MATERIAL" else None,
        maChuyenGia=expert_id,
        maDanhMuc=category_id,
        maChuyenMonKhop=fresh_score.matchedSpecialtyId,
        soVongKiemDuyet=current_round,
        phuongThucPhanCong="MANUAL",
        maNguoiPhanCong=admin_user_id,
        diemPhuHop=fresh_score.totalScore,
        chiTietDiem=score_json,
        lyDoPhanCong=clean_reason,
        trangThai="ASSIGNED",
        ngayPhanCong=eval_now,
        hanTiepNhan=acceptance_deadline,
        hanKiemDuyet=None,
        ngayCapNhat=eval_now,
    )
    db.add(assignment)
    db.flush()

    # Atomically close open queue jobs for the same target & round to prevent worker race
    col = HangDoiPhanCong.maKhoaHoc if target_type == "COURSE" else HangDoiPhanCong.maTaiLieu
    open_jobs = list(
        db.scalars(
            select(HangDoiPhanCong)
            .where(
                col == target_id,
                HangDoiPhanCong.soVongKiemDuyet == current_round,
                HangDoiPhanCong.trangThai.in_(("PENDING", "RETRYING", "WAITING_ELIGIBLE")),
            )
            .with_for_update()
        ).all()
    )
    for job in open_jobs:
        job.trangThai = "CANCELLED"
        job.lyDoCho = f"MANUAL_ASSIGNED_BY_ADMIN:#{admin_user_id}:PC#{assignment.maPhanCong}"
        job.ngayCapNhat = eval_now

    notification_service.create_notification_idempotent(
        db,
        recipient_user_id=int(locked_user.maNguoiDung),
        notification_type="ASSIGNMENT_NEW",
        title="Bạn được phân công nhiệm vụ kiểm duyệt mới",
        body=f"Quản trị viên đã phân công {target_type} #{target_id} (vòng {current_round}). Vui lòng tiếp nhận trước {acceptance_deadline.strftime('%Y-%m-%d %H:%M')} UTC.",
        event_key=f"ASSIGN_NEW:{assignment.maPhanCong}",
        payload={"maPhanCong": int(assignment.maPhanCong), "loaiDoiTuong": target_type, "maDoiTuong": target_id},
        now=eval_now,
    )
    db.commit()
    db.refresh(assignment)
    return assignment
