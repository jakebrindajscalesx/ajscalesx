from meme_bot.chain import _parse_swap

WALLET = "TrackedWallet111"
TOKEN = "SomeMemeToken111"


def test_buy_detected_when_sol_leaves_and_token_arrives():
    tx = {
        "signature": "sig1",
        "type": "SWAP",
        "source": "JUPITER",
        "timestamp": 100,
        "nativeTransfers": [
            {"fromUserAccount": WALLET, "toUserAccount": "pool", "amount": 1_000_000_000}
        ],
        "tokenTransfers": [
            {"mint": TOKEN, "toUserAccount": WALLET, "fromUserAccount": "pool", "tokenAmount": 5000}
        ],
    }
    event = _parse_swap(tx, WALLET)
    assert event is not None
    assert event.side == "buy"
    assert event.token_mint == TOKEN


def test_sell_detected_when_token_leaves_and_sol_arrives():
    tx = {
        "signature": "sig2",
        "type": "SWAP",
        "source": "JUPITER",
        "timestamp": 200,
        "nativeTransfers": [
            {"fromUserAccount": "pool", "toUserAccount": WALLET, "amount": 2_000_000_000}
        ],
        "tokenTransfers": [
            {"mint": TOKEN, "fromUserAccount": WALLET, "toUserAccount": "pool", "tokenAmount": 5000}
        ],
    }
    event = _parse_swap(tx, WALLET)
    assert event is not None
    assert event.side == "sell"
    assert event.token_mint == TOKEN


def test_token_for_token_swap_is_skipped():
    other_token = "OtherToken222"
    tx = {
        "signature": "sig3",
        "type": "SWAP",
        "source": "JUPITER",
        "timestamp": 300,
        "nativeTransfers": [],
        "tokenTransfers": [
            {"mint": TOKEN, "fromUserAccount": WALLET, "toUserAccount": "pool", "tokenAmount": 5000},
            {"mint": other_token, "toUserAccount": WALLET, "fromUserAccount": "pool", "tokenAmount": 3000},
        ],
    }
    assert _parse_swap(tx, WALLET) is None


def test_unrelated_transfers_dont_false_positive():
    tx = {
        "signature": "sig4",
        "type": "SWAP",
        "source": "JUPITER",
        "timestamp": 400,
        "nativeTransfers": [],
        "tokenTransfers": [
            {"mint": TOKEN, "toUserAccount": "someone_else", "fromUserAccount": "pool", "tokenAmount": 5000}
        ],
    }
    assert _parse_swap(tx, WALLET) is None
