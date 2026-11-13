from __future__ import annotations

import pandas as pd

from trading_bot.exchange import AlpacaClients, fetch_ohlcv_df


class CandleStore:
    """Keeps a rolling window of OHLCV candles per symbol in memory."""

    def __init__(self, client: AlpacaClients, timeframe: str, history_candles: int):
        self.client = client
        self.timeframe = timeframe
        self.history_candles = history_candles
        self._data: dict[str, pd.DataFrame] = {}

    def refresh(self, symbol: str) -> pd.DataFrame:
        df = fetch_ohlcv_df(self.client, symbol, self.timeframe, self.history_candles)
        self._data[symbol] = df
        return df

    def get(self, symbol: str) -> pd.DataFrame | None:
        return self._data.get(symbol)
