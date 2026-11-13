import json

from trading_bot.cycle import CycleState
from trading_bot.dashboard import write_dashboard_data
from trading_bot.portfolio import Portfolio


class _FakeModelConfig:
    pass


class _FakeConfig:
    mode = "paper"
    symbols = ["SPY"]
    paper_starting_balance_usd = 1000.0


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


def test_write_dashboard_data_includes_price_history_for_open_positions(tmp_path):
    portfolio = Portfolio(cash=980.0)
    portfolio.open_position("BTC/USDT", qty=0.01, entry_price=60000.0, stop_price=58800.0,
                             take_profit_price=62400.0)
    portfolio.record_prices({"BTC/USDT": 60000.0, "ETH/USDT": 1800.0}, at="2026-01-01T00:00:00+00:00")
    portfolio.record_prices({"BTC/USDT": 60100.0, "ETH/USDT": 1805.0}, at="2026-01-01T00:15:00+00:00")

    state = CycleState(paused=False, equity=1001.0, breaker_tripped=False)
    path = tmp_path / "data.json"

    write_dashboard_data(_FakeConfig(), portfolio, state, path)

    data = json.loads(path.read_text())
    # only symbols with an open position are exported -- ETH/USDT has none here
    assert set(data["price_history"].keys()) == {"BTC/USDT"}
    assert len(data["price_history"]["BTC/USDT"]) == 2
    assert data["price_history"]["BTC/USDT"][-1]["price"] == 60100.0
