import json

from trading_bot.cycle import CycleState
from trading_bot.dashboard import write_dashboard_data
from trading_bot.portfolio import Portfolio


class _FakeModelConfig:
    pass


class _FakeConfig:
    mode = "paper"
    symbols = ["BTC/USDT"]
    paper_starting_balance_usdt = 1000.0


def test_write_dashboard_data_includes_equity_history(tmp_path):
    portfolio = Portfolio(cash=1000.0)
    portfolio.record_equity(1000.0, at="2026-01-01T00:00:00+00:00")
    portfolio.record_equity(1010.0, at="2026-01-01T00:15:00+00:00")

    state = CycleState(paused=False, equity=1010.0, breaker_tripped=False)
    path = tmp_path / "data.json"

    write_dashboard_data(_FakeConfig(), portfolio, state, path)

    data = json.loads(path.read_text())
    assert data["equity"] == 1010.0
    assert len(data["equity_history"]) == 2
    assert data["equity_history"][-1]["equity"] == 1010.0


def test_write_dashboard_data_downsamples_long_history(tmp_path):
    portfolio = Portfolio(cash=1000.0)
    for i in range(1200):
        portfolio.record_equity(1000.0 + i, at=f"t{i}")

    state = CycleState(paused=False, equity=1000.0, breaker_tripped=False)
    path = tmp_path / "data.json"

    write_dashboard_data(_FakeConfig(), portfolio, state, path)

    data = json.loads(path.read_text())
    assert len(data["equity_history"]) <= 500
    # first and last real points should still be represented in order
    assert data["equity_history"][0]["t"] == "t0"
