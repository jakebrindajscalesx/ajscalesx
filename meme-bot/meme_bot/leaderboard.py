from __future__ import annotations

from dataclasses import dataclass

import requests

from meme_bot.logger import get_logger

log = get_logger(__name__)

# NOTE: api.fomoscope.xyz is unreachable from the environment this bot was
# written in, so this endpoint path and the field names below could not be
# verified against the live API. Before relying on this for real trades,
# open https://api.fomoscope.xyz/docs yourself and confirm/adjust:
#   - the leaderboard endpoint path and query params
#   - the JSON field names read in _parse_entry() below
#   - the header name for FOMOSCOPE_API_KEY, if you have one (currently
#     sent as both a Bearer token and an X-API-Key header since the docs
#     couldn't be checked -- harmless to send both, but confirm which one
#     the service actually reads)
BASE_URL = "https://api.fomoscope.xyz/v1"


@dataclass
class TraderEntry:
    wallet: str
    win_rate_pct: float
    trades_30d: int
    pnl_30d_usd: float


def fetch_top_traders(
    api_key: str = "",
    top_n: int = 10,
    min_win_rate_pct: float = 0,
    min_trades_30d: int = 0,
) -> list[TraderEntry]:
    """Returns up to top_n wallets from Fomoscope's trader leaderboard,
    filtered by the minimums, sorted best-first. Returns an empty list
    (rather than raising) on any request/parsing failure so a leaderboard
    outage degrades to "track nothing new this cycle" instead of crashing
    the whole scan."""
    headers = {}
    if api_key:
        headers["Authorization"] = f"Bearer {api_key}"
        headers["X-API-Key"] = api_key

    try:
        resp = requests.get(
            f"{BASE_URL}/leaderboard",
            params={"window": "30d", "sort": "pnl", "limit": max(top_n * 3, 30)},
            headers=headers,
            timeout=15,
        )
        resp.raise_for_status()
        payload = resp.json()
    except Exception as exc:
        log.warning(f"Fomoscope leaderboard fetch failed: {exc}")
        return []

    raw_entries = payload.get("data", payload if isinstance(payload, list) else [])
    entries: list[TraderEntry] = []
    for raw in raw_entries:
        entry = _parse_entry(raw)
        if entry is None:
            continue
        if entry.win_rate_pct < min_win_rate_pct:
            continue
        if entry.trades_30d < min_trades_30d:
            continue
        entries.append(entry)

    entries.sort(key=lambda e: e.pnl_30d_usd, reverse=True)
    return entries[:top_n]


def _parse_entry(raw: dict) -> TraderEntry | None:
    try:
        wallet = raw.get("wallet") or raw.get("address") or raw.get("wallet_address")
        if not wallet:
            return None
        return TraderEntry(
            wallet=wallet,
            win_rate_pct=float(raw.get("win_rate", raw.get("win_rate_pct", 0)) or 0),
            trades_30d=int(raw.get("trades_30d", raw.get("trade_count", 0)) or 0),
            pnl_30d_usd=float(raw.get("pnl_usd", raw.get("pnl_30d_usd", 0)) or 0),
        )
    except (TypeError, ValueError) as exc:
        log.warning(f"Skipping unparseable leaderboard entry: {exc}")
        return None
