"""CJ Dropshipping supplier adapter.

IMPORTANT -- endpoint accuracy: the URLs, params, and response fields below
follow CJ Dropshipping's documented Open API v2 structure
(https://developers.cjdropshipping.cn/en/api/api2/) as best known. This
sandbox's network policy blocks outbound access to that domain, so none of
it was re-verified against CJ's *current* docs before shipping -- treat
this as a first draft to check field-by-field against your own CJ
account's API reference once you have a key, not as tested code. A wrong
field name will come back as a clear 4xx from CJ, not a silent failure, so
it's safe to try against a sandbox/test order first.

Get credentials: CJ Dropshipping account -> Developer/API section -> apply
for API access -> you get an email + API key, exchanged here for a
short-lived access token.
"""
import time
from typing import Optional

import requests

from .base import SupplierAdapter, SupplierOrderResult, SupplierProduct

_BASE_URL = "https://developers.cjdropshipping.com/api2.0/v1"


class CJDropshippingSupplier(SupplierAdapter):
    def __init__(self, email: str, api_key: str):
        self._email = email
        self._api_key = api_key
        self._session = requests.Session()
        self._token: Optional[str] = None
        self._token_expires_at: float = 0

    def _ensure_token(self) -> str:
        if self._token and time.time() < self._token_expires_at:
            return self._token
        resp = self._session.post(
            f"{_BASE_URL}/authentication/getAccessToken",
            json={"email": self._email, "password": self._api_key},
            timeout=30,
        )
        resp.raise_for_status()
        data = resp.json()["data"]
        self._token = data["accessToken"]
        # CJ access tokens are typically valid ~15 days; refresh well before that.
        self._token_expires_at = time.time() + 14 * 24 * 3600
        return self._token

    def _headers(self) -> dict:
        return {"CJ-Access-Token": self._ensure_token(), "Content-Type": "application/json"}

    def list_products(self, page_size: int = 50) -> list:
        resp = self._session.get(
            f"{_BASE_URL}/product/list",
            headers=self._headers(),
            params={"pageNum": 1, "pageSize": page_size},
            timeout=30,
        )
        resp.raise_for_status()
        rows = resp.json().get("data", {}).get("list", [])
        return [
            SupplierProduct(
                supplier_product_id=raw["pid"],
                sku=raw.get("productSku") or raw["pid"],
                title=raw.get("productNameEn", ""),
                description=raw.get("description") or raw.get("productNameEn", ""),
                cost=float(raw.get("sellPrice") or 0),
                stock=int(raw.get("inventory") or 0),
                images=[raw["productImage"]] if raw.get("productImage") else [],
            )
            for raw in rows
        ]

    def place_order(self, order) -> SupplierOrderResult:
        addr = order.shipping_address or {}
        body = {
            "orderNumber": order.order_number,
            "shippingCustomerName": addr.get("name", ""),
            "shippingCountryCode": addr.get("country_code", ""),
            "shippingProvince": addr.get("province", ""),
            "shippingCity": addr.get("city", ""),
            "shippingAddress": addr.get("address1", ""),
            "shippingZip": addr.get("zip", ""),
            "shippingPhone": addr.get("phone", ""),
            "products": [
                # CJ orders by variant id (vid), not SKU -- line_items need
                # a "supplier_variant_id" populated (e.g. during product
                # sync) mapping our SKU to CJ's vid for this to work.
                {"vid": item.get("supplier_variant_id", item.get("sku")), "quantity": item["quantity"]}
                for item in order.line_items
            ],
        }
        resp = self._session.post(
            f"{_BASE_URL}/shopping/order/createOrder", headers=self._headers(), json=body, timeout=30
        )
        resp.raise_for_status()
        data = resp.json()["data"]
        # CJ typically assigns tracking after warehouse processing, not at
        # creation time -- no tracking yet, StoreBot will poll get_tracking
        # on later cycles until it appears.
        return SupplierOrderResult(
            supplier_order_id=data["orderId"], tracking_number=None, tracking_url=None, carrier=None
        )

    def get_tracking(self, supplier_order_id: str) -> SupplierOrderResult:
        resp = self._session.get(
            f"{_BASE_URL}/shopping/order/getOrderDetail",
            headers=self._headers(),
            params={"orderId": supplier_order_id},
            timeout=30,
        )
        resp.raise_for_status()
        data = resp.json()["data"]
        logistic = data.get("logisticInfo") or {}
        tracking_number = logistic.get("trackNumber")
        return SupplierOrderResult(
            supplier_order_id=supplier_order_id,
            tracking_number=tracking_number,
            tracking_url=f"https://www.cjdropshipping.com/tracking?num={tracking_number}" if tracking_number else None,
            carrier=logistic.get("logisticName"),
        )
