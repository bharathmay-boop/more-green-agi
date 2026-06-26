"""compute-attribution — blended/paid ROAS rollups (docs/plan/moregreen/03).

For each (sku, date) in the window:
    spend            = Σ ad_spend_daily.spend_inr
    paid_revenue     = Σ ad_spend_daily.purchase_value_inr   (Meta-attributed)
    blended_revenue  = Σ orders.revenue_inr                  (all sales, paid+organic)
    paid_roas        = paid_revenue / spend      (None when spend == 0)
    blended_roas     = blended_revenue / spend   (None when spend == 0)
    organic_assist   = blended_revenue − paid_revenue

Also rolls up scope=campaign and scope=blended (all SKUs). Refund-safe (negative
revenue flows through), ÷0-safe (ROAS → None, shown as "—"), IST day bucketing.
"""
from __future__ import annotations

import datetime as _dt
import logging
from collections import defaultdict

from utils.db import get_db

log = logging.getLogger(__name__)

_IST = _dt.timezone(_dt.timedelta(hours=5, minutes=30))


# ── pure helpers (unit-tested) ───────────────────────────────────────────────
def roas(revenue: float, spend: float) -> float | None:
    """ROAS = revenue/spend, or None when spend is 0 (avoid ÷0)."""
    if not spend:
        return None
    return revenue / spend


def ist_date(value: str | None) -> str | None:
    """Normalize a Shopify/ISO timestamp to an IST calendar date (YYYY-MM-DD)."""
    if not value:
        return None
    s = str(value).strip().replace("Z", "+00:00")
    try:
        dt = _dt.datetime.fromisoformat(s)
    except ValueError:
        # bare date already
        return s[:10] if len(s) >= 10 else None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=_dt.timezone.utc)
    return dt.astimezone(_IST).date().isoformat()


def _window_start(days: int) -> str:
    return (_dt.datetime.now(_IST) - _dt.timedelta(days=days)).date().isoformat()


# ── core ─────────────────────────────────────────────────────────────────────
def compute(db, days: int = 30) -> list[dict]:
    """Return attribution rows (does not write). Pure read over spend + orders."""
    start = _window_start(days)

    # spend + paid revenue per (sku,date) and per (campaign,date)
    spend_sku: dict[tuple, dict] = defaultdict(lambda: {"spend": 0.0, "paid": 0.0})
    spend_campaign: dict[tuple, dict] = defaultdict(lambda: {"spend": 0.0, "paid": 0.0})
    for r in db.execute(
        "SELECT sku, campaign_id, date, spend_inr, purchase_value_inr "
        "FROM ad_spend_daily WHERE date >= ?", (start,)
    ).fetchall():
        d = r["date"]
        sku = r["sku"] or "unmapped"
        spend_sku[(sku, d)]["spend"] += r["spend_inr"] or 0
        spend_sku[(sku, d)]["paid"] += r["purchase_value_inr"] or 0
        if r["campaign_id"]:
            spend_campaign[(r["campaign_id"], d)]["spend"] += r["spend_inr"] or 0
            spend_campaign[(r["campaign_id"], d)]["paid"] += r["purchase_value_inr"] or 0

    # blended revenue per (sku,date) from all orders (IST bucketed)
    blended_sku: dict[tuple, float] = defaultdict(float)
    for r in db.execute(
        "SELECT sku, created_at, revenue_inr FROM orders"
    ).fetchall():
        d = ist_date(r["created_at"])
        if not d or d < start:
            continue
        blended_sku[(r["sku"] or "unmapped", d)] += r["revenue_inr"] or 0

    rows: list[dict] = []
    # sku scope (union of keys seen in spend or orders)
    for key in set(spend_sku) | set(blended_sku):
        sku, d = key
        spend = spend_sku[key]["spend"]
        paid = spend_sku[key]["paid"]
        blended = blended_sku[key]
        rows.append({
            "scope": "sku", "scope_id": sku, "date": d,
            "spend_inr": spend, "revenue_inr": blended,
            "paid_roas": roas(paid, spend), "blended_roas": roas(blended, spend),
            "organic_assist_inr": blended - paid,
        })

    # campaign scope (paid only — no per-campaign organic signal)
    for (cid, d), v in spend_campaign.items():
        rows.append({
            "scope": "campaign", "scope_id": cid, "date": d,
            "spend_inr": v["spend"], "revenue_inr": v["paid"],
            "paid_roas": roas(v["paid"], v["spend"]),
            "blended_roas": roas(v["paid"], v["spend"]),
            "organic_assist_inr": 0.0,
        })

    # blended scope (all SKUs per day)
    by_day: dict[str, dict] = defaultdict(lambda: {"spend": 0.0, "paid": 0.0, "blended": 0.0})
    for (sku, d), v in spend_sku.items():
        by_day[d]["spend"] += v["spend"]; by_day[d]["paid"] += v["paid"]
    for (sku, d), v in blended_sku.items():
        by_day[d]["blended"] += v
    for d, v in by_day.items():
        rows.append({
            "scope": "blended", "scope_id": "all", "date": d,
            "spend_inr": v["spend"], "revenue_inr": v["blended"],
            "paid_roas": roas(v["paid"], v["spend"]),
            "blended_roas": roas(v["blended"], v["spend"]),
            "organic_assist_inr": v["blended"] - v["paid"],
        })
    return rows


def run(dry_run: bool = False, days: int = 30) -> None:
    db = get_db()
    rows = compute(db, days=days)
    if dry_run:
        print(f"compute-attribution dry-run: {len(rows)} rollup rows (writes none)")
        for r in rows[:10]:
            br = "—" if r["blended_roas"] is None else f"{r['blended_roas']:.2f}x"
            print(f"  {r['scope']:<8} {r['scope_id']:<12} {r['date']} "
                  f"spend=₹{r['spend_inr']:.0f} rev=₹{r['revenue_inr']:.0f} blendedROAS={br}")
        return
    for r in rows:
        with db:
            db.execute(
                "INSERT INTO attribution"
                "(scope,scope_id,date,paid_roas,blended_roas,organic_assist_inr,"
                " spend_inr,revenue_inr,computed_at) "
                "VALUES(?,?,?,?,?,?,?,?,datetime('now')) "
                "ON CONFLICT(scope,scope_id,date) DO UPDATE SET "
                " paid_roas=excluded.paid_roas, blended_roas=excluded.blended_roas, "
                " organic_assist_inr=excluded.organic_assist_inr, "
                " spend_inr=excluded.spend_inr, revenue_inr=excluded.revenue_inr, "
                " computed_at=datetime('now')",
                (r["scope"], r["scope_id"], r["date"], r["paid_roas"], r["blended_roas"],
                 r["organic_assist_inr"], r["spend_inr"], r["revenue_inr"]),
            )
    log.info("attribution: wrote %d rows", len(rows))
    print(f"compute-attribution: wrote {len(rows)} rollup rows")
