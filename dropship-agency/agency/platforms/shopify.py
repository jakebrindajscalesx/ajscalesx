import json
from pathlib import Path
from typing import Optional

import requests

from .base import Order, StorePlatform


class ShopifyStore(StorePlatform):
    """Drives one Shopify store via a custom-app Admin API token.

    See the top-level README for how to generate `access_token` from
    Shopify's Settings -> Apps -> Develop apps.
    """

    def __init__(self, shop_domain: str, access_token: str, state_path: Path, api_version: str = "2024-10"):
        self.base_url = f"https://{shop_domain}/admin/api/{api_version}"
        self.session = requests.Session()
        self.session.headers.update(
            {
                "X-Shopify-Access-Token": access_token,
                "Content-Type": "application/json",
            }
        )
        # Shopify's REST API has no "find product by SKU" endpoint, so we
        # remember what we created ourselves: sku -> {product_id,
        # variant_id, inventory_item_id}. Products this bot didn't create
        # (hand-added ones) are invisible to product sync until touched.
        self._state_path = state_path
        self._location_id: Optional[str] = None

    def _load_product_map(self) -> dict:
        if self._state_path.exists():
            return json.loads(self._state_path.read_text())
        return {}

    def _save_product_map(self, mapping: dict) -> None:
        self._state_path.parent.mkdir(parents=True, exist_ok=True)
        self._state_path.write_text(json.dumps(mapping, indent=2))

    def _primary_location_id(self) -> str:
        if self._location_id is None:
            resp = self.session.get(f"{self.base_url}/locations.json", timeout=30)
            resp.raise_for_status()
            locations = resp.json()["locations"]
            if not locations:
                raise RuntimeError("Shopify store has no locations to hold inventory")
            self._location_id = str(locations[0]["id"])
        return self._location_id

    def get_unfulfilled_orders(self) -> list[Order]:
        resp = self.session.get(
            f"{self.base_url}/orders.json",
            params={"fulfillment_status": "unfulfilled", "status": "open"},
            timeout=30,
        )
        resp.raise_for_status()
        orders = []
        for raw in resp.json().get("orders", []):
            orders.append(
                Order(
                    id=str(raw["id"]),
                    order_number=str(raw["order_number"]),
                    line_items=[
                        {"sku": li.get("sku"), "quantity": li["quantity"], "title": li["title"]}
                        for li in raw["line_items"]
                    ],
                    shipping_address=raw.get("shipping_address") or {},
                    customer_email=raw.get("email") or "",
                )
            )
        return orders

    def mark_fulfilled(self, order_id: str, tracking_number: str, tracking_url: str, carrier: str) -> None:
        resp = self.session.post(
            f"{self.base_url}/orders/{order_id}/fulfillments.json",
            json={
                "fulfillment": {
                    "tracking_number": tracking_number,
                    "tracking_urls": [tracking_url] if tracking_url else [],
                    "tracking_company": carrier,
                    "notify_customer": True,
                }
            },
            timeout=30,
        )
        resp.raise_for_status()

    def upsert_product(self, sku: str, title: str, description: str, price: float, images: list, quantity: int) -> str:
        mapping = self._load_product_map()
        entry = mapping.get(sku)

        if entry is None:
            resp = self.session.post(
                f"{self.base_url}/products.json",
                json={
                    "product": {
                        "title": title,
                        "body_html": description,
                        "images": [{"src": url} for url in images],
                        "variants": [{"sku": sku, "price": f"{price:.2f}", "inventory_management": "shopify"}],
                    }
                },
                timeout=30,
            )
            resp.raise_for_status()
            product = resp.json()["product"]
            variant = product["variants"][0]
            entry = {
                "product_id": str(product["id"]),
                "variant_id": str(variant["id"]),
                "inventory_item_id": str(variant["inventory_item_id"]),
            }
            mapping[sku] = entry
            self._save_product_map(mapping)
        else:
            resp = self.session.put(
                f"{self.base_url}/products/{entry['product_id']}.json",
                json={
                    "product": {
                        "id": int(entry["product_id"]),
                        "title": title,
                        "body_html": description,
                        "variants": [{"id": int(entry["variant_id"]), "price": f"{price:.2f}"}],
                    }
                },
                timeout=30,
            )
            resp.raise_for_status()

        self._set_inventory_item(entry["inventory_item_id"], quantity)
        return entry["product_id"]

    def _set_inventory_item(self, inventory_item_id: str, quantity: int) -> None:
        resp = self.session.post(
            f"{self.base_url}/inventory_levels/set.json",
            json={
                "location_id": self._primary_location_id(),
                "inventory_item_id": inventory_item_id,
                "available": quantity,
            },
            timeout=30,
        )
        resp.raise_for_status()

    def sync_inventory(self, sku: str, quantity: int) -> None:
        entry = self._load_product_map().get(sku)
        if not entry:
            raise ValueError(f"No known Shopify product for SKU '{sku}' -- run product sync (upsert_product) first")
        self._set_inventory_item(entry["inventory_item_id"], quantity)
