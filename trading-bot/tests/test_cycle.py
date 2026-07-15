from unittest.mock import MagicMock

import trading_bot.cycle as cycle_module
from trading_bot.cycle import CycleState, run_one_cycle
from trading_bot.portfolio import Portfolio
from trading_bot.risk import DailyCircuitBreaker


def test_run_one_cycle_does_nothing_when_market_is_closed(monkeypatch):
    # Regression test: stocks only trade during NYSE hours, unlike crypto's
    # 24/7 market -- when the market is closed, a scheduled run must not
    # fetch data, check exits, or record equity/price snapshots against
    # stale or nonexistent bars.
    monkeypatch.setattr(cycle_module, "is_market_open", lambda client: False)

    candle_store = MagicMock()
    executor = MagicMock()
    portfolio = Portfolio(cash=1000.0)
    circuit_breaker = DailyCircuitBreaker(max_daily_loss_pct=5.0)
    state = CycleState(paused=False, equity=1000.0, breaker_tripped=False)

    result = run_one_cycle(
        config=MagicMock(symbols=["SPY"]),
        client=MagicMock(),
        candle_store=candle_store,
        clf=MagicMock(),
        portfolio=portfolio,
        executor=executor,
        circuit_breaker=circuit_breaker,
        telegram=None,
        state=state,
    )

    candle_store.refresh.assert_not_called()
    executor.check_exits.assert_not_called()
    assert portfolio.equity_history == []
    assert result is state
