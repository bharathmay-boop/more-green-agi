import logging
from datetime import datetime, timedelta

from tabulate import tabulate

from utils.db import get_db, OperationalError

log = logging.getLogger(__name__)


def _roas(revenue, spend):
    """Blended/paid ROAS, ÷0-safe (returns None when spend == 0)."""
    if not spend:
        return None
    return revenue / spend


def _fmt_roas(value) -> str:
    return f"{value:.2f}x" if value is not None else "—"


def _trend(recent, baseline) -> str:
    """Arrow comparing the 7d rate against the 30d rate."""
    if recent is None or baseline is None:
        return "—"
    if recent > baseline * 1.02:
        return "↑"
    if recent < baseline * 0.98:
        return "↓"
    return "→"


def _blended_roas_rows(db):
    """Per-SKU spend/revenue aggregated over 7d and 30d windows from `attribution`."""
    cutoff_30 = (datetime.utcnow().date() - timedelta(days=30)).isoformat()
    cutoff_7 = (datetime.utcnow().date() - timedelta(days=7)).isoformat()
    try:
        records = db.execute(
            """
            SELECT scope_id AS sku, date, spend_inr, revenue_inr
            FROM attribution
            WHERE scope = 'sku' AND date >= ?
            """,
            (cutoff_30,),
        ).fetchall()
    except OperationalError:
        return None

    agg: dict[str, dict] = {}
    for r in records:
        a = agg.setdefault(
            r["sku"], {"spend7": 0.0, "rev7": 0.0, "spend30": 0.0, "rev30": 0.0}
        )
        spend = r["spend_inr"] or 0.0
        rev = r["revenue_inr"] or 0.0
        a["spend30"] += spend
        a["rev30"] += rev
        if r["date"] >= cutoff_7:
            a["spend7"] += spend
            a["rev7"] += rev

    rows = []
    for sku in sorted(agg):
        a = agg[sku]
        roas7 = _roas(a["rev7"], a["spend7"])
        roas30 = _roas(a["rev30"], a["spend30"])
        rows.append(
            [
                sku,
                f"₹{a['spend7']:.0f}",
                _fmt_roas(roas7),
                _fmt_roas(roas30),
                _trend(roas7, roas30),
            ]
        )
    return rows


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

    print("\n--- Blended ROAS by SKU (7/30d) ---")
    roas_rows = _blended_roas_rows(db)
    if roas_rows is None:
        print("  No attribution data yet (run compute-attribution).")
    elif roas_rows:
        print(
            tabulate(
                roas_rows,
                headers=["SKU", "Spend 7d", "Blended 7d", "Blended 30d", "Trend"],
                tablefmt="simple",
            )
        )
    else:
        print("  No attribution data yet.")

    print()
