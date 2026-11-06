from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path

import yaml
from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent


@dataclass
class LeaderboardConfig:
    source: str = "fomoscope"
    top_n: int = 10
    refresh_minutes: int = 60
    min_win_rate_pct: float = 55.0
    min_trades_30d: int = 10


@dataclass
class SizingConfig:
    mirror_mode: str = "fixed"
    trade_usd: float = 10.0
    max_daily_spend_usd: float = 50.0
    max_open_positions: int = 5


@dataclass
class ExecutionConfig:
    slippage_bps: int = 150
    confirmation_timeout_minutes: int = 15


@dataclass
class ExitConfig:
    mirror_sells: bool = True
    stand_alone_stop_loss_pct: float = 25.0


@dataclass
class Secrets:
    helius_api_key: str = ""
    fomoscope_api_key: str = ""
    wallet_public_key: str = ""
    wallet_private_key: str = ""
    telegram_bot_token: str = ""
    telegram_chat_id: str = ""


@dataclass
class Config:
    dry_run: bool = True
    chain: str = "solana"
    funding_token: str = "SOL"
    leaderboard: LeaderboardConfig = field(default_factory=LeaderboardConfig)
    sizing: SizingConfig = field(default_factory=SizingConfig)
    execution: ExecutionConfig = field(default_factory=ExecutionConfig)
    exit: ExitConfig = field(default_factory=ExitConfig)
    secrets: Secrets = field(default_factory=Secrets)

    @property
    def state_dir(self) -> Path:
        return BASE_DIR / "state"


def load_config(path: str | Path | None = None) -> Config:
    """Loads config.yaml (falling back to config.example.yaml if it doesn't
    exist yet -- mirrors ../trading-bot's convention) plus secrets from the
    environment / .env."""
    load_dotenv(BASE_DIR / ".env")

    path = Path(path) if path else BASE_DIR / "config.yaml"
    if not path.exists():
        path = BASE_DIR / "config.example.yaml"
    raw = yaml.safe_load(path.read_text()) or {}

    cfg = Config(
        dry_run=bool(raw.get("dry_run", True)),
        chain=raw.get("chain", "solana"),
        funding_token=raw.get("funding_token", "SOL"),
        leaderboard=LeaderboardConfig(**raw.get("leaderboard", {})),
        sizing=SizingConfig(**raw.get("sizing", {})),
        execution=ExecutionConfig(**raw.get("execution", {})),
        exit=ExitConfig(**raw.get("exit", {})),
        secrets=Secrets(
            helius_api_key=os.environ.get("HELIUS_API_KEY", ""),
            fomoscope_api_key=os.environ.get("FOMOSCOPE_API_KEY", ""),
            wallet_public_key=os.environ.get("WALLET_PUBLIC_KEY", ""),
            wallet_private_key=os.environ.get("WALLET_PRIVATE_KEY", ""),
            telegram_bot_token=os.environ.get("TELEGRAM_BOT_TOKEN", ""),
            telegram_chat_id=os.environ.get("TELEGRAM_CHAT_ID", ""),
        ),
    )

    if not cfg.dry_run:
        missing = [
            name
            for name, val in [
                ("HELIUS_API_KEY", cfg.secrets.helius_api_key),
                ("WALLET_PUBLIC_KEY", cfg.secrets.wallet_public_key),
                ("WALLET_PRIVATE_KEY", cfg.secrets.wallet_private_key),
            ]
            if not val
        ]
        if missing:
            raise RuntimeError(
                f"dry_run is false but required secret(s) missing: {', '.join(missing)}. "
                "Real execution needs these set -- see .env.example."
            )

    return cfg
