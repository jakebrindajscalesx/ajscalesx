import pytest

from trading_bot.portfolio import Portfolio


def test_open_position_deducts_cash():
    p = Portfolio(cash=1000.0)
    p.open_position("BTC/USDT", qty=0.1, entry_price=100.0, stop_price=98.0, take_profit_price=104.0)
    assert p.cash == 990.0
    assert "BTC/USDT" in p.positions


def test_open_position_insufficient_cash_raises():
    p = Portfolio(cash=10.0)
    with pytest.raises(ValueError):
        p.open_position("BTC/USDT", qty=1.0, entry_price=100.0, stop_price=98.0, take_profit_price=104.0)


def test_close_position_take_profit_pnl():
    p = Portfolio(cash=1000.0)
    p.open_position("BTC/USDT", qty=0.1, entry_price=100.0, stop_price=98.0, take_profit_price=104.0)
    record = p.close_position("BTC/USDT", exit_price=104.0, reason="take_profit")
    assert record["pnl"] == pytest.approx(0.4)
    assert p.cash == pytest.approx(1000.4)
    assert "BTC/USDT" not in p.positions
    assert len(p.trade_log) == 1


def test_close_position_stop_loss_pnl():
    p = Portfolio(cash=1000.0)
    p.open_position("BTC/USDT", qty=0.1, entry_price=100.0, stop_price=98.0, take_profit_price=104.0)
    record = p.close_position("BTC/USDT", exit_price=98.0, reason="stop_loss")
    assert record["pnl"] == pytest.approx(-0.2)
    assert p.cash == pytest.approx(999.8)


def test_total_equity_includes_open_positions():
    p = Portfolio(cash=1000.0)
    p.open_position("BTC/USDT", qty=1.0, entry_price=100.0, stop_price=98.0, take_profit_price=104.0)
    # cash is now 900.0 (1000 - 1.0*100 cost); equity should reflect the
    # position's current market value, not its entry price.
    equity = p.total_equity({"BTC/USDT": 110.0})
    assert equity == pytest.approx(900.0 + 1.0 * 110.0)


def test_save_and_load_roundtrip(tmp_path):
    p = Portfolio(cash=1000.0)
    p.open_position("ETH/USDT", qty=2.0, entry_price=50.0, stop_price=49.0, take_profit_price=52.0)
    path = tmp_path / "portfolio.json"
    p.save(path)

    loaded = Portfolio.load_or_create(path, starting_balance=999999.0)
    assert loaded.cash == p.cash
    assert "ETH/USDT" in loaded.positions
    assert loaded.positions["ETH/USDT"].qty == 2.0


def test_load_or_create_uses_starting_balance_when_missing(tmp_path):
    path = tmp_path / "does_not_exist.json"
    p = Portfolio.load_or_create(path, starting_balance=500.0)
    assert p.cash == 500.0
    assert p.positions == {}


def test_record_equity_appends_snapshot():
    p = Portfolio(cash=1000.0)
    p.record_equity(1000.0, at="2026-01-01T00:00:00+00:00")
    p.record_equity(1010.0, at="2026-01-01T00:15:00+00:00")
    assert len(p.equity_history) == 2
    assert p.equity_history[0] == {"t": "2026-01-01T00:00:00+00:00", "equity": 1000.0}
    assert p.equity_history[1]["equity"] == 1010.0


def test_record_equity_caps_history_length():
    p = Portfolio(cash=1000.0)
    from trading_bot.portfolio import MAX_EQUITY_HISTORY_POINTS

    for i in range(MAX_EQUITY_HISTORY_POINTS + 50):
        p.record_equity(1000.0 + i, at=f"t{i}")

    assert len(p.equity_history) == MAX_EQUITY_HISTORY_POINTS
    # oldest points got dropped, newest retained
    assert p.equity_history[-1]["t"] == f"t{MAX_EQUITY_HISTORY_POINTS + 49}"


def test_equity_history_persists_through_save_and_load(tmp_path):
    p = Portfolio(cash=1000.0)
    p.record_equity(1000.0, at="2026-01-01T00:00:00+00:00")
    p.record_equity(1005.0, at="2026-01-01T00:15:00+00:00")
    path = tmp_path / "portfolio.json"
    p.save(path)

    loaded = Portfolio.load_or_create(path, starting_balance=1.0)
    assert loaded.equity_history == p.equity_history
