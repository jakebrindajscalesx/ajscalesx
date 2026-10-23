from datetime import datetime, timezone

import pandas as pd
import pytest

from trading_bot.exchange import (
    AlpacaClients,
    fetch_account_cash,
    fetch_last_price,
    fetch_ohlcv_df,
    is_market_open,
    parse_timeframe,
)


@pytest.mark.parametrize(
    "text,expected_str",
    [("15m", "15Min"), ("1h", "1Hour"), ("1d", "1Day"), ("5m", "5Min")],
)
def test_parse_timeframe_accepts_expected_formats(text, expected_str):
    assert str(parse_timeframe(text)) == expected_str


def test_parse_timeframe_rejects_unrecognized_string():
    with pytest.raises(ValueError):
        parse_timeframe("weekly")


class _FakeBarSet:
    def __init__(self, df):
        self.df = df


class _FakeDataClient:
    def __init__(self, bars_df=None, latest_trade_price=None):
        self._bars_df = bars_df
        self._latest_trade_price = latest_trade_price
        self.last_bars_request = None
        self.last_trade_request = None

    def get_stock_bars(self, request_params):
        self.last_bars_request = request_params
        return _FakeBarSet(self._bars_df)

    def get_stock_latest_trade(self, request_params):
        self.last_trade_request = request_params

        class _FakeTrade:
            def __init__(self, price):
                self.price = price

        symbol = request_params.symbol_or_symbols
        return {symbol: _FakeTrade(self._latest_trade_price)}


class _FakeClock:
    def __init__(self, is_open):
        self.is_open = is_open


class _FakeAccount:
    def __init__(self, cash):
        self.cash = cash


class _FakeTradingClient:
    def __init__(self, market_open=True, cash=1000.0):
        self._market_open = market_open
        self._cash = cash

    def get_clock(self):
        return _FakeClock(self._market_open)

    def get_account(self):
        return _FakeAccount(self._cash)


def _multi_index_bars_df(symbol):
    idx = pd.MultiIndex.from_tuples(
        [
            (symbol, pd.Timestamp("2026-01-01T09:30", tz="UTC")),
            (symbol, pd.Timestamp("2026-01-01T09:45", tz="UTC")),
        ],
        names=["symbol", "timestamp"],
    )
    return pd.DataFrame(
        {
            "open": [500.0, 501.0],
            "high": [502.0, 503.0],
            "low": [499.0, 500.0],
            "close": [501.0, 502.0],
            "volume": [1000, 1200],
            "trade_count": [10, 12],
            "vwap": [500.5, 501.5],
        },
        index=idx,
    )


def test_fetch_ohlcv_df_reshapes_alpaca_multiindex_bars_to_single_symbol_frame():
    clients = AlpacaClients(
        trading=_FakeTradingClient(),
        data=_FakeDataClient(bars_df=_multi_index_bars_df("SPY")),
    )
    df = fetch_ohlcv_df(clients, "SPY", "15m", 500)
    assert list(df.columns) == ["open", "high", "low", "close", "volume"]
    assert len(df) == 2
    assert df.index.name == "timestamp"
    assert df["close"].iloc[-1] == 502.0


def test_fetch_ohlcv_df_returns_empty_frame_with_expected_columns_when_no_bars():
    clients = AlpacaClients(
        trading=_FakeTradingClient(),
        data=_FakeDataClient(bars_df=pd.DataFrame()),
    )
    df = fetch_ohlcv_df(clients, "SPY", "15m", 500)
    assert list(df.columns) == ["open", "high", "low", "close", "volume"]
    assert len(df) == 0


def test_fetch_ohlcv_df_always_sends_an_explicit_start():
    # Regression test: Alpaca's bars endpoint returned zero bars in
    # practice when start/end were both omitted and only `limit` was set,
    # even though nothing in the SDK's request model requires start. Every
    # request must carry an explicit start from here on.
    data_client = _FakeDataClient(bars_df=_multi_index_bars_df("SPY"))
    clients = AlpacaClients(trading=_FakeTradingClient(), data=data_client)

    fetch_ohlcv_df(clients, "SPY", "15m", 500)

    # StockBarsRequest normalizes start to a naive UTC datetime internally
    # (confirmed its to_request_fields() still serializes the timezone
    # offset correctly for the actual outgoing request) -- compare against
    # a naive "now" here to match.
    assert data_client.last_bars_request.start is not None
    assert data_client.last_bars_request.start < datetime.now(timezone.utc).replace(tzinfo=None)


@pytest.mark.parametrize(
    "timeframe,limit",
    [("15m", 500), ("15m", 2000), ("1h", 500), ("1d", 200)],
)
def test_lookback_start_is_generously_in_the_past_and_covers_the_requested_limit(timeframe, limit):
    from alpaca.data.timeframe import TimeFrameUnit

    from trading_bot.exchange import _lookback_start, parse_timeframe

    tf = parse_timeframe(timeframe)
    start = _lookback_start(tf, limit)
    now = datetime.now(timezone.utc)
    assert start < now

    # At minimum, the naive number of calendar minutes implied by
    # limit * timeframe should fit within the computed window (sanity
    # floor -- the real computation pads well beyond this for
    # weekends/holidays).
    if tf.unit != TimeFrameUnit.Day:
        unit_minutes = 60 if tf.unit == TimeFrameUnit.Hour else 1
        naive_minutes_needed = tf.amount * unit_minutes * limit
        assert (now - start).total_seconds() / 60 >= naive_minutes_needed


def test_fetch_last_price_returns_float_from_latest_trade():
    clients = AlpacaClients(
        trading=_FakeTradingClient(),
        data=_FakeDataClient(latest_trade_price=123.45),
    )
    assert fetch_last_price(clients, "AAPL") == 123.45


def test_is_market_open_reflects_alpaca_clock():
    open_clients = AlpacaClients(trading=_FakeTradingClient(market_open=True), data=_FakeDataClient())
    closed_clients = AlpacaClients(trading=_FakeTradingClient(market_open=False), data=_FakeDataClient())
    assert is_market_open(open_clients) is True
    assert is_market_open(closed_clients) is False


def test_fetch_account_cash_reads_real_alpaca_account_balance():
    clients = AlpacaClients(trading=_FakeTradingClient(cash=4321.0), data=_FakeDataClient())
    assert fetch_account_cash(clients) == 4321.0
