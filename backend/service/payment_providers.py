"""Payment Provider abstraction for GĐ4.3 Mock Sandbox and GĐ4.5 VNPay Sandbox (API v2.1.0)."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime, timedelta, timezone
from decimal import Decimal, InvalidOperation
import hashlib
import hmac
from typing import Protocol
from urllib.parse import quote_plus

from config.config import get_settings

_VN_TZ = timezone(timedelta(hours=7))
_VNPAY_SAFE_FIELDS = (
    "vnp_TmnCode",
    "vnp_TxnRef",
    "vnp_TransactionNo",
    "vnp_ResponseCode",
    "vnp_TransactionStatus",
    "vnp_Amount",
    "vnp_BankCode",
    "vnp_CardType",
    "vnp_PayDate",
    "vnp_OrderInfo",
)


class PaymentProviderError(Exception):
    pass


class PaymentSignatureError(PaymentProviderError):
    pass


@dataclass(frozen=True)
class PaymentSessionResult:
    gateway: str
    is_simulated: bool
    payment_url: str
    signature_hint: str | None = None


@dataclass(frozen=True)
class CallbackVerificationResult:
    gateway: str
    is_simulated: bool
    internal_txn_ref: str
    gateway_txn_id: str | None
    order_id: int | None  # None when gateway only supplies internal_txn_ref (e.g. VNPay vnp_TxnRef)
    amount: Decimal
    currency: str
    outcome: str  # PAID | FAILED | CANCELLED | EXPIRED
    response_code: str
    signature_valid: bool
    safe_payload: dict


class PaymentProvider(Protocol):
    gateway_code: str
    is_simulated: bool

    def create_session(
        self,
        *,
        order_id: int,
        order_number: str,
        internal_txn_ref: str,
        amount: Decimal,
        currency: str,
        client_ip: str = "127.0.0.1",
        created_at_utc: datetime | None = None,
        expires_at_utc: datetime | None = None,
    ) -> PaymentSessionResult: ...

    def verify_callback(self, payload: dict) -> CallbackVerificationResult: ...


# ---------------------------------------------------------------------------
# GĐ4.3 Mock Sandbox Payment Provider
# ---------------------------------------------------------------------------
def _mock_signing_secret() -> bytes:
    secret = get_settings().secret_key.get_secret_value().encode("utf-8")
    return hashlib.sha256(b"EduSuggest-MockPaymentSandbox-v1:" + secret).digest()


def compute_mock_callback_signature(
    *,
    internal_txn_ref: str,
    order_id: int,
    amount: Decimal,
    currency: str,
    outcome: str,
    gateway_txn_id: str | None = None,
) -> str:
    """Compute server-side HMAC-SHA256 signature for Mock Payment Sandbox callbacks."""
    canonical = "|".join(
        [
            "MOCK_SANDBOX",
            internal_txn_ref.strip(),
            str(int(order_id)),
            str(Decimal(amount).quantize(Decimal("1"))),
            currency.strip().upper(),
            outcome.strip().upper(),
            (gateway_txn_id or "").strip(),
        ]
    )
    return hmac.new(
        _mock_signing_secret(),
        canonical.encode("utf-8"),
        hashlib.sha256,
    ).hexdigest()


class MockSandboxPaymentProvider:
    """Simulated sandbox payment provider for testing. Never processes real money."""

    gateway_code = "MOCK_SANDBOX"
    is_simulated = True

    def create_session(
        self,
        *,
        order_id: int,
        order_number: str,
        internal_txn_ref: str,
        amount: Decimal,
        currency: str,
        client_ip: str = "127.0.0.1",
        created_at_utc: datetime | None = None,
        expires_at_utc: datetime | None = None,
    ) -> PaymentSessionResult:
        url = (
            f"/payment/mock-sandbox?txnRef={internal_txn_ref}"
            f"&orderId={order_id}&orderNumber={order_number}&simulated=true"
        )
        return PaymentSessionResult(
            gateway=self.gateway_code,
            is_simulated=True,
            payment_url=url,
        )

    def verify_callback(self, payload: dict) -> CallbackVerificationResult:
        provided_sig = str(payload.get("signature") or "").strip()
        internal_txn_ref = str(payload.get("maGiaoDichNoiBo") or "").strip()
        gateway_txn_id = (
            str(payload.get("maGiaoDichCong")).strip()
            if payload.get("maGiaoDichCong")
            else None
        )
        order_id = int(payload["maDonHang"])
        amount = Decimal(str(payload["soTien"]))
        currency = str(payload.get("donViTienTe") or "").strip().upper()
        outcome = str(payload.get("ketQua") or "").strip().upper()

        if outcome not in {"PAID", "FAILED", "CANCELLED", "EXPIRED"}:
            raise PaymentProviderError(f"Unsupported mock callback outcome: {outcome}")

        expected_sig = compute_mock_callback_signature(
            internal_txn_ref=internal_txn_ref,
            order_id=order_id,
            amount=amount,
            currency=currency,
            outcome=outcome,
            gateway_txn_id=gateway_txn_id,
        )
        if not provided_sig or not hmac.compare_digest(provided_sig, expected_sig):
            raise PaymentSignatureError("Chữ ký callback thanh toán mô phỏng không hợp lệ.")

        response_code_map = {
            "PAID": "00",
            "FAILED": "99",
            "CANCELLED": "24",
            "EXPIRED": "11",
        }
        safe_payload = {
            "gateway": self.gateway_code,
            "isSimulated": True,
            "maGiaoDichNoiBo": internal_txn_ref,
            "maGiaoDichCong": gateway_txn_id,
            "maDonHang": order_id,
            "soTien": str(amount),
            "donViTienTe": currency,
            "ketQua": outcome,
            "responseCode": response_code_map[outcome],
        }
        return CallbackVerificationResult(
            gateway=self.gateway_code,
            is_simulated=True,
            internal_txn_ref=internal_txn_ref,
            gateway_txn_id=gateway_txn_id,
            order_id=order_id,
            amount=amount,
            currency=currency,
            outcome=outcome,
            response_code=response_code_map[outcome],
            signature_valid=True,
            safe_payload=safe_payload,
        )


# ---------------------------------------------------------------------------
# GĐ4.5 VNPay Sandbox Payment Provider (Official API v2.1.0, HMAC-SHA512)
# ---------------------------------------------------------------------------
def is_vnpay_sandbox_configured() -> bool:
    """Return True only when VNPay Sandbox is explicitly enabled and fully configured (never Production)."""
    settings = get_settings()
    if not settings.vnpay_sandbox_enabled:
        return False
    if (settings.app_env or "").strip().lower() == "production":
        return False
    tmn = (settings.vnpay_tmn_code or "").strip()
    secret = settings.vnpay_hash_secret.get_secret_value().strip() if settings.vnpay_hash_secret else ""
    ret_url = (settings.vnpay_return_url or "").strip()
    pay_url = (settings.vnpay_payment_url or "").strip()
    if not (tmn and secret and ret_url and pay_url.startswith("https://sandbox.vnpayment.vn/")):
        return False
    return True


def build_vnpay_hash_data(params: dict[str, str]) -> str:
    """Build official VNPay v2.1.0 canonical hash string:
    - Filter keys starting with 'vnp_' (excluding vnp_SecureHash and vnp_SecureHashType)
    - Ignore None / empty values
    - Sort alphabetically by key
    - Encode values with urllib.parse.quote_plus and join with '&'
    """
    filtered = [
        (k, str(v))
        for k, v in params.items()
        if k.startswith("vnp_")
        and k not in {"vnp_SecureHash", "vnp_SecureHashType"}
        and v is not None
        and str(v) != ""
    ]
    filtered.sort(key=lambda pair: pair[0])
    return "&".join(f"{k}={quote_plus(v)}" for k, v in filtered)


def compute_vnpay_hmac_sha512(hash_data: str, secret: str) -> str:
    return hmac.new(
        secret.encode("utf-8"),
        hash_data.encode("utf-8"),
        hashlib.sha512,
    ).hexdigest()


def _format_vnpay_datetime(dt_utc_naive: datetime) -> str:
    aware_utc = dt_utc_naive.replace(tzinfo=UTC)
    vn_dt = aware_utc.astimezone(_VN_TZ)
    return vn_dt.strftime("%Y%m%d%H%M%S")


class VNPaySandboxPaymentProvider:
    """Official VNPay API v2.1.0 Sandbox Provider (HMAC-SHA512, VND x100, Asia/Ho_Chi_Minh)."""

    gateway_code = "VNPAY_SANDBOX"
    is_simulated = False

    def _require_config(self) -> tuple[str, str, str, str, str]:
        if not is_vnpay_sandbox_configured():
            raise PaymentProviderError(
                "VNPay Sandbox chưa được kích hoạt hoặc thiếu cấu hình bắt buộc."
            )
        settings = get_settings()
        return (
            settings.vnpay_tmn_code.strip(),  # type: ignore[union-attr]
            settings.vnpay_hash_secret.get_secret_value().strip(),  # type: ignore[union-attr]
            settings.vnpay_payment_url.strip(),
            settings.vnpay_return_url.strip(),  # type: ignore[union-attr]
            settings.vnpay_version.strip() or "2.1.0",
        )

    def create_session(
        self,
        *,
        order_id: int,
        order_number: str,
        internal_txn_ref: str,
        amount: Decimal,
        currency: str,
        client_ip: str = "127.0.0.1",
        created_at_utc: datetime | None = None,
        expires_at_utc: datetime | None = None,
    ) -> PaymentSessionResult:
        if currency.strip().upper() != "VND":
            raise PaymentProviderError("VNPay Sandbox chỉ hỗ trợ đơn vị tiền tệ VND.")
        tmn_code, hash_secret, payment_url, return_url, version = self._require_config()

        now_utc = created_at_utc or datetime.now(UTC).replace(tzinfo=None)
        exp_utc = expires_at_utc or (now_utc + timedelta(minutes=15))
        vnp_amount = int((Decimal(amount).quantize(Decimal("1"))) * 100)
        if vnp_amount <= 0:
            raise PaymentProviderError("Số tiền thanh toán VNPay phải lớn hơn 0.")

        params: dict[str, str] = {
            "vnp_Version": version,
            "vnp_Command": "pay",
            "vnp_TmnCode": tmn_code,
            "vnp_Amount": str(vnp_amount),
            "vnp_CurrCode": "VND",
            "vnp_TxnRef": internal_txn_ref.strip(),
            "vnp_OrderInfo": f"Thanh toan don hang {order_number}",
            "vnp_OrderType": "other",
            "vnp_Locale": "vn",
            "vnp_ReturnUrl": return_url,
            "vnp_IpAddr": (client_ip or "127.0.0.1").strip()[:45],
            "vnp_CreateDate": _format_vnpay_datetime(now_utc),
            "vnp_ExpireDate": _format_vnpay_datetime(exp_utc),
        }
        hash_data = build_vnpay_hash_data(params)
        secure_hash = compute_vnpay_hmac_sha512(hash_data, hash_secret)
        full_url = f"{payment_url}?{hash_data}&vnp_SecureHash={secure_hash}"

        return PaymentSessionResult(
            gateway=self.gateway_code,
            is_simulated=False,
            payment_url=full_url,
        )

    def verify_callback(self, payload: dict) -> CallbackVerificationResult:
        tmn_code, hash_secret, _pay_url, _ret_url, _ver = self._require_config()

        provided_sig = str(payload.get("vnp_SecureHash") or "").strip().lower()
        hash_data = build_vnpay_hash_data(payload)
        expected_sig = compute_vnpay_hmac_sha512(hash_data, hash_secret).lower()

        if not provided_sig or not hmac.compare_digest(provided_sig, expected_sig):
            raise PaymentSignatureError("Chữ ký VNPay (vnp_SecureHash) không hợp lệ.")

        if str(payload.get("vnp_TmnCode") or "").strip() != tmn_code:
            raise PaymentSignatureError("vnp_TmnCode không khớp với cấu hình merchant.")

        internal_txn_ref = str(payload.get("vnp_TxnRef") or "").strip()
        if not internal_txn_ref:
            raise PaymentProviderError("Thiếu vnp_TxnRef trong callback VNPay.")

        raw_amount = str(payload.get("vnp_Amount") or "").strip()
        try:
            amount_x100 = Decimal(raw_amount)
        except InvalidOperation as exc:
            raise PaymentProviderError("vnp_Amount không hợp lệ.") from exc
        if amount_x100 <= 0 or (amount_x100 % Decimal("100")) != 0:
            raise PaymentProviderError("vnp_Amount phải là bội số dương của 100.")
        amount_vnd = (amount_x100 / Decimal("100")).quantize(Decimal("1"))

        resp_code = str(payload.get("vnp_ResponseCode") or "").strip()
        txn_status = str(payload.get("vnp_TransactionStatus") or "").strip()
        # GĐ4.7A HARDEN-01: Require BOTH vnp_ResponseCode == "00" AND vnp_TransactionStatus == "00"
        if resp_code == "00" and txn_status == "00":
            outcome = "PAID"
        elif resp_code == "24":
            outcome = "CANCELLED"
        elif resp_code == "11":
            outcome = "EXPIRED"
        else:
            outcome = "FAILED"

        gateway_txn_id = (
            str(payload.get("vnp_TransactionNo")).strip()
            if payload.get("vnp_TransactionNo")
            else None
        )
        safe_payload = {
            "gateway": self.gateway_code,
            "isSimulated": False,
            **{k: str(payload[k]) for k in _VNPAY_SAFE_FIELDS if k in payload and payload[k] is not None},
        }
        return CallbackVerificationResult(
            gateway=self.gateway_code,
            is_simulated=False,
            internal_txn_ref=internal_txn_ref,
            gateway_txn_id=gateway_txn_id,
            order_id=None,
            amount=amount_vnd,
            currency="VND",
            outcome=outcome,
            response_code=resp_code or "99",
            signature_valid=True,
            safe_payload=safe_payload,
        )


def get_payment_provider(gateway: str) -> PaymentProvider:
    normalized = (gateway or "").strip().upper()
    if normalized == "MOCK_SANDBOX":
        return MockSandboxPaymentProvider()
    if normalized == "VNPAY_SANDBOX":
        return VNPaySandboxPaymentProvider()
    raise PaymentProviderError(f"Cổng thanh toán chưa được hỗ trợ trong giai đoạn hiện tại: {gateway}")


# ---------------------------------------------------------------------------
# GĐ4.6 Official VNPay v2.1.0 QueryDR & Refund Pipe-Delimited Request Builders
# ---------------------------------------------------------------------------
def build_vnpay_querydr_request(
    *,
    request_id: str,
    txn_ref: str,
    transaction_date_vnp: str,
    order_info: str,
    client_ip: str = "127.0.0.1",
    transaction_no: str | None = None,
    created_at_utc: datetime | None = None,
) -> dict[str, str]:
    """Build official VNPay v2.1.0 QueryDR JSON payload with pipe-delimited HMAC-SHA512 checksum."""
    provider = VNPaySandboxPaymentProvider()
    tmn_code, hash_secret, _pay_url, _ret_url, version = provider._require_config()
    create_date = _format_vnpay_datetime(created_at_utc or datetime.now(UTC).replace(tzinfo=None))

    hash_parts = [
        request_id.strip(),
        version,
        "querydr",
        tmn_code,
        txn_ref.strip(),
        transaction_date_vnp.strip(),
        create_date,
        client_ip.strip(),
        order_info.strip(),
    ]
    secure_hash = compute_vnpay_hmac_sha512("|".join(hash_parts), hash_secret)
    body = {
        "vnp_RequestId": request_id.strip(),
        "vnp_Version": version,
        "vnp_Command": "querydr",
        "vnp_TmnCode": tmn_code,
        "vnp_TxnRef": txn_ref.strip(),
        "vnp_OrderInfo": order_info.strip(),
        "vnp_TransactionDate": transaction_date_vnp.strip(),
        "vnp_CreateDate": create_date,
        "vnp_IpAddr": client_ip.strip(),
        "vnp_SecureHash": secure_hash,
    }
    if transaction_no:
        body["vnp_TransactionNo"] = transaction_no.strip()
    return body


def build_vnpay_refund_request(
    *,
    request_id: str,
    txn_ref: str,
    amount_vnd: Decimal,
    transaction_type: str,  # "02" full refund, "03" partial refund
    transaction_date_vnp: str,
    create_by: str,
    order_info: str,
    transaction_no: str = "",
    client_ip: str = "127.0.0.1",
    created_at_utc: datetime | None = None,
) -> dict[str, str]:
    """Build official VNPay v2.1.0 Refund JSON payload with pipe-delimited HMAC-SHA512 checksum."""
    if transaction_type not in {"02", "03"}:
        raise PaymentProviderError("vnp_TransactionType phải là '02' (toàn phần) hoặc '03' (một phần).")
    vnp_amount = int((Decimal(amount_vnd).quantize(Decimal("1"))) * 100)
    if vnp_amount <= 0:
        raise PaymentProviderError("Số tiền hoàn VNPay phải lớn hơn 0.")

    provider = VNPaySandboxPaymentProvider()
    tmn_code, hash_secret, _pay_url, _ret_url, version = provider._require_config()
    create_date = _format_vnpay_datetime(created_at_utc or datetime.now(UTC).replace(tzinfo=None))

    hash_parts = [
        request_id.strip(),
        version,
        "refund",
        tmn_code,
        transaction_type,
        txn_ref.strip(),
        str(vnp_amount),
        (transaction_no or "").strip(),
        transaction_date_vnp.strip(),
        create_by.strip(),
        create_date,
        client_ip.strip(),
        order_info.strip(),
    ]
    secure_hash = compute_vnpay_hmac_sha512("|".join(hash_parts), hash_secret)
    return {
        "vnp_RequestId": request_id.strip(),
        "vnp_Version": version,
        "vnp_Command": "refund",
        "vnp_TmnCode": tmn_code,
        "vnp_TransactionType": transaction_type,
        "vnp_TxnRef": txn_ref.strip(),
        "vnp_Amount": str(vnp_amount),
        "vnp_TransactionNo": (transaction_no or "").strip(),
        "vnp_TransactionDate": transaction_date_vnp.strip(),
        "vnp_CreateBy": create_by.strip(),
        "vnp_CreateDate": create_date,
        "vnp_IpAddr": client_ip.strip(),
        "vnp_OrderInfo": order_info.strip(),
        "vnp_SecureHash": secure_hash,
    }


def verify_vnpay_querydr_response(payload: dict[str, object]) -> bool:
    """Verify official VNPay v2.1.0 QueryDR response pipe-delimited HMAC-SHA512 signature."""
    provider = VNPaySandboxPaymentProvider()
    _tmn, hash_secret, _pay_url, _ret_url, _ver = provider._require_config()
    provided = str(payload.get("vnp_SecureHash") or "").strip().lower()
    if not provided:
        return False
    parts = [
        str(payload.get("vnp_ResponseId") or ""),
        str(payload.get("vnp_Command") or ""),
        str(payload.get("vnp_ResponseCode") or ""),
        str(payload.get("vnp_Message") or ""),
        str(payload.get("vnp_TmnCode") or ""),
        str(payload.get("vnp_TxnRef") or ""),
        str(payload.get("vnp_Amount") or ""),
        str(payload.get("vnp_BankCode") or ""),
        str(payload.get("vnp_PayDate") or ""),
        str(payload.get("vnp_TransactionNo") or ""),
        str(payload.get("vnp_TransactionType") or ""),
        str(payload.get("vnp_TransactionStatus") or ""),
        str(payload.get("vnp_OrderInfo") or ""),
        str(payload.get("vnp_PromotionCode") or ""),
        str(payload.get("vnp_PromotionAmount") or ""),
    ]
    expected = compute_vnpay_hmac_sha512("|".join(parts), hash_secret).lower()
    return hmac.compare_digest(provided, expected)


def verify_vnpay_refund_response(payload: dict[str, object]) -> bool:
    """Verify official VNPay v2.1.0 Refund response pipe-delimited HMAC-SHA512 signature."""
    provider = VNPaySandboxPaymentProvider()
    _tmn, hash_secret, _pay_url, _ret_url, _ver = provider._require_config()
    provided = str(payload.get("vnp_SecureHash") or "").strip().lower()
    if not provided:
        return False
    parts = [
        str(payload.get("vnp_ResponseId") or ""),
        str(payload.get("vnp_Command") or ""),
        str(payload.get("vnp_ResponseCode") or ""),
        str(payload.get("vnp_Message") or ""),
        str(payload.get("vnp_TmnCode") or ""),
        str(payload.get("vnp_TxnRef") or ""),
        str(payload.get("vnp_Amount") or ""),
        str(payload.get("vnp_BankCode") or ""),
        str(payload.get("vnp_PayDate") or ""),
        str(payload.get("vnp_TransactionNo") or ""),
        str(payload.get("vnp_TransactionType") or ""),
        str(payload.get("vnp_TransactionStatus") or ""),
        str(payload.get("vnp_OrderInfo") or ""),
    ]
    expected = compute_vnpay_hmac_sha512("|".join(parts), hash_secret).lower()
    return hmac.compare_digest(provided, expected)
