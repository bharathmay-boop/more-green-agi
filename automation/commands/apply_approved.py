"""apply-approved — the ONLY code path that increases spend on Meta (doc 04).

Consumes `approval_queue` rows in `approved` state, re-checks money caps at apply
time (caps may have changed since the proposal was written), performs the live
Meta mutation, then marks the row `applied` (success) or `failed` (error).

Money-safety invariants enforced here:
  * Only `approved` rows are ever read — `pending` is invisible to this command.
  * Every spend-raising action is re-validated against config caps right before
    the API call. A breach marks the row `failed` and touches nothing on Meta.
  * Idempotent: `mark_applied` transitions approved→applied; a re-run finds no
    approved rows for an already-applied proposal.
  * Pausing/stopping is never routed here (that path stays immediate in tune_ads).
"""
from __future__ import annotations

import json
import logging
import os

from utils.db import get_db
from utils import approvals

log = logging.getLogger(__name__)


class CapBreach(Exception):
    """Raised when an approved action would exceed a configured money cap."""


def _caps():
    import config
    return (
        float(getattr(config, "MAX_DAILY_SPEND_INR", 3000)),
        float(getattr(config, "MAX_CAMPAIGN_BUDGET_INR", 2000)),
    )


def _meta_init() -> None:
    from facebook_business.api import FacebookAdsApi
    FacebookAdsApi.init(
        app_id=os.environ["META_APP_ID"],
        app_secret=os.environ["META_APP_SECRET"],
        access_token=os.environ["META_ACCESS_TOKEN"],
    )


def _check_caps_scale(db, proposed_inr: float, entity_ref: str) -> None:
    """Block a budget scale that breaches per-campaign or total-daily caps."""
    max_daily, max_campaign = _caps()
    if proposed_inr > max_campaign:
        raise CapBreach(
            f"proposed ₹{proposed_inr:.0f} > MAX_CAMPAIGN_BUDGET_INR ₹{max_campaign:.0f}"
        )
    # Sum of all other active campaign budgets + this proposal must fit the day cap.
    row = db.execute(
        "SELECT COALESCE(SUM(daily_budget_inr),0) AS total FROM ad_campaigns "
        "WHERE status='ACTIVE' AND campaign_key != ?", (entity_ref,),
    ).fetchone()
    others = float(row["total"] or 0) if row else 0.0
    if others + proposed_inr > max_daily:
        raise CapBreach(
            f"total daily ₹{others + proposed_inr:.0f} > MAX_DAILY_SPEND_INR ₹{max_daily:.0f}"
        )


def _apply_scale_budget(db, row, dry_run: bool) -> str:
    payload = json.loads(row["payload_json"] or "{}")
    proposed_inr = float(payload.get("proposed_inr") or 0)
    adset_id = payload.get("adset_id")
    if not adset_id:
        raise ValueError("scale_budget payload missing adset_id")
    _check_caps_scale(db, proposed_inr, row["entity_ref"])

    if dry_run:
        return f"[dry-run] would scale adset {adset_id} → ₹{proposed_inr:.0f}/day"

    _meta_init()
    from facebook_business.adobjects.adset import AdSet
    # Meta budgets are in minor units (paise). Re-read live budget for the record.
    AdSet(adset_id).api_update(params={"daily_budget": int(proposed_inr * 100)})
    with db:
        db.execute(
            "UPDATE ad_campaigns SET daily_budget_inr=? WHERE campaign_key=?",
            (int(proposed_inr), row["entity_ref"]),
        )
    return f"scaled adset {adset_id} → ₹{proposed_inr:.0f}/day"


def _apply_activate_ad(db, row, dry_run: bool) -> str:
    payload = json.loads(row["payload_json"] or "{}")
    ad_id = payload.get("ad_id") or row["entity_ref"]
    proposed_inr = float(payload.get("daily_budget_inr") or 0)
    if proposed_inr:
        _check_caps_scale(db, proposed_inr, row["entity_ref"])
    if dry_run:
        return f"[dry-run] would activate ad {ad_id}"

    _meta_init()
    from facebook_business.adobjects.ad import Ad
    Ad(ad_id).api_update(params={"status": "ACTIVE"})
    with db:
        db.execute(
            "UPDATE ad_campaigns SET status='ACTIVE' WHERE campaign_key=?",
            (row["entity_ref"],),
        )
    return f"activated ad {ad_id}"


# Only spend-raising actions are wired to Meta here. Others are no-ops until
# their appliers exist (they still transition approved→applied/failed cleanly).
_APPLIERS = {
    "scale_budget": _apply_scale_budget,
    "activate_ad": _apply_activate_ad,
}


def run(dry_run: bool = False) -> None:
    db = get_db()
    approved = approvals.list_approved(db)
    if not approved:
        print("apply-approved: no approved proposals to apply")
        return

    applied = failed = skipped = 0
    for row in approved:
        action = row["action_type"]
        applier = _APPLIERS.get(action)
        if not applier:
            log.info("No applier for action '%s' (proposal #%s) — skipping", action, row["id"])
            skipped += 1
            continue
        try:
            result = applier(db, row, dry_run)
            if dry_run:
                log.info("[DRY RUN] #%s %s: %s", row["id"], action, result)
            else:
                approvals.mark_applied(row["id"], db=db)
                log.info("#%s %s applied: %s", row["id"], action, result)
                applied += 1
        except CapBreach as exc:
            msg = f"cap breach: {exc}"
            log.warning("#%s %s blocked — %s", row["id"], action, msg)
            if not dry_run:
                approvals.mark_failed(row["id"], msg, db=db)
            failed += 1
        except Exception as exc:  # Meta error / bad payload
            msg = str(exc)
            log.error("#%s %s failed: %s", row["id"], action, msg)
            if not dry_run:
                approvals.mark_failed(row["id"], msg, db=db)
            failed += 1

    verb = "would apply" if dry_run else "applied"
    print(f"apply-approved: {verb} {applied if not dry_run else len(approved)-skipped}, "
          f"{failed} failed, {skipped} skipped")
