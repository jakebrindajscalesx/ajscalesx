from __future__ import annotations

from pathlib import Path

import joblib
import numpy as np
import pandas as pd
from sklearn.ensemble import GradientBoostingClassifier
from sklearn.model_selection import train_test_split

from trading_bot.features import FEATURE_COLUMNS, compute_features
from trading_bot.logger import get_logger

log = get_logger(__name__)


def make_labeled_dataset(
    df: pd.DataFrame, horizon_candles: int, label_return_threshold: float
) -> pd.DataFrame:
    """Compute features and a binary label: 1 if price rises at least
    label_return_threshold within horizon_candles candles, else 0.
    """
    feat = compute_features(df)
    future_return = feat["close"].shift(-horizon_candles) / feat["close"] - 1
    feat["label"] = (future_return >= label_return_threshold).astype(int)
    feat = feat.dropna(subset=FEATURE_COLUMNS + ["label"])
    return feat


def train_model(
    df: pd.DataFrame, horizon_candles: int, label_return_threshold: float
) -> tuple[GradientBoostingClassifier, dict]:
    dataset = make_labeled_dataset(df, horizon_candles, label_return_threshold)
    if len(dataset) < 100:
        raise ValueError(
            f"Not enough labeled rows to train ({len(dataset)}). Fetch more history."
        )

    X = dataset[FEATURE_COLUMNS]
    y = dataset["label"]

    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, shuffle=False
    )

    clf = GradientBoostingClassifier(
        n_estimators=200, max_depth=3, learning_rate=0.05, random_state=42
    )
    clf.fit(X_train, y_train)

    train_acc = clf.score(X_train, y_train)
    test_acc = clf.score(X_test, y_test)
    positive_rate = float(y.mean())

    metrics = {
        "train_accuracy": train_acc,
        "test_accuracy": test_acc,
        "positive_rate": positive_rate,
        "n_samples": len(dataset),
    }
    log.info(f"Model trained: {metrics}")
    return clf, metrics


def save_model(clf: GradientBoostingClassifier, path: str | Path) -> None:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    joblib.dump(clf, path)


def load_model(path: str | Path) -> GradientBoostingClassifier:
    path = Path(path)
    if not path.exists():
        raise FileNotFoundError(
            f"No trained model at {path}. Run train_model.py first."
        )
    return joblib.load(path)


def predict_proba_up(clf: GradientBoostingClassifier, feature_row: pd.Series) -> float:
    X = feature_row[FEATURE_COLUMNS].to_frame().T
    proba = clf.predict_proba(X)[0]
    classes = list(clf.classes_)
    return float(proba[classes.index(1)]) if 1 in classes else 0.0
