# 04 — Approval Queue & Money-Safety

Implements the locked decision: **propose, human approves any spend**. Pausing to stop waste stays automatic.

## Lifecycle (status machine)
```
pending --approve--> approved --apply_approved--> applied
   |  \--reject--> rejected                         \--error--> failed --(retry)--> approved
   \--expire (TTL)--> expired
```
Guarded transitions (in code, not just UI): only `pending→approved|rejected|expired`; only `approved→applied|failed`; `failed→approved` (manual retry). Any other transition raises and writes `audit_log`.

## Producers (write `pending` rows; never act)
- `tune_ads.py` **refactor**: SCALE / activate decisions → `approval_queue` rows (`action_type=scale_budget|activate_ad`, `payload_json` = {ad_id, current, proposed}, `expected_impact_json` = {projected_roas, projected_spend}). **PAUSE / kill (waste-stopping) still applies immediately** (invariant #2) and is logged.
- `create_ads.py`: still creates campaigns **PAUSED**; an `activate_ad` proposal is what flips them live.
- `strategize.py` (doc 06): budget `reallocate`, `price_test`, `product_copy_change`, `publish_post` proposals.

## Consumer
- New `automation/commands/apply_approved.py` (`apply-approved` CLI): selects `approved` rows, **re-checks caps** (`MAX_DAILY_SPEND_INR`, `MAX_CAMPAIGN_BUDGET_INR`), reuses `validate_meta_token`, performs the Meta `api_update` (budget) / status flip, sets `applied`/`failed`, writes `audit_log`. Idempotent: re-running an already-`applied` row is a no-op.

## CRUD
| Op | Where | Notes |
|---|---|---|
| Create (propose) | workers/strategist/tune_ads | always `pending`; dedupe identical pending proposals for same entity |
| Read | web Approval Queue screen; `export_report` | grouped by action_type; shows current→proposed + expected impact |
| Update (decide) | web one-tap approve/reject; email deep-link; CLI `approve-proposal --id` | records `decided_by`,`decided_at` |
| Apply | `apply_approved` (cron or manual) | only `approved`; cap re-check at apply time |
| Delete | none (audit) | TTL job sets `expired`; rows retained |

## Caps & config (add to `config.py`)
`MAX_DAILY_SPEND_INR`, `MAX_CAMPAIGN_BUDGET_INR`, `ROAS_FLOOR_FOR_SCALE`, `APPROVAL_TTL_HOURS`, `AUTONOMY_MODE="propose"` (future-proof for the "graduate to autonomy" option, default propose).

## Happy flow
tune_ads sees ROAS 4.1 > floor → writes `scale_budget` proposal → founder taps Approve in web (or email link) → `apply-approved` bumps budget 20% via Meta, marks `applied`, logs audit, `notify_founder`.

## Unhappy flows
- **Approve then cap breach at apply** → `failed` with reason; founder re-decides; no spend made.
- **Meta API rejects update** (e.g., adset in learning) → `failed` + Meta error surfaced; auto-retry once after backoff.
- **Token revoked between approve and apply** → `validate_meta_token` exits; row stays `approved` for next run (no silent loss).
- **Duplicate proposals** (cron ran twice) → unique-ish key (entity_ref+action_type+proposed) prevents dup pending rows.
- **Proposal expires** before decision → `expired`; producer may re-propose next cycle with fresh data.
- **Race: two approvers** → optimistic `decided_at IS NULL` guard on update; second decision rejected.
- **Apply succeeds but audit write fails** → action already done; audit retried; alert (must never lose financial trail).

## Safety tests (doc 09)
Assert: no Meta budget/activate call exists outside `apply_approved`; PAUSE path needs no approval; cap breach blocks apply; status transitions illegal paths raise.
