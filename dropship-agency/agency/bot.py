import json
import logging
from dataclasses import dataclass, field
from pathlib import Path

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

    A cycle does the whole job a human store manager does for order
    fulfillment: place new orders with the supplier, and check back on
    ones already placed until the supplier hands back tracking. Some
    suppliers (the mock, some APIs) return tracking immediately; others
    only assign it after warehouse processing, so orders stay "pending"
    across cycles until `get_tracking` finds one.
    """

    def __init__(self, store_id: str, platform: StorePlatform, supplier: SupplierAdapter, state_dir: Path):
        self.store_id = store_id
        self.platform = platform
        self.supplier = supplier
        self._pending_path = state_dir / f"{store_id}_pending_orders.json"

    def _load_pending(self) -> dict:
        if self._pending_path.exists():
            return json.loads(self._pending_path.read_text())
        return {}

    def _save_pending(self, pending: dict) -> None:
        self._pending_path.parent.mkdir(parents=True, exist_ok=True)
        self._pending_path.write_text(json.dumps(pending, indent=2))

    def run_cycle(self) -> CycleResult:
        errors = []
        fulfilled = 0
        pending = self._load_pending()
        orders = self.platform.get_unfulfilled_orders()
        seen_ids = {order.id for order in orders}

        # Drop pending entries for orders the store no longer lists as
        # unfulfilled (already handled another way, cancelled, ...) so we
        # don't poll a supplier order forever.
        pending = {order_id: supplier_order_id for order_id, supplier_order_id in pending.items() if order_id in seen_ids}

        for order in orders:
            try:
                if order.id in pending:
                    result = self.supplier.get_tracking(pending[order.id])
                else:
                    result = self.supplier.place_order(order)
                    pending[order.id] = result.supplier_order_id

                if result.tracking_number:
                    self.platform.mark_fulfilled(order.id, result.tracking_number, result.tracking_url, result.carrier)
                    fulfilled += 1
                    pending.pop(order.id, None)
                    logger.info(
                        "[%s] order %s fulfilled via %s (tracking %s)",
                        self.store_id, order.order_number, self.supplier.__class__.__name__, result.tracking_number,
                    )
                else:
                    logger.info(
                        "[%s] order %s awaiting tracking from supplier (supplier order %s)",
                        self.store_id, order.order_number, result.supplier_order_id,
                    )
            except Exception as exc:
                errors.append(f"order {order.order_number}: {exc}")
                logger.exception("[%s] order %s failed", self.store_id, order.order_number)

        self._save_pending(pending)
        return CycleResult(store_id=self.store_id, orders_seen=len(orders), orders_fulfilled=fulfilled, errors=errors)
