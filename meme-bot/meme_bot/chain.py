from __future__ import annotations

from dataclasses import dataclass

import requests

from meme_bot.logger import get_logger

log = get_logger(__name__)

# Solana's native mint isn't a real SPL token account, but every tool in this
# ecosystem (Jupiter included) uses this placeholder address to mean "SOL".
SOL_MINT = "So11111111111111111111111111111111111111112"
USDC_MINT = "EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v"
_STABLE_OR_BASE_MINTS = {SOL_MINT, USDC_MINT}


@dataclass
class SwapEvent:
    signature: str
    wallet: str
    side: str  # "buy" or "sell"
    token_mint: str
    timestamp: int
    source: str  # e.g. "JUPITER", "RAYDIUM", "PUMP_FUN"


def fetch_recent_swaps(
    wallet: str, api_key: str, since_signature: str | None, limit: int = 20
) -> list[SwapEvent]:
    """Uses Helius's Enhanced Transactions API to pull a wallet's recent
    parsed transactions and filter down to swaps. Returns newest-first.
    since_signature, if given, stops paging once that signature is reached
    (Helius's `before` param already returns newest-first, so we just trim).

    Detecting "buy vs sell" and "which mint": a swap is a BUY of whichever
    non-SOL/USDC mint the wallet's tokenTransfers balance increased by, and
    a SELL if it decreased. Swaps that don't touch SOL or USDC on either leg
    (a token-for-token swap) are skipped -- mirroring those would require
    knowing which leg the caller cares about, which enhanced tx data alone
    doesn't make unambiguous.
    """
    if not api_key:
        log.warning("No Helius API key configured; cannot fetch on-chain activity.")
        return []

    try:
        resp = requests.get(
            f"https://api.helius.xyz/v0/addresses/{wallet}/transactions",
            params={"api-key": api_key, "limit": limit},
            timeout=20,
        )
        resp.raise_for_status()
        txs = resp.json()
    except Exception as exc:
        log.warning(f"Helius fetch failed for {wallet}: {exc}")
        return []

    events: list[SwapEvent] = []
    for tx in txs:
        sig = tx.get("signature", "")
        if since_signature and sig == since_signature:
            break
        if tx.get("type") != "SWAP":
            continue
        event = _parse_swap(tx, wallet)
        if event:
            events.append(event)

    return events


def _parse_swap(tx: dict, wallet: str) -> SwapEvent | None:
    transfers = tx.get("tokenTransfers", []) or []
    native = tx.get("nativeTransfers", []) or []

    net_by_mint: dict[str, float] = {}
    for t in transfers:
        mint = t.get("mint")
        amount = t.get("tokenAmount", 0) or 0
        if not mint:
            continue
        if t.get("toUserAccount") == wallet:
            net_by_mint[mint] = net_by_mint.get(mint, 0) + amount
        if t.get("fromUserAccount") == wallet:
            net_by_mint[mint] = net_by_mint.get(mint, 0) - amount

    sol_net = 0.0
    for n in native:
        amt_sol = (n.get("amount", 0) or 0) / 1_000_000_000
        if n.get("toUserAccount") == wallet:
            sol_net += amt_sol
        if n.get("fromUserAccount") == wallet:
            sol_net -= amt_sol
    if sol_net:
        net_by_mint[SOL_MINT] = net_by_mint.get(SOL_MINT, 0) + sol_net

    base_delta = sum(v for m, v in net_by_mint.items() if m in _STABLE_OR_BASE_MINTS)
    other_mints = {m: v for m, v in net_by_mint.items() if m not in _STABLE_OR_BASE_MINTS and abs(v) > 0}

    if len(other_mints) != 1 or base_delta == 0:
        # Not a clean base-token <-> meme-token swap (e.g. a token-for-token
        # route, an LP action, or a wash with no net base movement) -- skip
        # rather than guess.
        return None

    token_mint, token_delta = next(iter(other_mints.items()))
    side = "buy" if token_delta > 0 else "sell"

    return SwapEvent(
        signature=tx.get("signature", ""),
        wallet=wallet,
        side=side,
        token_mint=token_mint,
        timestamp=tx.get("timestamp", 0),
        source=tx.get("source", "UNKNOWN"),
    )
