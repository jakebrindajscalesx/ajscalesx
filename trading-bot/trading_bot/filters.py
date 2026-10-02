from __future__ import annotations

import pandas as pd

# Well-defined, testable day-trading heuristics applied as hard gates on top
# of the ML model's confidence score -- defense in depth, so a single model
# isn't the only thing standing between a bad signal and a trade. None of
# these require trusting any particular trader's authority; all are directly
# checkable against the historical backtest (backtest.py), and every one is
# config-toggleable specifically so that claim can be tested rather than
# assumed.


def passes_trend_filter(feature_row: pd.Series) -> bool:
    """"Trade with the trend": only buy when price is above its own
    longer-term moving average, i.e. the broader trend is up, not down or
    directionless. Rejects counter-trend entries the model might otherwise
    take on a short-term blip."""
    return bool(feature_row["sma_slow_rel"] > 0)


def passes_volume_filter(feature_row: pd.Series) -> bool:
    """Require rising volume as confirmation: a price move on shrinking
    volume has less conviction behind it and is more likely to reverse."""
    return bool(feature_row["volume_change"] > 0)


def passes_liquidity_sweep_filter(feature_row: pd.Series) -> bool:
    """Only buy right after price briefly traded below a recent swing low
    and then closed back above it (a "sweep and reverse" rather than a
    clean breakdown). The idea -- borrowed from retail day-trading
    terminology, but implemented here as a plain, checkable price pattern
    rather than a claim about anyone's intent -- is that a quick
    stop-hunt-then-reverse is a different, arguably higher-conviction signal
    than price just drifting down. Off by default: combined with the other
    filters it can make signals very rare, especially with limited
    history -- turn on and compare with backtest.py."""
    return bool(feature_row["swept_low"] == 1)


def passes_equilibrium_filter(feature_row: pd.Series) -> bool:
    """Only buy when price is in the cheaper ("discount") half of its
    recent trading range, rather than already extended toward the top of
    it. Off by default for the same reason as the liquidity sweep filter --
    verify with backtest.py before trusting it."""
    return bool(feature_row["equilibrium_position"] <= 0.5)


def passes_all_filters(
    feature_row: pd.Series,
    require_trend: bool,
    require_volume: bool,
    require_liquidity_sweep: bool = False,
    require_equilibrium: bool = False,
) -> bool:
    if require_trend and not passes_trend_filter(feature_row):
        return False
    if require_volume and not passes_volume_filter(feature_row):
        return False
    if require_liquidity_sweep and not passes_liquidity_sweep_filter(feature_row):
        return False
    if require_equilibrium and not passes_equilibrium_filter(feature_row):
        return False
    return True
