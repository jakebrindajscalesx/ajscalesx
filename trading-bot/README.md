# Trading Bot

A background trading bot for US stocks/ETFs via Alpaca: fetches market data,
generates buy signals from a trained ML model (plus optional manual signals
you send via Telegram), sizes and opens positions with a stop-loss and
take-profit on every trade, and a daily loss circuit breaker that halts new
trades if losses get too big in a day.

## Read this first

**No bot can guarantee you won't lose money.** Stop-loss and take-profit
orders bound risk per trade, and the daily circuit breaker bounds risk per
day, but slippage, exchange outages, gaps at the market open, or bugs can
still cause losses beyond those limits. Treat every number below (position
size, stop-loss %, daily loss cap) as risk you are choosing to accept, not a
guarantee.

**This code defaults to paper trading**: orders are placed through Alpaca's
own free paper-trading environment (simulated fills, fake money, but a real
order lifecycle) -- no real money moves. Run it in paper mode for a while and
actually look at `state/portfolio.json` / the trade log before ever
switching `mode: live` in `config.yaml`.

**Why Alpaca**: unlike crypto exchanges, US stock/ETF market data has no
public keyless equivalent -- Alpaca is a real broker with a genuine paper
trading environment (not a from-scratch simulation bolted onto public
prices), a straightforward API, and a free tier that covers everything this
bot needs. It does require creating a free account (see Setup below) -- that
account requirement is real, not something this bot can route around the way
it could with crypto's public ticker data.

**Stocks only trade during market hours** (NYSE, roughly 9:30am-4pm ET on
weekdays, closed holidays) -- unlike crypto's 24/7 market. The bot checks
Alpaca's market clock every cycle and does nothing at all outside those
hours (no fetch, no trades, no new dashboard data) rather than act on stale
or nonexistent prices.

**Stock positions are always whole shares, on purpose.** A real
exchange-side stop-loss order can only be attached to a whole-share order --
Alpaca's fractional/notional orders can't carry one. This bot always rounds
position size down to whole shares and skips the trade entirely if that
rounds to zero, rather than ever holding a fractional position with no
broker-side protection between scheduled runs. Practical consequence: with a
small `paper.starting_balance_usd` and a low `risk.position_size_pct`, some
higher-priced symbols may rarely or never clear a whole share -- that's
expected, not a bug. Raise the starting balance or position size, or pick
lower-priced symbols, if you want a symbol to trade more often.

**The live-trading order path (`AlpacaExecutor` in `trading_bot/executor.py`)
has NOT been exercised against a real Alpaca account** from the environment
this was built in (no outbound network access to exchange APIs there) -- it
was written carefully against Alpaca's documented API, but going live needs
real validation first: watch it run in paper mode (the default), read its
logs, and only change `mode: live` once you trust its behavior.

You generally need to be 18 to open any Alpaca account, even paper --
brokerage accounts require it regardless of whether real money is involved.

## What it does *not* do

It does not scrape social media / X posts and auto-trade off them. That
pattern (auto-buying whenever an influencer posts) is a common vector for
pump-and-dump schemes targeting exactly this kind of bot. Instead, there's a
manual signal channel: you personally decide something's worth acting on and
tell the bot via Telegram, with all the same risk controls applied.

## Setup

1. Create a free account at [alpaca.markets](https://alpaca.markets).
2. In the dashboard, switch to **Paper Trading** and generate API keys
   (this does not require funding anything or opening a live account).
3. Then:

```bash
cd trading-bot
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

cp config.example.yaml config.yaml
cp .env.example .env
```

Put the paper trading key/secret from step 2 into `.env` as
`EXCHANGE_API_KEY` / `EXCHANGE_API_SECRET`. `config.yaml` controls behavior
(mode, symbols, risk parameters). `.env` holds secrets (Alpaca API keys,
Telegram token) and is gitignored -- never commit it.

**Both paper and live mode need these keys** -- unlike a crypto exchange's
public ticker data, Alpaca requires an API key/secret to fetch market data
at all, not just to place orders.

### Train the signal model

```bash
python train_model.py
```

Fetches historical candles and trains a classifier that predicts whether
price is likely to rise enough, soon enough, to be worth a long trade.
Re-run this periodically (e.g. weekly) to retrain on fresh data -- markets
drift, an old model gets stale.

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

This doesn't place any orders and doesn't touch `state/` -- it's a pure
research report. It's also not a promise: good historical performance is a
reason for more confidence, not a guarantee of future results. Also
available as a one-click GitHub Actions run (see below) if you don't want
to install anything locally.

Four filters can run on top of the model's confidence score, each a
config-toggleable hard gate in `config.yaml` under `model:`:

- `require_trend_confirmation` / `require_volume_confirmation` -- **on by
  default.** Only buy when price is above its own longer-term trend, and
  only when volume is rising to confirm conviction behind the move.
- `require_liquidity_sweep` / `require_equilibrium_discount` -- **off by
  default.** Only buy right after price wicks below a recent swing low and
  closes back above it (a "sweep and reverse" pattern), and/or only when
  price is in the cheaper half of its recent range rather than already
  extended. These are specific, checkable price patterns -- not claims about
  anyone's intent -- pulled from retail day-trading material and included
  because they're well-defined enough to test, not because of who taught
  them. They're off by default because stacked with the other two filters
  they can make signals very rare. Turn them on and compare against off
  using `backtest.py` before trusting either setting.

Deliberately **not** implemented from that material: cross-index/cross-asset
divergence timing (would need restructuring signal generation to compare
symbols against each other mid-cycle -- a reasonable future addition, not
done here) and anything from that material that was really a
course/prop-firm-affiliate sales pitch rather than a trading rule. Fixed
NYSE-hours trading windows *are* implemented, unlike the earlier crypto
version of this bot -- the source material this strategy draws from was
written for index/NYSE-hours trading in the first place, so stocks are
actually a more natural fit for it than crypto ever was.

### Run in paper mode (default, recommended starting point)

```bash
python main.py
```

Runs continuously, logging to stdout and `state/trading_bot.log`, and
persisting portfolio state to `state/portfolio.json` so it survives
restarts. Stop with Ctrl-C -- it saves state before exiting.

### Or: run it for free on GitHub Actions, no server needed

If you don't have anywhere to run a long-lived process, `.github/workflows/trading-bot.yml`
runs `run_once.py` (a single decision cycle, not the infinite loop) on a
schedule using GitHub's free compute, commits the updated state back to this
branch each time, and publishes a dashboard to GitHub Pages.

- The workflow file has to live on the repo's **default branch** for its
  schedule to fire (a GitHub requirement) -- it was added there separately;
  it checks out and runs this branch's code rather than merging it in.
- **Add `EXCHANGE_API_KEY` / `EXCHANGE_API_SECRET` as repo secrets**
  (Settings -> Secrets and variables -> Actions) using your Alpaca paper
  trading keys -- every run fails without them, in both paper and live mode.
- Trigger it manually anytime from the repo's Actions tab -> "Trading Bot
  Cycle" -> "Run workflow", instead of waiting for the schedule.
- View the dashboard at `https://<your-username>.github.io/<repo>/trading-bot/`
  once it's run at least once. It has real charts, not just numbers: an
  equity-over-time line chart, a per-position price chart against its
  entry/stop/target lines, and a green/red bar chart of recent trade P&L.
- Optional: add `TELEGRAM_BOT_TOKEN` / `TELEGRAM_CHAT_ID` as repo secrets
  and set `telegram.enabled: true` in `config.yaml` to get alerts there too.
- `run_once.py` retrains the model automatically if it's missing or more
  than 7 days old, so this is self-maintaining -- nothing to run manually
  after initial setup.
- `.github/workflows/trading-bot-backtest.yml` runs `backtest.py` the same
  way, on demand only (Actions tab -> "Trading Bot Backtest" -> "Run
  workflow") -- results appear on that run's summary page, and also publish a
  "Backtest" section on the dashboard with a per-symbol equity curve chart so
  you can see what the current strategy would have done on historical data,
  not just the live numbers.
- Because the market is closed most hours of most days, don't expect every
  scheduled run to do anything visible -- most runs outside market hours
  just log "market is closed" and exit immediately.

### Telegram alerts and manual signals (optional but recommended)

1. Message [@BotFather](https://t.me/BotFather) on Telegram, create a bot,
   get its token.
2. Send your new bot any message, then visit
   `https://api.telegram.org/bot<token>/getUpdates` in a browser to find your
   `chat.id`.
3. Put `TELEGRAM_BOT_TOKEN` and `TELEGRAM_CHAT_ID` in `.env`, set
   `telegram.enabled: true` in `config.yaml`.

Commands you can send the bot in that chat:

- `/signal AAPL buy` -- manually trigger a buy (still goes through normal
  position sizing, max-positions, and circuit-breaker checks)
- `/signal AAPL close` -- manually close an open position
- `/pause` / `/resume` -- stop/allow new positions; `/resume` also clears a
  tripped circuit breaker
- `/status` -- current equity, cash, open positions, pause/breaker state

### Going live

1. Generate **live** Alpaca API keys (separate from your paper keys --
   Settings -> API Keys in the live view of the dashboard, which requires
   Alpaca's own account verification/funding process). Set `mode: live` in
   `config.yaml` and put the live keys in `.env`.
2. Start with a small `risk.position_size_pct` and watch its logs closely
   the first several times it trades -- this is genuinely the first time
   this exact order-placement code will have touched a real account, no
   matter how much paper-mode testing came before it (paper mode uses the
   exact same code, but Alpaca's paper and live environments are still
   separate systems).

### Running in the background

`systemd/trading-bot.service` is a template unit file -- edit the paths in it
for your machine, then:

```bash
sudo cp systemd/trading-bot.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable --now trading-bot
sudo journalctl -u trading-bot -f   # tail logs
```

## Risk settings (`config.yaml` -> `risk`)

- `position_size_pct` -- % of account equity risked per new position
- `stop_loss_pct` / `take_profit_pct` -- exit thresholds per position
- `max_open_positions` -- cap on simultaneous positions
- `max_daily_loss_pct` -- the circuit breaker: halts new entries for the rest
  of the UTC day once realized+unrealized loss hits this % of the day's
  starting equity (existing positions' own stops still apply)

## Tests

```bash
pip install pytest
pytest tests/ -v
```

Covers risk math (position sizing, stop/take-profit prices, circuit
breaker), portfolio accounting (open/close/equity/persistence), feature
computation, the model training/signal pipeline against synthetic data, the
Alpaca exchange/executor integration against fakes matching the real SDK's
shape, and the market-hours gate.

## Architecture

```
main.py               orchestration loop
trading_bot/
  config.py           loads config.yaml + .env
  exchange.py          Alpaca clients (market data, orders, market clock)
  data.py              rolling candle history per symbol
  features.py          technical-indicator feature computation
  model.py             train/save/load/predict the ML signal model
  signals.py            Signal dataclass + model-based signal generation
  risk.py              position sizing, stop/take-profit prices, circuit breaker
  portfolio.py          cash/positions/trade-log state, JSON persistence
  executor.py           AlpacaExecutor -- real order placement, paper or live
  telegram_bot.py        alerts + manual signal/command parsing
train_model.py          offline: fetch history, train, save model
```
