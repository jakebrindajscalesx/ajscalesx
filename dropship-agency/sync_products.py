#!/usr/bin/env python3
"""Pull every store's supplier catalog into its storefront, priced with markup.

Usage: python sync_products.py [--config config.yaml]
"""
import argparse
import logging
import sys

from agency.orchestrator import sync_all_products


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", default="config.example.yaml", help="Path to the store registry YAML")
    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")

    summary = sync_all_products(args.config)

    for row in summary:
        status = "errors" if row["errors"] else "ok"
        print(f"{row['store_id']}: {row['products_synced']}/{row['products_seen']} synced [{status}]")
        for err in row["errors"]:
            print(f"  ! {err}")

    return 1 if any(row["errors"] for row in summary) else 0


if __name__ == "__main__":
    sys.exit(main())
