from __future__ import annotations

from dataclasses import dataclass

import pandas as pd
from sklearn.ensemble import GradientBoostingClassifier

from trading_bot.model import predict_proba_up


@dataclass
class Signal:
    symbol: str
    action: str  # "buy" or "close"
    source: str  # "model" or "manual"
    confidence: float = 1.0


def model_signal(
    symbol: str,
    clf: GradientBoostingClassifier,
    feature_row: pd.Series | None,
    min_confidence: float,
) -> Signal | None:
    if feature_row is None:
        return None
    proba = predict_proba_up(clf, feature_row)
    if proba >= min_confidence:
        return Signal(symbol=symbol, action="buy", source="model", confidence=proba)
    return None
