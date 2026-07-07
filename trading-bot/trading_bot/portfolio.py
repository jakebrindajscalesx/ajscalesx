from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path


@dataclass
class Position:
    symbol: str
    qty: float
    entry_price: float
    stop_price: float
    take_profit_price: float
    opened_at: str
    live_order_id: str | None = None


@dataclass
class Portfolio:
    cash: float
    positions: dict[str, Position] = field(default_factory=dict)
    trade_log: list[dict] = field(default_factory=list)

    def total_equity(self, current_prices: dict[str, float]) -> float:
        equity = self.cash
        for symbol, pos in self.positions.items():
            price = current_prices.get(symbol, pos.entry_price)
            equity += pos.qty * price
        return equity

    def open_position(
        self,
        symbol: str,
        qty: float,
        entry_price: float,
        stop_price: float,
        take_profit_price: float,
        live_order_id: str | None = None,
    ) -> Position:
        cost = qty * entry_price
        if cost > self.cash:
            raise ValueError(
                f"Insufficient cash to open {symbol}: need {cost:.2f}, have {self.cash:.2f}"
            )
        self.cash -= cost
        pos = Position(
            symbol=symbol,
            qty=qty,
            entry_price=entry_price,
            stop_price=stop_price,
            take_profit_price=take_profit_price,
            opened_at=datetime.now(timezone.utc).isoformat(),
            live_order_id=live_order_id,
        )
        self.positions[symbol] = pos
        return pos

    def close_position(self, symbol: str, exit_price: float, reason: str) -> dict:
        pos = self.positions.pop(symbol)
        proceeds = pos.qty * exit_price
        self.cash += proceeds
        pnl = proceeds - (pos.qty * pos.entry_price)
        record = {
            "symbol": symbol,
            "qty": pos.qty,
            "entry_price": pos.entry_price,
            "exit_price": exit_price,
            "pnl": pnl,
            "reason": reason,
            "opened_at": pos.opened_at,
            "closed_at": datetime.now(timezone.utc).isoformat(),
        }
        self.trade_log.append(record)
        return record

    def to_dict(self) -> dict:
        return {
            "cash": self.cash,
            "positions": {k: asdict(v) for k, v in self.positions.items()},
            "trade_log": self.trade_log,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "Portfolio":
        positions = {k: Position(**v) for k, v in data.get("positions", {}).items()}
        return cls(cash=data["cash"], positions=positions, trade_log=data.get("trade_log", []))

    def save(self, path: str | Path) -> None:
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, "w") as f:
            json.dump(self.to_dict(), f, indent=2)

    @classmethod
    def load_or_create(cls, path: str | Path, starting_balance: float) -> "Portfolio":
        path = Path(path)
        if path.exists():
            with open(path) as f:
                return cls.from_dict(json.load(f))
        return cls(cash=starting_balance)
