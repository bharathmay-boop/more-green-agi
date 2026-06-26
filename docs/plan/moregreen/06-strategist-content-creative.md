# 06 — Strategist, Calendar Autopilot, Creative Studio, Storefront Loop

These are the "marketing head" capabilities. E4 first-cut ships this run (proposal-only); E5–E7 are built by the Build Engine over subsequent resumed runs. Everything that spends or publishes goes through `approval_queue` (doc 04).

## E4 — Strategist (`automation/commands/strategize.py`, this run)
- Inputs: `attribution` (blended ROAS by SKU), `config.SKUS`, `cultural_calendar.yaml`, recent post performance, current `ad_campaigns`.
- Claude (reuse `ANTHROPIC_MODEL`, `generate_prompts.py` client pattern) produces a structured weekly plan: which SKUs/pillars to feature, which winning creatives to scale, suggested budget split — as JSON.
- Writes: draft `post` rows (status `draft`) for next week + `approval_queue` proposals (`reallocate`, `activate_ad`, `scale_budget`). **No autonomous spend or publish.**
- Happy: produces N proposals + draft calendar; founder reviews in web. Unhappy: no attribution yet → falls back to cultural_calendar defaults; Claude JSON parse fail → retry then skip with log.

## E5 — Creative Studio (Build Engine)
- Multi-variant generation (raise `IMAGE_VARIANTS_PER_POST`), per-pillar caption/hashtag selection from `hashtags.yaml`, **brand-safety lint** against `brand.yaml` `banned_phrases` (reject + regenerate), variant scoring loop fed by `ad_spend_daily` CTR to pick promote-worthy creatives. CRUD via `creative` table + Creative Review screen.

## E6 — Calendar Autopilot (Build Engine)
- Replace manual Google-Sheets editing: auto-seed `post` rows from `cultural_calendar.yaml` + performance gaps + SKU rotation, honoring `sku_split`. Keeps `seed_calendar.py`/`new_week.py` as fallback. Dedupe by `post_id`. Proposes, founder approves the week.

## E7 — Storefront / Product-Page Loop (Build Engine)
- Read Shopify product pages (`shopify.Product`) + landing performance (orders by `landing_ref`, ad CTR→ATC drop-off).
- Claude proposes product-page copy / offer / price-test changes as `product_copy_change` / `price_test` proposals. **Write-gated**: only `apply_approved` calls `Product.save()` after human approval. Never auto-edits storefront.
- Unhappy: missing `write_products` scope → proposal flagged "needs scope"; price test guardrails (min margin) enforced before apply.

## Channel & hardening (E8/E9, Build Engine)
- E8: surface influencer CRM + conversations in web; YouTube Shorts auto cross-post; email/WhatsApp lifecycle.
- E9: NextAuth + multi-tenant orgs/RBAC, secrets vault, observability (structured logs/metrics), retries/DLQ on queue, full test suite + GitHub Actions CI.

All of E5–E9 are enumerated as granular, file-disjoint, independently-dispatchable tasks in `08-backlog.md` so parallel agents build them safely.
