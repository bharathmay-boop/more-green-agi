# 03 — Profit / Blended-ROAS Attribution

Goal: a trustworthy ROAS number (the chosen north-star) combining Shopify revenue and Meta spend per SKU/campaign/day.

## New CLI commands (registered in `automation/main.py`)
- `sync-orders` → `automation/commands/sync_orders.py`
- `compute-attribution` → `automation/commands/attribution.py`
- (extend) `monitor-ads` also writes `ad_spend_daily`.

## sync_orders.py
- Reuse `utils/secrets.require("SHOPIFY_STORE_URL"/"SHOPIFY_ACCESS_TOKEN")`, `utils/db.get_db`, `utils/retry`.
- Pull orders via `shopify.Order.find(updated_at_min=<last_ingest>, status="any", limit=250)` paginated; map line items → per-SKU rows; **upsert by `order_id`** (INSERT … ON CONFLICT DO UPDATE).
- Store `revenue_inr` (line subtotal), `discount_inr`, `customer_hash` (sha256 lowercased email, reuse hashing pattern from `sync_audience.py`), `raw_json`.
- **Happy:** `--dry-run` prints count + would-write, writes nothing. Real run upserts; logs new vs updated.
- **Unhappy:** 401/403 → clear "token/scope" message (needs `read_orders`); rate-limit (429) → `checked_post`-style backoff; partial page failure → continue, record `last_error`; empty store → no-op; SKU mapping miss (product not in `config.SKUS`) → bucket as `unmapped`, warn.

## ad_spend_daily ingest (extend monitor_ads.py)
- For each active ad, in addition to lifetime `insights_cache`, fetch `date_preset="last_7d"` with `time_increment=1` to get **per-day** spend/impressions/clicks/actions(purchase + value).
- Upsert (`ad_id`,`date`); derive `sku` from `ad_campaigns`. Keep existing lifetime cache untouched (backward compatible).
- **Unhappy:** ad deleted/archived → skip + mark; insight not yet available (learning) → zero-row tolerated; Meta token invalid → `validate_meta_token` exits with guidance.

## attribution.py (compute-attribution)
- For each (sku, date) in a window: `spend_inr = Σ ad_spend_daily.spend`; `paid_revenue = Σ purchase_value_inr`; `blended_revenue = Σ order.revenue_inr` (all orders for the SKU that day, paid + organic); `paid_roas = paid_revenue/spend`; `blended_roas = blended_revenue/spend`; `organic_assist_inr = blended_revenue − paid_revenue`.
- Also roll up `scope=campaign` and `scope=blended` (all SKUs). Upsert into `attribution`.
- **Edge cases:** `spend=0` → ROAS null (not ÷0), shown as "—"; refunds (negative revenue) honored; multi-SKU orders split by line item; timezone normalized to IST for day bucketing.
- Output feeds: ROAS dashboard (doc 05), `export_report.py`, and the strategist (doc 06).

## Reporting
- Extend `export_report.py` to add a blended-ROAS section (by SKU, last 7/30 days, trend arrows).
- Define `ROAS_TARGET_INR` and `BREAKEVEN_ROAS` (from gross margin) in `config.py` so dashboards/strategist can flag below-target SKUs. (We optimize ROAS per the locked decision; margin constants are advisory only.)

## Verification (dry-run, no spend)
`python automation/main.py --dry-run sync-orders` → prints N orders; `compute-attribution` → writes `attribution`; dashboard renders blended vs paid by SKU. Unit tests assert ÷0 safety, refund handling, and SKU split.
