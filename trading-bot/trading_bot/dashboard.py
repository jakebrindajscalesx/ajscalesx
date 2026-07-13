from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

from trading_bot.config import Config
from trading_bot.cycle import CycleState
from trading_bot.portfolio import Portfolio

MAX_TRADES_SHOWN = 50
MAX_EQUITY_POINTS_SHOWN = 500


def _downsample(points: list, max_points: int) -> list:
    if len(points) <= max_points:
        return points
    step = len(points) / max_points
    return [points[int(i * step)] for i in range(max_points)]


def write_dashboard_data(
    config: Config, portfolio: Portfolio, state: CycleState, path: str | Path
) -> None:
    """Writes a JSON snapshot the static dashboard page reads to render
    balance, open positions, recent trade history, and an equity curve."""
    data = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "mode": config.mode,
        "symbols": config.symbols,
        "equity": round(state.equity, 4),
        "cash": round(portfolio.cash, 4),
        "starting_balance": config.paper_starting_balance_usdt,
        "paused": state.paused,
        "circuit_breaker_tripped": state.breaker_tripped,
        "open_positions": [
            {
                "symbol": pos.symbol,
                "qty": pos.qty,
                "entry_price": pos.entry_price,
                "stop_price": pos.stop_price,
                "take_profit_price": pos.take_profit_price,
                "opened_at": pos.opened_at,
            }
            for pos in portfolio.positions.values()
        ],
        "recent_trades": list(reversed(portfolio.trade_log[-MAX_TRADES_SHOWN:])),
        "total_trades": len(portfolio.trade_log),
        "equity_history": _downsample(portfolio.equity_history, MAX_EQUITY_POINTS_SHOWN),
        "price_history": {
            symbol: _downsample(portfolio.price_history.get(symbol, []), MAX_EQUITY_POINTS_SHOWN)
            for symbol in portfolio.positions
        },
    }

    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w") as f:
        json.dump(data, f, indent=2)
