import numpy as np
import pandas as pd

from trading_bot.model import predict_proba_up, train_model
from trading_bot.features import compute_features, latest_feature_row
from trading_bot.signals import model_signal


def _make_trending_ohlcv(n=600, seed=1):
    rng = np.random.default_rng(seed)
    returns = rng.normal(loc=0.0005, scale=0.008, size=n)
    close = 100 * np.cumprod(1 + returns)
    high = close * (1 + np.abs(rng.normal(0, 0.002, size=n)))
    low = close * (1 - np.abs(rng.normal(0, 0.002, size=n)))
    open_ = close * (1 + rng.normal(0, 0.001, size=n))
    volume = rng.uniform(100, 1000, size=n)
    idx = pd.date_range("2026-01-01", periods=n, freq="15min")
    return pd.DataFrame(
        {"open": open_, "high": high, "low": low, "close": close, "volume": volume}, index=idx
    )


def test_train_model_produces_usable_classifier():
    df = _make_trending_ohlcv()
    clf, metrics = train_model(df, horizon_candles=4, label_return_threshold=0.006)
    assert metrics["n_samples"] > 0
    assert 0.0 <= metrics["test_accuracy"] <= 1.0

    feat = compute_features(df)
    row = latest_feature_row(feat)
    assert row is not None
    proba = predict_proba_up(clf, row)
    assert 0.0 <= proba <= 1.0


def test_model_signal_respects_confidence_threshold():
    df = _make_trending_ohlcv()
    clf, _ = train_model(df, horizon_candles=4, label_return_threshold=0.006)
    feat = compute_features(df)
    row = latest_feature_row(feat)

    # Threshold of 0 should always fire a buy signal.
    sig = model_signal("BTC/USDT", clf, row, min_confidence=0.0)
    assert sig is not None
    assert sig.action == "buy"

    # Threshold above 1 can never fire.
    sig_none = model_signal("BTC/USDT", clf, row, min_confidence=1.01)
    assert sig_none is None
