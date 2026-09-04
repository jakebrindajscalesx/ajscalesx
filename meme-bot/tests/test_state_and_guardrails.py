from meme_bot.config import Config, SizingConfig
from meme_bot.guardrails import can_execute, can_propose_new_buy
from meme_bot.state import BotState


def make_cfg(**sizing_overrides) -> Config:
    cfg = Config()
    cfg.sizing = SizingConfig(**{**cfg.sizing.__dict__, **sizing_overrides})
    return cfg


def test_daily_spend_blocks_once_cap_reached():
    cfg = make_cfg(trade_usd=10, max_daily_spend_usd=15)
    state = BotState()

    ok, _ = can_propose_new_buy(cfg, state, "tokenA")
    assert ok

    state.record_spend(10)
    ok, reason = can_propose_new_buy(cfg, state, "tokenB")
    assert not ok
    assert "max_daily_spend_usd" in reason


def test_daily_spend_resets_on_new_day():
    cfg = make_cfg(trade_usd=10, max_daily_spend_usd=15)
    state = BotState()
    state.record_spend(10)
    state.spend_day = "2020-01-01"  # simulate a stale day
    assert state.spend_today() == 0.0  # rolled over, doesn't carry stale spend forward


def test_max_open_positions_blocks_new_buy():
    cfg = make_cfg(trade_usd=10, max_daily_spend_usd=1000)
    cfg.sizing.max_open_positions = 1
    state = BotState()
    state.open_position("tokenA", "walletX", cost_sol=0.1, token_amount_raw=1000)

    ok, reason = can_propose_new_buy(cfg, state, "tokenB")
    assert not ok
    assert "max_open_positions" in reason


def test_already_holding_token_blocks_duplicate_buy():
    cfg = make_cfg(trade_usd=10, max_daily_spend_usd=1000)
    state = BotState()
    state.open_position("tokenA", "walletX", cost_sol=0.1, token_amount_raw=1000)

    ok, reason = can_propose_new_buy(cfg, state, "tokenA")
    assert not ok
    assert "already holding" in reason


def test_paused_blocks_new_buy():
    cfg = make_cfg(trade_usd=10, max_daily_spend_usd=1000)
    state = BotState()
    state.paused = True

    ok, reason = can_propose_new_buy(cfg, state, "tokenA")
    assert not ok
    assert "paused" in reason


def test_can_execute_rejects_unknown_or_non_pending_trade():
    cfg = make_cfg()
    state = BotState()
    ok, reason = can_execute(cfg, state, "doesnotexist")
    assert not ok
    assert "no such pending trade" in reason

    trade = state.add_pending_trade("walletX", "buy", "tokenA", 10, timeout_minutes=15)
    trade.status = "rejected"
    ok, reason = can_execute(cfg, state, trade.id)
    assert not ok
    assert "already" in reason


def test_pending_trade_expiry():
    state = BotState()
    trade = state.add_pending_trade("walletX", "buy", "tokenA", 10, timeout_minutes=15)
    trade.expires_at = 0  # force it into the past
    expired = state.expire_stale_pending()
    assert trade in expired
    assert trade.status == "expired"


def test_state_round_trips_through_json(tmp_path):
    state = BotState()
    state.set_last_seen("walletX", "sig123")
    state.open_position("tokenA", "walletX", cost_sol=0.5, token_amount_raw=42)
    trade = state.add_pending_trade("walletX", "sell", "tokenA", 0, timeout_minutes=15)
    state.record_spend(7.5)

    path = tmp_path / "state.json"
    state.save(path)
    loaded = BotState.load_or_create(path)

    assert loaded.tracked_wallets["walletX"] == "sig123"
    assert loaded.positions["tokenA"].cost_sol == 0.5
    assert loaded.pending_trades[trade.id].side == "sell"
    assert loaded.spend_usd_today == 7.5
