from __future__ import annotations

import time
from typing import Callable

from alpaca.trading.client import TradingClient
from alpaca.trading.enums import OrderSide, OrderStatus, TimeInForce
from alpaca.trading.requests import MarketOrderRequest, StopLimitOrderRequest

from trading_bot.logger import get_logger
from trading_bot.portfolio import Portfolio

log = get_logger(__name__)

AlertFn = Callable[[str], None]


class AlpacaExecutor:
    """Places real orders through Alpaca -- paper or live, same code path
    either way (the TradingClient it's built with points at Alpaca's paper
    or live environment based on config.mode; this class doesn't know or
    care which). Running the exact same order-placement logic every day in
    paper mode, not just once you flip to live, is deliberate -- it's the
    only way real bugs in this path get caught before real money is on
    the line.

    Design choice: a real exchange-side stop-loss order can only be
    attached to a WHOLE-SHARE order -- Alpaca's fractional/notional orders
    can't carry one. This executor therefore always rounds position size
    down to whole shares and skips the trade entirely if that rounds to
    zero, rather than ever holding an unprotected fractional position
    between scheduled cycles (which, since this bot runs on a scheduler
    rather than continuously, could be hours).

    Design choice: the stop-loss is placed as a real GTC stop-limit order
    on the exchange, so the position stays protected between scheduled
    runs, not just while this process happens to be executing. Take-profit
    is monitored and executed by the bot itself (cancel the stop order,
    then market-sell) since Alpaca's OCO/bracket order support doesn't
    cleanly fit this bot's per-cycle decision model -- if a cycle is
    skipped, you simply don't take profit exactly at target, but the
    stop-loss protection is unaffected.

    IMPORTANT: this has NOT been exercised against a real Alpaca account
    from this development environment (no outbound network access to
    exchange APIs here) -- it is written carefully against the documented
    alpaca-py API, but validate it in paper mode (the default) and watch
    its logs the first several times it trades before trusting it, the
    same discipline that applies before ever going live with real money.
    """

    STOP_LIMIT_SLIPPAGE = 0.001  # stop-limit price set 0.1% below stop trigger
    FILL_POLL_ATTEMPTS = 5
    FILL_POLL_DELAY_SECONDS = 1

    def __init__(
        self,
        client: TradingClient,
        portfolio: Portfolio,
        alert_fn: AlertFn | None = None,
        fill_poll_attempts: int | None = None,
        fill_poll_delay_seconds: float | None = None,
    ):
        self.client = client
        self.portfolio = portfolio
        self.alert_fn = alert_fn or (lambda msg: None)
        self.fill_poll_attempts = fill_poll_attempts if fill_poll_attempts is not None else self.FILL_POLL_ATTEMPTS
        self.fill_poll_delay_seconds = (
            fill_poll_delay_seconds if fill_poll_delay_seconds is not None else self.FILL_POLL_DELAY_SECONDS
        )

    def open_position(
        self, symbol: str, qty: float, price: float, stop_price: float, take_profit_price: float
    ) -> None:
        qty_whole = int(qty)
        if qty_whole <= 0:
            log.warning(
                f"Position size for {symbol} rounds to 0 whole shares at ${price:.2f}/share "
                f"(target qty {qty:.4f}) -- skipping. Stocks need a whole share to carry a real "
                f"exchange-side stop-loss order, so this bot never buys a fractional share."
            )
            return

        order = self.client.submit_order(
            MarketOrderRequest(symbol=symbol, qty=qty_whole, side=OrderSide.BUY, time_in_force=TimeInForce.DAY)
        )
        fill_price = self._poll_for_fill_price(order.id) or price

        # From here on, real money has already bought a real position on
        # the exchange -- whatever happens next, we must not lose track of
        # it. Everything below is best-effort protection layered on top of
        # a fill that has already happened, not a precondition for
        # recording it.
        live_order_id = None
        try:
            stop_order = self.client.submit_order(
                StopLimitOrderRequest(
                    symbol=symbol,
                    qty=qty_whole,
                    side=OrderSide.SELL,
                    time_in_force=TimeInForce.GTC,
                    stop_price=round(stop_price, 2),
                    limit_price=round(stop_price * (1 - self.STOP_LIMIT_SLIPPAGE), 2),
                )
            )
            live_order_id = str(stop_order.id)
        except Exception as exc:
            log.error(f"Stop-loss order failed for {symbol} after the buy already filled: {exc}")

        self.portfolio.open_position(
            symbol, qty_whole, fill_price, round(stop_price, 2), take_profit_price, live_order_id=live_order_id
        )

        if live_order_id is None:
            self.alert_fn(
                f"URGENT: Opened {symbol} qty={qty_whole} @ {fill_price:.2f} but the exchange "
                f"stop-loss order FAILED to place. This position is currently UNPROTECTED on the "
                f"exchange -- the bot will keep watching price and force-sell if it falls well past "
                f"{stop_price:.2f}, but until then it has no exchange-side protection. Check the "
                f"logs and consider placing a manual stop order now."
            )
        else:
            self.alert_fn(
                f"Opened {symbol}: qty={qty_whole} @ {fill_price:.2f} "
                f"(exchange stop-loss order {live_order_id} @ {stop_price:.2f}, "
                f"take-profit target {take_profit_price:.2f})"
            )
        log.info(f"Opened {symbol} qty={qty_whole} fill_price={fill_price} live_order_id={live_order_id}")

    def _poll_for_fill_price(self, order_id) -> float | None:
        """Market orders don't always report a fill price synchronously --
        poll briefly rather than record an approximate price for a real
        fill. Falls back to the pre-trade quoted price (by the caller) if
        it never confirms within the poll window -- logged clearly, not
        silent."""
        for _ in range(self.fill_poll_attempts):
            try:
                order = self.client.get_order_by_id(order_id)
            except Exception as exc:
                log.warning(f"Could not poll order {order_id} for fill price: {exc}")
                return None
            if order.filled_avg_price is not None:
                return float(order.filled_avg_price)
            time.sleep(self.fill_poll_delay_seconds)
        log.warning(f"Order {order_id} did not report a fill price within the poll window.")
        return None

    def _cancel_stop_order(self, pos) -> None:
        if not pos.live_order_id:
            return
        try:
            self.client.cancel_order_by_id(pos.live_order_id)
        except Exception as exc:
            log.warning(f"Could not cancel stop order for {pos.symbol}: {exc}")

    def _market_sell(self, symbol: str, qty: float, fallback_price: float) -> float:
        order = self.client.submit_order(
            MarketOrderRequest(symbol=symbol, qty=qty, side=OrderSide.SELL, time_in_force=TimeInForce.DAY)
        )
        return self._poll_for_fill_price(order.id) or fallback_price

    def check_exits(self, current_prices: dict[str, float]) -> None:
        for symbol in list(self.portfolio.positions.keys()):
            pos = self.portfolio.positions[symbol]
            price = current_prices.get(symbol)

            order = None
            if pos.live_order_id:
                try:
                    order = self.client.get_order_by_id(pos.live_order_id)
                except Exception as exc:
                    log.warning(f"Could not fetch stop order for {symbol}: {exc}")

            if order and order.status == OrderStatus.FILLED:
                exit_price = float(order.filled_avg_price or pos.stop_price)
                record = self.portfolio.close_position(symbol, exit_price, "stop_loss")
                self.alert_fn(f"Stop-loss filled {symbol} @ {exit_price:.2f}, pnl={record['pnl']:.2f}")
                continue

            if price is None:
                continue

            if price >= pos.take_profit_price:
                self._cancel_stop_order(pos)
                exit_price = self._market_sell(symbol, pos.qty, price)
                record = self.portfolio.close_position(symbol, exit_price, "take_profit")
                self.alert_fn(f"Take-profit executed {symbol} @ {exit_price:.2f}, pnl={record['pnl']:.2f}")
                continue

            # Safety net: if price has blown well past the stop and the
            # exchange stop order somehow hasn't filled (or, per the
            # unprotected-position path above, never existed), force an
            # exit rather than let the position ride unprotected.
            if price <= pos.stop_price * 0.98:
                log.warning(f"{symbol} price {price} far past stop {pos.stop_price}, forcing exit.")
                self._cancel_stop_order(pos)
                exit_price = self._market_sell(symbol, pos.qty, price)
                record = self.portfolio.close_position(symbol, exit_price, "forced_stop")
                self.alert_fn(f"Forced exit {symbol} @ {exit_price:.2f}, pnl={record['pnl']:.2f}")

    def close_position_manually(self, symbol: str, price: float) -> None:
        if symbol not in self.portfolio.positions:
            return
        pos = self.portfolio.positions[symbol]
        self._cancel_stop_order(pos)
        exit_price = self._market_sell(symbol, pos.qty, price)
        record = self.portfolio.close_position(symbol, exit_price, "manual")
        self.alert_fn(f"Manually closed {symbol} @ {exit_price:.2f}, pnl={record['pnl']:.2f}")
