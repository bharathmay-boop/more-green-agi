import json
import logging
import os
from datetime import datetime

from facebook_business.api import FacebookAdsApi
from facebook_business.adobjects.ad import Ad
from facebook_business.adobjects.adaccount import AdAccount
from facebook_business.adobjects.adcreative import AdCreative
from facebook_business.adobjects.adset import AdSet
from facebook_business.adobjects.campaign import Campaign

from config import (
    META_BUDGET_PHASE,
    META_CAMPAIGN_OBJECTIVE_PHASE,
    META_CAMPAIGN_PHASE,
    META_TARGETING_GROWTH,
    META_TARGETING_LAUNCH,
    SKUS,
)
from utils.db import get_db
from utils.guards import require_approval
from utils.meta_auth import validate_meta_token

log = logging.getLogger(__name__)


@require_approval("creatives_approved", "creatives")
def run(post_id: str = None, dry_run: bool = False,
        budget_override: int = None, phase_override: int = None) -> None:
    validate_meta_token()
    FacebookAdsApi.init(
        app_id=os.environ["META_APP_ID"],
        app_secret=os.environ["META_APP_SECRET"],
        access_token=os.environ["META_ACCESS_TOKEN"],
    )
    account = AdAccount(os.environ["META_AD_ACCOUNT_ID"])
    db = get_db()

    posts = _fetch_approved_posts(db, post_id)
    if not posts:
        log.info("No approved posts to create ads for.")
        return

    for post in posts:
        _create_campaign_for_post(db, account, post, dry_run,
                                  budget_override=budget_override,
                                  phase_override=phase_override)


def _fetch_approved_posts(db, post_id):
    query = "SELECT * FROM posts WHERE creatives_approved=1 AND on_hold=0"
    params = []
    if post_id:
        query += " AND post_id = ?"
        params.append(post_id)
    return db.execute(query, params).fetchall()


def _create_campaign_for_post(db, account: AdAccount, post, dry_run: bool,
                              budget_override: int = None, phase_override: int = None) -> None:
    pid = post["post_id"]
    campaign_date = datetime.now().strftime("%Y-%m-%d")
    campaign_key = f"{post['sku']}_{campaign_date}"

    # Idempotency — never create duplicates
    existing = db.execute(
        "SELECT campaign_key FROM ad_campaigns WHERE campaign_key=?", (campaign_key,)
    ).fetchone()
    if existing:
        log.info("Campaign already exists for %s (%s) — skipping.", post["sku"], campaign_date)
        return

    urls = json.loads(post["cloudinary_urls"] or "[]")
    if not urls:
        log.error("No Cloudinary image URL for %s — run upload-media first", pid)
        return
    image_url = urls[0]

    phase = phase_override if phase_override is not None else META_CAMPAIGN_PHASE
    budget_inr = budget_override if budget_override is not None else META_BUDGET_PHASE[phase]
    objective = META_CAMPAIGN_OBJECTIVE_PHASE[phase]
    targeting = META_TARGETING_LAUNCH if phase == 1 else META_TARGETING_GROWTH
    sku_data = SKUS[post["sku"]]

    if dry_run:
        log.info(
            "[DRY RUN] Would create campaign for %s on %s — ₹%d/day, objective=%s, phase=%d",
            post["sku"], campaign_date, budget_inr, objective, phase,
        )
        return

    log.info("Creating campaign: %s %s (Phase %d, ₹%d/day)", post["sku"], campaign_date, phase, budget_inr)

    campaign = account.create_campaign(
        fields=[],
        params={
            Campaign.Field.name: f"MG_{post['sku']}_{campaign_date}_P{phase}",
            Campaign.Field.objective: objective,
            Campaign.Field.status: Campaign.Status.paused,  # ALWAYS start paused
            Campaign.Field.special_ad_categories: [],
        },
    )

    optimization_goal = (
        AdSet.OptimizationGoal.reach if phase == 1
        else AdSet.OptimizationGoal.offsite_conversions
    )

    adset = account.create_ad_set(
        fields=[],
        params={
            AdSet.Field.name: f"MG_{post['sku']}_adset_P{phase}",
            AdSet.Field.campaign_id: campaign["id"],
            AdSet.Field.daily_budget: budget_inr * 100,  # paise
            AdSet.Field.billing_event: AdSet.BillingEvent.impressions,
            AdSet.Field.optimization_goal: optimization_goal,
            AdSet.Field.targeting: targeting,
            AdSet.Field.status: AdSet.Status.paused,
        },
    )

    creative = account.create_ad_creative(
        fields=[],
        params={
            AdCreative.Field.name: f"MG_{post['sku']}_creative",
            AdCreative.Field.object_story_spec: {
                "page_id": os.environ["META_PAGE_ID"],
                "link_data": {
                    "image_url": image_url,
                    "link": sku_data["shopify_url"],
                    "message": post["ad_primary_text"],
                    "call_to_action": {
                        "type": "SHOP_NOW",
                        "value": {"link": sku_data["shopify_url"]},
                    },
                },
            },
        },
    )

    ad = account.create_ad(
        fields=[],
        params={
            Ad.Field.name: f"MG_{post['sku']}_ad",
            Ad.Field.adset_id: adset["id"],
            Ad.Field.creative: {"creative_id": creative["id"]},
            Ad.Field.status: Ad.Status.paused,
        },
    )

    with db:
        db.execute(
            """
            INSERT INTO ad_campaigns
                (campaign_key, sku, campaign_date, campaign_phase,
                 campaign_id, adset_id, creative_id, ad_id, daily_budget_inr, post_id)
            VALUES (?,?,?,?,?,?,?,?,?,?)
            """,
            (
                campaign_key, post["sku"], campaign_date, phase,
                campaign["id"], adset["id"], creative["id"], ad["id"], budget_inr, pid,
            ),
        )

    log.info(
        "  ✓ Campaign %s created (PAUSED) — activate manually in Meta Ads Manager",
        campaign["id"],
    )
