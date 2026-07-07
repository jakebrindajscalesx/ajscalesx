# Trading Bot

A background trading bot for Binance: fetches market data, generates buy
signals from a trained ML model (plus optional manual signals you send via
Telegram), sizes and opens positions with a stop-loss and take-profit on
every trade, and a daily loss circuit breaker that halts new trades if
losses get too big in a day.

## Read this first

**No bot can guarantee you won't lose money.** Stop-loss and take-profit
orders bound risk per trade, and the daily circuit breaker bounds risk per
day, but slippage, exchange outages, gaps in volatile crypto markets, or bugs
can still cause losses beyond those limits. Treat every number below
(position size, stop-loss %, daily loss cap) as risk you are choosing to
accept, not a guarantee.

**This code defaults to paper trading**: simulated fills against real live
prices, no real orders, no real money. Run it in paper mode for a while and
actually look at `state/portfolio.json` / the trade log before ever
switching `mode: live` in `config.yaml`.

**The live-trading order path (`LiveExecutor` in `trading_bot/executor.py`)
was written against the documented ccxt/Binance API but could not be
exercised against a real exchange from the environment this was built in**
(no outbound network access to exchange APIs there). Before trusting it with
real funds: run it against
[Binance Spot Testnet](https://testnet.binance.vision/) first
(`exchange.testnet: true` in config, fake funds, real-like API), watch it
place and manage several trades, and only then consider mainnet — starting
with a small amount you can afford to lose entirely.

You generally need to be 18 to open a funded exchange/brokerage account —
paper trading and testnet don't require that, so they're the right place to
start regardless.

## What it does *not* do

It does not scrape social media / X posts and auto-trade off them. That
pattern (auto-buying whenever an influencer posts) is a common vector for
pump-and-dump schemes targeting exactly this kind of bot. Instead, there's a
manual signal channel: you personally decide something's worth acting on and
tell the bot via Telegram, with all the same risk controls applied.

## Setup

```bash
cd trading-bot
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

cp config.example.yaml config.yaml
cp .env.example .env
```

`config.yaml` controls behavior (mode, symbols, risk parameters). `.env`
holds secrets (exchange API keys, Telegram token) and is gitignored — never
commit it.

### Train the signal model

```bash
python train_model.py
```

Fetches historical candles (public data, no API key needed) and trains a
classifier that predicts whether price is likely to rise enough, soon
enough, to be worth a long trade. Re-run this periodically (e.g. weekly) to
retrain on fresh data — markets drift, an old model gets stale.

### Run in paper mode (default, recommended starting point)

```bash
python main.py
```

Runs continuously, logging to stdout and `state/trading_bot.log`, and
persisting portfolio state to `state/portfolio.json` so it survives
restarts. Stop with Ctrl-C — it saves state before exiting.

### Telegram alerts and manual signals (optional but recommended)

1. Message [@BotFather](https://t.me/BotFather) on Telegram, create a bot,
   get its token.
2. Send your new bot any message, then visit
   `https://api.telegram.org/bot<token>/getUpdates` in a browser to find your
   `chat.id`.
3. Put `TELEGRAM_BOT_TOKEN` and `TELEGRAM_CHAT_ID` in `.env`, set
   `telegram.enabled: true` in `config.yaml`.

Commands you can send the bot in that chat:

- `/signal BTC/USDT buy` — manually trigger a buy (still goes through normal
  position sizing, max-positions, and circuit-breaker checks)
- `/signal BTC/USDT close` — manually close an open position
- `/pause` / `/resume` — stop/allow new positions; `/resume` also clears a
  tripped circuit breaker
- `/status` — current equity, cash, open positions, pause/breaker state

### Going live

1. Set `exchange.testnet: true`, `mode: live` in `config.yaml`, add real
   [Binance Testnet](https://testnet.binance.vision/) API keys to `.env`.
   Run it, watch it trade with fake funds for a while.
2. Only after that, set `exchange.testnet: false` with real mainnet API
   keys (trading-only permissions, no withdrawal permission, on the API key
   itself) to go live with real money. Start with small `risk.position_size_pct`
   and a small account balance.

### Running in the background

`systemd/trading-bot.service` is a template unit file — edit the paths in it
for your machine, then:

```bash
sudo cp systemd/trading-bot.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable --now trading-bot
sudo journalctl -u trading-bot -f   # tail logs
```

## Risk settings (`config.yaml` -> `risk`)

- `position_size_pct` — % of account equity risked per new position
- `stop_loss_pct` / `take_profit_pct` — exit thresholds per position
- `max_open_positions` — cap on simultaneous positions
- `max_daily_loss_pct` — the circuit breaker: halts new entries for the rest
  of the UTC day once realized+unrealized loss hits this % of the day's
  starting equity (existing positions' own stops still apply)

## Tests

```bash
pip install pytest
pytest tests/ -v
```

Covers risk math (position sizing, stop/take-profit prices, circuit
breaker), portfolio accounting (open/close/equity/persistence), feature
computation, and the model training/signal pipeline against synthetic data.

## Architecture

```
main.py               orchestration loop
trading_bot/
  config.py           loads config.yaml + .env
  exchange.py          ccxt Binance client (market data + orders)
  data.py              rolling candle history per symbol
  features.py          technical-indicator feature computation
  model.py             train/save/load/predict the ML signal model
  signals.py            Signal dataclass + model-based signal generation
  risk.py              position sizing, stop/take-profit prices, circuit breaker
  portfolio.py          cash/positions/trade-log state, JSON persistence
  executor.py           PaperExecutor (simulated) / LiveExecutor (real orders)
  telegram_bot.py        alerts + manual signal/command parsing
train_model.py          offline: fetch history, train, save model
```
