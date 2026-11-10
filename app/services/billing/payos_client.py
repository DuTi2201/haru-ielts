"""A small payOS client (payment link, status, cancel, webhook check) over httpx.

Written against payOS's own SDK (payos-lib-python 1.1.0), whose signing it reproduces exactly:
every body and every `data` object is signed with HMAC-SHA256 over "key=value" pairs joined by "&",
keys in ascending order. The SDK itself is not a dependency because it needs a newer pydantic than
the app pins.

The three credentials come from the environment only (Railway variables). Nothing here prints,
logs or stores them or a signature.
"""
import hashlib
import hmac
import json
import time
from dataclasses import dataclass, field
from typing import Any

import httpx

from app.core.config import settings

SUCCESS = "00"
# fields payOS's own SDK always lists in a webhook's `data`; when one is absent from the JSON the
# SDK signs it as an empty value, so a verifier has to be able to do the same
_WEBHOOK_OPTIONAL = (
    "counterAccountBankId",
    "counterAccountBankName",
    "counterAccountName",
    "counterAccountNumber",
    "virtualAccountName",
    "virtualAccountNumber",
)


class PayosError(Exception):
    """payOS refused, could not be reached, or sent something that does not verify."""

    def __init__(self, message: str, code: str | None = None):
        super().__init__(message)
        self.code = code


def _text(value: Any) -> str:
    if isinstance(value, bool):
        return "true" if value else "false"
    if value is None:
        return ""
    return str(value)


def signature_of(data: dict[str, Any], key: str) -> str:
    """HMAC-SHA256 of the data object: keys sorted, `key=value` joined by `&`, None -> "",
    a list as compact JSON with the keys of its objects sorted."""
    parts = []
    for name in sorted(data):
        value = data[name]
        if isinstance(value, list):
            value = json.dumps(
                [{k: item[k] for k in sorted(item)} if isinstance(item, dict) else item for item in value],
                separators=(",", ":"),
                ensure_ascii=False,
            )
        else:
            value = "" if value in (None, "undefined", "null") else _text(value)
        parts.append(f"{name}={value}")
    return hmac.new(key.encode(), "&".join(parts).encode(), hashlib.sha256).hexdigest()


def _same(given: Any, expected: str) -> bool:
    """Constant-time comparison of a signature that came from outside. Compared as bytes: a
    non-ASCII string would make hmac.compare_digest raise instead of answering "no"."""
    return hmac.compare_digest(str(given).encode("utf-8"), expected.encode("utf-8"))


def signature_of_payment_request(body: dict[str, Any], key: str) -> str:
    """The create-link signature covers only these five fields."""
    text = "&".join(f"{n}={_text(body[n])}" for n in ("amount", "cancelUrl", "description", "orderCode", "returnUrl"))
    return hmac.new(key.encode(), text.encode(), hashlib.sha256).hexdigest()


@dataclass
class CreatedLink:
    payment_link_id: str
    checkout_url: str
    qr_code: str
    bin: str | None = None
    account_number: str | None = None
    account_name: str | None = None
    description: str | None = None
    amount: int = 0
    expired_at: int | None = None


@dataclass
class Transaction:
    reference: str
    amount: int


@dataclass
class LinkInfo:
    id: str
    order_code: int
    status: str  # PENDING | PAID | UNDERPAID | CANCELLED | EXPIRED | PROCESSING | FAILED
    amount: int
    amount_paid: int
    transactions: list[Transaction] = field(default_factory=list)


@dataclass
class WebhookPayment:
    order_code: int
    amount: int
    reference: str
    paid: bool  # the transaction succeeded (data.code == "00")
    payment_link_id: str | None = None
    description: str | None = None


class PayosClient:
    def __init__(
        self,
        client_id: str,
        api_key: str,
        checksum_key: str,
        base_url: str = "https://api-merchant.payos.vn",
        http: httpx.Client | None = None,
        timeout: float = 15.0,
    ):
        if not (client_id and api_key and checksum_key):
            raise PayosError("payOS is not configured")
        self._headers = {"x-client-id": client_id, "x-api-key": api_key, "Content-Type": "application/json"}
        self._key = checksum_key
        self._base = base_url.rstrip("/")
        self._http = http or httpx.Client(timeout=timeout)

    # ------------------------------------------------------------ requests --
    def _call(self, method: str, path: str, body: dict | None = None) -> dict[str, Any]:
        try:
            response = self._http.request(method, self._base + path, json=body, headers=self._headers)
        except httpx.HTTPError as exc:
            raise PayosError(f"payOS could not be reached ({type(exc).__name__})") from None
        try:
            payload = response.json()
        except ValueError:
            raise PayosError(f"payOS answered with something that is not JSON (HTTP {response.status_code})") from None
        if not isinstance(payload, dict):
            raise PayosError("payOS answered with an unexpected body")
        if payload.get("code") != SUCCESS:
            raise PayosError(str(payload.get("desc") or "payOS refused the request"), code=str(payload.get("code")))
        data = payload.get("data")
        if not isinstance(data, dict):
            raise PayosError("payOS answered without data")
        given = payload.get("signature")
        if not given or not _same(given, signature_of(data, self._key)):
            raise PayosError("the signature of payOS's answer does not match")
        return data

    def create_payment(
        self, *, order_code: int, amount: int, description: str, return_url: str, cancel_url: str, expired_at: int | None = None
    ) -> CreatedLink:
        body: dict[str, Any] = {
            "orderCode": order_code,
            "amount": amount,
            "description": description,
            "cancelUrl": cancel_url,
            "returnUrl": return_url,
        }
        if expired_at:
            body["expiredAt"] = expired_at
        body["signature"] = signature_of_payment_request(body, self._key)
        data = self._call("POST", "/v2/payment-requests", body)
        return CreatedLink(
            payment_link_id=str(data["paymentLinkId"]),
            checkout_url=str(data["checkoutUrl"]),
            qr_code=str(data.get("qrCode") or ""),
            bin=data.get("bin"),
            account_number=data.get("accountNumber"),
            account_name=data.get("accountName"),
            description=data.get("description"),
            amount=int(data.get("amount") or amount),
            expired_at=data.get("expiredAt"),
        )

    def get_payment(self, order_code: int | str) -> LinkInfo:
        data = self._call("GET", f"/v2/payment-requests/{order_code}")
        return LinkInfo(
            id=str(data.get("id") or ""),
            order_code=int(data["orderCode"]),
            status=str(data.get("status") or ""),
            amount=int(data.get("amount") or 0),
            amount_paid=int(data.get("amountPaid") or 0),
            transactions=[
                Transaction(reference=str(t["reference"]), amount=int(t["amount"]))
                for t in (data.get("transactions") or [])
                if isinstance(t, dict) and t.get("reference") and t.get("amount") is not None
            ],
        )

    def cancel_payment(self, order_code: int | str, reason: str | None = None) -> None:
        body: dict[str, Any] = {"cancellationReason": reason} if reason else {}
        if body:
            body["signature"] = signature_of(body, self._key)
        self._call("POST", f"/v2/payment-requests/{order_code}/cancel", body)

    # ------------------------------------------------------------- webhook --
    def verify_webhook(self, payload: Any) -> WebhookPayment:
        """The payment a webhook body announces, if its signature is right. Raises PayosError
        for anything else: the caller must not act on an unsigned or altered body."""
        if not isinstance(payload, dict):
            raise PayosError("the webhook body is not an object")
        data, given = payload.get("data"), payload.get("signature")
        if not isinstance(data, dict) or not given:
            raise PayosError("the webhook has no data or no signature")
        candidates = [signature_of(data, self._key)]
        filled = {**{name: None for name in _WEBHOOK_OPTIONAL}, **data}
        candidates.append(signature_of(filled, self._key))
        if not any(_same(given, c) for c in candidates):
            raise PayosError("the webhook signature does not match")
        try:
            return WebhookPayment(
                order_code=int(data["orderCode"]),
                amount=int(data["amount"]),
                reference=str(data["reference"]),
                paid=str(data.get("code")) == SUCCESS and payload.get("success") is not False,
                payment_link_id=data.get("paymentLinkId"),
                description=data.get("description"),
            )
        except (KeyError, TypeError, ValueError):
            raise PayosError("the webhook data is incomplete") from None


def make_client(http: httpx.Client | None = None) -> PayosClient:
    return PayosClient(
        settings.PAYOS_CLIENT_ID,
        settings.PAYOS_API_KEY,
        settings.PAYOS_CHECKSUM_KEY,
        settings.PAYOS_BASE_URL,
        http=http,
    )


def new_order_code() -> int:
    """A number payOS has not seen: the clock in milliseconds followed by three random digits
    (16 digits at most, under the 9007199254740991 limit for the next two centuries)."""
    import secrets

    return int(time.time() * 1000) * 1000 + secrets.randbelow(1000)
