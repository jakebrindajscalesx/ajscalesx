"""Entrypoint: polls Telegram for /confirm, /reject, /pause, /resume,
/status and acts on them -- this is the only place that ever actually
signs and sends a transaction. Meant to run on the same schedule as
run_scan.py (see ../.github/workflows/meme-bot.yml) or by hand:
`python run_confirm.py`.
"""
from __future__ import annotations

from meme_bot import guardrails, jupiter, wallet
from meme_bot.chain import SOL_MINT
from meme_bot.config import Config, load_config
from meme_bot.logger import get_logger
from meme_bot.state import BotState, PendingTrade
from meme_bot.telegram_bot import TelegramClient, parse_command

log = get_logger(__name__)


def main() -> None:
    cfg = load_config()
    state_path = cfg.state_dir / "state.json"
    offset_path = cfg.state_dir / "telegram_offset.json"
    state = BotState.load_or_create(state_path)
    telegram = TelegramClient.load(
        cfg.secrets.telegram_bot_token, cfg.secrets.telegram_chat_id, offset_path
    )

    for raw in telegram.poll_commands():
        cmd = parse_command(raw)
        if cmd is None:
            telegram.send(f"Unrecognized command: {raw}")
            continue
        _handle_command(cfg, state, telegram, cmd)

    telegram.save_offset(offset_path)
    state.save(state_path)


def _handle_command(cfg: Config, state: BotState, telegram: TelegramClient, cmd: dict) -> None:
    if cmd["type"] == "pause":
        state.paused = True
        telegram.send("⏸ Paused. No new buy proposals until /resume. Sell/stop-loss proposals still fire.")
        return

    if cmd["type"] == "resume":
        state.paused = False
        telegram.send("▶️ Resumed.")
        return

    if cmd["type"] == "status":
        telegram.send(_status_text(cfg, state))
        return

    if cmd["type"] == "reject":
        trade = state.pending_trades.get(cmd["trade_id"])
        if trade is None:
            telegram.send(f"No pending trade {cmd['trade_id']}.")
            return
        trade.status = "rejected"
        telegram.send(f"❌ Rejected {trade.id}.")
        return

    if cmd["type"] == "confirm":
        _confirm_trade(cfg, state, telegram, cmd["trade_id"])
        return


def _status_text(cfg: Config, state: BotState) -> str:
    lines = [
        f"Mode: {'DRY RUN' if cfg.dry_run else 'LIVE'}",
        f"Paused: {state.paused}",
        f"Tracked wallets: {len(state.tracked_wallets)}",
        f"Open positions: {len(state.positions)}",
        f"Spent today: ${state.spend_today():.2f} / ${cfg.sizing.max_daily_spend_usd:.2f}",
        f"Pending proposals: {len(state.open_pending_trades())}",
    ]
    return "\n".join(lines)


def _confirm_trade(cfg: Config, state: BotState, telegram: TelegramClient, trade_id: str) -> None:
    ok, reason = guardrails.can_execute(cfg, state, trade_id)
    if not ok:
        telegram.send(f"Can't execute {trade_id}: {reason}")
        return
    trade = state.pending_trades[trade_id]
    trade.status = "confirmed"

    if cfg.dry_run:
        trade.status = "executed"
        trade.note = "dry run -- no real transaction sent"
        telegram.send(
            f"✅ (DRY RUN, no funds moved) Would have executed {trade.side} on {trade.token_mint}."
        )
        return

    if trade.side == "buy":
        _execute_buy(cfg, state, telegram, trade)
    else:
        _execute_sell(cfg, state, telegram, trade)


def _execute_buy(cfg: Config, state: BotState, telegram: TelegramClient, trade: PendingTrade) -> None:
    sol_price = jupiter.get_sol_usd_price()
    if sol_price is None:
        trade.status = "failed"
        trade.note = "could not fetch SOL/USD price"
        telegram.send(f"❌ {trade.id} failed: couldn't fetch SOL/USD price, try again shortly.")
        return

    sol_amount = trade.trade_usd / sol_price
    lamports = int(sol_amount * 1_000_000_000)

    quote = jupiter.get_quote(SOL_MINT, trade.token_mint, lamports, cfg.execution.slippage_bps)
    if quote is None:
        trade.status = "failed"
        trade.note = "no swap route available"
        telegram.send(f"❌ {trade.id} failed: Jupiter couldn't route this swap (no liquidity?).")
        return

    signature = _sign_and_submit(cfg, telegram, trade, quote)
    if signature is None:
        return

    state.open_position(trade.token_mint, trade.wallet, cost_sol=sol_amount, token_amount_raw=quote.out_amount)
    state.record_spend(trade.trade_usd)
    trade.status = "executed"
    trade.tx_signature = signature
    telegram.send(
        f"✅ Bought {trade.token_mint} for ~{sol_amount:.4f} SOL (${trade.trade_usd:.2f}).\n"
        f"https://solscan.io/tx/{signature}"
    )


def _execute_sell(cfg: Config, state: BotState, telegram: TelegramClient, trade: PendingTrade) -> None:
    position = state.positions.get(trade.token_mint)
    if position is None:
        trade.status = "failed"
        trade.note = "position no longer open"
        telegram.send(f"❌ {trade.id} failed: no open position in {trade.token_mint} anymore.")
        return

    quote = jupiter.get_quote(
        trade.token_mint, SOL_MINT, position.token_amount_raw, cfg.execution.slippage_bps
    )
    if quote is None:
        trade.status = "failed"
        trade.note = "no swap route available"
        telegram.send(f"❌ {trade.id} failed: Jupiter couldn't route this swap (no liquidity? possible rug).")
        return

    signature = _sign_and_submit(cfg, telegram, trade, quote)
    if signature is None:
        return

    proceeds_sol = quote.out_amount / 1_000_000_000
    pnl_sol = proceeds_sol - position.cost_sol
    state.close_position(trade.token_mint)
    trade.status = "executed"
    trade.tx_signature = signature
    telegram.send(
        f"✅ Sold {trade.token_mint} for ~{proceeds_sol:.4f} SOL "
        f"({'+' if pnl_sol >= 0 else ''}{pnl_sol:.4f} SOL vs cost).\n"
        f"https://solscan.io/tx/{signature}"
    )


def _sign_and_submit(cfg: Config, telegram: TelegramClient, trade: PendingTrade, quote: jupiter.Quote) -> str | None:
    unsigned = jupiter.build_swap_transaction(quote, cfg.secrets.wallet_public_key)
    if unsigned is None:
        trade.status = "failed"
        trade.note = "failed to build swap transaction"
        telegram.send(f"❌ {trade.id} failed: couldn't build the swap transaction.")
        return None

    keypair = wallet.load_keypair(cfg.secrets.wallet_private_key)
    signature = wallet.sign_and_send(unsigned, keypair, cfg.secrets.helius_api_key)
    if signature is None:
        trade.status = "failed"
        trade.note = "sign/submit failed"
        telegram.send(f"❌ {trade.id} failed: transaction was not accepted by the network.")
        return None

    confirmed = wallet.confirm(signature, cfg.secrets.helius_api_key)
    if not confirmed:
        telegram.send(
            f"⚠️ {trade.id} submitted but not confirmed within the timeout -- "
            f"check https://solscan.io/tx/{signature} manually before trusting this bot's state for it."
        )
    return signature


if __name__ == "__main__":
    main()
