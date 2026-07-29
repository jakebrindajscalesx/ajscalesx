import os
from dataclasses import dataclass

import yaml

from .platforms.base import StorePlatform
from .platforms.mock import MockStore
from .platforms.shopify import ShopifyStore
from .suppliers.base import SupplierAdapter
from .suppliers.mock_supplier import MockSupplier


def _env(name: str) -> str:
    value = os.environ.get(name)
    if not value:
        raise RuntimeError(f"Missing required env var: {name}")
    return value


PLATFORM_BUILDERS = {
    "mock": lambda cfg: MockStore(),
    "shopify": lambda cfg: ShopifyStore(
        shop_domain=cfg["shop_domain"],
        access_token=_env(cfg["access_token_env"]),
    ),
}

SUPPLIER_BUILDERS = {
    "mock": lambda cfg: MockSupplier(),
}


@dataclass
class StoreConfig:
    store_id: str
    platform: StorePlatform
    supplier: SupplierAdapter


def load_registry(path: str) -> list[StoreConfig]:
    """Load the store -> bot assignment registry.

    The file only ever holds env var *names*, never secrets themselves --
    credentials come from the environment (repo secrets in CI, a local
    .env otherwise).
    """
    with open(path) as f:
        raw = yaml.safe_load(f)

    stores = []
    for entry in raw["stores"]:
        platform_cfg = entry["platform"]
        supplier_cfg = entry["supplier"]

        try:
            platform_builder = PLATFORM_BUILDERS[platform_cfg["type"]]
        except KeyError:
            raise ValueError(f"Unknown platform type '{platform_cfg['type']}' for store '{entry['id']}'")
        try:
            supplier_builder = SUPPLIER_BUILDERS[supplier_cfg["type"]]
        except KeyError:
            raise ValueError(f"Unknown supplier type '{supplier_cfg['type']}' for store '{entry['id']}'")

        stores.append(
            StoreConfig(
                store_id=entry["id"],
                platform=platform_builder(platform_cfg),
                supplier=supplier_builder(supplier_cfg),
            )
        )
    return stores
