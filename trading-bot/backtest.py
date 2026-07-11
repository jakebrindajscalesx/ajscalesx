"""Walk-forward backtest: trains on the first 80% of history, then
simulates the bot's actual signal + risk + filter logic candle-by-candle on
the held-out last 20% it never trained on. Reports what would really have
happened -- real win rate, return, and drawdown -- instead of asking anyone
to take a strategy's effectiveness on faith.

    python backtest.py

This is a research tool, not the live bot: it doesn't place any orders,
paper or real. Run it whenever you change model/risk/filter settings in
config.yaml to see how the change would have performed historically.

Caveats that keep this honest, not just optimistic:
  - Past performance on this data does not predict future performance --
    markets change. A good backtest is a reason for cautious confidence,
    not a guarantee.
  - Assumes fills at each candle's close with no slippage and no fees --
    real execution will be slightly worse than this.
  - When a candle's high and low both cross the take-profit and stop-loss
    in the same candle, the stop-loss is assumed to hit first (the
    conservative assumption -- avoids overstating performance).
  - Each symbol is backtested independently; it doesn't model shared
    max_open_positions / equity across symbols the way live trading does.
"""
from __future__ import annotations

import sys
from dataclasses import dataclass, field

import pandas as pd

from trading_bot.config import load_config
from trading_bot.exchange import build_exchange
from trading_bot.features import FEATURE_COLUMNS, compute_features
from trading_bot.filters import passes_all_filters
from trading_bot.logger import get_logger
from trading_bot.model import predict_proba_up, train_model
from trading_bot.risk import position_size_qty, stop_loss_price, take_profit_price
from train_model import fetch_history

log = get_logger("backtest")

BACKTEST_CANDLES = 3000
TRAIN_FRACTION = 0.8


@dataclass
class BacktestResult:
    symbol: str
    num_trades: int = 0
    wins: int = 0
    losses: int = 0
    gross_profit: float = 0.0
    gross_loss: float = 0.0
    starting_equity: float = 1000.0
    ending_equity: float = 1000.0
    peak_equity: float = 1000.0
    max_drawdown_pct: float = 0.0
    trades: list = field(default_factory=list)

    @property
    def win_rate(self) -> float:
        return self.wins / self.num_trades if self.num_trades else 0.0

    @property
    def total_return_pct(self) -> float:
        return (self.ending_equity - self.starting_equity) / self.starting_equity * 100

    @property
    def profit_factor(self) -> float:
        return self.gross_profit / self.gross_loss if self.gross_loss > 0 else float("inf")

    def report(self) -> str:
        return (
            f"\n{self.symbol}\n"
            f"{'-' * len(self.symbol)}\n"
            f"  Trades:        {self.num_trades}  ({self.wins} win / {self.losses} loss, "
            f"win rate {self.win_rate * 100:.1f}%)\n"
            f"  Total return:  {self.total_return_pct:+.2f}%  "
            f"(${self.starting_equity:.2f} -> ${self.ending_equity:.2f})\n"
            f"  Max drawdown:  {self.max_drawdown_pct:.2f}%\n"
            f"  Profit factor: {self._profit_factor_str()}"
        )

    def _profit_factor_str(self) -> str:
        if self.num_trades == 0:
            return "N/A (no trades)"
        if self.gross_loss == 0:
            return f"{self.profit_factor:.2f}  (no losing trades yet)"
        return f"{self.profit_factor:.2f}"


def backtest_symbol(config, df: pd.DataFrame, symbol: str, starting_equity: float = 1000.0) -> BacktestResult:
    split_idx = int(len(df) * TRAIN_FRACTION)
    train_df, test_df = df.iloc[:split_idx], df.iloc[split_idx:]

    clf, metrics = train_model(train_df, config.model.horizon_candles, config.model.label_return_threshold)
    log.info(f"{symbol}: trained on {len(train_df)} candles, test accuracy {metrics['test_accuracy']:.3f}")

    feat = compute_features(df).dropna(subset=FEATURE_COLUMNS)
    test_feat = feat[feat.index >= test_df.index[0]]

    result = BacktestResult(symbol=symbol, starting_equity=starting_equity, ending_equity=starting_equity,
                             peak_equity=starting_equity)
    cash = starting_equity
    position = None  # dict: qty, entry_price, stop_price, take_profit_price

    for _, row in test_feat.iterrows():
        price, high, low = row["close"], row["high"], row["low"]

        if position is not None:
            hit_stop = low <= position["stop_price"]
            hit_take_profit = high >= position["take_profit_price"]
            exit_price = None
            if hit_stop:
                exit_price = position["stop_price"]
            elif hit_take_profit:
                exit_price = position["take_profit_price"]
            if exit_price is not None:
                proceeds = position["qty"] * exit_price
                cost = position["qty"] * position["entry_price"]
                pnl = proceeds - cost
                cash += proceeds
                result.num_trades += 1
                if pnl >= 0:
                    result.wins += 1
                    result.gross_profit += pnl
                else:
                    result.losses += 1
                    result.gross_loss += -pnl
                result.trades.append({"entry": position["entry_price"], "exit": exit_price, "pnl": pnl})
                position = None

        equity = cash + (position["qty"] * price if position else 0)
        result.peak_equity = max(result.peak_equity, equity)
        drawdown = (result.peak_equity - equity) / result.peak_equity * 100 if result.peak_equity > 0 else 0
        result.max_drawdown_pct = max(result.max_drawdown_pct, drawdown)

        if position is None:
            proba = predict_proba_up(clf, row)
            confident = proba >= config.model.min_confidence
            confirmed = passes_all_filters(
                row,
                require_trend=config.model.require_trend_confirmation,
                require_volume=config.model.require_volume_confirmation,
            )
            if confident and confirmed:
                qty = position_size_qty(cash, price, config.risk.position_size_pct)
                if qty > 0:
                    cash -= qty * price
                    position = {
                        "qty": qty,
                        "entry_price": price,
                        "stop_price": stop_loss_price(price, config.risk.stop_loss_pct),
                        "take_profit_price": take_profit_price(price, config.risk.take_profit_pct),
                    }

    final_price = test_feat["close"].iloc[-1] if len(test_feat) else starting_equity
    result.ending_equity = cash + (position["qty"] * final_price if position else 0)
    return result


def main() -> int:
    config = load_config()
    client = build_exchange(config)

    results = []
    for symbol in config.symbols:
        log.info(f"Fetching history for {symbol}...")
        df = fetch_history(client, symbol, config.timeframe, BACKTEST_CANDLES)
        if len(df) < 200:
            log.warning(f"Not enough history for {symbol} ({len(df)} candles), skipping.")
            continue
        try:
            result = backtest_symbol(config, df, symbol)
        except ValueError as exc:
            log.error(f"Backtest failed for {symbol}: {exc}")
            continue
        results.append(result)
        print(result.report())

    if results:
        combined_return = sum(r.total_return_pct for r in results) / len(results)
        combined_trades = sum(r.num_trades for r in results)
        print(f"\nAverage return across {len(results)} symbol(s): {combined_return:+.2f}%  "
              f"({combined_trades} total trades)")
        print(
            "\nRemember: this is what the current model/risk/filter settings would have\n"
            "done on past data, not a promise about the future."
        )

    return 0


if __name__ == "__main__":
    sys.exit(main())
