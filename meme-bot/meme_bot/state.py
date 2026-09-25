from __future__ import annotations

import json
import time
import uuid
from dataclasses import asdict, dataclass, field
from datetime import date, datetime, timezone
from pathlib import Path

from meme_bot.logger import get_logger

log = get_logger(__name__)


@dataclass
class PendingTrade:
    id: str
    created_at: float
    expires_at: float
    wallet: str
    side: str  # "buy" or "sell"
    token_mint: str
    trade_usd: float
    status: str = "pending"  # pending | confirmed | rejected | expired | executed | failed
    tx_signature: str | None = None
    note: str = ""


@dataclass
class Position:
    token_mint: str
    opened_from_wallet: str
    opened_at: float
    cost_sol: float  # SOL spent to open this position -- P&L/stop-loss are
                      # tracked in SOL terms throughout to avoid needing a
                      # second USD price lookup on every check
    token_amount_raw: int  # raw base units received from the buy


@dataclass
class BotState:
    tracked_wallets: dict[str, str] = field(default_factory=dict)  # wallet -> last_seen_signature
    pending_trades: dict[str, PendingTrade] = field(default_factory=dict)
    positions: dict[str, Position] = field(default_factory=dict)  # token_mint -> Position
    spend_day: str | None = None
    spend_usd_today: float = 0.0
    paused: bool = False
    leaderboard_refreshed_at: float = 0.0

    # -- daily spend / circuit breaker -----------------------------------

    def _roll_day_if_needed(self) -> None:
        today = date.today().isoformat()
        if self.spend_day != today:
            self.spend_day = today
            self.spend_usd_today = 0.0

    def record_spend(self, usd: float) -> None:
        self._roll_day_if_needed()
        self.spend_usd_today += usd

    def spend_today(self) -> float:
        self._roll_day_if_needed()
        return self.spend_usd_today

    # -- tracked wallets ---------------------------------------------------

    def last_seen(self, wallet: str) -> str | None:
        return self.tracked_wallets.get(wallet)

    def set_last_seen(self, wallet: str, signature: str) -> None:
        self.tracked_wallets[wallet] = signature

    def prune_wallets(self, keep: set[str]) -> None:
        """Drops last-seen bookkeeping for wallets no longer on the current
        leaderboard, so the state file doesn't grow forever."""
        for w in list(self.tracked_wallets):
            if w not in keep:
                del self.tracked_wallets[w]

    # -- pending trades ------------------------------------------------

    def add_pending_trade(
        self, wallet: str, side: str, token_mint: str, trade_usd: float, timeout_minutes: int
    ) -> PendingTrade:
        now = time.time()
        trade = PendingTrade(
            id=uuid.uuid4().hex[:8],
            created_at=now,
            expires_at=now + timeout_minutes * 60,
            wallet=wallet,
            side=side,
            token_mint=token_mint,
            trade_usd=trade_usd,
        )
        self.pending_trades[trade.id] = trade
        return trade

    def expire_stale_pending(self) -> list[PendingTrade]:
        now = time.time()
        expired = []
        for trade in self.pending_trades.values():
            if trade.status == "pending" and now > trade.expires_at:
                trade.status = "expired"
                expired.append(trade)
        return expired

    def open_pending_trades(self) -> list[PendingTrade]:
        return [t for t in self.pending_trades.values() if t.status == "pending"]

    # -- positions -------------------------------------------------------

    def open_position(self, token_mint: str, wallet: str, cost_sol: float, token_amount_raw: int) -> None:
        self.positions[token_mint] = Position(
            token_mint=token_mint,
            opened_from_wallet=wallet,
            opened_at=time.time(),
            cost_sol=cost_sol,
            token_amount_raw=token_amount_raw,
        )

    def close_position(self, token_mint: str) -> None:
        self.positions.pop(token_mint, None)

    # -- persistence -------------------------------------------------------

    def to_json(self) -> str:
        return json.dumps(
            {
                "tracked_wallets": self.tracked_wallets,
                "pending_trades": {k: asdict(v) for k, v in self.pending_trades.items()},
                "positions": {k: asdict(v) for k, v in self.positions.items()},
                "spend_day": self.spend_day,
                "spend_usd_today": self.spend_usd_today,
                "paused": self.paused,
                "leaderboard_refreshed_at": self.leaderboard_refreshed_at,
            },
            indent=2,
        )

    def save(self, path: str | Path) -> None:
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(self.to_json())

    @classmethod
    def load_or_create(cls, path: str | Path) -> "BotState":
        path = Path(path)
        if not path.exists():
            return cls()
        try:
            data = json.loads(path.read_text())
        except Exception as exc:
            log.warning(f"Could not read state file, starting fresh: {exc}")
            return cls()

        state = cls(
            tracked_wallets=data.get("tracked_wallets", {}),
            spend_day=data.get("spend_day"),
            spend_usd_today=data.get("spend_usd_today", 0.0),
            paused=data.get("paused", False),
            leaderboard_refreshed_at=data.get("leaderboard_refreshed_at", 0.0),
        )
        for k, v in data.get("pending_trades", {}).items():
            state.pending_trades[k] = PendingTrade(**v)
        for k, v in data.get("positions", {}).items():
            state.positions[k] = Position(**v)
        return state
