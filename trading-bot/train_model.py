"""Offline script: fetch historical candles and train the signal model.

Run this before starting the bot for the first time, and periodically
(e.g. weekly) to retrain on fresh data:

    python train_model.py

Uses only public market data endpoints -- no API keys needed even for
Binance, regardless of paper/live mode.
"""
from __future__ import annotations

import sys

import pandas as pd

from trading_bot.config import load_config
from trading_bot.exchange import build_exchange
from trading_bot.logger import get_logger
from trading_bot.model import save_model, train_model

log = get_logger("train_model")

TRAIN_CANDLES = 5000  # paginate to gather this many candles per symbol


def fetch_history(client, symbol: str, timeframe: str, total_candles: int) -> pd.DataFrame:
    all_rows: list[list] = []
    since = None
    remaining = total_candles
    while remaining > 0:
        batch_limit = min(1000, remaining)
        batch = client.fetch_ohlcv(symbol, timeframe=timeframe, since=since, limit=batch_limit)
        if not batch:
            break
        all_rows = batch + all_rows
        oldest_ts = batch[0][0]
        since = oldest_ts - (batch_limit * client.parse_timeframe(timeframe) * 1000)
        remaining -= len(batch)
        if len(batch) < batch_limit:
            break

    df = pd.DataFrame(all_rows, columns=["timestamp", "open", "high", "low", "close", "volume"])
    df = df.drop_duplicates(subset="timestamp").sort_values("timestamp")
    df["timestamp"] = pd.to_datetime(df["timestamp"], unit="ms")
    df.set_index("timestamp", inplace=True)
    return df


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
