import requests

from .base import Order, StorePlatform


class ShopifyStore(StorePlatform):
    """Drives one Shopify store via a custom-app Admin API token.

    See the top-level README for how to generate `access_token` from
    Shopify's Settings -> Apps -> Develop apps.
    """

    def __init__(self, shop_domain: str, access_token: str, api_version: str = "2024-10"):
        self.base_url = f"https://{shop_domain}/admin/api/{api_version}"
        self.session = requests.Session()
        self.session.headers.update(
            {
                "X-Shopify-Access-Token": access_token,
                "Content-Type": "application/json",
            }
        )

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

    def sync_inventory(self, sku: str, quantity: int) -> None:
        # Shopify has no "set by SKU" endpoint: it needs the inventory_item_id
        # (via /variants.json or /inventory_items.json lookup) and a
        # location_id before POSTing inventory_levels/set.json. Wire this up
        # once a real store + supplier stock feed are connected.
        raise NotImplementedError("sync_inventory needs an inventory_item_id/location_id lookup for this store")
