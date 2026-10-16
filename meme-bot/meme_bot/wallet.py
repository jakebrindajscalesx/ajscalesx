from __future__ import annotations

import base64
import time

import requests
from solders.keypair import Keypair
from solders.transaction import VersionedTransaction

from meme_bot.logger import get_logger

log = get_logger(__name__)


def load_keypair(private_key: str) -> Keypair:
    """Accepts either a base58 secret key string (what Phantom's "Export
    Private Key" gives you) or a JSON array of 64 ints (what the Solana CLI
    writes to a keyfile)."""
    private_key = private_key.strip()
    if private_key.startswith("["):
        import json

        return Keypair.from_bytes(bytes(json.loads(private_key)))
    return Keypair.from_base58_string(private_key)


def rpc_url(helius_api_key: str) -> str:
    return f"https://mainnet.helius-rpc.com/?api-key={helius_api_key}"


def get_sol_balance(public_key: str, helius_api_key: str) -> float | None:
    try:
        resp = requests.post(
            rpc_url(helius_api_key),
            json={
                "jsonrpc": "2.0",
                "id": 1,
                "method": "getBalance",
                "params": [public_key],
            },
            timeout=15,
        )
        resp.raise_for_status()
        lamports = resp.json()["result"]["value"]
        return lamports / 1_000_000_000
    except Exception as exc:
        log.warning(f"Balance check failed: {exc}")
        return None


def sign_and_send(unsigned_tx_b64: str, keypair: Keypair, helius_api_key: str) -> str | None:
    """Signs a Jupiter-built unsigned versioned transaction and submits it.
    Returns the transaction signature on success, None on failure. Does NOT
    wait for finalization -- call confirm() separately if you need to know
    the swap actually landed before, e.g., updating position state."""
    try:
        raw = base64.b64decode(unsigned_tx_b64)
        unsigned = VersionedTransaction.from_bytes(raw)
        signed = VersionedTransaction(unsigned.message, [keypair])
        signed_b64 = base64.b64encode(bytes(signed)).decode("ascii")
    except Exception as exc:
        log.error(f"Failed to sign transaction: {exc}")
        return None

    try:
        resp = requests.post(
            rpc_url(helius_api_key),
            json={
                "jsonrpc": "2.0",
                "id": 1,
                "method": "sendTransaction",
                "params": [
                    signed_b64,
                    {"encoding": "base64", "skipPreflight": False, "maxRetries": 3},
                ],
            },
            timeout=20,
        )
        resp.raise_for_status()
        body = resp.json()
        if "error" in body:
            log.error(f"sendTransaction rejected: {body['error']}")
            return None
        return body["result"]
    except Exception as exc:
        log.error(f"Failed to submit transaction: {exc}")
        return None


def confirm(signature: str, helius_api_key: str, timeout_seconds: int = 45) -> bool:
    """Polls getSignatureStatuses until the transaction is confirmed/
    finalized, fails, or the timeout elapses. Returns False (not
    necessarily failed -- possibly just slow) on timeout, so callers should
    treat False as "unknown, check the explorer" rather than "definitely
    failed."""
    deadline = time.monotonic() + timeout_seconds
    while time.monotonic() < deadline:
        try:
            resp = requests.post(
                rpc_url(helius_api_key),
                json={
                    "jsonrpc": "2.0",
                    "id": 1,
                    "method": "getSignatureStatuses",
                    "params": [[signature]],
                },
                timeout=15,
            )
            resp.raise_for_status()
            status = resp.json()["result"]["value"][0]
        except Exception as exc:
            log.warning(f"Status check failed: {exc}")
            time.sleep(3)
            continue

        if status is not None:
            if status.get("err"):
                log.error(f"Transaction {signature} failed on-chain: {status['err']}")
                return False
            confirmation = status.get("confirmationStatus")
            if confirmation in ("confirmed", "finalized"):
                return True
        time.sleep(3)

    log.warning(f"Transaction {signature} not confirmed within {timeout_seconds}s")
    return False
