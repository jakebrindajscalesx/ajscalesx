from __future__ import annotations

from datetime import date, datetime, timezone


def position_size_qty(equity: float, price: float, position_size_pct: float) -> float:
    """How much of an asset to buy so the position's notional value equals
    position_size_pct of total account equity."""
    if equity <= 0 or price <= 0:
        return 0.0
    notional = equity * (position_size_pct / 100.0)
    return notional / price


def stop_loss_price(entry_price: float, stop_loss_pct: float) -> float:
    return entry_price * (1 - stop_loss_pct / 100.0)


def take_profit_price(entry_price: float, take_profit_pct: float) -> float:
    return entry_price * (1 + take_profit_pct / 100.0)


def can_open_position(open_positions_count: int, max_open_positions: int) -> bool:
    return open_positions_count < max_open_positions


class DailyCircuitBreaker:
    """The bot's "takeout stop": halts all new entries for the rest of the
    UTC day once realized+unrealized losses reach max_daily_loss_pct of the
    equity the account had at the start of that day. Existing open positions
    still get managed (their own stop-loss/take-profit still apply) -- this
    only blocks opening new ones.
    """

    def __init__(self, max_daily_loss_pct: float):
        self.max_daily_loss_pct = max_daily_loss_pct
        self._day: date | None = None
        self._day_start_equity: float | None = None
        self._tripped = False

    def _roll_day_if_needed(self, equity: float, now: datetime) -> None:
        today = now.date()
        if self._day != today:
            self._day = today
            self._day_start_equity = equity
            self._tripped = False

    def update(self, equity: float, now: datetime | None = None) -> bool:
        """Call once per loop with current total equity (cash + open
        position value). Returns True if new trading should be halted."""
        now = now or datetime.now(timezone.utc)
        self._roll_day_if_needed(equity, now)
        assert self._day_start_equity is not None
        if self._day_start_equity > 0:
            loss_pct = (self._day_start_equity - equity) / self._day_start_equity * 100.0
            if loss_pct >= self.max_daily_loss_pct:
                self._tripped = True
        return self._tripped

    @property
    def tripped(self) -> bool:
        return self._tripped

    def reset(self) -> None:
        """Manually clear a trip (e.g. via a /resume Telegram command)."""
        self._tripped = False
