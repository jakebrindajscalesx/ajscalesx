from __future__ import annotations

import ccxt
import pandas as pd

from trading_bot.config import Config
from trading_bot.logger import get_logger

log = get_logger(__name__)


def build_exchange(config: Config) -> ccxt.Exchange:
    """Build a ccxt exchange client.

    Market data (OHLCV, ticker prices) works without API keys regardless of
    mode. API keys are only required, and only used, for order placement in
    live mode.
    """
    exchange_class = getattr(ccxt, config.exchange.name)
    client = exchange_class(
        {
            "apiKey": config.exchange.api_key or None,
            "secret": config.exchange.api_secret or None,
            "enableRateLimit": True,
        }
    )
    if config.is_live and config.exchange.testnet:
        client.set_sandbox_mode(True)
        log.info("Exchange client in TESTNET mode (sandbox trading, fake funds).")
    elif config.is_live:
        log.warning("Exchange client in LIVE mode with REAL FUNDS.")
    else:
        log.info("Exchange client in paper mode: live market data, simulated orders.")
    return client


def fetch_ohlcv_df(client: ccxt.Exchange, symbol: str, timeframe: str, limit: int) -> pd.DataFrame:
    raw = client.fetch_ohlcv(symbol, timeframe=timeframe, limit=limit)
    df = pd.DataFrame(raw, columns=["timestamp", "open", "high", "low", "close", "volume"])
    df["timestamp"] = pd.to_datetime(df["timestamp"], unit="ms")
    df.set_index("timestamp", inplace=True)
    return df


def fetch_last_price(client: ccxt.Exchange, symbol: str) -> float:
    ticker = client.fetch_ticker(symbol)
    return float(ticker["last"])
