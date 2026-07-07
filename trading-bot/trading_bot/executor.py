from __future__ import annotations

from typing import Callable, Protocol

import ccxt

from trading_bot.logger import get_logger
from trading_bot.portfolio import Portfolio

log = get_logger(__name__)

AlertFn = Callable[[str], None]


class Executor(Protocol):
    def open_position(
        self, symbol: str, qty: float, price: float, stop_price: float, take_profit_price: float
    ) -> None: ...

    def check_exits(self, current_prices: dict[str, float]) -> None: ...

    def close_position_manually(self, symbol: str, price: float) -> None: ...


class PaperExecutor:
    """Simulates fills at the current market price against real live prices.
    No real orders are ever placed. This is the default and recommended mode
    until you've watched the bot run and trust its behavior.
    """

    def __init__(self, portfolio: Portfolio, alert_fn: AlertFn | None = None):
        self.portfolio = portfolio
        self.alert_fn = alert_fn or (lambda msg: None)

    def open_position(
        self, symbol: str, qty: float, price: float, stop_price: float, take_profit_price: float
    ) -> None:
        pos = self.portfolio.open_position(symbol, qty, price, stop_price, take_profit_price)
        self.alert_fn(
            f"[PAPER] Opened {symbol}: qty={qty:.6f} @ {price:.4f} "
            f"(stop {stop_price:.4f}, take-profit {take_profit_price:.4f})"
        )
        log.info(f"Paper opened {symbol} qty={qty} price={price}")

    def check_exits(self, current_prices: dict[str, float]) -> None:
        for symbol in list(self.portfolio.positions.keys()):
            pos = self.portfolio.positions[symbol]
            price = current_prices.get(symbol)
            if price is None:
                continue
            if price <= pos.stop_price:
                record = self.portfolio.close_position(symbol, price, "stop_loss")
                self.alert_fn(f"[PAPER] Stop-loss hit {symbol} @ {price:.4f}, pnl={record['pnl']:.2f}")
            elif price >= pos.take_profit_price:
                record = self.portfolio.close_position(symbol, price, "take_profit")
                self.alert_fn(f"[PAPER] Take-profit hit {symbol} @ {price:.4f}, pnl={record['pnl']:.2f}")

    def close_position_manually(self, symbol: str, price: float) -> None:
        if symbol not in self.portfolio.positions:
            return
        record = self.portfolio.close_position(symbol, price, "manual")
        self.alert_fn(f"[PAPER] Manually closed {symbol} @ {price:.4f}, pnl={record['pnl']:.2f}")


class LiveExecutor:
    """Places real orders on the exchange.

    IMPORTANT: this path places real orders and, outside of Binance testnet,
    real money moves. It has NOT been exercised against a live exchange from
    this development environment (no outbound network access to exchange
    APIs here) -- it is written carefully against the documented ccxt/Binance
    order API, but you must validate it on Binance Testnet with small size
    before trusting it with real funds, and watch its logs the first several
    times it trades live.

    Design choice: the stop-loss is placed as a real STOP_LOSS_LIMIT order on
    the exchange, so the position stays protected even if this bot process
    crashes or loses connectivity. Take-profit is monitored and executed by
    the bot itself (cancel the stop order, then market-sell) since OCO order
    support/behavior varies by ccxt version -- if the bot is down, you simply
    don't take profit exactly at target, but the stop-loss protection is
    unaffected.
    """

    STOP_LIMIT_SLIPPAGE = 0.001  # stop-limit price set 0.1% below stop trigger

    def __init__(self, client: ccxt.Exchange, portfolio: Portfolio, alert_fn: AlertFn | None = None):
        self.client = client
        self.portfolio = portfolio
        self.alert_fn = alert_fn or (lambda msg: None)

    def open_position(
        self, symbol: str, qty: float, price: float, stop_price: float, take_profit_price: float
    ) -> None:
        qty_str = self.client.amount_to_precision(symbol, qty)
        qty_adj = float(qty_str)
        if qty_adj <= 0:
            log.warning(f"Position size for {symbol} rounds to 0 at exchange precision, skipping.")
            return

        order = self.client.create_order(symbol, "market", "buy", qty_adj)
        fill_price = float(order.get("average") or order.get("price") or price)

        stop_price_adj = float(self.client.price_to_precision(symbol, stop_price))
        stop_limit_price = float(
            self.client.price_to_precision(symbol, stop_price * (1 - self.STOP_LIMIT_SLIPPAGE))
        )
        stop_order = self.client.create_order(
            symbol,
            "STOP_LOSS_LIMIT",
            "sell",
            qty_adj,
            stop_limit_price,
            {"stopPrice": stop_price_adj},
        )

        self.portfolio.open_position(
            symbol, qty_adj, fill_price, stop_price_adj, take_profit_price, live_order_id=stop_order["id"]
        )
        self.alert_fn(
            f"[LIVE] Opened {symbol}: qty={qty_adj} @ {fill_price:.4f} "
            f"(exchange stop-loss order {stop_order['id']} @ {stop_price_adj:.4f}, "
            f"take-profit target {take_profit_price:.4f})"
        )
        log.info(f"Live opened {symbol} qty={qty_adj} fill_price={fill_price}")

    def check_exits(self, current_prices: dict[str, float]) -> None:
        for symbol in list(self.portfolio.positions.keys()):
            pos = self.portfolio.positions[symbol]
            price = current_prices.get(symbol)

            order_status = None
            if pos.live_order_id:
                try:
                    order_status = self.client.fetch_order(pos.live_order_id, symbol)
                except Exception as exc:
                    log.warning(f"Could not fetch stop order for {symbol}: {exc}")

            if order_status and order_status.get("status") in ("closed", "filled"):
                exit_price = float(order_status.get("average") or pos.stop_price)
                record = self.portfolio.close_position(symbol, exit_price, "stop_loss")
                self.alert_fn(f"[LIVE] Stop-loss filled {symbol} @ {exit_price:.4f}, pnl={record['pnl']:.2f}")
                continue

            if price is None:
                continue

            if price >= pos.take_profit_price:
                try:
                    if pos.live_order_id:
                        self.client.cancel_order(pos.live_order_id, symbol)
                except Exception as exc:
                    log.warning(f"Could not cancel stop order for {symbol} before take-profit: {exc}")
                sell_order = self.client.create_order(symbol, "market", "sell", pos.qty)
                exit_price = float(sell_order.get("average") or price)
                record = self.portfolio.close_position(symbol, exit_price, "take_profit")
                self.alert_fn(f"[LIVE] Take-profit executed {symbol} @ {exit_price:.4f}, pnl={record['pnl']:.2f}")
                continue

            # Safety net: if price has blown well past the stop and the
            # exchange stop order somehow hasn't filled, force an exit
            # rather than let the position ride unprotected.
            if price <= pos.stop_price * 0.98:
                log.warning(f"{symbol} price {price} far past stop {pos.stop_price}, forcing exit.")
                try:
                    if pos.live_order_id:
                        self.client.cancel_order(pos.live_order_id, symbol)
                except Exception as exc:
                    log.warning(f"Could not cancel stop order for {symbol} during forced exit: {exc}")
                sell_order = self.client.create_order(symbol, "market", "sell", pos.qty)
                exit_price = float(sell_order.get("average") or price)
                record = self.portfolio.close_position(symbol, exit_price, "forced_stop")
                self.alert_fn(f"[LIVE] Forced exit {symbol} @ {exit_price:.4f}, pnl={record['pnl']:.2f}")

    def close_position_manually(self, symbol: str, price: float) -> None:
        if symbol not in self.portfolio.positions:
            return
        pos = self.portfolio.positions[symbol]
        try:
            if pos.live_order_id:
                self.client.cancel_order(pos.live_order_id, symbol)
        except Exception as exc:
            log.warning(f"Could not cancel stop order for {symbol} during manual close: {exc}")
        sell_order = self.client.create_order(symbol, "market", "sell", pos.qty)
        exit_price = float(sell_order.get("average") or price)
        record = self.portfolio.close_position(symbol, exit_price, "manual")
        self.alert_fn(f"[LIVE] Manually closed {symbol} @ {exit_price:.4f}, pnl={record['pnl']:.2f}")
