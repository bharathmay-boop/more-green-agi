# 01 — Data Model, CRUD, Migrations

Postgres (via Prisma) is the system of record. SQLite (`automation/db/pipeline.db`) stays usable for the Python CLI in dev and as the seed source; `seed_from_sqlite.py` imports existing rows. New `automation/db/schema.sql` tables are added so the CLI keeps working offline; the canonical schema is `platform/packages/db/schema.prisma`.

## Entities (canonical)

### Existing (ported 1:1 from SQLite, keys unchanged)
- **post** — content unit. PK `post_id` (text). Fields per current `posts` table (scheduling, sku, topic, prompts, captions, approval flags, media paths, platform post ids, `pipeline_status`, `last_error`).
- **ad_campaign** — PK `campaign_key`. Meta ids (campaign/adset/creative/ad), `status`, `daily_budget_inr`, `campaign_phase`.
- **insights_cache** — PK (`ad_id`,`fetched_date`). Lifetime-to-date snapshot.
- **influencer**, **influencer_conversation**, **hashtag_usage** — unchanged.

### New
- **creative** — one row per generated asset variant (decouples assets from `post`).
  `id` PK, `post_id` FK→post, `kind` (image|video), `variant_index`, `local_path`, `cloudinary_url`, `cloudinary_public_id`, `status` (generating|ready|failed|selected|rejected), `cost_usd`, `error`, `created_at`, `updated_at`.
- **order** — Shopify orders for attribution.
  `order_id` PK, `created_at`, `sku`, `quantity`, `revenue_inr`, `discount_inr`, `customer_hash` (sha256 email), `landing_ref` (utm/referrer if available), `raw_json`, `ingested_at`.
- **ad_spend_daily** — per ad per day spend + conversions.
  PK (`ad_id`,`date`); `campaign_id`, `sku`, `spend_inr`, `impressions`, `clicks`, `purchases`, `purchase_value_inr`, `cpm_inr`, `ctr`, `frequency`, `fetched_at`.
- **attribution** — computed ROAS rollups.
  PK (`scope`,`scope_id`,`date`) where `scope`∈(sku|campaign|blended); `paid_roas`, `blended_roas`, `organic_assist_inr`, `spend_inr`, `revenue_inr`, `computed_at`.
- **approval_queue** — money/state proposals awaiting human decision.
  `id` PK, `action_type` (activate_ad|scale_budget|reallocate|price_test|publish_post|product_copy_change), `entity_ref`, `payload_json`, `expected_impact_json`, `status` (pending|approved|rejected|applied|failed|expired), `requested_by`, `requested_at`, `decided_by`, `decided_at`, `applied_at`, `error`, `expires_at`.
- **build_task** — mirror of `backlog.yaml` for the web UI.
  `id` PK, `epic`, `story`, `title`, `depends_on` (json), `status` (todo|in_progress|done|blocked), `agent`, `acceptance`, `verify`, `artifacts` (json), `last_run_at`, `last_error`.
- **audit_log** — `id` PK, `actor` (human|orchestrator|worker), `action`, `entity`, `entity_id`, `before_json`, `after_json`, `created_at`.
- **user / org** (E9, schema stubbed now) — `user`(id, email, role, org_id), `org`(id, name, plan). RBAC roles: owner|approver|viewer.

## Relationships
- `post 1—* creative`; `post 1—* ad_campaign` (via sku/date key today, FK `post_id` added).
- `ad_campaign 1—* ad_spend_daily` (by `ad_id`).
- `order *—1 sku`; attribution joins `order` + `ad_spend_daily` by (`sku`,`date`).
- `approval_queue *—1` referenced entity (`entity_ref` polymorphic); applying a row mutates the target + writes `audit_log`.

## Indexes & constraints
- `order(created_at)`, `order(sku, created_at)`, `ad_spend_daily(sku, date)`, `attribution(scope, scope_id, date)`, `approval_queue(status, requested_at)`, `creative(post_id, status)`, `build_task(status)`.
- CHECK constraints on enum-like columns; `approval_queue.status` transitions guarded in code (see doc 04).
- Idempotency: `order_id`, (`ad_id`,`date`), `campaign_key` are natural unique keys → upserts are safe to re-run.

## CRUD matrix

| Entity | Create | Read | Update | Delete |
|---|---|---|---|---|
| post | sync_sheets / calendar autopilot / web "New Post" | web Calendar + detail; CLI | edit prompts/captions, approval flags, status; web Server Action | soft-delete (`on_hold`/archived flag); hard-delete owner-only |
| creative | generate_images/videos worker | Creative Review screen; CLI | select/reject variant, regenerate | delete failed variants (cleans Cloudinary public_id) |
| order | sync_orders (upsert by order_id) | ROAS dashboard; reports | re-ingest updates `raw_json`/revenue | never delete (financial record); only re-sync |
| ad_spend_daily | monitor_ads ingest (upsert) | dashboard | upsert refresh | retention purge job (>18mo) |
| attribution | compute-attribution (upsert) | dashboard/report | recompute | recompute overwrites |
| approval_queue | tune_ads/strategize/create_ads propose | Approval Queue screen | approve/reject (status transition); apply_approved sets applied/failed | expire job sets `expired`; rows retained for audit |
| build_task | backlog sync | web Build screen; BUILD_PLAN.md | orchestrator status updates | never (history) |
| audit_log | every mutating action | web Audit screen | append-only | retention purge only |

## Migrations & seeding
- `automation/db/schema.sql` — append new `CREATE TABLE IF NOT EXISTS` for creative/order/ad_spend_daily/attribution/approval_queue/build_task/audit_log; `get_db()._ensure_schema()` auto-applies (verified by opening a fresh DB).
- `platform/packages/db/schema.prisma` + `prisma migrate` for Postgres; `prisma validate` is the no-DB fallback.
- `platform/packages/db/seed_from_sqlite.py` — reads `automation/db/pipeline.db`, upserts into Postgres; **idempotent** (re-runnable), reports per-table counts; on conflict → update. Unhappy path: missing SQLite file → no-op with warning; column drift → log + skip unknown columns.
