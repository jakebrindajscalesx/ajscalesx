"""Entry point: run the trading bot as a long-lived background process.

    python main.py

Reads config.yaml (mode: paper by default) and .env (API keys / Telegram,
only needed for live mode / alerts). Stops cleanly on Ctrl-C or SIGTERM,
saving portfolio state first.

For scheduled/serverless execution (e.g. GitHub Actions) where nothing runs
continuously, use run_once.py instead -- it does a single cycle and exits.
"""
from __future__ import annotations

import signal
import sys
import time

from trading_bot.config import load_config
from trading_bot.cycle import CycleState, run_one_cycle
from trading_bot.data import CandleStore
from trading_bot.exchange import build_exchange, fetch_account_cash
from trading_bot.executor import AlpacaExecutor
from trading_bot.logger import get_logger
from trading_bot.model import load_model
from trading_bot.portfolio import Portfolio
from trading_bot.risk import DailyCircuitBreaker
from trading_bot.telegram_bot import TelegramClient

log = get_logger("main")

PORTFOLIO_STATE_PATH = "state/portfolio.json"
CIRCUIT_BREAKER_STATE_PATH = "state/circuit_breaker.json"

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
            starting_cash = fetch_account_cash(client)
        except Exception as exc:
            log.error(f"Could not fetch live account balance: {exc}")
            return 1
        portfolio = Portfolio.load_or_create(PORTFOLIO_STATE_PATH, starting_cash)
    else:
        portfolio = Portfolio.load_or_create(PORTFOLIO_STATE_PATH, config.paper_starting_balance_usd)

    telegram = None
    if config.telegram.enabled:
        telegram = TelegramClient(config.telegram.bot_token, config.telegram.chat_id)

    def alert(msg: str) -> None:
        log.info(msg)
        if telegram:
            telegram.send(msg)

    executor = AlpacaExecutor(client.trading, portfolio, alert)
    circuit_breaker = DailyCircuitBreaker.load_or_create(CIRCUIT_BREAKER_STATE_PATH, config.risk.max_daily_loss_pct)
    state = CycleState()

    alert(f"Trading bot started in {config.mode.upper()} mode. Symbols: {', '.join(config.symbols)}")

    while not _shutdown:
        state = run_one_cycle(config, client, candle_store, clf, portfolio, executor, circuit_breaker, telegram, state)
        portfolio.save(PORTFOLIO_STATE_PATH)
        circuit_breaker.save(CIRCUIT_BREAKER_STATE_PATH)

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
