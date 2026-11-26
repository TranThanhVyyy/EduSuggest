"""FastAPI routes for GĐ4.6 ADMIN Commerce Management, Exception Refunds, Incidents & PROVIDER Sales."""
from __future__ import annotations

from collections.abc import Callable
from typing import Annotated, ParamSpec, TypeVar

from fastapi import APIRouter, Depends, Header, HTTPException, Query, status
from sqlalchemy.exc import ProgrammingError
from sqlalchemy.orm import Session

from api.dependencies import require_roles
from config.database import get_db
from models import NguoiDung
from schemas.commerce import OrderResponse
from schemas.commerce_admin import (
    AdminCommerceOverviewResponse,
    AdminExceptionRefundCreateRequest,
    AdminOrderListResponse,
    AdminReconciliationActivateRequest,
    AdminRefundExecuteRequest,
    AdminRefundReconcileUnknownRequest,
    AdminRefundVerifyRequest,
    AdminRevenueDashboardResponse,
    AdminTransactionItem,
    ExceptionRefundRecordResponse,
    PaymentIncidentReportRequest,
    PaymentIncidentReportResponse,
    ProviderSaleItemResponse,
    ProviderSalesSummaryResponse,
)
from service import commerce_admin_service
from service.commerce_service import (
    CommerceBadRequestError,
    CommerceConflictError,
    CommerceForbiddenError,
    CommerceNotFoundError,
)

router = APIRouter(tags=["commerce-admin-provider"])

P = ParamSpec("P")
T = TypeVar("T")


def _run(fn: Callable[P, T], *args: P.args, **kwargs: P.kwargs) -> T:
    try:
        return fn(*args, **kwargs)
    except CommerceNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except CommerceBadRequestError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    except CommerceConflictError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc
    except CommerceForbiddenError as exc:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc)) from exc
    except ProgrammingError as exc:
        if "does not exist" in str(exc).lower() or "undefinedtable" in str(exc).lower():
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Chức năng Marketplace chưa được kích hoạt trên cơ sở dữ liệu hiện tại.",
            ) from exc
        raise


# ---------------------------------------------------------------------------
# USER: Report Payment Incident (No general refund button)
# ---------------------------------------------------------------------------
@router.post(
    "/orders/{order_id}/incidents",
    response_model=PaymentIncidentReportResponse,
    status_code=status.HTTP_201_CREATED,
)
def user_report_payment_incident(
    order_id: int,
    payload: PaymentIncidentReportRequest,
    user: Annotated[NguoiDung, Depends(require_roles("USER"))],
    db: Annotated[Session, Depends(get_db)],
) -> PaymentIncidentReportResponse:
    return _run(
        commerce_admin_service.report_payment_incident, db, user, order_id, payload
    )


@router.get(
    "/orders/{order_id}/incidents",
    response_model=list[PaymentIncidentReportResponse],
)
def user_list_order_incidents(
    order_id: int,
    user: Annotated[NguoiDung, Depends(require_roles("USER"))],
    db: Annotated[Session, Depends(get_db)],
) -> list[PaymentIncidentReportResponse]:
    return _run(commerce_admin_service.list_user_order_incidents, db, user, order_id)


# ---------------------------------------------------------------------------
# ADMIN: Commerce Overview, Revenue, Orders, Transactions, Reconciliation, Refunds
# ---------------------------------------------------------------------------
@router.get("/admin/commerce/overview", response_model=AdminCommerceOverviewResponse)
def get_admin_commerce_overview(
    _admin: Annotated[NguoiDung, Depends(require_roles("ADMIN"))],
    db: Annotated[Session, Depends(get_db)],
) -> AdminCommerceOverviewResponse:
    return _run(commerce_admin_service.admin_commerce_overview, db)


@router.get("/admin/commerce/revenue", response_model=AdminRevenueDashboardResponse)
def get_admin_revenue_dashboard(
    _admin: Annotated[NguoiDung, Depends(require_roles("ADMIN"))],
    db: Annotated[Session, Depends(get_db)],
) -> AdminRevenueDashboardResponse:
    return _run(commerce_admin_service.admin_revenue_dashboard, db)


@router.get("/admin/commerce/orders", response_model=AdminOrderListResponse)
def get_admin_orders(
    _admin: Annotated[NguoiDung, Depends(require_roles("ADMIN"))],
    db: Annotated[Session, Depends(get_db)],
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    trang_thai: str | None = Query(default=None),
    q: str | None = Query(default=None),
) -> AdminOrderListResponse:
    return _run(
        commerce_admin_service.admin_list_orders,
        db,
        page=page,
        page_size=page_size,
        status_filter=trang_thai,
        q=q,
    )


@router.get("/admin/commerce/orders/{order_id}", response_model=OrderResponse)
def get_admin_order_detail(
    order_id: int,
    _admin: Annotated[NguoiDung, Depends(require_roles("ADMIN"))],
    db: Annotated[Session, Depends(get_db)],
) -> OrderResponse:
    return _run(commerce_admin_service.admin_get_order_detail, db, order_id)


@router.get("/admin/commerce/transactions", response_model=list[AdminTransactionItem])
def get_admin_transactions(
    _admin: Annotated[NguoiDung, Depends(require_roles("ADMIN"))],
    db: Annotated[Session, Depends(get_db)],
) -> list[AdminTransactionItem]:
    return _run(commerce_admin_service.admin_list_transactions, db, reconciliation_only=False)


@router.get("/admin/commerce/reconciliation", response_model=list[AdminTransactionItem])
def get_admin_reconciliation_queue(
    _admin: Annotated[NguoiDung, Depends(require_roles("ADMIN"))],
    db: Annotated[Session, Depends(get_db)],
) -> list[AdminTransactionItem]:
    return _run(commerce_admin_service.admin_list_transactions, db, reconciliation_only=True)


@router.get("/admin/commerce/incidents", response_model=list[PaymentIncidentReportResponse])
def get_admin_incidents(
    _admin: Annotated[NguoiDung, Depends(require_roles("ADMIN"))],
    db: Annotated[Session, Depends(get_db)],
) -> list[PaymentIncidentReportResponse]:
    return _run(commerce_admin_service.admin_list_incidents, db)


@router.post(
    "/admin/commerce/reconciliation/{payment_id}/activate",
    response_model=OrderResponse,
)
def resolve_reconciliation_activate(
    payment_id: int,
    payload: AdminReconciliationActivateRequest,
    admin: Annotated[NguoiDung, Depends(require_roles("ADMIN"))],
    db: Annotated[Session, Depends(get_db)],
) -> OrderResponse:
    return _run(
        commerce_admin_service.admin_resolve_reconciliation_activate,
        db,
        admin,
        payment_id,
        payload,
    )


@router.post(
    "/admin/commerce/refunds",
    response_model=ExceptionRefundRecordResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_admin_exception_refund(
    payload: AdminExceptionRefundCreateRequest,
    admin: Annotated[NguoiDung, Depends(require_roles("ADMIN"))],
    db: Annotated[Session, Depends(get_db)],
    idempotency_key: Annotated[str | None, Header(alias="Idempotency-Key")] = None,
) -> ExceptionRefundRecordResponse:
    return _run(
        commerce_admin_service.admin_create_exception_refund,
        db,
        admin,
        payload,
        idempotency_key=idempotency_key or "",
    )


@router.post(
    "/admin/commerce/refunds/{payment_id}/verify",
    response_model=ExceptionRefundRecordResponse,
)
def verify_admin_exception_refund(
    payment_id: int,
    payload: AdminRefundVerifyRequest,
    admin: Annotated[NguoiDung, Depends(require_roles("ADMIN"))],
    db: Annotated[Session, Depends(get_db)],
) -> ExceptionRefundRecordResponse:
    return _run(
        commerce_admin_service.admin_verify_exception_refund,
        db,
        admin,
        payment_id,
        payload,
    )


@router.post(
    "/admin/commerce/refunds/{payment_id}/execute",
    response_model=ExceptionRefundRecordResponse,
)
def execute_admin_exception_refund(
    payment_id: int,
    payload: AdminRefundExecuteRequest,
    admin: Annotated[NguoiDung, Depends(require_roles("ADMIN"))],
    db: Annotated[Session, Depends(get_db)],
) -> ExceptionRefundRecordResponse:
    return _run(
        commerce_admin_service.admin_execute_exception_refund,
        db,
        admin,
        payment_id,
        payload,
    )


@router.post(
    "/admin/commerce/refunds/{payment_id}/reconcile-unknown",
    response_model=ExceptionRefundRecordResponse,
)
def reconcile_unknown_admin_refund(
    payment_id: int,
    payload: AdminRefundReconcileUnknownRequest,
    admin: Annotated[NguoiDung, Depends(require_roles("ADMIN"))],
    db: Annotated[Session, Depends(get_db)],
) -> ExceptionRefundRecordResponse:
    return _run(
        commerce_admin_service.admin_reconcile_unknown_refund,
        db,
        admin,
        payment_id,
        payload,
    )


# ---------------------------------------------------------------------------
# PROVIDER: Owner-Scoped Sales Dashboard & History
# ---------------------------------------------------------------------------
@router.get("/provider/sales/summary", response_model=ProviderSalesSummaryResponse)
def get_provider_sales_summary(
    provider: Annotated[NguoiDung, Depends(require_roles("PROVIDER"))],
    db: Annotated[Session, Depends(get_db)],
) -> ProviderSalesSummaryResponse:
    return _run(commerce_admin_service.provider_sales_summary, db, provider)


@router.get("/provider/sales/items", response_model=list[ProviderSaleItemResponse])
def get_provider_sales_items(
    provider: Annotated[NguoiDung, Depends(require_roles("PROVIDER"))],
    db: Annotated[Session, Depends(get_db)],
) -> list[ProviderSaleItemResponse]:
    return _run(commerce_admin_service.provider_sales_items, db, provider)
