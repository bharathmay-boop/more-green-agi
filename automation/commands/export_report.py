import logging
from datetime import datetime

from tabulate import tabulate

from utils.db import get_db

log = logging.getLogger(__name__)


def run() -> None:
    db = get_db()
    today = datetime.utcnow().date().isoformat()

    # Ad performance
    insights = db.execute(
        """
        SELECT ic.ad_id, ac.sku, ac.campaign_date,
               ic.impressions, ic.clicks, ic.ctr, ic.spend_inr,
               ic.frequency, ic.roas, ic.action_taken
        FROM insights_cache ic
        JOIN ad_campaigns ac ON ic.ad_id = ac.ad_id
        ORDER BY ic.fetched_date DESC
        LIMIT 20
        """
    ).fetchall()

    # Post pipeline
    posts = db.execute(
        "SELECT post_id, sku, pipeline_status, scheduled_at FROM posts ORDER BY scheduled_at DESC LIMIT 10"
    ).fetchall()

    print(f"\n== More Green Weekly Report — {today} ==\n")

    print("--- Ad Performance ---")
    if insights:
        rows = [
            [r["sku"], r["campaign_date"], f"₹{r['spend_inr'] or 0:.0f}",
             f"{r['ctr'] or 0:.2f}%", f"{r['frequency'] or 0:.1f}",
             f"{r['roas'] or 0:.1f}x", r["action_taken"] or "—"]
            for r in insights
        ]
        print(tabulate(rows, headers=["SKU", "Date", "Spend", "CTR", "Freq", "ROAS", "Action"], tablefmt="simple"))
    else:
        print("  No insights data yet.")

    print("\n--- Recent Posts ---")
    if posts:
        rows = [[r["post_id"], r["sku"], r["pipeline_status"], r["scheduled_at"]] for r in posts]
        print(tabulate(rows, headers=["Post ID", "SKU", "Status", "Scheduled"], tablefmt="simple"))
    else:
        print("  No posts yet.")

    print()
