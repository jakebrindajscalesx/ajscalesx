import pytest

from trading_bot.config import load_config

MINIMAL_CONFIG = """
mode: {mode}
exchange:
  name: kraken
  testnet: {testnet}
symbols:
  - BTC/USDT
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
  starting_balance_usdt: 1000
"""


def _write_config(tmp_path, mode="paper", testnet=True):
    path = tmp_path / "config.yaml"
    path.write_text(MINIMAL_CONFIG.format(mode=mode, testnet=str(testnet).lower()))
    return path


def test_load_config_reads_exchange_credentials_from_generic_env_vars(tmp_path, monkeypatch):
    # Regression test: credentials used to be read from BINANCE_API_KEY/
    # SECRET even after the default exchange moved to Kraken, which meant a
    # live deploy on any non-Binance exchange needed keys stashed under a
    # misleadingly-named env var.
    monkeypatch.setenv("EXCHANGE_API_KEY", "test-key")
    monkeypatch.setenv("EXCHANGE_API_SECRET", "test-secret")
    config = load_config(_write_config(tmp_path))
    assert config.exchange.api_key == "test-key"
    assert config.exchange.api_secret == "test-secret"


def test_load_config_live_mode_without_testnet_requires_credentials(tmp_path, monkeypatch):
    monkeypatch.delenv("EXCHANGE_API_KEY", raising=False)
    monkeypatch.delenv("EXCHANGE_API_SECRET", raising=False)
    with pytest.raises(ValueError, match="EXCHANGE_API_KEY"):
        load_config(_write_config(tmp_path, mode="live", testnet=False))


def test_load_config_live_mode_with_testnet_does_not_require_credentials(tmp_path, monkeypatch):
    monkeypatch.delenv("EXCHANGE_API_KEY", raising=False)
    monkeypatch.delenv("EXCHANGE_API_SECRET", raising=False)
    config = load_config(_write_config(tmp_path, mode="live", testnet=True))
    assert config.is_live
    assert config.exchange.api_key == ""


def test_load_config_rejects_invalid_mode(tmp_path):
    path = tmp_path / "config.yaml"
    path.write_text(MINIMAL_CONFIG.format(mode="not_a_real_mode", testnet="true"))
    with pytest.raises(ValueError, match="mode"):
        load_config(path)
