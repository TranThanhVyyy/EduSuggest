"""FastAPI routes for GĐ4.2 Wishlist, Shopping Cart, and Buy Now validation."""
from __future__ import annotations

from collections.abc import Callable
from typing import Annotated, ParamSpec, TypeVar

from fastapi import APIRouter, Depends, Header, HTTPException, Query, Request, Response, status
from sqlalchemy.exc import ProgrammingError
from sqlalchemy.orm import Session

from api.dependencies import require_roles
from config.database import get_db
from models import NguoiDung
from schemas.commerce import (
    BuyNowValidationResponse,
    CartClearResponse,
    CartCountResponse,
    CartItemAddRequest,
    CartResponse,
    CommerceCapabilitiesResponse,
    MockPaymentCallbackRequest,
    MockPaymentSessionDetailResponse,
    MockPaymentSimulateRequest,
    MoveWishlistToCartResponse,
    OrderCancelRequest,
    OrderCreateRequest,
    OrderListResponse,
    OrderPreviewRequest,
    OrderPreviewResponse,
    OrderResponse,
    OrderStatusResponse,
    PaymentCallbackResponse,
    PaymentInitiateRequest,
    PaymentInitiateResponse,
    VNPayIpnResponse,
    VNPayReturnVerifyResponse,
    WishlistCountResponse,
    WishlistListResponse,
    WishlistStatusResponse,
)
from service import commerce_service, order_payment_service
from service.commerce_service import (
    CommerceBadRequestError,
    CommerceConflictError,
    CommerceForbiddenError,
    CommerceNotFoundError,
)

router = APIRouter(tags=["commerce"])

P = ParamSpec("P")
T = TypeVar("T")


def _run_commerce(fn: Callable[P, T], *args: P.args, **kwargs: P.kwargs) -> T:
    try:
        return fn(*args, **kwargs)
    except CommerceNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)
        ) from exc
    except CommerceBadRequestError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)
        ) from exc
    except CommerceConflictError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT, detail=str(exc)
        ) from exc
    except CommerceForbiddenError as exc:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail=str(exc)
        ) from exc
    except ProgrammingError as exc:
        if "does not exist" in str(exc).lower() or "undefinedtable" in str(exc).lower():
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Chức năng Marketplace chưa được kích hoạt trên cơ sở dữ liệu hiện tại.",
            ) from exc
        raise


# ---------------------------------------------------------------------------
# Wishlist Endpoints (USER only)
# ---------------------------------------------------------------------------
@router.get("/wishlist", response_model=WishlistListResponse)
def get_my_wishlist(
    user: Annotated[NguoiDung, Depends(require_roles("USER"))],
    db: Annotated[Session, Depends(get_db)],
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
) -> WishlistListResponse:
    return _run_commerce(
        commerce_service.list_wishlist, db, user, page=page, page_size=page_size
    )


@router.get("/wishlist/count", response_model=WishlistCountResponse)
def get_my_wishlist_count(
    user: Annotated[NguoiDung, Depends(require_roles("USER"))],
    db: Annotated[Session, Depends(get_db)],
) -> WishlistCountResponse:
    return _run_commerce(commerce_service.get_wishlist_count, db, user)


@router.get("/wishlist/{course_id}/status", response_model=WishlistStatusResponse)
def get_wishlist_course_status(
    course_id: int,
    user: Annotated[NguoiDung, Depends(require_roles("USER"))],
    db: Annotated[Session, Depends(get_db)],
) -> WishlistStatusResponse:
    return _run_commerce(commerce_service.get_wishlist_status, db, user, course_id)


@router.post(
    "/wishlist/{course_id}",
    response_model=WishlistStatusResponse,
    status_code=status.HTTP_200_OK,
)
def add_course_to_wishlist(
    course_id: int,
    user: Annotated[NguoiDung, Depends(require_roles("USER"))],
    db: Annotated[Session, Depends(get_db)],
) -> WishlistStatusResponse:
    return _run_commerce(commerce_service.add_to_wishlist, db, user, course_id)


@router.delete("/wishlist/{course_id}", response_model=WishlistStatusResponse)
def remove_course_from_wishlist(
    course_id: int,
    user: Annotated[NguoiDung, Depends(require_roles("USER"))],
    db: Annotated[Session, Depends(get_db)],
) -> WishlistStatusResponse:
    return _run_commerce(commerce_service.remove_from_wishlist, db, user, course_id)


@router.post(
    "/wishlist/{course_id}/move-to-cart",
    response_model=MoveWishlistToCartResponse,
)
def move_wishlist_course_to_cart(
    course_id: int,
    user: Annotated[NguoiDung, Depends(require_roles("USER"))],
    db: Annotated[Session, Depends(get_db)],
) -> MoveWishlistToCartResponse:
    return _run_commerce(commerce_service.move_wishlist_to_cart, db, user, course_id)


# ---------------------------------------------------------------------------
# Shopping Cart Endpoints (USER only)
# ---------------------------------------------------------------------------
@router.get("/cart", response_model=CartResponse)
def get_my_cart(
    user: Annotated[NguoiDung, Depends(require_roles("USER"))],
    db: Annotated[Session, Depends(get_db)],
) -> CartResponse:
    return _run_commerce(commerce_service.get_cart, db, user)


@router.get("/cart/count", response_model=CartCountResponse)
def get_my_cart_count(
    user: Annotated[NguoiDung, Depends(require_roles("USER"))],
    db: Annotated[Session, Depends(get_db)],
) -> CartCountResponse:
    return _run_commerce(commerce_service.get_cart_count, db, user)


@router.post(
    "/cart/items",
    response_model=CartResponse,
    status_code=status.HTTP_200_OK,
)
def add_item_to_cart(
    payload: CartItemAddRequest,
    user: Annotated[NguoiDung, Depends(require_roles("USER"))],
    db: Annotated[Session, Depends(get_db)],
) -> CartResponse:
    return _run_commerce(commerce_service.add_to_cart, db, user, payload.maKhoaHoc)


@router.delete("/cart/items/{course_id}", response_model=CartResponse)
def remove_item_from_cart(
    course_id: int,
    user: Annotated[NguoiDung, Depends(require_roles("USER"))],
    db: Annotated[Session, Depends(get_db)],
) -> CartResponse:
    return _run_commerce(commerce_service.remove_from_cart, db, user, course_id)


@router.delete("/cart", response_model=CartClearResponse)
def clear_my_cart(
    user: Annotated[NguoiDung, Depends(require_roles("USER"))],
    db: Annotated[Session, Depends(get_db)],
) -> CartClearResponse:
    return _run_commerce(commerce_service.clear_cart, db, user)


# ---------------------------------------------------------------------------
# Buy Now Preparation Endpoint (Read-only validation, no order/payment created)
# ---------------------------------------------------------------------------
@router.get(
    "/commerce/buy-now/validate/{course_id}",
    response_model=BuyNowValidationResponse,
)
def validate_buy_now_course(
    course_id: int,
    user: Annotated[NguoiDung, Depends(require_roles("USER"))],
    db: Annotated[Session, Depends(get_db)],
) -> BuyNowValidationResponse:
    return _run_commerce(
        commerce_service.validate_buy_now_response, db, user, course_id
    )


# ---------------------------------------------------------------------------
# GĐ4.3 Order & Checkout Endpoints (USER only)
# ---------------------------------------------------------------------------
@router.post("/orders/preview", response_model=OrderPreviewResponse)
def preview_checkout_order(
    payload: OrderPreviewRequest,
    user: Annotated[NguoiDung, Depends(require_roles("USER"))],
    db: Annotated[Session, Depends(get_db)],
) -> OrderPreviewResponse:
    return _run_commerce(order_payment_service.preview_order, db, user, payload)


@router.post(
    "/orders",
    response_model=OrderResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_checkout_order(
    payload: OrderCreateRequest,
    response: Response,
    user: Annotated[NguoiDung, Depends(require_roles("USER"))],
    db: Annotated[Session, Depends(get_db)],
    idempotency_key: Annotated[str | None, Header(alias="Idempotency-Key")] = None,
) -> OrderResponse:
    order_res, created_new = _run_commerce(
        order_payment_service.create_order,
        db,
        user,
        payload,
        idempotency_key=idempotency_key or "",
    )
    response.status_code = status.HTTP_201_CREATED if created_new else status.HTTP_200_OK
    return order_res


@router.get("/orders", response_model=OrderListResponse)
def list_my_orders(
    user: Annotated[NguoiDung, Depends(require_roles("USER"))],
    db: Annotated[Session, Depends(get_db)],
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    trang_thai: str | None = Query(default=None),
) -> OrderListResponse:
    return _run_commerce(
        order_payment_service.list_my_orders,
        db,
        user,
        page=page,
        page_size=page_size,
        status_filter=trang_thai,
    )


@router.get("/orders/{order_id}", response_model=OrderResponse)
def get_my_order_detail(
    order_id: int,
    user: Annotated[NguoiDung, Depends(require_roles("USER"))],
    db: Annotated[Session, Depends(get_db)],
) -> OrderResponse:
    return _run_commerce(order_payment_service.get_my_order_detail, db, user, order_id)


@router.get("/orders/{order_id}/status", response_model=OrderStatusResponse)
def get_my_order_status(
    order_id: int,
    user: Annotated[NguoiDung, Depends(require_roles("USER"))],
    db: Annotated[Session, Depends(get_db)],
) -> OrderStatusResponse:
    return _run_commerce(order_payment_service.get_my_order_status, db, user, order_id)


@router.post("/orders/{order_id}/cancel", response_model=OrderResponse)
def cancel_my_order(
    order_id: int,
    user: Annotated[NguoiDung, Depends(require_roles("USER"))],
    db: Annotated[Session, Depends(get_db)],
    payload: OrderCancelRequest | None = None,
) -> OrderResponse:
    return _run_commerce(
        order_payment_service.cancel_my_order, db, user, order_id, payload
    )


@router.post(
    "/orders/{order_id}/payments",
    response_model=PaymentInitiateResponse,
    status_code=status.HTTP_201_CREATED,
)
def initiate_order_payment(
    order_id: int,
    payload: PaymentInitiateRequest,
    request: Request,
    user: Annotated[NguoiDung, Depends(require_roles("USER"))],
    db: Annotated[Session, Depends(get_db)],
    idempotency_key: Annotated[str | None, Header(alias="Idempotency-Key")] = None,
) -> PaymentInitiateResponse:
    client_ip = (
        request.headers.get("x-forwarded-for", "").split(",")[0].strip()
        or (request.client.host if request.client else "127.0.0.1")
    )
    return _run_commerce(
        order_payment_service.initiate_payment,
        db,
        user,
        order_id,
        payload,
        idempotency_key=idempotency_key or "",
        client_ip=client_ip,
    )


# ---------------------------------------------------------------------------
# GĐ4.3 Mock Payment Sandbox Callback (HMAC-verified, Feature-Flagged, Never Production)
# ---------------------------------------------------------------------------
@router.post("/payments/mock/callback", response_model=PaymentCallbackResponse)
def mock_payment_callback(
    payload: MockPaymentCallbackRequest,
    db: Annotated[Session, Depends(get_db)],
) -> PaymentCallbackResponse:
    return _run_commerce(
        order_payment_service.process_mock_payment_callback, db, payload
    )


@router.get("/commerce/capabilities", response_model=CommerceCapabilitiesResponse)
def get_commerce_capabilities() -> CommerceCapabilitiesResponse:
    return order_payment_service.get_commerce_capabilities()


@router.get(
    "/payments/mock/{txn_ref}",
    response_model=MockPaymentSessionDetailResponse,
)
def get_mock_payment_session(
    txn_ref: str,
    user: Annotated[NguoiDung, Depends(require_roles("USER"))],
    db: Annotated[Session, Depends(get_db)],
) -> MockPaymentSessionDetailResponse:
    return _run_commerce(
        order_payment_service.get_mock_payment_session_detail, db, user, txn_ref
    )


@router.post(
    "/payments/mock/{txn_ref}/simulate",
    response_model=PaymentCallbackResponse,
)
def simulate_mock_payment(
    txn_ref: str,
    payload: MockPaymentSimulateRequest,
    user: Annotated[NguoiDung, Depends(require_roles("USER"))],
    db: Annotated[Session, Depends(get_db)],
) -> PaymentCallbackResponse:
    return _run_commerce(
        order_payment_service.simulate_mock_payment_outcome,
        db,
        user,
        txn_ref,
        payload,
    )


# ---------------------------------------------------------------------------
# GĐ4.5 VNPay Sandbox IPN (Server-to-Server) & Return URL (Read-Only Verify)
# ---------------------------------------------------------------------------
@router.get("/payments/vnpay/ipn", response_model=VNPayIpnResponse)
def vnpay_sandbox_ipn(
    request: Request,
    db: Annotated[Session, Depends(get_db)],
) -> VNPayIpnResponse:
    return order_payment_service.process_vnpay_ipn(
        db, dict(request.query_params)
    )


@router.get("/payments/vnpay/return", response_model=VNPayReturnVerifyResponse)
def vnpay_sandbox_return_verify(
    request: Request,
    user: Annotated[NguoiDung, Depends(require_roles("USER"))],
    db: Annotated[Session, Depends(get_db)],
) -> VNPayReturnVerifyResponse:
    return _run_commerce(
        order_payment_service.verify_vnpay_return_readonly,
        db,
        user,
        dict(request.query_params),
    )
