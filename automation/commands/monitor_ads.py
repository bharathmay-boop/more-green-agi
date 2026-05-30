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

    headers = ["SKU", "Date", "Spend", "CTR", "Freq", "CPM", "ROAS"]
    print(tabulate(rows, headers=headers, tablefmt="simple"))


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
