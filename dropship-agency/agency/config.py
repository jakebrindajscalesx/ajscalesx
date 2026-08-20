import os
from dataclasses import dataclass
from pathlib import Path

import yaml

from .pricing import PricingRule
from .platforms.base import StorePlatform
from .platforms.mock import MockStore
from .platforms.shopify import ShopifyStore
from .suppliers.base import SupplierAdapter
from .suppliers.cj_dropshipping import CJDropshippingSupplier
from .suppliers.mock_supplier import MockSupplier


def _env(name: str) -> str:
    value = os.environ.get(name)
    if not value:
        raise RuntimeError(f"Missing required env var: {name}")
    return value


PLATFORM_BUILDERS = {
    "mock": lambda cfg, store_id, state_dir: MockStore(),
    "shopify": lambda cfg, store_id, state_dir: ShopifyStore(
        shop_domain=cfg["shop_domain"],
        access_token=_env(cfg["access_token_env"]),
        state_path=state_dir / f"{store_id}_shopify_products.json",
    ),
}

SUPPLIER_BUILDERS = {
    "mock": lambda cfg: MockSupplier(),
    "cj": lambda cfg: CJDropshippingSupplier(
        email=_env(cfg["email_env"]),
        api_key=_env(cfg["api_key_env"]),
    ),
}


@dataclass
class StoreConfig:
    store_id: str
    platform: StorePlatform
    supplier: SupplierAdapter
    pricing: PricingRule


def load_registry(path: str, state_dir: Path) -> list[StoreConfig]:
    """Load the store -> bot assignment registry.

    The file only ever holds env var *names*, never secrets themselves --
    credentials come from the environment (repo secrets in CI, a local
    .env otherwise).
    """
    with open(path) as f:
        raw = yaml.safe_load(f)

    stores = []
    for entry in raw["stores"]:
        store_id = entry["id"]
        platform_cfg = entry["platform"]
        supplier_cfg = entry["supplier"]
        pricing_cfg = entry.get("pricing", {})

        try:
            platform_builder = PLATFORM_BUILDERS[platform_cfg["type"]]
        except KeyError:
            raise ValueError(f"Unknown platform type '{platform_cfg['type']}' for store '{store_id}'")
        try:
            supplier_builder = SUPPLIER_BUILDERS[supplier_cfg["type"]]
        except KeyError:
            raise ValueError(f"Unknown supplier type '{supplier_cfg['type']}' for store '{store_id}'")

        stores.append(
            StoreConfig(
                store_id=store_id,
                platform=platform_builder(platform_cfg, store_id, state_dir),
                supplier=supplier_builder(supplier_cfg),
                pricing=PricingRule(
                    multiplier=pricing_cfg.get("multiplier", 2.5),
                    flat_fee=pricing_cfg.get("flat_fee", 0.0),
                ),
            )
        )
    return stores
