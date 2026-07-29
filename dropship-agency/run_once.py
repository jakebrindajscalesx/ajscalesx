#!/usr/bin/env python3
"""Run one orchestration cycle across every store in the registry.

Usage: python run_once.py [--config config.yaml]
"""
import argparse
import logging
import sys

from agency.orchestrator import run_all


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", default="config.example.yaml", help="Path to the store registry YAML")
    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")

    summary = run_all(args.config)

    for row in summary:
        status = "errors" if row["errors"] else "ok"
        print(f"{row['store_id']}: {row['orders_fulfilled']}/{row['orders_seen']} fulfilled [{status}]")
        for err in row["errors"]:
            print(f"  ! {err}")

    return 1 if any(row["errors"] for row in summary) else 0


if __name__ == "__main__":
    sys.exit(main())
