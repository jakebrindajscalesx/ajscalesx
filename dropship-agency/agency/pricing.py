from dataclasses import dataclass


@dataclass
class PricingRule:
    """Turns a supplier's cost into what the storefront charges.

    retail = cost * multiplier + flat_fee. Defaults to a 2.5x markup,
    which is a common dropshipping starting point -- tune per store once
    you know real shipping cost and ad spend.
    """

    multiplier: float = 2.5
    flat_fee: float = 0.0

    def retail_price(self, cost: float) -> float:
        return round(cost * self.multiplier + self.flat_fee, 2)
