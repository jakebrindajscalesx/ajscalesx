import logging
from dataclasses import dataclass, field

from .platforms.base import StorePlatform
from .suppliers.base import SupplierAdapter

logger = logging.getLogger(__name__)


@dataclass
class CycleResult:
    store_id: str
    orders_seen: int
    orders_fulfilled: int
    errors: list = field(default_factory=list)


class StoreBot:
    """One bot, permanently assigned to one store.

    A cycle is the whole job a human store manager does for order
    fulfillment: look for new orders, place them with the supplier, and
    write tracking back to the store once it's available.
    """

    def __init__(self, store_id: str, platform: StorePlatform, supplier: SupplierAdapter):
        self.store_id = store_id
        self.platform = platform
        self.supplier = supplier

    def run_cycle(self) -> CycleResult:
        errors = []
        fulfilled = 0
        orders = self.platform.get_unfulfilled_orders()

        for order in orders:
            try:
                result = self.supplier.place_order(order)
                if result.tracking_number:
                    self.platform.mark_fulfilled(order.id, result.tracking_number, result.tracking_url, result.carrier)
                    fulfilled += 1
                    logger.info(
                        "[%s] order %s fulfilled via %s (tracking %s)",
                        self.store_id, order.order_number, self.supplier.__class__.__name__, result.tracking_number,
                    )
                else:
                    logger.info(
                        "[%s] order %s placed with supplier, tracking pending (supplier order %s)",
                        self.store_id, order.order_number, result.supplier_order_id,
                    )
            except Exception as exc:
                errors.append(f"order {order.order_number}: {exc}")
                logger.exception("[%s] order %s failed", self.store_id, order.order_number)

        return CycleResult(store_id=self.store_id, orders_seen=len(orders), orders_fulfilled=fulfilled, errors=errors)
