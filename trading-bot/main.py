"""Entry point: run the trading bot as a long-lived background process.

    python main.py

Reads config.yaml (mode: paper by default) and .env (API keys / Telegram,
only needed for live mode / alerts). Stops cleanly on Ctrl-C or SIGTERM,
saving portfolio state first.
"""
from __future__ import annotations

import signal
import sys
import time

from trading_bot.config import load_config
from trading_bot.exchange import build_exchange, fetch_last_price
from trading_bot.data import CandleStore
from trading_bot.executor import LiveExecutor, PaperExecutor
from trading_bot.features import compute_features, latest_feature_row
from trading_bot.logger import get_logger
from trading_bot.model import load_model, predict_proba_up
from trading_bot.portfolio import Portfolio
from trading_bot.risk import DailyCircuitBreaker, can_open_position, position_size_qty, stop_loss_price, take_profit_price
from trading_bot.signals import Signal
from trading_bot.telegram_bot import TelegramClient, parse_command

log = get_logger("main")

PORTFOLIO_STATE_PATH = "state/portfolio.json"

_shutdown = False


def _handle_shutdown(signum, frame):
    global _shutdown
    log.info(f"Received signal {signum}, shutting down after this cycle...")
    _shutdown = True


def main() -> int:
    signal.signal(signal.SIGINT, _handle_shutdown)
    signal.signal(signal.SIGTERM, _handle_shutdown)

    config = load_config()
    log.info(f"Starting trading bot in {config.mode.upper()} mode. Symbols: {config.symbols}")

    client = build_exchange(config)
    candle_store = CandleStore(client, config.timeframe, config.history_candles)
    clf = load_model(config.model.path)

    if config.is_live:
        try:
            balance = client.fetch_balance()
            starting_cash = float(balance.get("USDT", {}).get("free", 0))
        except Exception as exc:
            log.error(f"Could not fetch live account balance: {exc}")
            return 1
        portfolio = Portfolio.load_or_create(PORTFOLIO_STATE_PATH, starting_cash)
    else:
        portfolio = Portfolio.load_or_create(PORTFOLIO_STATE_PATH, config.paper_starting_balance_usdt)

    telegram = None
    if config.telegram.enabled:
        telegram = TelegramClient(config.telegram.bot_token, config.telegram.chat_id)

    def alert(msg: str) -> None:
        log.info(msg)
        if telegram:
            telegram.send(msg)

    executor = LiveExecutor(client, portfolio, alert) if config.is_live else PaperExecutor(portfolio, alert)

    circuit_breaker = DailyCircuitBreaker(config.risk.max_daily_loss_pct)
    paused = False

    alert(f"Trading bot started in {config.mode.upper()} mode. Symbols: {', '.join(config.symbols)}")

    while not _shutdown:
        current_prices: dict[str, float] = {}
        feature_rows = {}

        for symbol in config.symbols:
            try:
                df = candle_store.refresh(symbol)
                feature_rows[symbol] = latest_feature_row(compute_features(df))
                current_prices[symbol] = fetch_last_price(client, symbol)
            except Exception as exc:
                log.error(f"Failed to fetch data for {symbol}: {exc}")

        executor.check_exits(current_prices)

        equity = portfolio.total_equity(current_prices)
        breaker_tripped = circuit_breaker.update(equity)
        if breaker_tripped:
            log.warning(f"Daily circuit breaker tripped. Equity {equity:.2f}. Halting new entries today.")

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
                    signal_ = manual
                else:
                    row = feature_rows.get(symbol)
                    if row is None:
                        continue
                    proba = predict_proba_up(clf, row)
                    signal_ = Signal(symbol, "buy", "model", proba) if proba >= config.model.min_confidence else None

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

        portfolio.save(PORTFOLIO_STATE_PATH)

        for _ in range(config.loop_interval_seconds):
            if _shutdown:
                break
            time.sleep(1)

    portfolio.save(PORTFOLIO_STATE_PATH)
    alert("Trading bot stopped.")
    log.info("Shutdown complete.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
