import itertools
import random

from .base import SupplierAdapter, SupplierOrderResult

_counter = itertools.count(1)


class MockSupplier(SupplierAdapter):
    """Fake supplier for local demos and tests.

    Returns a tracking number immediately, standing in for a real supplier
    API (CJ Dropshipping, Spocket, AliExpress) until one is connected. Real
    suppliers often need `get_tracking` polled after the fact instead.
    """

    def place_order(self, order) -> SupplierOrderResult:
        supplier_order_id = f"MOCK-{next(_counter):05d}"
        tracking_number = f"TRK{random.randint(10 ** 8, 10 ** 9 - 1)}"
        return SupplierOrderResult(
            supplier_order_id=supplier_order_id,
            tracking_number=tracking_number,
            tracking_url=f"https://track.example.com/{tracking_number}",
            carrier="MockShip",
        )

    def get_tracking(self, supplier_order_id: str) -> SupplierOrderResult:
        raise NotImplementedError("MockSupplier resolves tracking synchronously in place_order")
