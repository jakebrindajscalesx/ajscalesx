# Trading Bot

A background trading bot for crypto (Kraken by default, ccxt supports many
exchanges): fetches market data, generates buy signals from a trained ML
model (plus optional manual signals you send via Telegram), sizes and opens
positions with a stop-loss and take-profit on every trade, and a daily loss
circuit breaker that halts new trades if losses get too big in a day.

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

**Why Kraken instead of Binance**: this was originally built against Binance,
but Binance returns an HTTP 451 and refuses all requests from US-based IPs
(including GitHub Actions' runners) as a matter of their own policy — not
something to route around. Kraken serves US IPs and works the same way
through ccxt, so it's the default for anything running on GitHub Actions or
US infrastructure generally. If you're running this somewhere with a non-US
IP and specifically want Binance, set `exchange.name: binance` in
`config.yaml`.

**The live-trading order path (`LiveExecutor` in `trading_bot/executor.py`)
was written against the documented ccxt/Binance order API and has NOT been
adapted or tested for Kraken's order types** — going live needs real work
first regardless of which exchange, but especially if you're on Kraken,
which also has no public spot testnet/sandbox the way Binance does (so
"dry-run against fake funds" isn't available there the same way). Come back
and we can work through that properly when you're actually ready to go live
— for now this is a paper-trading tool.

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

### Check whether any of this actually works: backtest it

```bash
python backtest.py
```

Trains on the first 80% of history and simulates the exact signal + risk +
filter logic candle-by-candle on the last 20%, which the model never saw
during training. Reports real numbers: win rate, total return, max
drawdown, profit factor. Run this after any change to `config.yaml`'s
`model` or `risk` settings to see how the change would have performed
historically, rather than trusting that it's an improvement.

This doesn't place any orders and doesn't touch `state/` — it's a pure
research report. It's also not a promise: good historical performance is a
reason for more confidence, not a guarantee of future results. Also
available as a one-click GitHub Actions run (see below) if you don't want
to install anything locally.

Four filters can run on top of the model's confidence score, each a
config-toggleable hard gate in `config.yaml` under `model:`:

- `require_trend_confirmation` / `require_volume_confirmation` — **on by
  default.** Only buy when price is above its own longer-term trend, and
  only when volume is rising to confirm conviction behind the move.
- `require_liquidity_sweep` / `require_equilibrium_discount` — **off by
  default.** Only buy right after price wicks below a recent swing low and
  closes back above it (a "sweep and reverse" pattern), and/or only when
  price is in the cheaper half of its recent range rather than already
  extended. These are specific, checkable price patterns — not claims about
  anyone's intent — pulled from retail day-trading material and included
  because they're well-defined enough to test, not because of who taught
  them. They're off by default because stacked with the other two filters
  they can make signals very rare, especially with Kraken's limited history
  (see below). Turn them on and compare against off using `backtest.py`
  before trusting either setting.

Deliberately **not** implemented from that material: cross-index/cross-asset
divergence timing (would need restructuring signal generation to compare
symbols against each other mid-cycle — a reasonable future addition, not
done here), fixed-session trading windows (the source material is for
NYSE-hours index trading; crypto trades 24/7 and the transplant seemed weak
enough not to be worth a config option), and anything from that material
that was really a course/prop-firm-affiliate sales pitch rather than a
trading rule.

### Run in paper mode (default, recommended starting point)

```bash
python main.py
```

Runs continuously, logging to stdout and `state/trading_bot.log`, and
persisting portfolio state to `state/portfolio.json` so it survives
restarts. Stop with Ctrl-C — it saves state before exiting.

### Or: run it for free on GitHub Actions, no server needed

If you don't have anywhere to run a long-lived process, `.github/workflows/trading-bot.yml`
runs `run_once.py` (a single decision cycle, not the infinite loop) on a
schedule using GitHub's free compute, commits the updated state back to this
branch each time, and publishes a dashboard to GitHub Pages.

- The workflow file has to live on the repo's **default branch** for its
  schedule to fire (a GitHub requirement) — it was added there separately;
  it checks out and runs this branch's code rather than merging it in.
- No account/signup beyond GitHub itself, and no credentials are required
  for paper mode.
- Trigger it manually anytime from the repo's Actions tab -> "Trading Bot
  Cycle" -> "Run workflow", instead of waiting for the schedule.
- View the dashboard at `https://<your-username>.github.io/<repo>/trading-bot/`
  once it's run at least once. It has real charts, not just numbers: an
  equity-over-time line chart (hover for the exact value at any point) and a
  green/red bar chart of recent trade P&L, both built from the equity history
  the bot records on every cycle.
- Optional: add `TELEGRAM_BOT_TOKEN` / `TELEGRAM_CHAT_ID` as repo secrets
  (Settings -> Secrets and variables -> Actions) and set `telegram.enabled: true`
  in `config.yaml` to get alerts there too.
- `run_once.py` retrains the model automatically if it's missing or more
  than 7 days old, so this is self-maintaining — nothing to run manually
  after initial setup.
- `.github/workflows/trading-bot-backtest.yml` runs `backtest.py` the same
  way, on demand only (Actions tab -> "Trading Bot Backtest" -> "Run
  workflow") — results appear on that run's summary page, and also publish a
  "Backtest" section on the dashboard with a per-symbol equity curve chart so
  you can see what the current strategy would have done on historical data,
  not just the live numbers.

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
