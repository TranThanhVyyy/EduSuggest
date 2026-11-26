"""Repository layer for GĐ3.2 Automatic Expert Assignment Engine.

Designed for:
- Zero N+1 queries during candidate pool retrieval (constant query count).
- Strict ARCH-05 lock ordering:
  HangDoiPhanCong -> KhoaHoc/TaiLieu -> NguoiDung -> ChuyenGia -> YeuCauTamNgungChuyenGia -> PhanCongKiemDuyet
- Fresh database revalidation under row locks (populate_existing=True).
"""
from __future__ import annotations

from datetime import datetime

from sqlalchemy import func, select
from sqlalchemy.orm import Session, joinedload

from models import (
    CauHinhPhanCong,
    ChuyenGia,
    ChuyenGiaChuyenMon,
    ChuyenMon,
    ChuyenMonDanhMuc,
    KhoaHoc,
    NguoiDung,
    NhaCungCapKhoaHoc,
    PhanCongKiemDuyet,
    TaiLieu,
    YeuCauTamNgungChuyenGia,
)
from schemas.assignment import (
    AssignmentConfigurationError,
    EligibilityReasonCode,
    MatchedSpecialtyInfo,
    TargetType,
)

ACTIVE_ASSIGNMENT_STATUSES = ("ASSIGNED", "ACCEPTED", "IN_PROGRESS")
EXCLUDED_ROUND_STATUSES = ("DECLINED", "EXPIRED")


def get_singleton_config(db: Session) -> CauHinhPhanCong:
    """Load singleton CauHinhPhanCong (maCauHinh = 1). Fail-closed if missing or invalid."""
    cfg = db.scalar(
        select(CauHinhPhanCong)
        .where(CauHinhPhanCong.maCauHinh == 1)
        .execution_options(populate_existing=True)
    )
    if cfg is None:
        raise AssignmentConfigurationError(
            "CauHinhPhanCong singleton (maCauHinh=1) is missing."
        )
    if cfg.gioiHanTaiToiDa is None or cfg.gioiHanTaiToiDa < 1:
        raise AssignmentConfigurationError(
            f"Invalid CauHinhPhanCong.gioiHanTaiToiDa={cfg.gioiHanTaiToiDa}."
        )
    if cfg.hanTiepNhanGio is None or cfg.hanTiepNhanGio < 1:
        raise AssignmentConfigurationError(
            f"Invalid CauHinhPhanCong.hanTiepNhanGio={cfg.hanTiepNhanGio}."
        )
    if cfg.soLanTaiPhanCongToiDa is None or cfg.soLanTaiPhanCongToiDa < 1:
        raise AssignmentConfigurationError(
            f"Invalid CauHinhPhanCong.soLanTaiPhanCongToiDa={cfg.soLanTaiPhanCongToiDa}."
        )
    return cfg


def get_target(
    db: Session,
    target_type: TargetType,
    target_id: int,
    *,
    for_update: bool = False,
) -> tuple[KhoaHoc | TaiLieu | None, int | None]:
    """Load target (KhoaHoc or TaiLieu) and its owner user_id (if determinable).

    When for_update=True, acquires FOR UPDATE on the target table (Step 2 of ARCH-05).
    """
    if target_type == "COURSE":
        stmt = select(KhoaHoc).where(KhoaHoc.maKhoaHoc == target_id)
        if for_update:
            stmt = stmt.with_for_update(of=KhoaHoc)
        target = db.scalars(stmt.execution_options(populate_existing=True)).first()
        if target is None:
            return None, None
        owner_uid = None
        if target.maNhaCungCap is not None:
            owner_uid = db.scalar(
                select(NhaCungCapKhoaHoc.maNguoiDung).where(
                    NhaCungCapKhoaHoc.maNhaCungCap == target.maNhaCungCap
                )
            )
        return target, owner_uid

    if target_type == "MATERIAL":
        stmt = select(TaiLieu).where(TaiLieu.maTaiLieu == target_id)
        if for_update:
            stmt = stmt.with_for_update(of=TaiLieu)
        target = db.scalars(stmt.execution_options(populate_existing=True)).first()
        if target is None:
            return None, None
        owner_uid = None
        if target.maNhaCungCap is not None:
            owner_uid = db.scalar(
                select(NhaCungCapKhoaHoc.maNguoiDung).where(
                    NhaCungCapKhoaHoc.maNhaCungCap == target.maNhaCungCap
                )
            )
        return target, owner_uid

    return None, None


def get_active_assignment(
    db: Session, target_type: TargetType, target_id: int
) -> PhanCongKiemDuyet | None:
    col = (
        PhanCongKiemDuyet.maKhoaHoc
        if target_type == "COURSE"
        else PhanCongKiemDuyet.maTaiLieu
    )
    return db.scalars(
        select(PhanCongKiemDuyet)
        .where(
            col == target_id,
            PhanCongKiemDuyet.trangThai.in_(ACTIVE_ASSIGNMENT_STATUSES),
        )
        .execution_options(populate_existing=True)
    ).first()


def count_round_assignments(
    db: Session, target_type: TargetType, target_id: int, review_round: int
) -> int:
    col = (
        PhanCongKiemDuyet.maKhoaHoc
        if target_type == "COURSE"
        else PhanCongKiemDuyet.maTaiLieu
    )
    cnt = db.scalar(
        select(func.count(PhanCongKiemDuyet.maPhanCong)).where(
            col == target_id,
            PhanCongKiemDuyet.soVongKiemDuyet == review_round,
        )
    )
    return int(cnt or 0)


def get_round_exclusions(
    db: Session, target_type: TargetType, target_id: int, review_round: int
) -> dict[int, set[EligibilityReasonCode]]:
    """Return experts excluded in the current review round due to DECLINED or EXPIRED."""
    col = (
        PhanCongKiemDuyet.maKhoaHoc
        if target_type == "COURSE"
        else PhanCongKiemDuyet.maTaiLieu
    )
    rows = db.execute(
        select(PhanCongKiemDuyet.maChuyenGia, PhanCongKiemDuyet.trangThai).where(
            col == target_id,
            PhanCongKiemDuyet.soVongKiemDuyet == review_round,
            PhanCongKiemDuyet.trangThai.in_(EXCLUDED_ROUND_STATUSES),
        )
    ).all()
    excluded: dict[int, set[EligibilityReasonCode]] = {}
    for expert_id, status in rows:
        code = (
            EligibilityReasonCode.DECLINED_IN_CURRENT_ROUND
            if status == "DECLINED"
            else EligibilityReasonCode.EXPIRED_IN_CURRENT_ROUND
        )
        excluded.setdefault(int(expert_id), set()).add(code)
    return excluded


def fetch_candidate_pool_bulk(
    db: Session,
    *,
    category_id: int,
    now: datetime,
) -> dict:
    """Fetch all data needed for eligibility & scoring in a constant number of queries (5 queries)."""
    # Query 1: All ChuyenGia profiles with NguoiDung + VaiTro
    experts = list(
        db.scalars(
            select(ChuyenGia)
            .options(joinedload(ChuyenGia.nguoiDung).joinedload(NguoiDung.vaiTro))
            .order_by(ChuyenGia.maChuyenGia.asc())
            .execution_options(populate_existing=True)
        )
        .unique()
        .all()
    )

    # Query 2: All ACTIVE specialties linked to experts (to distinguish NO_ACTIVE_SPECIALTY vs SPECIALTY_NOT_MATCHED)
    active_spec_rows = db.execute(
        select(
            ChuyenGiaChuyenMon.maChuyenGia,
            ChuyenMon.maChuyenMon,
            ChuyenMon.tenChuyenMon,
            ChuyenGiaChuyenMon.laChuyenMonChinh,
        )
        .join(ChuyenMon, ChuyenMon.maChuyenMon == ChuyenGiaChuyenMon.maChuyenMon)
        .where(ChuyenMon.trangThai == "ACTIVE")
        .order_by(ChuyenGiaChuyenMon.maChuyenGia.asc(), ChuyenMon.maChuyenMon.asc())
    ).all()

    experts_with_any_active_specialty: set[int] = set()
    for eid, _, _, _ in active_spec_rows:
        experts_with_any_active_specialty.add(int(eid))

    # Query 3: Active specialties mapped to target category_id
    matched_rows = db.execute(
        select(
            ChuyenGiaChuyenMon.maChuyenGia,
            ChuyenMon.maChuyenMon,
            ChuyenMon.tenChuyenMon,
            ChuyenGiaChuyenMon.laChuyenMonChinh,
        )
        .join(ChuyenMon, ChuyenMon.maChuyenMon == ChuyenGiaChuyenMon.maChuyenMon)
        .join(
            ChuyenMonDanhMuc,
            ChuyenMonDanhMuc.maChuyenMon == ChuyenMon.maChuyenMon,
        )
        .where(
            ChuyenMon.trangThai == "ACTIVE",
            ChuyenMonDanhMuc.maDanhMuc == category_id,
        )
        .order_by(ChuyenGiaChuyenMon.maChuyenGia.asc(), ChuyenMon.maChuyenMon.asc())
    ).all()

    matched_by_expert: dict[int, list[MatchedSpecialtyInfo]] = {}
    for eid, sid, sname, is_primary in matched_rows:
        matched_by_expert.setdefault(int(eid), []).append(
            MatchedSpecialtyInfo(
                maChuyenMon=int(sid),
                tenChuyenMon=str(sname),
                laChuyenMonChinh=bool(is_primary),
            )
        )

    # Query 4: Aggregate active workload & lastAssignedAt per expert in ONE query
    agg_rows = db.execute(
        select(
            PhanCongKiemDuyet.maChuyenGia,
            func.count(PhanCongKiemDuyet.maPhanCong)
            .filter(PhanCongKiemDuyet.trangThai.in_(ACTIVE_ASSIGNMENT_STATUSES))
            .label("active_count"),
            func.max(PhanCongKiemDuyet.ngayPhanCong).label("last_assigned_at"),
        ).group_by(PhanCongKiemDuyet.maChuyenGia)
    ).all()

    active_workload_by_expert: dict[int, int] = {}
    last_assigned_by_expert: dict[int, datetime | None] = {}
    for eid, active_cnt, last_dt in agg_rows:
        active_workload_by_expert[int(eid)] = int(active_cnt or 0)
        last_assigned_by_expert[int(eid)] = last_dt

    # Query 5: Currently paused experts via YeuCauTamNgungChuyenGia [ngayBatDau, ngayKetThuc)
    paused_expert_ids = set(
        int(eid)
        for eid in db.scalars(
            select(YeuCauTamNgungChuyenGia.maChuyenGia).where(
                YeuCauTamNgungChuyenGia.trangThai == "APPROVED",
                YeuCauTamNgungChuyenGia.ngayBatDau <= now,
                YeuCauTamNgungChuyenGia.ngayKetThuc > now,
            )
        ).all()
    )

    return {
        "experts": experts,
        "experts_with_any_active_specialty": experts_with_any_active_specialty,
        "matched_by_expert": matched_by_expert,
        "active_workload_by_expert": active_workload_by_expert,
        "last_assigned_by_expert": last_assigned_by_expert,
        "paused_expert_ids": paused_expert_ids,
    }


def lock_user_and_expert_in_order(
    db: Session, *, user_id: int, expert_id: int
) -> tuple[NguoiDung | None, ChuyenGia | None]:
    """ARCH-05 lock ordering: ALWAYS lock NguoiDung BEFORE ChuyenGia."""
    user = db.scalars(
        select(NguoiDung)
        .options(joinedload(NguoiDung.vaiTro))
        .where(NguoiDung.maNguoiDung == user_id)
        .with_for_update(of=NguoiDung)
        .execution_options(populate_existing=True)
    ).unique().first()

    expert = db.scalars(
        select(ChuyenGia)
        .where(ChuyenGia.maChuyenGia == expert_id)
        .with_for_update(of=ChuyenGia)
        .execution_options(populate_existing=True)
    ).first()

    return user, expert


def get_expert_matched_specialties_fresh(
    db: Session, *, expert_id: int, category_id: int
) -> tuple[bool, list[MatchedSpecialtyInfo]]:
    """Fresh DB lookup of expert's active specialties & category matches under lock."""
    any_active = db.scalar(
        select(func.count(ChuyenGiaChuyenMon.maChuyenMon))
        .join(ChuyenMon, ChuyenMon.maChuyenMon == ChuyenGiaChuyenMon.maChuyenMon)
        .where(
            ChuyenGiaChuyenMon.maChuyenGia == expert_id,
            ChuyenMon.trangThai == "ACTIVE",
        )
    )
    matched_rows = db.execute(
        select(
            ChuyenMon.maChuyenMon,
            ChuyenMon.tenChuyenMon,
            ChuyenGiaChuyenMon.laChuyenMonChinh,
        )
        .join(ChuyenMon, ChuyenMon.maChuyenMon == ChuyenGiaChuyenMon.maChuyenMon)
        .join(
            ChuyenMonDanhMuc,
            ChuyenMonDanhMuc.maChuyenMon == ChuyenMon.maChuyenMon,
        )
        .where(
            ChuyenGiaChuyenMon.maChuyenGia == expert_id,
            ChuyenMon.trangThai == "ACTIVE",
            ChuyenMonDanhMuc.maDanhMuc == category_id,
        )
        .order_by(ChuyenMon.maChuyenMon.asc())
    ).all()
    matched = [
        MatchedSpecialtyInfo(
            maChuyenMon=int(sid),
            tenChuyenMon=str(sname),
            laChuyenMonChinh=bool(is_primary),
        )
        for sid, sname, is_primary in matched_rows
    ]
    return bool(any_active and int(any_active) > 0), matched


def get_expert_workload_and_last_assigned_fresh(
    db: Session, *, expert_id: int
) -> tuple[int, datetime | None]:
    row = db.execute(
        select(
            func.count(PhanCongKiemDuyet.maPhanCong)
            .filter(PhanCongKiemDuyet.trangThai.in_(ACTIVE_ASSIGNMENT_STATUSES))
            .label("active_count"),
            func.max(PhanCongKiemDuyet.ngayPhanCong).label("last_assigned_at"),
        ).where(PhanCongKiemDuyet.maChuyenGia == expert_id)
    ).one()
    return int(row.active_count or 0), row.last_assigned_at


def is_expert_paused_fresh(
    db: Session, *, expert_id: int, now: datetime
) -> bool:
    """Check half-open interval [ngayBatDau, ngayKetThuc) for APPROVED availability pauses."""
    cnt = db.scalar(
        select(func.count(YeuCauTamNgungChuyenGia.maYeuCau)).where(
            YeuCauTamNgungChuyenGia.maChuyenGia == expert_id,
            YeuCauTamNgungChuyenGia.trangThai == "APPROVED",
            YeuCauTamNgungChuyenGia.ngayBatDau <= now,
            YeuCauTamNgungChuyenGia.ngayKetThuc > now,
        )
    )
    return bool(cnt and int(cnt) > 0)
