# Dropship Agency

A prototype for running a fleet of bots that each manage one dropshipping
store: watching for new orders, placing them with the supplier, and writing
tracking back to the store — the recurring part of what a human store
manager currently does by hand.

## How it's structured

```
agency/
  platforms/    one adapter per storefront platform (Shopify implemented; add WooCommerce etc. the same way)
  suppliers/    one adapter per fulfillment supplier (mock included; add CJ Dropshipping/Spocket/etc. the same way)
  bot.py        StoreBot — one instance per store, runs a fulfillment cycle
  config.py     loads config.yaml into StoreBot-ready platform/supplier objects
  orchestrator.py  runs every store's bot for one cycle, writes state + dashboard data
run_once.py     CLI entrypoint: one cycle across the whole registry
config.example.yaml  the store -> bot registry (copy to config.yaml)
docs/index.html      static status dashboard (reads docs/data.json)
state/                per-run JSON written by the orchestrator (gitignored)
```

Each store is independent: one bot's failure is caught, logged, and recorded
against that store only — it never stops the other bots from running. A new
store is a new registry entry, not new code.

## Try it now (no credentials needed)

```bash
pip install -r requirements.txt
python run_once.py --config config.example.yaml
```

This runs the bundled `demo-store`, which uses the mock storefront + mock
supplier (`agency/platforms/mock.py`, `agency/suppliers/mock_supplier.py`) so
you can see a full cycle — orders in, "supplier" order placed, tracking
written back — without any real accounts. Open `docs/index.html` (any static
file server, e.g. `python -m http.server` from `docs/`) to see the same run
as a status dashboard.

## Connecting a real store

1. **Get store credentials.** In Shopify: *Settings → Apps and sales
   channels → Develop apps → Create an app*, give it `read_orders`,
   `write_orders`, `read_inventory`, `write_inventory` scopes, install it,
   and copy the Admin API access token it generates.
2. **Store the token as an env var**, never in the config file — e.g.
   `SHOPIFY_STORE1_TOKEN` in a local `.env`, or as a GitHub Actions repo
   secret if this runs on a schedule.
3. **Add the store to `config.yaml`** (copy from `config.example.yaml`):
   ```yaml
   - id: friend-store-1
     platform:
       type: shopify
       shop_domain: friend-store-1.myshopify.com
       access_token_env: SHOPIFY_STORE1_TOKEN
     supplier:
       type: mock   # swap once a real supplier adapter exists
   ```
4. **Run it**: `python run_once.py --config config.yaml`. That's the whole
   "connect a bot to a store" step — nothing else in the system needs to
   know a new store exists.

Each store in the registry gets fulfillment run in its own bot for that
cycle; add ten stores and you get ten independent bots without touching the
orchestrator.

## Connecting a real supplier

`agency/suppliers/base.py` defines the two methods a supplier adapter needs:
`place_order` and `get_tracking`. Implement one class per supplier (CJ
Dropshipping, Spocket, AliExpress, a private warehouse API — whatever your
friend's stores actually use), register it in `SUPPLIER_BUILDERS` in
`agency/config.py`, and reference it by `type:` in the registry. Some
suppliers return tracking immediately on order placement (like the mock
does); others need `get_tracking` polled on a later cycle before a bot can
mark the order fulfilled — the interface supports both.

## Running on a schedule

This repo already has a working pattern for a credential-driven bot that
runs unattended: see `.github/workflows/trading-bot.yml`. It fires on a
cron, checks out the branch with the bot's code, runs one cycle, commits
updated state back, and publishes a dashboard to GitHub Pages. Wiring this
up the same way for the agency (one scheduled workflow, one `run_once.py`
call, `docs/` published to Pages) is the natural next step — it needs a
workflow file on the repo's default branch (a GitHub requirement for
scheduled triggers) plus real store/supplier secrets, so it's left for you
to greenlight before I touch `main`.

## Known gaps (by design, not oversight)

- `ShopifyStore.sync_inventory` raises `NotImplementedError` — needs a
  SKU → `inventory_item_id` → `location_id` lookup that only makes sense
  once a real store and a real supplier stock feed are both connected.
- Only Shopify + a mock supplier are implemented. Every other platform or
  supplier is a new adapter behind the same two interfaces, not a change to
  the bot or orchestrator.
- No retry/backoff, rate-limit handling, or customer-service automation yet
  — this is the fulfillment core the rest would be built around.
