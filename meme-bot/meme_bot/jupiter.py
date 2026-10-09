from __future__ import annotations

from dataclasses import dataclass

import requests

from meme_bot.logger import get_logger

log = get_logger(__name__)

QUOTE_URL = "https://quote-api.jup.ag/v6/quote"
SWAP_URL = "https://quote-api.jup.ag/v6/swap"
# Jupiter's price API has moved/renamed endpoints before -- if this starts
# 404ing, check https://station.jup.ag/docs/apis/price-api for the current
# URL rather than assuming the bot itself is broken.
PRICE_URL = "https://api.jup.ag/price/v2"
SOL_MINT = "So11111111111111111111111111111111111111112"


@dataclass
class Quote:
    input_mint: str
    output_mint: str
    in_amount: int  # raw base units (lamports for SOL, token's own decimals otherwise)
    out_amount: int
    price_impact_pct: float
    raw: dict


def get_quote(input_mint: str, output_mint: str, amount: int, slippage_bps: int) -> Quote | None:
    """amount is in the input token's raw base units (e.g. lamports if
    input_mint is SOL). Returns None if Jupiter can't route the swap right
    now (e.g. the token has no liquidity) -- that's a legitimate outcome for
    a brand-new meme coin, not necessarily a bug."""
    try:
        resp = requests.get(
            QUOTE_URL,
            params={
                "inputMint": input_mint,
                "outputMint": output_mint,
                "amount": amount,
                "slippageBps": slippage_bps,
            },
            timeout=15,
        )
        resp.raise_for_status()
        data = resp.json()
    except Exception as exc:
        log.warning(f"Jupiter quote failed ({input_mint} -> {output_mint}): {exc}")
        return None

    if "outAmount" not in data:
        log.warning(f"Jupiter returned no route ({input_mint} -> {output_mint}): {data}")
        return None

    return Quote(
        input_mint=input_mint,
        output_mint=output_mint,
        in_amount=int(data["inAmount"]),
        out_amount=int(data["outAmount"]),
        price_impact_pct=float(data.get("priceImpactPct", 0) or 0),
        raw=data,
    )


def build_swap_transaction(quote: Quote, user_public_key: str) -> str | None:
    """Returns a base64-encoded, unsigned (versioned) transaction ready for
    meme_bot.wallet to sign and send, or None on failure."""
    try:
        resp = requests.post(
            SWAP_URL,
            json={
                "quoteResponse": quote.raw,
                "userPublicKey": user_public_key,
                "wrapAndUnwrapSol": True,
                "dynamicComputeUnitLimit": True,
                "prioritizationFeeLamports": "auto",
            },
            timeout=15,
        )
        resp.raise_for_status()
        data = resp.json()
    except Exception as exc:
        log.warning(f"Jupiter swap-transaction build failed: {exc}")
        return None

    tx = data.get("swapTransaction")
    if not tx:
        log.warning(f"Jupiter swap response had no transaction: {data}")
        return None
    return tx


def get_sol_usd_price() -> float | None:
    """Used only to translate config's trade_usd into a lamport amount for
    the buy-side quote. Returns None (rather than guessing) on failure --
    callers must abort the trade in that case, not fall back to a stale or
    made-up price."""
    try:
        resp = requests.get(PRICE_URL, params={"ids": SOL_MINT}, timeout=10)
        resp.raise_for_status()
        data = resp.json()
        return float(data["data"][SOL_MINT]["price"])
    except Exception as exc:
        log.warning(f"SOL/USD price lookup failed: {exc}")
        return None
