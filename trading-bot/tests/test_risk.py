from datetime import datetime, timezone

from trading_bot.risk import (
    DailyCircuitBreaker,
    can_open_position,
    position_size_qty,
    stop_loss_price,
    take_profit_price,
)


def test_position_size_qty_basic():
    qty = position_size_qty(equity=1000, price=100, position_size_pct=2.0)
    assert qty == 0.2  # 2% of 1000 = 20 notional / 100 price


def test_position_size_qty_zero_inputs():
    assert position_size_qty(equity=0, price=100, position_size_pct=2.0) == 0.0
    assert position_size_qty(equity=1000, price=0, position_size_pct=2.0) == 0.0


def test_stop_and_take_profit_prices():
    assert stop_loss_price(100, 2.0) == 98.0
    assert take_profit_price(100, 4.0) == 104.0


def test_can_open_position():
    assert can_open_position(0, 3) is True
    assert can_open_position(2, 3) is True
    assert can_open_position(3, 3) is False


def test_circuit_breaker_trips_on_daily_loss():
    breaker = DailyCircuitBreaker(max_daily_loss_pct=5.0)
    now = datetime(2026, 1, 1, tzinfo=timezone.utc)

    assert breaker.update(1000.0, now) is False  # sets day start equity

    assert breaker.update(960.0, now) is False  # 4% loss, under threshold
    assert breaker.tripped is False

    assert breaker.update(940.0, now) is True  # 6% loss, over threshold
    assert breaker.tripped is True


def test_circuit_breaker_resets_on_new_day():
    breaker = DailyCircuitBreaker(max_daily_loss_pct=5.0)
    day1 = datetime(2026, 1, 1, tzinfo=timezone.utc)
    day2 = datetime(2026, 1, 2, tzinfo=timezone.utc)

    breaker.update(1000.0, day1)
    breaker.update(900.0, day1)
    assert breaker.tripped is True

    # new day rolls over: fresh baseline, breaker no longer tripped
    assert breaker.update(900.0, day2) is False
    assert breaker.tripped is False


def test_circuit_breaker_manual_reset():
    breaker = DailyCircuitBreaker(max_daily_loss_pct=5.0)
    now = datetime(2026, 1, 1, tzinfo=timezone.utc)
    breaker.update(1000.0, now)
    breaker.update(900.0, now)
    assert breaker.tripped is True

    breaker.reset()
    assert breaker.tripped is False
