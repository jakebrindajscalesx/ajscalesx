from abc import ABC, abstractmethod
from dataclasses import dataclass, field


@dataclass
class Order:
    """A single unfulfilled order pulled from a storefront."""

    id: str
    order_number: str
    line_items: list = field(default_factory=list)  # [{"sku", "quantity", "title"}]
    shipping_address: dict = field(default_factory=dict)
    customer_email: str = ""


class StorePlatform(ABC):
    """What a bot needs from the storefront it's assigned to.

    Implement this once per e-commerce platform (Shopify, WooCommerce,
    BigCommerce, ...) and every bot can drive any store on that platform.
    """

    @abstractmethod
    def get_unfulfilled_orders(self) -> list[Order]:
        ...

    @abstractmethod
    def mark_fulfilled(self, order_id: str, tracking_number: str, tracking_url: str, carrier: str) -> None:
        ...

    @abstractmethod
    def upsert_product(self, sku: str, title: str, description: str, price: float, images: list, quantity: int) -> str:
        """Create the product if it's new, update it if a bot already synced this SKU. Returns the platform's product id."""
        ...

    @abstractmethod
    def sync_inventory(self, sku: str, quantity: int) -> None:
        ...
