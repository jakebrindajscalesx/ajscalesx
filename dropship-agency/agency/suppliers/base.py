from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Optional


@dataclass
class SupplierOrderResult:
    supplier_order_id: str
    tracking_number: Optional[str]
    tracking_url: Optional[str]
    carrier: Optional[str]


@dataclass
class SupplierProduct:
    """One product from a supplier's catalog, before markup is applied."""

    supplier_product_id: str
    sku: str
    title: str
    description: str
    cost: float
    stock: int
    images: list = field(default_factory=list)


class SupplierAdapter(ABC):
    """What a bot needs from the fulfillment supplier behind a store.

    Implement this once per supplier (CJ Dropshipping, Spocket, AliExpress,
    a private warehouse API, ...) and any bot can place orders through it.
    """

    @abstractmethod
    def list_products(self) -> list:
        """The supplier's catalog, for pulling products into a storefront."""
        ...

    @abstractmethod
    def place_order(self, order) -> SupplierOrderResult:
        ...

    @abstractmethod
    def get_tracking(self, supplier_order_id: str) -> SupplierOrderResult:
        """Poll for tracking when a supplier doesn't return it at order time."""
        ...
