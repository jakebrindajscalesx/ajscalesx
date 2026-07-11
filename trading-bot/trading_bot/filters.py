from __future__ import annotations

import pandas as pd

# Two well-established, unglamorous day-trading principles applied as hard
# gates on top of the ML model's confidence score -- defense in depth, so a
# single model isn't the only thing standing between a bad signal and a
# trade. Neither requires trusting any particular guru; both are directly
# checkable against the historical backtest.


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


def passes_all_filters(feature_row: pd.Series, require_trend: bool, require_volume: bool) -> bool:
    if require_trend and not passes_trend_filter(feature_row):
        return False
    if require_volume and not passes_volume_filter(feature_row):
        return False
    return True
