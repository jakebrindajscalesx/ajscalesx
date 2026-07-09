"""Entry point for scheduled/serverless execution (e.g. GitHub Actions):
does exactly one decision cycle and exits, instead of looping forever like
main.py. Persists all state to disk between runs (portfolio, circuit
breaker, Telegram offset) so behavior is consistent whether it's run
continuously or every N minutes by a scheduler.

    python run_once.py

Also retrains the signal model if it's missing or older than
MODEL_MAX_AGE_DAYS, so a scheduled setup stays self-maintaining without a
separate retraining job.
"""
from __future__ import annotations

import sys
import time
from pathlib import Path

from trading_bot.config import load_config
from trading_bot.cycle import CycleState, run_one_cycle
from trading_bot.dashboard import write_dashboard_data
from trading_bot.data import CandleStore
from trading_bot.exchange import build_exchange
from trading_bot.executor import LiveExecutor, PaperExecutor
from trading_bot.logger import get_logger
from trading_bot.model import load_model, save_model, train_model
from trading_bot.portfolio import Portfolio
from trading_bot.risk import DailyCircuitBreaker
from trading_bot.telegram_bot import TelegramClient

log = get_logger("run_once")

PORTFOLIO_STATE_PATH = "state/portfolio.json"
CIRCUIT_BREAKER_STATE_PATH = "state/circuit_breaker.json"
TELEGRAM_OFFSET_PATH = "state/telegram_offset.json"
DASHBOARD_DATA_PATH = "docs/data.json"
MODEL_MAX_AGE_DAYS = 7
MODEL_TRAIN_CANDLES = 2000


def ensure_model_fresh(config, client) -> None:
    model_path = Path(config.model.path)
    needs_training = True
    if model_path.exists():
        age_days = (time.time() - model_path.stat().st_mtime) / 86400
        needs_training = age_days > MODEL_MAX_AGE_DAYS
        if needs_training:
            log.info(f"Model is {age_days:.1f} days old (max {MODEL_MAX_AGE_DAYS}), retraining.")
    else:
        log.info("No model found, training one now.")

    if not needs_training:
        return

    from train_model import fetch_history  # local import: avoids circular import at module load

    for symbol in config.symbols:
        df = fetch_history(client, symbol, config.timeframe, MODEL_TRAIN_CANDLES)
        try:
            clf, metrics = train_model(df, config.model.horizon_candles, config.model.label_return_threshold)
        except ValueError as exc:
            log.error(f"Could not train on {symbol}: {exc}")
            continue
        save_model(clf, config.model.path)
        log.info(f"Trained and saved model from {symbol}: {metrics}")
        return  # one shared model across configured symbols, see train_model.py


def main() -> int:
    config = load_config()
    log.info(f"Running one cycle in {config.mode.upper()} mode. Symbols: {config.symbols}")

    client = build_exchange(config)
    ensure_model_fresh(config, client)
    clf = load_model(config.model.path)

    candle_store = CandleStore(client, config.timeframe, config.history_candles)

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
        telegram = TelegramClient.load(config.telegram.bot_token, config.telegram.chat_id, TELEGRAM_OFFSET_PATH)

    def alert(msg: str) -> None:
        log.info(msg)
        if telegram:
            telegram.send(msg)

    executor = LiveExecutor(client, portfolio, alert) if config.is_live else PaperExecutor(portfolio, alert)
    circuit_breaker = DailyCircuitBreaker.load_or_create(CIRCUIT_BREAKER_STATE_PATH, config.risk.max_daily_loss_pct)
    state = CycleState()

    state = run_one_cycle(config, client, candle_store, clf, portfolio, executor, circuit_breaker, telegram, state)

    portfolio.save(PORTFOLIO_STATE_PATH)
    circuit_breaker.save(CIRCUIT_BREAKER_STATE_PATH)
    if telegram:
        telegram.save_offset(TELEGRAM_OFFSET_PATH)
    write_dashboard_data(config, portfolio, state, DASHBOARD_DATA_PATH)

    log.info(f"Cycle complete. Equity: {state.equity:.2f}, open positions: {list(portfolio.positions.keys())}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
