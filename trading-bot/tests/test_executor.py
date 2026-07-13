import pytest

from trading_bot.executor import LiveExecutor, PaperExecutor
from trading_bot.portfolio import Portfolio


class _FakeClient:
    """Minimal stand-in for the slice of ccxt.Exchange LiveExecutor uses."""

    def __init__(self, exchange_id, stop_order_should_fail=False):
        self.id = exchange_id
        self.stop_order_should_fail = stop_order_should_fail
        self.created_orders = []
        self.cancelled_order_ids = []
        self._next_order_id = 1

    def amount_to_precision(self, symbol, qty):
        return str(qty)

    def price_to_precision(self, symbol, price):
        return str(price)

    def create_order(self, symbol, type_, side, amount, price=None, params=None):
        if type_ != "market" and self.stop_order_should_fail:
            raise RuntimeError("exchange rejected stop order")
        order_id = f"order-{self._next_order_id}"
        self._next_order_id += 1
        self.created_orders.append(
            {"symbol": symbol, "type": type_, "side": side, "amount": amount, "price": price, "params": params}
        )
        return {"id": order_id, "average": price or 100.0}

    def fetch_order(self, order_id, symbol):
        return {"id": order_id, "status": "open"}

    def cancel_order(self, order_id, symbol):
        self.cancelled_order_ids.append(order_id)


def test_live_executor_refuses_to_buy_on_unsupported_exchange():
    client = _FakeClient("some_unlisted_exchange")
    portfolio = Portfolio(cash=1000.0)
    executor = LiveExecutor(client, portfolio)

    with pytest.raises(NotImplementedError):
        executor.open_position("BTC/USDT", 0.01, 100.0, 98.0, 104.0)

    # Critically: no real buy should have been placed either.
    assert client.created_orders == []
    assert portfolio.positions == {}


def test_live_executor_places_market_buy_and_kraken_stop_loss_limit_order():
    client = _FakeClient("kraken")
    portfolio = Portfolio(cash=1000.0)
    executor = LiveExecutor(client, portfolio)

    executor.open_position("BTC/USDT", 0.01, 100.0, 98.0, 104.0)

    assert len(client.created_orders) == 2
    buy, stop = client.created_orders
    assert buy["type"] == "market" and buy["side"] == "buy"
    assert stop["type"] == "stop-loss-limit" and stop["side"] == "sell"

    assert "BTC/USDT" in portfolio.positions
    assert portfolio.positions["BTC/USDT"].live_order_id is not None


def test_live_executor_still_records_position_when_stop_order_fails():
    # Regression test: the buy already executes with real money before the
    # stop order is attempted. If the stop order call throws, the position
    # must still be recorded locally -- losing track of a real fill because
    # a *protective* order failed would be worse than the failure itself.
    client = _FakeClient("kraken", stop_order_should_fail=True)
    alerts = []
    portfolio = Portfolio(cash=1000.0)
    executor = LiveExecutor(client, portfolio, alert_fn=alerts.append)

    executor.open_position("BTC/USDT", 0.01, 100.0, 98.0, 104.0)

    # The buy still went through even though the stop order failed.
    assert len(client.created_orders) == 1
    assert client.created_orders[0]["type"] == "market"

    assert "BTC/USDT" in portfolio.positions
    assert portfolio.positions["BTC/USDT"].live_order_id is None

    assert any("URGENT" in msg for msg in alerts)


def test_live_executor_check_exits_force_sells_unprotected_position_past_stop():
    client = _FakeClient("kraken", stop_order_should_fail=True)
    portfolio = Portfolio(cash=1000.0)
    executor = LiveExecutor(client, portfolio)
    executor.open_position("BTC/USDT", 0.01, 100.0, 98.0, 104.0)
    assert portfolio.positions["BTC/USDT"].live_order_id is None

    # Price craters well past the (unenforced, since the exchange order
    # failed) stop -- the bot's own safety net should force a market sell.
    executor.check_exits({"BTC/USDT": 96.0})

    assert "BTC/USDT" not in portfolio.positions
    sell_orders = [o for o in client.created_orders if o["side"] == "sell"]
    assert len(sell_orders) == 1
    assert portfolio.trade_log[-1]["reason"] == "forced_stop"


def test_paper_executor_unaffected_by_live_executor_changes():
    portfolio = Portfolio(cash=1000.0)
    executor = PaperExecutor(portfolio)
    executor.open_position("BTC/USDT", 0.01, 100.0, 98.0, 104.0)
    assert "BTC/USDT" in portfolio.positions
