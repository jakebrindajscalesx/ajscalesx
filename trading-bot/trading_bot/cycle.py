from __future__ import annotations

from dataclasses import dataclass, field

import ccxt
from sklearn.ensemble import GradientBoostingClassifier

from trading_bot.config import Config
from trading_bot.data import CandleStore
from trading_bot.executor import Executor
from trading_bot.features import compute_features, latest_feature_row
from trading_bot.filters import passes_all_filters
from trading_bot.logger import get_logger
from trading_bot.model import predict_proba_up
from trading_bot.portfolio import Portfolio
from trading_bot.risk import (
    DailyCircuitBreaker,
    can_open_position,
    position_size_qty,
    stop_loss_price,
    take_profit_price,
)
from trading_bot.signals import Signal
from trading_bot.telegram_bot import TelegramClient, parse_command

log = get_logger(__name__)


@dataclass
class CycleState:
    """Mutable state that persists across cycles (in-memory for the
    long-running loop in main.py, or reloaded from disk for the single-shot
    run_once.py)."""

    paused: bool = False
    equity: float = 0.0
    breaker_tripped: bool = False


def run_one_cycle(
    config: Config,
    client: ccxt.Exchange,
    candle_store: CandleStore,
    clf: GradientBoostingClassifier,
    portfolio: Portfolio,
    executor: Executor,
    circuit_breaker: DailyCircuitBreaker,
    telegram: TelegramClient | None,
    state: CycleState,
) -> CycleState:
    """Runs one full decision cycle: refresh data, manage exits, process any
    manual Telegram commands, and open new positions if signals say to.
    Mutates portfolio/circuit_breaker in place; returns updated CycleState.
    """
    current_prices: dict[str, float] = {}
    feature_rows = {}

    for symbol in config.symbols:
        try:
            df = candle_store.refresh(symbol)
            feature_rows[symbol] = latest_feature_row(compute_features(df))
            current_prices[symbol] = df["close"].iloc[-1]
        except Exception as exc:
            log.error(f"Failed to fetch data for {symbol}: {exc}")

    executor.check_exits(current_prices)

    portfolio.record_prices(current_prices)
    equity = portfolio.total_equity(current_prices)
    portfolio.record_equity(equity)
    breaker_tripped = circuit_breaker.update(equity)
    if breaker_tripped:
        log.warning(f"Daily circuit breaker tripped. Equity {equity:.2f}. Halting new entries today.")

    def alert(msg: str) -> None:
        log.info(msg)
        if telegram:
            telegram.send(msg)

    paused = state.paused
    manual_signals: list[Signal] = []
    if telegram and config.telegram.poll_manual_signals:
        for raw in telegram.poll_commands():
            cmd = parse_command(raw)
            if cmd is None:
                telegram.send(f"Unrecognized command: {raw}")
                continue
            if cmd["type"] == "signal":
                if cmd["action"] == "buy":
                    manual_signals.append(Signal(symbol=cmd["symbol"], action="buy", source="manual"))
                else:
                    executor.close_position_manually(cmd["symbol"], current_prices.get(cmd["symbol"], 0))
            elif cmd["type"] == "pause":
                paused = True
                telegram.send("Paused: no new positions will be opened until /resume.")
            elif cmd["type"] == "resume":
                paused = False
                circuit_breaker.reset()
                telegram.send("Resumed: circuit breaker cleared, new positions allowed again.")
            elif cmd["type"] == "status":
                telegram.send(
                    f"Mode: {config.mode}\nEquity: {equity:.2f}\n"
                    f"Cash: {portfolio.cash:.2f}\nOpen positions: {list(portfolio.positions.keys())}\n"
                    f"Paused: {paused}\nCircuit breaker tripped: {circuit_breaker.tripped}"
                )

    if not paused and not breaker_tripped:
        for symbol in config.symbols:
            if symbol in portfolio.positions:
                continue
            if not can_open_position(len(portfolio.positions), config.risk.max_open_positions):
                break

            manual = next((s for s in manual_signals if s.symbol == symbol), None)
            if manual:
                # A manual signal is an explicit human decision -- it
                # bypasses the model's confirmation filters the same way it
                # bypasses the model itself.
                signal_ = manual
            else:
                row = feature_rows.get(symbol)
                if row is None:
                    continue
                proba = predict_proba_up(clf, row)
                confident_enough = proba >= config.model.min_confidence
                confirmed = passes_all_filters(
                    row,
                    require_trend=config.model.require_trend_confirmation,
                    require_volume=config.model.require_volume_confirmation,
                    require_liquidity_sweep=config.model.require_liquidity_sweep,
                    require_equilibrium=config.model.require_equilibrium_discount,
                )
                signal_ = Signal(symbol, "buy", "model", proba) if confident_enough and confirmed else None

            if signal_ is None:
                continue

            price = current_prices.get(symbol)
            if not price:
                continue

            qty = position_size_qty(equity, price, config.risk.position_size_pct)
            if qty <= 0:
                continue
            stop = stop_loss_price(price, config.risk.stop_loss_pct)
            take_profit = take_profit_price(price, config.risk.take_profit_pct)
            try:
                executor.open_position(symbol, qty, price, stop, take_profit)
            except Exception as exc:
                log.error(f"Failed to open position for {symbol}: {exc}")

    return CycleState(paused=paused, equity=equity, breaker_tripped=breaker_tripped)
