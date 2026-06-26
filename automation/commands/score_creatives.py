"""E5-T3 — CTR-fed variant scoring loop.

Reads the latest Meta CTR for each ad (insights_cache), maps it back to the post
that ran it (ad_campaigns.post_id), and marks that post's creatives 'selected'
when CTR clears the format floor, else 'rejected'. The next ad run can then ship
a proven creative instead of variant 0.

ponytail: CTR attributes at the post level (one ad per post today), so all of a
post's ready creatives share the verdict. True per-variant scoring needs
create_ads to ship each variant as its own ad and record creatives.id on the
ad row — upgrade there when multi-variant ads ship.
"""
import logging

from config import PAUSE_CTR_FEED_BELOW, PAUSE_CTR_REELS_BELOW
from utils.db import get_db

log = logging.getLogger(__name__)


def _floor_for(post_type: str) -> float:
    return PAUSE_CTR_REELS_BELOW if post_type and "reel" in post_type.lower() else PAUSE_CTR_FEED_BELOW


def run(dry_run: bool = False) -> None:
    db = get_db()

    # Latest CTR per post: newest insight row for each ad that has a post_id.
    rows = db.execute(
        """
        SELECT ac.post_id AS post_id, p.post_type AS post_type, ic.ctr AS ctr
        FROM ad_campaigns ac
        JOIN posts p ON p.post_id = ac.post_id
        JOIN insights_cache ic ON ic.ad_id = ac.ad_id
        WHERE ac.post_id IS NOT NULL AND ic.ctr IS NOT NULL
          AND ic.fetched_date = (
              SELECT MAX(fetched_date) FROM insights_cache WHERE ad_id = ac.ad_id
          )
        """
    ).fetchall()

    if not rows:
        log.info("No CTR data linked to creatives yet — nothing to score.")
        return

    promoted = rejected = 0
    for r in rows:
        floor = _floor_for(r["post_type"])
        verdict = "selected" if r["ctr"] >= floor else "rejected"
        log.info("post=%s ctr=%.4f floor=%.4f -> %s", r["post_id"], r["ctr"], floor, verdict)
        if dry_run:
            continue
        with db:
            db.execute(
                "UPDATE creatives SET status=?, updated_at=datetime('now') "
                "WHERE post_id=? AND status IN ('ready','selected','rejected')",
                (verdict, r["post_id"]),
            )
        promoted += verdict == "selected"
        rejected += verdict == "rejected"

    log.info("Scored %d posts — %d selected, %d rejected.", len(rows), promoted, rejected)
