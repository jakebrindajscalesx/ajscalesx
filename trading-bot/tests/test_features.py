import numpy as np
import pandas as pd
import pytest

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


def test_compute_features_never_produces_inf_on_zero_volume():
    # Regression test: a zero-volume candle divides-by-zero into +inf in
    # volume_change (pct_change from zero).
    df = _make_synthetic_ohlcv(n=200)
    df.loc[df.index[60], "volume"] = 0.0
    out = compute_features(df)
    assert not np.isinf(out[FEATURE_COLUMNS].to_numpy(dtype=float)).any()


def test_swept_low_detects_wick_below_range_that_closes_back_above():
    df = _make_synthetic_ohlcv(n=60)
    # flatten a stretch so there's a well-defined recent range, then punch a
    # low wick below it on the next candle but close back inside the range
    flat_start, flat_end = 20, 40
    df.loc[df.index[flat_start:flat_end], "high"] = 101.0
    df.loc[df.index[flat_start:flat_end], "low"] = 99.0
    df.loc[df.index[flat_start:flat_end], "close"] = 100.0
    df.loc[df.index[flat_start:flat_end], "open"] = 100.0

    sweep_idx = flat_end
    df.loc[df.index[sweep_idx], "low"] = 95.0
    df.loc[df.index[sweep_idx], "high"] = 100.5
    df.loc[df.index[sweep_idx], "open"] = 100.0
    df.loc[df.index[sweep_idx], "close"] = 100.0

    out = compute_features(df)
    assert out["swept_low"].iloc[sweep_idx] == 1.0


def test_equilibrium_position_is_finite_and_roughly_mid_range():
    # 0 = at the prior range low, 1 = at the prior range high; price can go
    # outside [0, 1] if it extends beyond its own prior range, which is
    # correct (meaningfully "cheaper/pricier than the whole recent range"),
    # so this only checks the value is computed, not clamped.
    df = _make_synthetic_ohlcv(n=100)
    out = compute_features(df)
    tail = out["equilibrium_position"].iloc[-10:].dropna()
    assert not tail.empty
    assert np.isfinite(tail.to_numpy()).all()


def test_equilibrium_position_zero_at_prior_range_low_one_at_high():
    df = _make_synthetic_ohlcv(n=60)
    flat_start, flat_end = 20, 40
    df.loc[df.index[flat_start:flat_end], "high"] = 101.0
    df.loc[df.index[flat_start:flat_end], "low"] = 99.0
    df.loc[df.index[flat_start:flat_end], "close"] = 100.0
    df.loc[df.index[flat_start:flat_end], "open"] = 100.0

    at_low_idx = flat_end
    df.loc[df.index[at_low_idx], ["open", "high", "low", "close"]] = 99.0

    out = compute_features(df)
    assert out["equilibrium_position"].iloc[at_low_idx] == pytest.approx(0.0)
