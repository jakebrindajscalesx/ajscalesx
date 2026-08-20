from .base import Order, StorePlatform

_DEMO_ORDERS = [
    Order(
        id="1001",
        order_number="#1001",
        line_items=[{"sku": "WIDGET-BLU", "quantity": 2, "title": "Blue Widget"}],
        shipping_address={"city": "Austin", "province": "TX"},
        customer_email="buyer1@example.com",
    ),
    Order(
        id="1002",
        order_number="#1002",
        line_items=[{"sku": "WIDGET-RED", "quantity": 1, "title": "Red Widget"}],
        shipping_address={"city": "Reno", "province": "NV"},
        customer_email="buyer2@example.com",
    ),
]


class MockStore(StorePlatform):
    """Fake storefront for local demos and tests -- no store credentials needed."""

    def __init__(self, seed_orders=None):
        self._orders = seed_orders if seed_orders is not None else list(_DEMO_ORDERS)
        self._fulfilled = {}
        self._products = {}

    def get_unfulfilled_orders(self) -> list[Order]:
        return [o for o in self._orders if o.id not in self._fulfilled]

    def mark_fulfilled(self, order_id: str, tracking_number: str, tracking_url: str, carrier: str) -> None:
        self._fulfilled[order_id] = (tracking_number, tracking_url, carrier)

    def upsert_product(self, sku: str, title: str, description: str, price: float, images: list, quantity: int) -> str:
        self._products[sku] = {
            "title": title,
            "description": description,
            "price": price,
            "images": images,
            "quantity": quantity,
        }
        return sku

    def sync_inventory(self, sku: str, quantity: int) -> None:
        if sku in self._products:
            self._products[sku]["quantity"] = quantity
