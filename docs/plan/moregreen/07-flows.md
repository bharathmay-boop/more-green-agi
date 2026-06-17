# 07 — End-to-End Flow Catalog (Happy + Unhappy)

Sequence-level flows with failure handling, retries, and compensation. Every mutating step writes `audit_log`.

## F1 — Content: brief → live post (happy)
calendar autopilot/sync_sheets creates `post(draft)` → generate_prompts (Claude) → `prompts_ready` → founder approves prompts (web) → generate_images/videos workers → `creative(ready)` ×N → founder selects variant (`creatives_approved`) → post_organic publishes IG/FB → `posted`, ids saved → notify_founder.

**F1 unhappy:**
- Claude JSON malformed → retry (existing logic) → after N, `last_error`, status stays `draft`, founder sees error chip.
- fal.ai timeout (video) → async job persisted (`pending_video_jobs.json`), `resume-video-jobs` polls; on hard fail → `creative(failed)`, regenerate action offered.
- Cloudinary upload fail → retry (`checked_post`); dead URL caught by `verify-media`.
- Meta publish rate-limited → `check_meta_rate_limit` defers; token invalid → `validate_meta_token` exits with guidance; partial (IG ok, FB fail) → per-platform status, retry FB only.
- Banned phrase in caption (E5) → reject + regenerate before any publish.

## F2 — Ads: creative → spend (approval-gated)
create_ads builds campaign **PAUSED** → strategist/tune proposes `activate_ad` → founder approves → apply_approved flips live (cap re-check) → monitor_ads ingests `ad_spend_daily` → compute-attribution → ROAS dashboard.

**F2 unhappy:** approval expired → re-propose; cap breach at apply → `failed`, no spend; Meta rejects (learning/policy) → `failed` + reason, retry once; ROAS below floor → tune proposes PAUSE which **applies immediately** (waste stop), logged.

## F3 — Optimization loop (daily, mostly autonomous on the safe side)
monitor_ads (per-day spend+conv) → compute-attribution → tune_ads evaluates: **PAUSE/kill low-CTR/high-CPM = immediate**; **SCALE/activate = proposal**. strategize weekly reallocation proposals. Founder approves spend moves; pauses already applied.

**F3 unhappy:** insights missing (learning <14d) → no action (`LEARNING_PHASE_DAYS`); spend=0 → ROAS null, skip; ins-cache stale → re-fetch; Meta down → skip cycle, retry next cron.

## F4 — Profit truth (daily)
sync_orders upsert → ad_spend_daily upsert → compute-attribution rollups → dashboard/report.
**Unhappy:** Shopify 401/scope → clear message; pagination partial → resume from `updated_at_min`; refund/negative revenue honored; unmapped SKU → `unmapped` bucket + warn; ÷0 guarded.

## F5 — Storefront change (E7, write-gated)
strategist reads product page + landing perf → `product_copy_change`/`price_test` proposal → founder approves → apply_approved `Product.save()` (margin guardrail) → audit.
**Unhappy:** missing `write_products` scope → "needs scope"; margin floor breach → blocked; Shopify save conflict (version) → re-fetch + retry.

## F6 — Build Engine self-continuation
orchestrate picks ready tasks → dispatch agents → verify → commit → loop; on usage limit/context reset/crash → resume.sh (cron) backs off and continues from disk state.
**Unhappy:** verify fail → `blocked` + revert task artifacts + follow-up FIX task; cycle/no-ready → alert; stale lock → reclaim; push fail → retry/backoff then local-only; dirty tree → WIP-branch safeguard. (Full matrix in doc 02.)

## Cross-cutting
- **Idempotency** on natural keys (`order_id`, `ad_id+date`, `campaign_key`, `post_id`, proposal dedupe) → every flow is safe to re-run after a crash.
- **Compensation**: failed apply never leaves partial spend (Meta calls are single atomic updates; status reflects truth). Failed publish retried per-platform.
- **Alerting**: hard failures and cap breaches → `notify_founder` + audit row.
