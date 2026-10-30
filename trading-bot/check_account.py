"""One-off diagnostic: prints your full real Alpaca account state -- cash,
buying power, all open positions, and recent orders -- including anything
you placed yourself directly through Alpaca's own site/app, not just
orders this bot placed.

    python check_account.py

Useful because the bot's own state/portfolio.json only tracks orders it
placed itself; it has no visibility into trades made directly in the same
account outside the bot. Doesn't place any orders -- read-only.
"""
from __future__ import annotations

import sys

from alpaca.trading.enums import QueryOrderStatus
from alpaca.trading.requests import GetOrdersRequest

from trading_bot.config import load_config
from trading_bot.exchange import build_exchange


def main() -> int:
    config = load_config()
    client = build_exchange(config)

    account = client.trading.get_account()
    print(f"\nAccount ({'LIVE' if config.is_live else 'PAPER'} mode)")
    print(f"  Cash:             ${float(account.cash):.2f}")
    print(f"  Buying power:     ${float(account.buying_power):.2f}")
    print(f"  Portfolio value:  ${float(account.portfolio_value):.2f}")

    positions = client.trading.get_all_positions()
    print(f"\nOpen positions ({len(positions)}):")
    if not positions:
        print("  (none)")
    for pos in positions:
        print(
            f"  {pos.symbol}: {pos.qty} shares @ avg ${float(pos.avg_entry_price):.2f}"
            f" -- market value ${float(pos.market_value):.2f},"
            f" unrealized P&L ${float(pos.unrealized_pl):.2f}"
        )

    orders = client.trading.get_orders(GetOrdersRequest(status=QueryOrderStatus.ALL, limit=100))
    print(f"\nRecent orders ({len(orders)}, most recent first):")
    if not orders:
        print("  (none)")
    for order in orders:
        filled = f" filled @ ${float(order.filled_avg_price):.2f}" if order.filled_avg_price else ""
        qty = order.qty or order.notional
        print(f"  {order.created_at}  {order.symbol}  {order.side.value} {qty}  [{order.status.value}]{filled}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
