import logging
import os
from datetime import datetime

from facebook_business.api import FacebookAdsApi
from facebook_business.adobjects.ad import Ad
from facebook_business.adobjects.adset import AdSet

from config import (
    CREATIVE_REFRESH_FREQUENCY,
    LEARNING_PHASE_DAYS,
    MAX_CPM_INR,
    MIN_SPEND_INR_BEFORE_JUDGE,
    PAUSE_CTR_FEED_BELOW,
    PAUSE_CTR_REELS_BELOW,
    SCALE_BUDGET_MULTIPLIER,
    SCALE_ROAS_ABOVE_WARM,
)
from utils.db import get_db
from utils.notifications import notify_founder
from utils import approvals

log = logging.getLogger(__name__)


def run(dry_run: bool = True) -> None:
    if dry_run:
        log.info("DRY RUN — pass --apply to commit changes")

    db = get_db()
    campaigns = db.execute(
        "SELECT * FROM ad_campaigns WHERE status != 'ARCHIVED'"
    ).fetchall()

    if not campaigns:
        log.info("No active campaigns to tune.")
        return

    today = datetime.utcnow().date().isoformat()

    for c in campaigns:
        _evaluate(c, db, today, dry_run)


def _evaluate(c, db, today: str, dry_run: bool) -> None:
    created = datetime.fromisoformat(c["created_at"])
    days_live = (datetime.utcnow() - created).days
    if days_live < LEARNING_PHASE_DAYS:
        log.info("  %s: Day %d/%d — learning phase, skip", c["sku"], days_live, LEARNING_PHASE_DAYS)
        return

    ins = db.execute(
        "SELECT * FROM insights_cache WHERE ad_id=? ORDER BY fetched_date DESC LIMIT 1",
        (c["ad_id"],),
    ).fetchone()
    if not ins:
        log.info("  %s: No insights yet — skip", c["sku"])
        return

    spend = float(ins["spend_inr"] or 0)
    if spend < MIN_SPEND_INR_BEFORE_JUDGE:
        log.info("  %s: ₹%.0f spend < ₹%d minimum — skip", c["sku"], spend, MIN_SPEND_INR_BEFORE_JUDGE)
        return

    ctr       = float(ins["ctr"] or 0) / 100
    frequency = float(ins["frequency"] or 0)
    cpm       = float(ins.get("cpm") or 0) if "cpm" in ins.keys() else 0.0
    roas      = float(ins["roas"] or 0)
    ad_format = "reels"  # default; derive from creative type when available
    ctr_floor = PAUSE_CTR_REELS_BELOW if ad_format == "reels" else PAUSE_CTR_FEED_BELOW

    if cpm > MAX_CPM_INR:
        action = "PAUSE_HIGH_CPM"
    elif frequency > CREATIVE_REFRESH_FREQUENCY:
        action = "REFRESH_CREATIVE"
    elif ctr < ctr_floor:
        action = "PAUSE_LOW_CTR"
    elif roas >= SCALE_ROAS_ABOVE_WARM:
        action = "SCALE"
    else:
        action = "OK"

    log.info(
        "  %s: CTR=%.2f%% Freq=%.1f CPM=₹%.0f ROAS=%.1fx → %s",
        c["sku"], ctr * 100, frequency, cpm, roas, action,
    )

    if not dry_run:
        # Meta init is only needed for the immediate PAUSE path. SCALE never
        # touches Meta here — it writes an approval proposal instead.
        if action in ("PAUSE_HIGH_CPM", "PAUSE_LOW_CTR"):
            FacebookAdsApi.init(
                app_id=os.environ["META_APP_ID"],
                app_secret=os.environ["META_APP_SECRET"],
                access_token=os.environ["META_ACCESS_TOKEN"],
            )
        _apply_action(c, action, db, metrics={"roas": roas, "cpm": cpm,
                                              "ctr": ctr, "spend": spend})

    with db:
        db.execute(
            "UPDATE insights_cache SET action_taken=? WHERE ad_id=? AND fetched_date=?",
            (action, c["ad_id"], today),
        )


def _apply_action(campaign, action: str, db, metrics: dict | None = None) -> None:
    metrics = metrics or {}
    if action in ("PAUSE_HIGH_CPM", "PAUSE_LOW_CTR"):
        # Pausing only ever reduces waste → immediate, bypasses the approval queue.
        Ad(campaign["ad_id"]).api_update(params={"status": "PAUSED"})
        with db:
            db.execute(
                "UPDATE ad_campaigns SET status='PAUSED' WHERE campaign_key=?",
                (campaign["campaign_key"],),
            )
        log.info("    Paused ad %s", campaign["ad_id"])

    elif action == "SCALE":
        # MONEY-SAFETY: never raise budget here. Write a proposal; only
        # apply_approved.py (after human approval + cap re-check) touches Meta.
        current_inr = float(campaign["daily_budget_inr"] or 0)
        proposed_inr = round(current_inr * SCALE_BUDGET_MULTIPLIER)
        roas = float(metrics.get("roas") or 0)
        pid = approvals.propose(
            action_type="scale_budget",
            entity_ref=campaign["campaign_key"],
            payload={
                "adset_id": campaign["adset_id"],
                "sku": campaign["sku"],
                "current_inr": current_inr,
                "proposed_inr": proposed_inr,
                "multiplier": SCALE_BUDGET_MULTIPLIER,
            },
            expected_impact={
                "current_roas": roas,
                "current_spend_inr": float(metrics.get("spend") or 0),
                "projected_spend_inr": proposed_inr,
            },
            requested_by="tune_ads",
            db=db,
        )
        log.info("    Proposed scale ₹%.0f→₹%.0f for %s (approval #%s)",
                 current_inr, proposed_inr, campaign["sku"], pid)
        notify_founder(
            subject=f"Approve budget scale: {campaign['sku']} (ROAS {roas:.1f}x)",
            body=(
                f"{campaign['sku']} is hitting ROAS {roas:.1f}x. Proposed daily "
                f"budget ₹{current_inr:.0f} → ₹{proposed_inr:.0f}. "
                f"Approve in the dashboard (proposal #{pid}) to apply."
            ),
        )

    elif action == "REFRESH_CREATIVE":
        log.warning("    Creative refresh needed for %s", campaign["sku"])
        notify_founder(
            subject=f"Creative fatigue: {campaign['sku']} ad needs a new creative",
            body=(
                f"Frequency is above {CREATIVE_REFRESH_FREQUENCY} for {campaign['sku']}. "
                f"Open the dashboard to generate a new creative variant."
            ),
        )
