from __future__ import annotations

import pandas as pd
import ta

FEATURE_COLUMNS = [
    "return_1",
    "return_3",
    "return_6",
    "sma_fast_rel",
    "sma_slow_rel",
    "ema_fast_rel",
    "rsi",
    "macd_diff",
    "bb_pct",
    "volatility",
    "volume_change",
]


def compute_features(df: pd.DataFrame) -> pd.DataFrame:
    """Compute technical-indicator features from an OHLCV dataframe.

    Returns a new dataframe with the original columns plus FEATURE_COLUMNS.
    Rows at the start that don't have enough history for an indicator are
    left as NaN and should be dropped by the caller before training/predicting.
    """
    out = df.copy()

    out["return_1"] = out["close"].pct_change(1)
    out["return_3"] = out["close"].pct_change(3)
    out["return_6"] = out["close"].pct_change(6)

    sma_fast = ta.trend.sma_indicator(out["close"], window=10)
    sma_slow = ta.trend.sma_indicator(out["close"], window=30)
    ema_fast = ta.trend.ema_indicator(out["close"], window=10)
    out["sma_fast_rel"] = out["close"] / sma_fast - 1
    out["sma_slow_rel"] = out["close"] / sma_slow - 1
    out["ema_fast_rel"] = out["close"] / ema_fast - 1

    out["rsi"] = ta.momentum.rsi(out["close"], window=14) / 100.0

    macd = ta.trend.MACD(out["close"])
    out["macd_diff"] = macd.macd_diff()

    bb = ta.volatility.BollingerBands(out["close"], window=20)
    bb_high = bb.bollinger_hband()
    bb_low = bb.bollinger_lband()
    out["bb_pct"] = (out["close"] - bb_low) / (bb_high - bb_low)

    out["volatility"] = out["close"].pct_change().rolling(14).std()
    out["volume_change"] = out["volume"].pct_change(3)

    return out


def latest_feature_row(df_with_features: pd.DataFrame) -> pd.Series | None:
    """Return the most recent row usable for prediction, or None if it has NaNs."""
    if df_with_features.empty:
        return None
    row = df_with_features.iloc[-1]
    if row[FEATURE_COLUMNS].isna().any():
        return None
    return row
