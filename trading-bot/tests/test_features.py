import numpy as np
import pandas as pd

from trading_bot.features import FEATURE_COLUMNS, compute_features, latest_feature_row


def _make_synthetic_ohlcv(n=200, seed=42):
    rng = np.random.default_rng(seed)
    returns = rng.normal(loc=0.0002, scale=0.01, size=n)
    close = 100 * np.cumprod(1 + returns)
    high = close * (1 + np.abs(rng.normal(0, 0.002, size=n)))
    low = close * (1 - np.abs(rng.normal(0, 0.002, size=n)))
    open_ = close * (1 + rng.normal(0, 0.001, size=n))
    volume = rng.uniform(100, 1000, size=n)
    idx = pd.date_range("2026-01-01", periods=n, freq="15min")
    return pd.DataFrame(
        {"open": open_, "high": high, "low": low, "close": close, "volume": volume}, index=idx
    )


def test_compute_features_adds_expected_columns():
    df = _make_synthetic_ohlcv()
    out = compute_features(df)
    for col in FEATURE_COLUMNS:
        assert col in out.columns


def test_compute_features_tail_rows_have_no_nan():
    df = _make_synthetic_ohlcv()
    out = compute_features(df)
    tail = out.iloc[-10:]
    assert not tail[FEATURE_COLUMNS].isna().any().any()


def test_latest_feature_row_returns_none_when_insufficient_history():
    df = _make_synthetic_ohlcv(n=5)
    out = compute_features(df)
    assert latest_feature_row(out) is None


def test_latest_feature_row_returns_series_when_ready():
    df = _make_synthetic_ohlcv(n=200)
    out = compute_features(df)
    row = latest_feature_row(out)
    assert row is not None
    assert set(FEATURE_COLUMNS).issubset(row.index)
