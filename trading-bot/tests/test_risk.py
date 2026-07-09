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


def test_circuit_breaker_persists_across_stateless_runs(tmp_path):
    """Simulates a scheduled job: a fresh DailyCircuitBreaker instance each
    run must not reset its day-start baseline, or it could never trip."""
    path = tmp_path / "circuit_breaker.json"
    now = datetime(2026, 1, 1, 12, 0, tzinfo=timezone.utc)

    run1 = DailyCircuitBreaker.load_or_create(path, max_daily_loss_pct=5.0)
    run1.update(1000.0, now)  # sets day-start equity to 1000
    run1.save(path)

    # a new process, later the same day, sees a big loss
    run2 = DailyCircuitBreaker.load_or_create(path, max_daily_loss_pct=5.0)
    later_same_day = datetime(2026, 1, 1, 13, 0, tzinfo=timezone.utc)
    assert run2.update(940.0, later_same_day) is True  # 6% loss from the persisted 1000 baseline
    run2.save(path)

    # a third process the next day should get a fresh baseline
    run3 = DailyCircuitBreaker.load_or_create(path, max_daily_loss_pct=5.0)
    next_day = datetime(2026, 1, 2, tzinfo=timezone.utc)
    assert run3.update(940.0, next_day) is False
    assert run3.tripped is False


def test_circuit_breaker_load_or_create_missing_file(tmp_path):
    path = tmp_path / "does_not_exist.json"
    breaker = DailyCircuitBreaker.load_or_create(path, max_daily_loss_pct=5.0)
    assert breaker.tripped is False
