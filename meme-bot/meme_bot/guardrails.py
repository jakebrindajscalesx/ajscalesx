from __future__ import annotations

from meme_bot.config import Config
from meme_bot.state import BotState


def can_propose_new_buy(cfg: Config, state: BotState, token_mint: str) -> tuple[bool, str]:
    """Checks run before a newly-detected buy signal even becomes a pending
    trade proposal (as opposed to checks run again at confirm time, which
    guard against state changing in between)."""
    if state.paused:
        return False, "bot is paused (/resume to clear)"
    if token_mint in state.positions:
        return False, "already holding this token"
    if len(state.positions) >= cfg.sizing.max_open_positions:
        return False, f"at max_open_positions ({cfg.sizing.max_open_positions})"
    if state.spend_today() + cfg.sizing.trade_usd > cfg.sizing.max_daily_spend_usd:
        return False, (
            f"would exceed max_daily_spend_usd "
            f"(${state.spend_today():.2f} spent today + ${cfg.sizing.trade_usd:.2f} > "
            f"${cfg.sizing.max_daily_spend_usd:.2f})"
        )
    return True, ""


def can_execute(cfg: Config, state: BotState, trade_id: str) -> tuple[bool, str]:
    """Re-checked at confirm time in case circumstances changed since the
    trade was proposed (e.g. daily cap already hit by another confirmed
    trade, or the position got closed another way in the meantime)."""
    trade = state.pending_trades.get(trade_id)
    if trade is None:
        return False, "no such pending trade"
    if trade.status != "pending":
        return False, f"trade is already {trade.status}, not pending"
    import time

    if time.time() > trade.expires_at:
        return False, "trade proposal expired"
    if trade.side == "buy":
        ok, reason = can_propose_new_buy(cfg, state, trade.token_mint)
        if not ok:
            return False, reason
    if trade.side == "sell" and trade.token_mint not in state.positions:
        return False, "no open position in this token to sell"
    return True, ""
