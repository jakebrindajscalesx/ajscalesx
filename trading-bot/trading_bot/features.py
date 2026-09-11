from __future__ import annotations

import numpy as np
import pandas as pd
import ta

SWING_LOOKBACK = 20  # candles used to define the "recent swing high/low"

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
    "swept_low",
    "swept_high",
    "equilibrium_position",
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

    # Liquidity sweep: price briefly trades beyond a recent swing extreme
    # (often where stop-loss/entry orders cluster) then closes back inside
    # it -- a wick-based "stop hunt then reverse" pattern rather than a
    # clean breakout. swing_high/low look back over the window *before*
    # the current candle so the current candle can be compared against it.
    swing_high = out["high"].shift(1).rolling(SWING_LOOKBACK).max()
    swing_low = out["low"].shift(1).rolling(SWING_LOOKBACK).min()
    out["swept_low"] = ((out["low"] < swing_low) & (out["close"] > swing_low)).astype(float)
    out["swept_high"] = ((out["high"] > swing_high) & (out["close"] < swing_high)).astype(float)

    # Equilibrium: where the current close sits within its recent trading
    # range, 0 = at the range low, 1 = at the range high, 0.5 = the
    # midpoint. A common heuristic is to prefer buying in the cheaper
    # ("discount") half of a range rather than chasing price that's already
    # extended toward the top of it.
    range_high = out["high"].shift(1).rolling(SWING_LOOKBACK).max()
    range_low = out["low"].shift(1).rolling(SWING_LOOKBACK).min()
    out["equilibrium_position"] = (out["close"] - range_low) / (range_high - range_low)

    # A handful of these are divisions that can hit zero on real exchange
    # data (e.g. bb_pct when price is flat enough that the Bollinger Bands
    # collapse to a single value, or volume_change when a candle reports
    # zero volume). Treat those as missing data, same as an indicator that
    # hasn't warmed up yet, rather than letting +/-inf reach the model --
    # sklearn raises on infinite inputs instead of silently mishandling
    # them, and that crash has taken down a live run before.
    out[FEATURE_COLUMNS] = out[FEATURE_COLUMNS].replace([np.inf, -np.inf], np.nan)

    return out


def latest_feature_row(df_with_features: pd.DataFrame) -> pd.Series | None:
    """Return the most recent row usable for prediction, or None if it has NaNs."""
    if df_with_features.empty:
        return None
    row = df_with_features.iloc[-1]
    if row[FEATURE_COLUMNS].isna().any():
        return None
    return row
