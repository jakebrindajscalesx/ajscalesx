import pandas as pd

from trading_bot.filters import passes_all_filters, passes_trend_filter, passes_volume_filter


def _row(sma_slow_rel=0.0, volume_change=0.0):
    return pd.Series({"sma_slow_rel": sma_slow_rel, "volume_change": volume_change})


def test_trend_filter_requires_price_above_slow_sma():
    assert passes_trend_filter(_row(sma_slow_rel=0.01)) is True
    assert passes_trend_filter(_row(sma_slow_rel=-0.01)) is False
    assert passes_trend_filter(_row(sma_slow_rel=0.0)) is False


def test_volume_filter_requires_rising_volume():
    assert passes_volume_filter(_row(volume_change=0.05)) is True
    assert passes_volume_filter(_row(volume_change=-0.05)) is False


def test_passes_all_filters_combines_both():
    good = _row(sma_slow_rel=0.01, volume_change=0.05)
    bad_trend = _row(sma_slow_rel=-0.01, volume_change=0.05)
    bad_volume = _row(sma_slow_rel=0.01, volume_change=-0.05)

    assert passes_all_filters(good, require_trend=True, require_volume=True) is True
    assert passes_all_filters(bad_trend, require_trend=True, require_volume=True) is False
    assert passes_all_filters(bad_volume, require_trend=True, require_volume=True) is False


def test_passes_all_filters_can_be_disabled():
    bad_trend = _row(sma_slow_rel=-0.01, volume_change=0.05)
    assert passes_all_filters(bad_trend, require_trend=False, require_volume=True) is True
    assert passes_all_filters(bad_trend, require_trend=False, require_volume=False) is True
