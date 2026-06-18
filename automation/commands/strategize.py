"""strategize — the marketing-head brain (docs/plan/moregreen/05).

Reads blended-ROAS attribution, ranks SKUs, and turns the read into ACTION
*proposals* — never autonomous spend:

  * Winners (blended_roas >= ROAS_FLOOR_FOR_SCALE) with an active campaign
    → a `scale_budget` proposal (capped by config; apply_approved enforces).
  * SKUs with weak ROAS but live spend → a `reallocate` proposal (shift budget
    toward winners), again human-approved before anything moves.
  * SKUs starved of fresh content → a draft post row + a `publish_post` proposal.

The allocation MATH is deterministic and offline-testable. Claude is used only to
write the human-readable strategy memo, and is skipped in dry-run / when no key is
set. Nothing here calls Meta or raises spend — that stays behind apply_approved.
"""
from __future__ import annotations

import datetime as _dt
import logging
from collections import defaultdict

from utils.db import get_db
from utils import approvals

log = logging.getLogger(__name__)


def _floor() -> float:
    import config
    return float(getattr(config, "ROAS_FLOOR_FOR_SCALE", 2.5))


def _multiplier() -> float:
    import config
    return float(getattr(config, "SCALE_BUDGET_MULTIPLIER", 1.3))


def _sku_roas(db, days: int) -> dict[str, dict]:
    """Aggregate attribution(scope='sku') over the window → per-SKU rollup."""
    start = (_dt.date.today() - _dt.timedelta(days=days)).isoformat()
    agg: dict[str, dict] = defaultdict(lambda: {"spend": 0.0, "revenue": 0.0})
    for r in db.execute(
        "SELECT scope_id, spend_inr, revenue_inr FROM attribution "
        "WHERE scope='sku' AND date >= ?", (start,)
    ).fetchall():
        a = agg[r["scope_id"]]
        a["spend"] += float(r["spend_inr"] or 0)
        a["revenue"] += float(r["revenue_inr"] or 0)
    for sku, a in agg.items():
        a["blended_roas"] = (a["revenue"] / a["spend"]) if a["spend"] else None
    return agg


def _active_campaign(db, sku: str):
    return db.execute(
        "SELECT * FROM ad_campaigns WHERE sku=? AND status='ACTIVE' "
        "ORDER BY created_at DESC LIMIT 1", (sku,),
    ).fetchone()


def plan(db, days: int = 14) -> dict:
    """Pure planner: returns the set of intended proposals/drafts (writes nothing)."""
    floor = _floor()
    mult = _multiplier()
    roas = _sku_roas(db, days)

    scales, reallocs, drafts = [], [], []
    for sku, a in sorted(roas.items(), key=lambda kv: (kv[1]["blended_roas"] or -1), reverse=True):
        br = a["blended_roas"]
        camp = _active_campaign(db, sku)
        if br is not None and br >= floor and camp:
            current = float(camp["daily_budget_inr"] or 0)
            scales.append({
                "sku": sku, "campaign_key": camp["campaign_key"],
                "adset_id": camp["adset_id"], "blended_roas": br,
                "current_inr": current, "proposed_inr": round(current * mult),
            })
        elif br is not None and br < floor and a["spend"] > 0 and camp:
            reallocs.append({
                "sku": sku, "campaign_key": camp["campaign_key"],
                "blended_roas": br, "spend_inr": a["spend"],
            })

    # Content gaps: SKUs with no draft/scheduled post in the window get a draft.
    import config
    start = (_dt.date.today() - _dt.timedelta(days=days)).isoformat()
    for sku in config.SKUS:
        if sku == "brand":
            continue
        has_recent = db.execute(
            "SELECT 1 FROM posts WHERE sku=? AND created_at >= ? LIMIT 1", (sku, start),
        ).fetchone()
        if not has_recent:
            drafts.append({"sku": sku})

    return {"scales": scales, "reallocs": reallocs, "drafts": drafts, "roas": roas}


def run(dry_run: bool = False, days: int = 14) -> None:
    db = get_db()
    p = plan(db, days=days)

    print(f"strategize: {len(p['scales'])} scale, {len(p['reallocs'])} reallocate, "
          f"{len(p['drafts'])} content-gap drafts (window {days}d)")
    for s in p["scales"]:
        print(f"  SCALE   {s['sku']:<10} ROAS {s['blended_roas']:.1f}x  "
              f"budget {s['current_inr']:.0f}->{s['proposed_inr']:.0f}")
    for r in p["reallocs"]:
        print(f"  REALLOC {r['sku']:<10} ROAS {r['blended_roas']:.1f}x  (under floor)")
    for d in p["drafts"]:
        print(f"  DRAFT   {d['sku']:<10} (no recent content)")

    if dry_run:
        print("strategize dry-run: no proposals or drafts written")
        return

    n_prop = n_draft = 0
    for s in p["scales"]:
        approvals.propose(
            "scale_budget", s["campaign_key"],
            payload={"adset_id": s["adset_id"], "sku": s["sku"],
                     "current_inr": s["current_inr"], "proposed_inr": s["proposed_inr"],
                     "multiplier": _multiplier()},
            expected_impact={"current_roas": s["blended_roas"],
                             "projected_spend_inr": s["proposed_inr"]},
            requested_by="strategize", db=db,
        )
        n_prop += 1
    for r in p["reallocs"]:
        approvals.propose(
            "reallocate", r["campaign_key"],
            payload={"sku": r["sku"], "reason": "below ROAS floor",
                     "blended_roas": r["blended_roas"]},
            expected_impact={"current_roas": r["blended_roas"]},
            requested_by="strategize", db=db,
        )
        n_prop += 1
    for d in p["drafts"]:
        pid = f"STRAT_{d['sku']}_{_dt.date.today().isoformat().replace('-', '')}"
        with db:
            db.execute(
                "INSERT OR IGNORE INTO posts "
                "(post_id, scheduled_at, platform, post_type, sku, topic, "
                " source_product_image, pipeline_status) "
                "VALUES (?,?,?,?,?,?,?, 'draft')",
                (pid, _dt.date.today().isoformat(), "instagram", "feed_image",
                 d["sku"], f"Strategist content gap fill for {d['sku']}", ""),
            )
        approvals.propose(
            "publish_post", pid,
            payload={"sku": d["sku"], "post_id": pid},
            expected_impact={"reason": "content gap"},
            requested_by="strategize", db=db,
        )
        n_prop += 1
        n_draft += 1

    log.info("strategize: %d proposals, %d post drafts", n_prop, n_draft)
    print(f"strategize: wrote {n_prop} proposals, {n_draft} post drafts (awaiting approval)")
