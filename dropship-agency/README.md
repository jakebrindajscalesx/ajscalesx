# Dropship Agency

A prototype for running a fleet of bots that each manage one dropshipping
store: pulling supplier products into the storefront, watching for new
orders, placing them with the supplier, and writing tracking back — the
recurring part of what a human store manager currently does by hand.

**Storefront choice: Shopify.** Shopify owns hosting, checkout, payment
compliance (PCI-DSS), and fraud/chargeback handling — none of that is worth
rebuilding from scratch. This system is the automation layer that runs
*behind* a Shopify store, not a replacement for it. You (or your friend)
still need a real Shopify account and a real payment processor connected to
it before any store can charge real customers — that part requires your
legal/business identity and isn't something code can stand in for.

## How it's structured

```
agency/
  platforms/     one adapter per storefront platform (Shopify implemented; add WooCommerce etc. the same way)
  suppliers/      one adapter per fulfillment supplier (mock + CJ Dropshipping; add Spocket/AliExpress etc. the same way)
  bot.py          StoreBot -- one instance per store, runs a fulfillment cycle
  product_bot.py  ProductSyncBot -- one instance per store, pulls the supplier catalog into the storefront
  pricing.py      PricingRule -- turns supplier cost into retail price (markup)
  config.py       loads config.yaml into StoreBot/ProductSyncBot-ready objects
  orchestrator.py runs every store's bots for one cycle, writes state + dashboard data
run_once.py       CLI: one fulfillment cycle across the whole registry
sync_products.py  CLI: one product-catalog sync across the whole registry
config.example.yaml  the store -> bot registry (copy to config.yaml)
docs/index.html   static status dashboard (reads docs/data.json)
state/            per-run JSON written by the orchestrator (gitignored, except last committed demo data in docs/)
```

Each store is independent: one bot's failure is caught, logged, and
recorded against that store only. A new store is a new registry entry, not
new code.

## Try it now (no credentials needed)

```bash
pip install -r requirements.txt
python run_once.py --config config.example.yaml       # fulfillment cycle
python sync_products.py --config config.example.yaml  # product catalog sync
```

Both run the bundled `demo-store`, which uses the mock storefront + mock
supplier (`agency/platforms/mock.py`, `agency/suppliers/mock_supplier.py`)
so you can see a full cycle — products priced with markup and "listed,"
orders placed with the "supplier," tracking written back — without any real
accounts. Open `docs/index.html` (any static file server, e.g.
`python -m http.server` from `docs/`) to see the fulfillment run as a status
dashboard.

## Connecting a real store

1. **Get store credentials.** In Shopify: *Settings → Apps and sales
   channels → Develop apps → Create an app*, give it `read_orders`,
   `write_orders`, `read_products`, `write_products`, `read_inventory`,
   `write_inventory` scopes, install it, and copy the Admin API access
   token it generates.
2. **Store the token as an env var**, never in the config file — e.g.
   `SHOPIFY_STORE1_TOKEN` in a local `.env`, or as a GitHub Actions repo
   secret if this runs on a schedule.
3. **Add the store to `config.yaml`** (copy from `config.example.yaml`) —
   see the commented `friend-store-1` example there.
4. **Run it**: `python sync_products.py --config config.yaml` to list
   products, then `python run_once.py --config config.yaml` to start
   fulfilling orders. That's the whole "connect a bot to a store" step —
   nothing else in the system needs to know a new store exists.

## Connecting a real supplier

`agency/suppliers/cj_dropshipping.py` is a first-draft CJ Dropshipping
adapter — it follows CJ's documented Open API v2 structure, but **this
sandbox's network policy blocked outbound access to CJ's docs domain**, so
none of the endpoint paths/field names were verified live before shipping.
Treat it as a starting point to check against your own CJ account's API
reference once you have a key, not as tested code — a wrong field name
comes back as a clear 4xx from CJ's API, so it's safe to try against a
sandbox order first.

To add a different supplier: implement `agency/suppliers/base.py`'s three
methods (`list_products`, `place_order`, `get_tracking`), register the
class in `SUPPLIER_BUILDERS` in `agency/config.py`, reference it by `type:`
in the registry. Some suppliers return tracking immediately on order
placement (like the mock); others need `get_tracking` polled on later
cycles — `StoreBot` already handles both (see `state/<store>_pending_orders.json`).

## Running on a schedule

This repo already has a working pattern for a credential-driven bot that
runs unattended: see `.github/workflows/trading-bot.yml`. It fires on a
cron, checks out the branch with the bot's code, runs one cycle, commits
updated state back, and publishes a dashboard to GitHub Pages. Wiring this
up the same way for the agency (a fulfillment cron every 15 min, a product
sync cron daily, `docs/` published to Pages) is the natural next step — it
needs a workflow file on the repo's default branch (a GitHub requirement
for scheduled triggers) plus real store/supplier secrets, so it's left for
you to greenlight before touching `main`.

## Known gaps (by design, not oversight)

- CJ Dropshipping endpoints are unverified against live docs (see above).
- Only Shopify + one supplier are implemented. Every other platform or
  supplier is a new adapter behind the same interfaces, not a change to
  the bot or orchestrator.
- Product sync creates a single default variant per SKU — no size/color
  option support yet.
- No retry/backoff, rate-limit handling, or customer-service automation.
- Nothing here creates a Shopify account, a payment processor account, or
  handles real money — those are accounts you set up; this system connects
  to them once they exist.
