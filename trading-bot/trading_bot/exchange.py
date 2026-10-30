from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone

import pandas as pd
from alpaca.data.enums import DataFeed
from alpaca.data.historical import StockHistoricalDataClient
from alpaca.data.requests import StockBarsRequest, StockLatestTradeRequest
from alpaca.data.timeframe import TimeFrame, TimeFrameUnit
from alpaca.trading.client import TradingClient

from trading_bot.config import Config
from trading_bot.logger import get_logger

log = get_logger(__name__)

# Alpaca's free data plan serves the IEX feed (one US exchange's trades/
# quotes, not the full consolidated SIP tape covering every exchange) --
# fine for this bot's purposes and avoids the SIP feed's paid subscription
# requirement.
DATA_FEED = DataFeed.IEX

_TIMEFRAME_PATTERN = re.compile(r"^(\d+)([mhd])$")
_TIMEFRAME_UNITS = {"m": TimeFrameUnit.Minute, "h": TimeFrameUnit.Hour, "d": TimeFrameUnit.Day}


def parse_timeframe(timeframe: str) -> TimeFrame:
    """Parses a "15m"/"1h"/"1d"-style config string into an Alpaca TimeFrame."""
    match = _TIMEFRAME_PATTERN.match(timeframe.strip().lower())
    if not match:
        raise ValueError(f"Unrecognized timeframe {timeframe!r}, expected e.g. '15m', '1h', '1d'")
    amount, unit = match.groups()
    return TimeFrame(int(amount), _TIMEFRAME_UNITS[unit])


@dataclass
class AlpacaClients:
    """Bundles the two Alpaca clients the bot needs: trading (orders,
    account, market clock) and historical market data. Both point at the
    same paper/live environment."""

    trading: TradingClient
    data: StockHistoricalDataClient


def build_exchange(config: Config) -> AlpacaClients:
    """Builds the Alpaca clients for the configured mode.

    Unlike Kraken, Alpaca requires an API key/secret for market data in
    both paper and live mode -- config.py already refuses to load without
    them. mode: paper uses Alpaca's own free paper-trading environment
    (fake money, real simulated order lifecycle, same order-placement code
    path as live); mode: live places real orders with real money.
    """
    trading = TradingClient(
        api_key=config.exchange.api_key,
        secret_key=config.exchange.api_secret,
        paper=not config.is_live,
    )
    data = StockHistoricalDataClient(
        api_key=config.exchange.api_key,
        secret_key=config.exchange.api_secret,
    )
    if config.is_live:
        log.warning("Exchange client in LIVE mode with REAL FUNDS.")
    else:
        log.info("Exchange client in Alpaca PAPER mode: simulated fills, fake money.")
    return AlpacaClients(trading=trading, data=data)


def is_market_open(client: AlpacaClients) -> bool:
    """Stocks only trade during NYSE hours on weekdays (unlike crypto's
    24/7 market) -- callers should skip fetching/trading entirely when
    this is False rather than act on stale or nonexistent data."""
    return bool(client.trading.get_clock().is_open)


# Trading-hours-per-day estimates used only to size a generous lookback
# window -- overestimating just means the request's `limit` still caps the
# result, underestimating would mean too few bars come back.
_TRADING_MINUTES_PER_DAY = 390  # 6.5 hours, NYSE regular session
_CALENDAR_DAYS_PER_TRADING_DAY = 7 / 5  # padding for weekends
_LOOKBACK_SAFETY_MULTIPLIER = 1.5  # extra padding for holidays/early closes
_MIN_LOOKBACK_DAYS = 10


def _lookback_start(tf: TimeFrame, limit: int) -> datetime:
    """Alpaca's bars endpoint expects an explicit start (or returns no bars
    at all if start/end are both omitted and only `limit` is given, even
    though the SDK's request model doesn't require start) -- so this always
    computes one generously rather than relying on limit alone."""
    if tf.unit == TimeFrameUnit.Day:
        calendar_days = limit * _CALENDAR_DAYS_PER_TRADING_DAY * _LOOKBACK_SAFETY_MULTIPLIER
    else:
        minutes_per_bar = tf.amount * (60 if tf.unit == TimeFrameUnit.Hour else 1)
        trading_days_needed = (limit * minutes_per_bar) / _TRADING_MINUTES_PER_DAY
        calendar_days = trading_days_needed * _CALENDAR_DAYS_PER_TRADING_DAY * _LOOKBACK_SAFETY_MULTIPLIER
    calendar_days = max(calendar_days, _MIN_LOOKBACK_DAYS)
    return datetime.now(timezone.utc) - timedelta(days=calendar_days)


def fetch_ohlcv_df(client: AlpacaClients, symbol: str, timeframe: str, limit: int) -> pd.DataFrame:
    tf = parse_timeframe(timeframe)
    request = StockBarsRequest(
        symbol_or_symbols=symbol,
        timeframe=tf,
        start=_lookback_start(tf, limit),
        limit=limit,
        feed=DATA_FEED,
    )
    bars = client.data.get_stock_bars(request)
    df = bars.df
    if df.empty:
        return pd.DataFrame(columns=["open", "high", "low", "close", "volume"])
    df = df.xs(symbol, level="symbol")
    df.index.name = "timestamp"
    return df[["open", "high", "low", "close", "volume"]]


def fetch_last_price(client: AlpacaClients, symbol: str) -> float:
    request = StockLatestTradeRequest(symbol_or_symbols=symbol, feed=DATA_FEED)
    trades = client.data.get_stock_latest_trade(request)
    return float(trades[symbol].price)


def fetch_account_cash(client: AlpacaClients) -> float:
    """Used to seed the local Portfolio ledger's starting cash the very
    first time the bot runs in live mode, from Alpaca's real account
    balance. Every later run loads persisted state instead -- this only
    matters once, before state/portfolio.json exists."""
    return float(client.trading.get_account().cash)
