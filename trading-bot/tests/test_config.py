import pytest

from trading_bot.config import load_config

MINIMAL_CONFIG = """
mode: {mode}
symbols:
  - SPY
timeframe: 15m
model:
  path: models/model.joblib
  min_confidence: 0.6
  horizon_candles: 4
  label_return_threshold: 0.006
risk:
  position_size_pct: 2.0
  stop_loss_pct: 2.0
  take_profit_pct: 4.0
  max_open_positions: 3
  max_daily_loss_pct: 5.0
paper:
  starting_balance_usd: 1000
"""


def _write_config(tmp_path, mode="paper"):
    path = tmp_path / "config.yaml"
    path.write_text(MINIMAL_CONFIG.format(mode=mode))
    return path


def test_load_config_reads_exchange_credentials_from_generic_env_vars(tmp_path, monkeypatch):
    monkeypatch.setenv("EXCHANGE_API_KEY", "test-key")
    monkeypatch.setenv("EXCHANGE_API_SECRET", "test-secret")
    config = load_config(_write_config(tmp_path))
    assert config.exchange.api_key == "test-key"
    assert config.exchange.api_secret == "test-secret"


def test_load_config_requires_credentials_even_in_paper_mode(tmp_path, monkeypatch):
    # Regression test: unlike Kraken's public keyless data, Alpaca requires
    # an API key/secret to fetch market data at all -- including paper mode,
    # not just live. Config loading must fail loudly, not silently proceed
    # with an exchange client that can't fetch anything.
    monkeypatch.delenv("EXCHANGE_API_KEY", raising=False)
    monkeypatch.delenv("EXCHANGE_API_SECRET", raising=False)
    with pytest.raises(ValueError, match="EXCHANGE_API_KEY"):
        load_config(_write_config(tmp_path, mode="paper"))


def test_load_config_requires_credentials_in_live_mode(tmp_path, monkeypatch):
    monkeypatch.delenv("EXCHANGE_API_KEY", raising=False)
    monkeypatch.delenv("EXCHANGE_API_SECRET", raising=False)
    with pytest.raises(ValueError, match="EXCHANGE_API_KEY"):
        load_config(_write_config(tmp_path, mode="live"))


def test_load_config_rejects_invalid_mode(tmp_path, monkeypatch):
    monkeypatch.setenv("EXCHANGE_API_KEY", "test-key")
    monkeypatch.setenv("EXCHANGE_API_SECRET", "test-secret")
    path = tmp_path / "config.yaml"
    path.write_text(MINIMAL_CONFIG.format(mode="not_a_real_mode"))
    with pytest.raises(ValueError, match="mode"):
        load_config(path)
