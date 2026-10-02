# Meme Bot

Watches a rotating set of top-performing Solana traders (pulled from
Fomoscope's leaderboard), and when one of them buys or sells a token, proposes
you mirror the trade at a size you set. Nothing executes automatically --
every proposal goes out over Telegram and waits for you to reply `/confirm`
or `/reject`. Only on confirmation does it sign and submit a real on-chain
swap, via Jupiter.

## Read this first

**This is real money, not a simulation.** Unlike `../trading-bot` (paper
trading through a regulated broker), this bot moves actual funds on-chain the
moment you type `/confirm`. There's no support line, no chargeback, no
undo. A wrong tap, a compromised key, or a rug-pulled token can lose the
full amount involved, instantly and permanently.

**Following a trader's on-chain wallet is not the same as following their
public calls.** This bot only ever mirrors what a wallet *actually did*
on-chain -- it does not read X/Twitter, does not auto-buy because someone
posted a ticker, and never will by design. Public "buy this" calls are
extremely often posted by someone already positioned and selling into the
attention it generates. On-chain wallet activity is at least real, verifiable
data -- it is not, on its own, proof the trade will work out. A wallet with a
good 30-day win rate can still be having a lucky streak, and even a
genuinely skilled trader's next few calls can lose.

**Ships defaulting to `dry_run: true`.** In dry-run mode the bot does
everything except sign and send the transaction: it scans, detects, sizes,
alerts you on Telegram, and logs exactly what it would have executed. Watch
it run for real signals over a few days before ever setting `dry_run:
false` in `config.yaml`. When you do, start with the smallest `trade_usd`
you're willing to test with -- treat the first week live as "did I wire
this up correctly," not "let's see if this makes money."

**One endpoint in this codebase (Fomoscope's leaderboard API) could not be
verified against live documentation** -- the sandbox this bot was built in
couldn't reach `api.fomoscope.xyz`. Before relying on `meme_bot/leaderboard.py`,
open https://api.fomoscope.xyz/docs yourself and confirm the endpoint path
and field names in `_parse_entry()` match; the rest of the codebase
(Helius, Jupiter, Solana RPC) is built against endpoints that are widely
documented and used elsewhere, but you should still watch the first few
dry-run cycles' logs rather than assume everything lines up.

## Setup

### 1. Helius account (Solana RPC + wallet activity)

Free at https://helius.dev. After signing up, copy your API key into
`.env` as `HELIUS_API_KEY`. Used both to read tracked wallets' recent swaps
and to submit this bot's own transactions.

### 2. Fomoscope API key (optional)

The free tier works per-IP without a key. If you outgrow it, get a key at
https://www.fomoscope.xyz/setup and set `FOMOSCOPE_API_KEY`.

### 3. Wallet -- do this carefully

Use a wallet **dedicated to this bot only**, funded with only what you're
willing to lose entirely -- never your main wallet. In Phantom (or any
Solana wallet): create a new wallet, fund it with a small amount of SOL,
then export its private key (Settings -> Show Private Key).

- `WALLET_PUBLIC_KEY` is safe to share/commit.
- `WALLET_PRIVATE_KEY` is not. **Never paste it into a chat with an AI
  assistant, a GitHub issue/PR, or anywhere it could be logged.** For local
  runs it goes in `.env` (already gitignored). For the GitHub Actions
  workflow, add it as an encrypted repo secret yourself, directly through
  GitHub's UI: Settings -> Secrets and variables -> Actions -> New repository
  secret. Nobody assisting you with this codebase needs to see the raw key.

### 4. Telegram bot

Reuse the same bot as `../trading-bot` (message `@BotFather`'s existing
token) or create a second one -- either works, but use a `chat_id` only you
have access to. Set `TELEGRAM_BOT_TOKEN` / `TELEGRAM_CHAT_ID`.

### 5. Config

```
cp config.example.yaml config.yaml
cp .env.example .env      # fill in the values from steps 1-4
pip install -r requirements.txt
```

Read every comment in `config.example.yaml` -- `sizing.trade_usd` and
`sizing.max_daily_spend_usd` are the two numbers that most directly bound
how much you can lose per trade and per day.

### 6. Try it

```
python run_scan.py      # checks tracked wallets, proposes trades, alerts on Telegram
python run_confirm.py   # polls Telegram, executes confirmed trades (no-ops in dry_run)
```

Run both by hand a few times and read the Telegram messages and console
output before wiring up the scheduled workflow.

## Telegram commands

- `/confirm <id>` -- execute the proposed trade
- `/reject <id>` -- discard it
- `/pause` / `/resume` -- stop/resume new buy proposals (sells and
  stop-losses still fire while paused, so you can always get out)
- `/status` -- tracked wallet count, open positions, today's spend, pending proposals

## How sizing and exits work

Every mirrored buy uses a fixed `sizing.trade_usd`, regardless of how big
the tracked wallet's own buy was (`sizing.mirror_mode: fixed` is the only
mode implemented -- proportional mirroring, matching a tracked wallet's
position size as a fraction of its own balance, is a reasonable extension
but isn't built here).

Positions can close two ways: the tracked wallet that we mirrored sells
(configurable via `exit.mirror_sells`), or the position's own value drops
`exit.stand_alone_stop_loss_pct` below cost, checked independently every
scan regardless of what the tracked wallet does -- meme coins can crash
faster than a wallet you're watching reacts.

## Known limitations

- Only tracks wallets currently on Fomoscope's leaderboard -- a trader who
  isn't ranked there (including most pure X/Twitter callers with no
  verifiable on-chain track record) can't be tracked by this bot.
- Swap detection skips token-for-token trades (neither leg is SOL/USDC) --
  see the comment in `meme_bot/chain.py` for why.
- No portfolio-level P&L dashboard yet (state/state.json has the raw data;
  `../trading-bot`'s dashboard approach would be a reasonable model to copy).
- Solana only. The `chain: solana` config key exists for when/if that changes.
