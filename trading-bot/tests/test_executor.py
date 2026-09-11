import uuid

from trading_bot.executor import AlpacaExecutor
from trading_bot.portfolio import Portfolio


class _FakeOrder:
    def __init__(self, order_id, filled_avg_price=None, status="new"):
        self.id = order_id
        self.filled_avg_price = filled_avg_price
        self.status = status


class _FakeTradingClient:
    """Minimal stand-in for the slice of alpaca.trading.client.TradingClient
    AlpacaExecutor uses."""

    def __init__(self, stop_order_should_fail=False):
        self.stop_order_should_fail = stop_order_should_fail
        self.submitted_orders = []
        self.cancelled_order_ids = []
        self._orders_by_id = {}

    def submit_order(self, order_data):
        from alpaca.trading.enums import OrderStatus

        if order_data.type.value == "stop_limit" and self.stop_order_should_fail:
            raise RuntimeError("exchange rejected stop order")

        order_id = uuid.uuid4()
        # Market orders fill immediately in this fake, at the requested
        # price if one was implied, else a fixed stub price.
        fill_price = getattr(order_data, "limit_price", None) or 100.0
        status = OrderStatus.FILLED if order_data.type.value == "market" else OrderStatus.NEW
        order = _FakeOrder(order_id, filled_avg_price=fill_price if status == OrderStatus.FILLED else None, status=status)
        self.submitted_orders.append(order_data)
        self._orders_by_id[str(order_id)] = order
        return order

    def get_order_by_id(self, order_id):
        return self._orders_by_id[str(order_id)]

    def cancel_order_by_id(self, order_id):
        self.cancelled_order_ids.append(order_id)


def _fast_executor(client, portfolio, alert_fn=None):
    # fill_poll_delay_seconds=0 so tests don't actually sleep.
    return AlpacaExecutor(client, portfolio, alert_fn=alert_fn, fill_poll_attempts=2, fill_poll_delay_seconds=0)


def test_open_position_rounds_down_to_whole_shares_and_skips_if_zero():
    client = _FakeTradingClient()
    portfolio = Portfolio(cash=1000.0)
    executor = _fast_executor(client, portfolio)

    # price implies qty < 1 share
    executor.open_position("AAPL", qty=0.4, price=200.0, stop_price=196.0, take_profit_price=208.0)

    assert client.submitted_orders == []
    assert portfolio.positions == {}


def test_open_position_places_market_buy_and_gtc_stop_limit_sell():
    client = _FakeTradingClient()
    portfolio = Portfolio(cash=1000.0)
    executor = _fast_executor(client, portfolio)

    executor.open_position("AAPL", qty=2.7, price=100.0, stop_price=98.0, take_profit_price=104.0)

    assert len(client.submitted_orders) == 2
    buy, stop = client.submitted_orders
    assert buy.side.value == "buy" and buy.type.value == "market" and buy.qty == 2
    assert stop.side.value == "sell" and stop.type.value == "stop_limit" and stop.time_in_force.value == "gtc"
    assert stop.qty == 2

    assert "AAPL" in portfolio.positions
    pos = portfolio.positions["AAPL"]
    assert pos.qty == 2
    assert pos.live_order_id is not None


def test_open_position_still_records_fill_when_stop_order_fails():
    # Regression test, same shape as the crypto-era fix: the buy already
    # executes with real money before the stop order is attempted. If the
    # stop order call throws, the position must still be recorded locally.
    client = _FakeTradingClient(stop_order_should_fail=True)
    alerts = []
    portfolio = Portfolio(cash=1000.0)
    executor = _fast_executor(client, portfolio, alert_fn=alerts.append)

    executor.open_position("AAPL", qty=2.0, price=100.0, stop_price=98.0, take_profit_price=104.0)

    assert len(client.submitted_orders) == 1
    assert "AAPL" in portfolio.positions
    assert portfolio.positions["AAPL"].live_order_id is None
    assert any("URGENT" in msg for msg in alerts)


def test_check_exits_closes_position_when_stop_order_reports_filled():
    client = _FakeTradingClient()
    portfolio = Portfolio(cash=1000.0)
    executor = _fast_executor(client, portfolio)
    executor.open_position("AAPL", qty=2.0, price=100.0, stop_price=98.0, take_profit_price=104.0)

    stop_order_id = portfolio.positions["AAPL"].live_order_id
    from alpaca.trading.enums import OrderStatus

    client._orders_by_id[stop_order_id].status = OrderStatus.FILLED
    client._orders_by_id[stop_order_id].filled_avg_price = 98.0

    executor.check_exits({"AAPL": 98.0})

    assert "AAPL" not in portfolio.positions
    assert portfolio.trade_log[-1]["reason"] == "stop_loss"


def test_check_exits_takes_profit_and_cancels_stop_order():
    client = _FakeTradingClient()
    portfolio = Portfolio(cash=1000.0)
    executor = _fast_executor(client, portfolio)
    executor.open_position("AAPL", qty=2.0, price=100.0, stop_price=98.0, take_profit_price=104.0)
    stop_order_id = portfolio.positions["AAPL"].live_order_id

    executor.check_exits({"AAPL": 105.0})

    assert "AAPL" not in portfolio.positions
    assert portfolio.trade_log[-1]["reason"] == "take_profit"
    assert stop_order_id in client.cancelled_order_ids


def test_check_exits_force_sells_unprotected_position_past_stop():
    client = _FakeTradingClient(stop_order_should_fail=True)
    portfolio = Portfolio(cash=1000.0)
    executor = _fast_executor(client, portfolio)
    executor.open_position("AAPL", qty=2.0, price=100.0, stop_price=98.0, take_profit_price=104.0)
    assert portfolio.positions["AAPL"].live_order_id is None

    executor.check_exits({"AAPL": 96.0})

    assert "AAPL" not in portfolio.positions
    assert portfolio.trade_log[-1]["reason"] == "forced_stop"


def test_close_position_manually_cancels_stop_and_sells():
    client = _FakeTradingClient()
    portfolio = Portfolio(cash=1000.0)
    executor = _fast_executor(client, portfolio)
    executor.open_position("AAPL", qty=2.0, price=100.0, stop_price=98.0, take_profit_price=104.0)
    stop_order_id = portfolio.positions["AAPL"].live_order_id

    executor.close_position_manually("AAPL", price=101.0)

    assert "AAPL" not in portfolio.positions
    assert portfolio.trade_log[-1]["reason"] == "manual"
    assert stop_order_id in client.cancelled_order_ids
