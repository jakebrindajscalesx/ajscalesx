"""Entrypoint: refresh the tracked-trader leaderboard, check each tracked
wallet for new on-chain buys/sells, and turn qualifying ones into pending
trade proposals with a Telegram alert. Never executes anything itself --
see run_confirm.py for that half. Meant to be run on a schedule (see
../.github/workflows/meme-bot.yml) or by hand: `python run_scan.py`.
"""
from __future__ import annotations

import time

from meme_bot import chain, guardrails, jupiter, leaderboard
from meme_bot.config import load_config
from meme_bot.logger import get_logger
from meme_bot.state import BotState
from meme_bot.telegram_bot import TelegramClient

log = get_logger(__name__)


def main() -> None:
    cfg = load_config()
    state_path = cfg.state_dir / "state.json"
    state = BotState.load_or_create(state_path)
    telegram = TelegramClient(cfg.secrets.telegram_bot_token, cfg.secrets.telegram_chat_id)

    for trade in state.expire_stale_pending():
        telegram.send(f"⌛ Proposal {trade.id} expired unconfirmed ({trade.side} {trade.token_mint[:8]}...).")

    _maybe_refresh_leaderboard(cfg, state, telegram)
    _scan_tracked_wallets(cfg, state, telegram)
    _check_stop_losses(cfg, state, telegram)

    state.save(state_path)


def _maybe_refresh_leaderboard(cfg, state: BotState, telegram: TelegramClient) -> None:
    now = time.time()
    if now - state.leaderboard_refreshed_at < cfg.leaderboard.refresh_minutes * 60:
        return

    entries = leaderboard.fetch_top_traders(
        api_key=cfg.secrets.fomoscope_api_key,
        top_n=cfg.leaderboard.top_n,
        min_win_rate_pct=cfg.leaderboard.min_win_rate_pct,
        min_trades_30d=cfg.leaderboard.min_trades_30d,
    )
    if not entries:
        log.warning("Leaderboard refresh returned nothing; keeping current tracked wallets.")
        return

    new_wallet_set = {e.wallet for e in entries}
    added = new_wallet_set - set(state.tracked_wallets)
    removed = set(state.tracked_wallets) - new_wallet_set

    state.prune_wallets(new_wallet_set)
    for wallet in added:
        # Baseline a newly-tracked wallet against its current latest swap
        # rather than backfilling every historical trade it's ever made.
        recent = chain.fetch_recent_swaps(wallet, cfg.secrets.helius_api_key, since_signature=None, limit=1)
        state.set_last_seen(wallet, recent[0].signature if recent else "")

    state.leaderboard_refreshed_at = now
    if added or removed:
        telegram.send(
            f"📊 Leaderboard refreshed: now tracking {len(new_wallet_set)} wallets "
            f"(+{len(added)} / -{len(removed)})."
        )


def _scan_tracked_wallets(cfg, state: BotState, telegram: TelegramClient) -> None:
    for wallet in list(state.tracked_wallets):
        last_seen = state.last_seen(wallet) or None
        swaps = chain.fetch_recent_swaps(wallet, cfg.secrets.helius_api_key, since_signature=last_seen)
        if not swaps:
            continue

        # swaps is newest-first; walk oldest-first so proposals/alerts are
        # generated in the order they actually happened.
        for swap in reversed(swaps):
            _handle_swap(cfg, state, telegram, swap)

        state.set_last_seen(wallet, swaps[0].signature)


def _handle_swap(cfg, state: BotState, telegram: TelegramClient, swap: chain.SwapEvent) -> None:
    if swap.side == "buy":
        ok, reason = guardrails.can_propose_new_buy(cfg, state, swap.token_mint)
        if not ok:
            log.info(f"Skipping buy signal from {swap.wallet[:8]}...: {reason}")
            return
        trade = state.add_pending_trade(
            wallet=swap.wallet,
            side="buy",
            token_mint=swap.token_mint,
            trade_usd=cfg.sizing.trade_usd,
            timeout_minutes=cfg.execution.confirmation_timeout_minutes,
        )
        telegram.send(
            "🟢 BUY signal\n"
            f"Tracked wallet {swap.wallet[:8]}... bought token {swap.token_mint}\n"
            f"via {swap.source}\n\n"
            f"Proposed mirror: ${cfg.sizing.trade_usd:.2f}\n"
            f"Reply /confirm {trade.id} to execute, /reject {trade.id} to skip.\n"
            f"Expires in {cfg.execution.confirmation_timeout_minutes} min."
        )

    elif swap.side == "sell" and cfg.exit.mirror_sells:
        position = state.positions.get(swap.token_mint)
        if position is None or position.opened_from_wallet != swap.wallet:
            return  # we don't hold this one (from this wallet), nothing to mirror
        trade = state.add_pending_trade(
            wallet=swap.wallet,
            side="sell",
            token_mint=swap.token_mint,
            trade_usd=0.0,  # sells close the whole tracked position, not a fixed $ amount
            timeout_minutes=cfg.execution.confirmation_timeout_minutes,
        )
        telegram.send(
            "🔴 SELL signal\n"
            f"Tracked wallet {swap.wallet[:8]}... sold token {swap.token_mint}\n"
            f"You hold a position opened from this same wallet's earlier buy.\n\n"
            f"Reply /confirm {trade.id} to close it, /reject {trade.id} to hold.\n"
            f"Expires in {cfg.execution.confirmation_timeout_minutes} min."
        )


def _check_stop_losses(cfg, state: BotState, telegram: TelegramClient) -> None:
    for token_mint, position in list(state.positions.items()):
        if any(
            t.token_mint == token_mint and t.status == "pending" and t.side == "sell"
            for t in state.pending_trades.values()
        ):
            continue  # already have a pending sell proposal out for this one

        quote = jupiter.get_quote(
            input_mint=token_mint,
            output_mint=jupiter.SOL_MINT,
            amount=position.token_amount_raw,
            slippage_bps=cfg.execution.slippage_bps,
        )
        if quote is None:
            continue  # can't currently price it (e.g. no liquidity) -- try again next scan

        current_value_sol = quote.out_amount / 1_000_000_000
        if position.cost_sol <= 0:
            continue
        loss_pct = (position.cost_sol - current_value_sol) / position.cost_sol * 100.0
        if loss_pct < cfg.exit.stand_alone_stop_loss_pct:
            continue

        trade = state.add_pending_trade(
            wallet=position.opened_from_wallet,
            side="sell",
            token_mint=token_mint,
            trade_usd=0.0,
            timeout_minutes=cfg.execution.confirmation_timeout_minutes,
        )
        telegram.send(
            "🛑 STOP-LOSS triggered (independent of the tracked wallet)\n"
            f"{token_mint} is down {loss_pct:.1f}% from cost.\n"
            f"Reply /confirm {trade.id} to sell now, /reject {trade.id} to hold anyway.\n"
            f"Expires in {cfg.execution.confirmation_timeout_minutes} min."
        )


if __name__ == "__main__":
    main()
