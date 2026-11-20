"""Offline script: fetch historical candles and train the signal model.

Run this before starting the bot for the first time, and periodically
(e.g. weekly) to retrain on fresh data:

    python train_model.py

Needs Alpaca API keys in .env (EXCHANGE_API_KEY/EXCHANGE_API_SECRET) --
unlike Kraken, Alpaca requires a key/secret for market data regardless of
paper/live mode.
"""
from __future__ import annotations

import sys

import pandas as pd

from trading_bot.config import load_config
from trading_bot.exchange import AlpacaClients, build_exchange, fetch_ohlcv_df
from trading_bot.logger import get_logger
from trading_bot.model import save_model, train_model

log = get_logger("train_model")

TRAIN_CANDLES = 5000  # candles to gather per symbol


def fetch_history(client: AlpacaClients, symbol: str, timeframe: str, total_candles: int) -> pd.DataFrame:
    """Thin wrapper so callers don't need to know it's really just a bigger
    fetch_ohlcv_df call -- alpaca-py paginates internally up to `limit`,
    unlike ccxt where this used to hand-roll pagination in batches of 1000."""
    return fetch_ohlcv_df(client, symbol, timeframe, total_candles)


def main() -> int:
    config = load_config()
    client = build_exchange(config)

    for symbol in config.symbols:
        log.info(f"Fetching history for {symbol}...")
        df = fetch_history(client, symbol, config.timeframe, TRAIN_CANDLES)
        log.info(f"Got {len(df)} candles for {symbol}.")

        try:
            clf, metrics = train_model(
                df, config.model.horizon_candles, config.model.label_return_threshold
            )
        except ValueError as exc:
            log.error(f"Skipping {symbol}: {exc}")
            continue

        model_path = config.model.path
        save_model(clf, model_path)
        log.info(f"Saved model for {symbol} to {model_path}: {metrics}")
        # Note: this saves one model shared across all configured symbols.
        # For meaningfully different markets, run with one symbol in
        # config.yaml at a time and use separate model paths.

    return 0


if __name__ == "__main__":
    sys.exit(main())
