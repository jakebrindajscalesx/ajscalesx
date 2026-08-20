import logging
from dataclasses import dataclass, field

from .pricing import PricingRule
from .platforms.base import StorePlatform
from .suppliers.base import SupplierAdapter

logger = logging.getLogger(__name__)


@dataclass
class ProductSyncResult:
    store_id: str
    products_seen: int
    products_synced: int
    errors: list = field(default_factory=list)


class ProductSyncBot:
    """Pulls a store's assigned supplier catalog into the storefront.

    Runs on its own, slower cadence than order fulfillment -- a catalog
    doesn't change every 15 minutes the way orders come in.
    """

    def __init__(self, store_id: str, platform: StorePlatform, supplier: SupplierAdapter, pricing: PricingRule):
        self.store_id = store_id
        self.platform = platform
        self.supplier = supplier
        self.pricing = pricing

    def run_cycle(self) -> ProductSyncResult:
        errors = []
        synced = 0
        products = self.supplier.list_products()

        for product in products:
            try:
                price = self.pricing.retail_price(product.cost)
                self.platform.upsert_product(
                    sku=product.sku,
                    title=product.title,
                    description=product.description,
                    price=price,
                    images=product.images,
                    quantity=product.stock,
                )
                synced += 1
                logger.info(
                    "[%s] synced %s: cost $%.2f -> price $%.2f (stock %d)",
                    self.store_id, product.sku, product.cost, price, product.stock,
                )
            except Exception as exc:
                errors.append(f"product {product.sku}: {exc}")
                logger.exception("[%s] product %s failed", self.store_id, product.sku)

        return ProductSyncResult(store_id=self.store_id, products_seen=len(products), products_synced=synced, errors=errors)
