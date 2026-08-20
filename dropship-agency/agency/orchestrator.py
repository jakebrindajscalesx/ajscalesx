import json
import logging
from datetime import datetime, timezone
from pathlib import Path

from .bot import StoreBot
from .config import load_registry
from .product_bot import ProductSyncBot

logger = logging.getLogger(__name__)

ROOT_DIR = Path(__file__).resolve().parent.parent
STATE_DIR = ROOT_DIR / "state"
DOCS_DIR = ROOT_DIR / "docs"


def run_all(config_path: str) -> list[dict]:
    """Run one fulfillment cycle for every store in the registry, one bot each.

    Stores are independent: one bot's failure is recorded in its own
    result and never stops the others from running.
    """
    STATE_DIR.mkdir(exist_ok=True)
    stores = load_registry(config_path, STATE_DIR)

    summary = []
    for store in stores:
        bot = StoreBot(store.store_id, store.platform, store.supplier, STATE_DIR)
        result = bot.run_cycle()
        summary.append(
            {
                "store_id": result.store_id,
                "orders_seen": result.orders_seen,
                "orders_fulfilled": result.orders_fulfilled,
                "errors": result.errors,
                "ran_at": datetime.now(timezone.utc).isoformat(),
            }
        )

    (STATE_DIR / "last_run.json").write_text(json.dumps(summary, indent=2))
    _publish_dashboard_data(summary)
    return summary


def sync_all_products(config_path: str) -> list[dict]:
    """Pull every store's supplier catalog into its storefront, priced with markup."""
    STATE_DIR.mkdir(exist_ok=True)
    stores = load_registry(config_path, STATE_DIR)

    summary = []
    for store in stores:
        bot = ProductSyncBot(store.store_id, store.platform, store.supplier, store.pricing)
        result = bot.run_cycle()
        summary.append(
            {
                "store_id": result.store_id,
                "products_seen": result.products_seen,
                "products_synced": result.products_synced,
                "errors": result.errors,
                "ran_at": datetime.now(timezone.utc).isoformat(),
            }
        )

    (STATE_DIR / "last_product_sync.json").write_text(json.dumps(summary, indent=2))
    return summary


def _publish_dashboard_data(summary: list[dict]) -> None:
    DOCS_DIR.mkdir(exist_ok=True)
    (DOCS_DIR / "data.json").write_text(json.dumps(summary, indent=2))
