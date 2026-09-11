import pandas as pd

from trading_bot.filters import (
    passes_all_filters,
    passes_equilibrium_filter,
    passes_liquidity_sweep_filter,
    passes_trend_filter,
    passes_volume_filter,
)


def _row(sma_slow_rel=0.0, volume_change=0.0, swept_low=0.0, swept_high=0.0, equilibrium_position=0.5):
    return pd.Series(
        {
            "sma_slow_rel": sma_slow_rel,
            "volume_change": volume_change,
            "swept_low": swept_low,
            "swept_high": swept_high,
            "equilibrium_position": equilibrium_position,
        }
    )


def test_trend_filter_requires_price_above_slow_sma():
    assert passes_trend_filter(_row(sma_slow_rel=0.01)) is True
    assert passes_trend_filter(_row(sma_slow_rel=-0.01)) is False
    assert passes_trend_filter(_row(sma_slow_rel=0.0)) is False


def test_volume_filter_requires_rising_volume():
    assert passes_volume_filter(_row(volume_change=0.05)) is True
    assert passes_volume_filter(_row(volume_change=-0.05)) is False


def test_liquidity_sweep_filter_requires_swept_low():
    assert passes_liquidity_sweep_filter(_row(swept_low=1.0)) is True
    assert passes_liquidity_sweep_filter(_row(swept_low=0.0)) is False


def test_equilibrium_filter_requires_discount_half():
    assert passes_equilibrium_filter(_row(equilibrium_position=0.3)) is True
    assert passes_equilibrium_filter(_row(equilibrium_position=0.5)) is True
    assert passes_equilibrium_filter(_row(equilibrium_position=0.7)) is False


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


def test_passes_all_filters_includes_liquidity_sweep_and_equilibrium():
    good = _row(sma_slow_rel=0.01, volume_change=0.05, swept_low=1.0, equilibrium_position=0.2)
    no_sweep = _row(sma_slow_rel=0.01, volume_change=0.05, swept_low=0.0, equilibrium_position=0.2)
    premium = _row(sma_slow_rel=0.01, volume_change=0.05, swept_low=1.0, equilibrium_position=0.8)

    assert passes_all_filters(
        good, require_trend=True, require_volume=True, require_liquidity_sweep=True, require_equilibrium=True
    ) is True
    assert passes_all_filters(
        no_sweep, require_trend=True, require_volume=True, require_liquidity_sweep=True, require_equilibrium=True
    ) is False
    assert passes_all_filters(
        premium, require_trend=True, require_volume=True, require_liquidity_sweep=True, require_equilibrium=True
    ) is False
    # off by default -- doesn't affect existing behavior
    assert passes_all_filters(no_sweep, require_trend=True, require_volume=True) is True
