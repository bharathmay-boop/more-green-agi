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
        FacebookAdsApi.init(
            app_id=os.environ["META_APP_ID"],
            app_secret=os.environ["META_APP_SECRET"],
            access_token=os.environ["META_ACCESS_TOKEN"],
        )
        _apply_action(c, action, db)

    with db:
        db.execute(
            "UPDATE insights_cache SET action_taken=? WHERE ad_id=? AND fetched_date=?",
            (action, c["ad_id"], today),
        )


def _apply_action(campaign, action: str, db) -> None:
    if action in ("PAUSE_HIGH_CPM", "PAUSE_LOW_CTR"):
        Ad(campaign["ad_id"]).api_update(params={"status": "PAUSED"})
        with db:
            db.execute(
                "UPDATE ad_campaigns SET status='PAUSED' WHERE campaign_key=?",
                (campaign["campaign_key"],),
            )
        log.info("    Paused ad %s", campaign["ad_id"])

    elif action == "SCALE":
        adset = AdSet(campaign["adset_id"]).api_get(fields=["daily_budget"])
        new_budget = int(float(adset["daily_budget"]) * SCALE_BUDGET_MULTIPLIER)
        AdSet(campaign["adset_id"]).api_update(params={"daily_budget": new_budget})
        log.info("    Scaled adset budget to ₹%.0f", new_budget / 100)

    elif action == "REFRESH_CREATIVE":
        log.warning("    Creative refresh needed for %s", campaign["sku"])
        notify_founder(
            subject=f"Creative fatigue: {campaign['sku']} ad needs a new creative",
            body=(
                f"Frequency is above {CREATIVE_REFRESH_FREQUENCY} for {campaign['sku']}. "
                f"Open the dashboard to generate a new creative variant."
            ),
        )
