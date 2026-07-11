from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path

import yaml
from dotenv import load_dotenv

ROOT_DIR = Path(__file__).resolve().parent.parent


@dataclass
class RiskConfig:
    position_size_pct: float
    stop_loss_pct: float
    take_profit_pct: float
    max_open_positions: int
    max_daily_loss_pct: float


@dataclass
class ModelConfig:
    path: str
    min_confidence: float
    horizon_candles: int
    label_return_threshold: float
    require_trend_confirmation: bool = True
    require_volume_confirmation: bool = True
    require_liquidity_sweep: bool = False
    require_equilibrium_discount: bool = False


@dataclass
class ExchangeConfig:
    name: str
    testnet: bool
    api_key: str = ""
    api_secret: str = ""


@dataclass
class TelegramConfig:
    enabled: bool
    poll_manual_signals: bool
    bot_token: str = ""
    chat_id: str = ""


@dataclass
class Config:
    mode: str
    exchange: ExchangeConfig
    symbols: list[str]
    timeframe: str
    history_candles: int
    loop_interval_seconds: int
    model: ModelConfig
    risk: RiskConfig
    paper_starting_balance_usdt: float
    telegram: TelegramConfig
    raw: dict = field(default_factory=dict)

    @property
    def is_live(self) -> bool:
        return self.mode == "live"


def load_config(config_path: str | Path | None = None) -> Config:
    load_dotenv(ROOT_DIR / ".env")

    path = Path(config_path) if config_path else ROOT_DIR / "config.yaml"
    if not path.exists():
        raise FileNotFoundError(
            f"Config file not found at {path}. Copy config.example.yaml to "
            f"config.yaml and edit it first."
        )

    with open(path) as f:
        raw = yaml.safe_load(f)

    mode = raw.get("mode", "paper")
    if mode not in ("paper", "live"):
        raise ValueError(f"config.mode must be 'paper' or 'live', got {mode!r}")

    exchange_raw = raw["exchange"]
    exchange = ExchangeConfig(
        name=exchange_raw["name"],
        testnet=bool(exchange_raw.get("testnet", True)),
        api_key=os.environ.get("BINANCE_API_KEY", ""),
        api_secret=os.environ.get("BINANCE_API_SECRET", ""),
    )
    if mode == "live" and not exchange.testnet and not (exchange.api_key and exchange.api_secret):
        raise ValueError(
            "mode is 'live' with testnet false, but BINANCE_API_KEY / "
            "BINANCE_API_SECRET are not set in .env. Refusing to start "
            "live trading without real credentials."
        )

    model_raw = raw["model"]
    model = ModelConfig(
        path=model_raw["path"],
        min_confidence=float(model_raw.get("min_confidence", 0.6)),
        horizon_candles=int(model_raw.get("horizon_candles", 4)),
        label_return_threshold=float(model_raw.get("label_return_threshold", 0.006)),
        require_trend_confirmation=bool(model_raw.get("require_trend_confirmation", True)),
        require_volume_confirmation=bool(model_raw.get("require_volume_confirmation", True)),
        require_liquidity_sweep=bool(model_raw.get("require_liquidity_sweep", False)),
        require_equilibrium_discount=bool(model_raw.get("require_equilibrium_discount", False)),
    )

    risk_raw = raw["risk"]
    risk = RiskConfig(
        position_size_pct=float(risk_raw["position_size_pct"]),
        stop_loss_pct=float(risk_raw["stop_loss_pct"]),
        take_profit_pct=float(risk_raw["take_profit_pct"]),
        max_open_positions=int(risk_raw["max_open_positions"]),
        max_daily_loss_pct=float(risk_raw["max_daily_loss_pct"]),
    )

    telegram_raw = raw.get("telegram", {})
    telegram = TelegramConfig(
        enabled=bool(telegram_raw.get("enabled", False)),
        poll_manual_signals=bool(telegram_raw.get("poll_manual_signals", True)),
        bot_token=os.environ.get("TELEGRAM_BOT_TOKEN", ""),
        chat_id=os.environ.get("TELEGRAM_CHAT_ID", ""),
    )
    if telegram.enabled and not (telegram.bot_token and telegram.chat_id):
        raise ValueError(
            "telegram.enabled is true but TELEGRAM_BOT_TOKEN / "
            "TELEGRAM_CHAT_ID are not set in .env."
        )

    return Config(
        mode=mode,
        exchange=exchange,
        symbols=list(raw["symbols"]),
        timeframe=raw["timeframe"],
        history_candles=int(raw.get("history_candles", 500)),
        loop_interval_seconds=int(raw.get("loop_interval_seconds", 60)),
        model=model,
        risk=risk,
        paper_starting_balance_usdt=float(raw["paper"]["starting_balance_usdt"]),
        telegram=telegram,
        raw=raw,
    )
