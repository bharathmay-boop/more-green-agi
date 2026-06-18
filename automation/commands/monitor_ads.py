import logging
import os
from datetime import datetime

from facebook_business.api import FacebookAdsApi
from facebook_business.adobjects.ad import Ad
from tabulate import tabulate

from utils.db import get_db

log = logging.getLogger(__name__)

_INSIGHT_FIELDS = [
    "impressions", "clicks", "ctr", "spend",
    "frequency", "cpm", "actions",
]


def run() -> None:
    db = get_db()
    campaigns = db.execute(
        "SELECT * FROM ad_campaigns WHERE status != 'ARCHIVED'"
    ).fetchall()

    if not campaigns:
        log.info("No active campaigns to monitor.")
        print("No campaigns in the database yet.")
        return

    FacebookAdsApi.init(
        app_id=os.environ["META_APP_ID"],
        app_secret=os.environ["META_APP_SECRET"],
        access_token=os.environ["META_ACCESS_TOKEN"],
    )

    today = datetime.utcnow().date().isoformat()
    rows = []

    for c in campaigns:
        ins = _fetch_insights(c["ad_id"])
        if not ins:
            rows.append([c["sku"], c["campaign_date"], "N/A", "N/A", "N/A", "N/A", "N/A"])
            continue

        spend   = float(ins.get("spend", 0))
        ctr     = float(ins.get("ctr", 0))
        freq    = float(ins.get("frequency", 0))
        cpm     = float(ins.get("cpm", 0))
        roas    = _extract_roas(ins)

        rows.append([
            c["sku"],
            c["campaign_date"],
            f"₹{spend:.0f}",
            f"{ctr:.2f}%",
            f"{freq:.1f}",
            f"₹{cpm:.0f}",
            f"{roas:.1f}x" if roas else "N/A",
        ])

        with db:
            db.execute(
                """
                INSERT OR REPLACE INTO insights_cache
                    (ad_id, fetched_date, impressions, clicks, ctr,
                     spend_inr, frequency, roas)
                VALUES (?,?,?,?,?,?,?,?)
                """,
                (
                    c["ad_id"], today,
                    int(ins.get("impressions", 0)),
                    int(ins.get("clicks", 0)),
                    ctr, spend, freq, roas,
                ),
            )

        # Per-day spend rows for blended-ROAS attribution (doc 03). Additive —
        # the lifetime cache above is left untouched for backward compatibility.
        _upsert_daily(db, c)

    headers = ["SKU", "Date", "Spend", "CTR", "Freq", "CPM", "ROAS"]
    print(tabulate(rows, headers=headers, tablefmt="simple"))


def _upsert_daily(db, campaign) -> None:
    """Fetch last-7-day per-day insights for one ad and upsert ad_spend_daily.

    Keyed by (ad_id, date); sku/campaign_id are carried from the ad_campaigns
    row so attribution can roll up by SKU and by campaign.
    """
    for day in _fetch_daily_insights(campaign["ad_id"]):
        date = day.get("date_start")
        if not date:
            continue
        spend       = float(day.get("spend", 0) or 0)
        impressions = int(float(day.get("impressions", 0) or 0))
        clicks      = int(float(day.get("clicks", 0) or 0))
        cpm         = float(day.get("cpm", 0) or 0)
        ctr         = float(day.get("ctr", 0) or 0)
        freq        = float(day.get("frequency", 0) or 0)
        purchases, purchase_value = _extract_purchases(day)
        with db:
            db.execute(
                """
                INSERT INTO ad_spend_daily
                    (ad_id, date, campaign_id, sku, spend_inr, impressions,
                     clicks, purchases, purchase_value_inr, cpm_inr, ctr,
                     frequency, fetched_at)
                VALUES (?,?,?,?,?,?,?,?,?,?,?,?,datetime('now'))
                ON CONFLICT(ad_id, date) DO UPDATE SET
                     campaign_id=excluded.campaign_id, sku=excluded.sku,
                     spend_inr=excluded.spend_inr, impressions=excluded.impressions,
                     clicks=excluded.clicks, purchases=excluded.purchases,
                     purchase_value_inr=excluded.purchase_value_inr,
                     cpm_inr=excluded.cpm_inr, ctr=excluded.ctr,
                     frequency=excluded.frequency, fetched_at=datetime('now')
                """,
                (
                    campaign["ad_id"], date, campaign["campaign_id"], campaign["sku"],
                    spend, impressions, clicks, purchases, purchase_value,
                    cpm, ctr, freq,
                ),
            )


def _fetch_daily_insights(ad_id: str) -> list:
    """Per-day insights for the last 7 days (time_increment=1)."""
    try:
        ad = Ad(ad_id)
        insights = ad.get_insights(
            fields=_INSIGHT_FIELDS + ["action_values", "date_start", "date_stop"],
            params={"date_preset": "last_7d", "time_increment": 1},
        )
        return [dict(i) for i in insights] if insights else []
    except Exception as e:
        log.warning("Could not fetch daily insights for ad %s: %s", ad_id, e)
        return []


def _extract_purchases(ins: dict) -> tuple:
    """Return (purchase_count, purchase_value_inr) from the actions arrays."""
    count = 0
    for action in ins.get("actions", []) or []:
        if action.get("action_type") == "omni_purchase":
            try:
                count = int(float(action.get("value", 0)))
            except (TypeError, ValueError):
                pass
            break
    value = 0.0
    for av in ins.get("action_values", []) or []:
        if av.get("action_type") == "omni_purchase":
            try:
                value = float(av.get("value", 0))
            except (TypeError, ValueError):
                pass
            break
    return count, value


def _fetch_insights(ad_id: str) -> dict:
    try:
        ad = Ad(ad_id)
        insights = ad.get_insights(fields=_INSIGHT_FIELDS, params={"date_preset": "lifetime"})
        return dict(insights[0]) if insights else {}
    except Exception as e:
        log.warning("Could not fetch insights for ad %s: %s", ad_id, e)
        return {}


def _extract_roas(ins: dict) -> float:
    """Extract purchase ROAS from the actions array."""
    for action in ins.get("actions", []) or []:
        if action.get("action_type") == "omni_purchase":
            try:
                spend = float(ins.get("spend", 0))
                value = float(action.get("value", 0))
                if spend > 0:
                    return value / spend
            except (TypeError, ValueError):
                pass
    return 0.0
