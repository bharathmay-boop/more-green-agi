"""autopilot_calendar — E6 Calendar Autopilot (docs/plan/moregreen/06).

Replaces manual Google-Sheets editing: auto-seeds draft ``post`` rows for the
next week from three deterministic sources, then proposes the week for founder
approval. Nothing here publishes or spends — every seeded post gets a
``publish_post`` proposal that a human approves in the queue (doc 04).

Sources blended into the weekly slot plan:
  1. ``cultural_calendar.yaml`` — events whose date window overlaps the target
     week bias those days toward their ``skus_to_feature`` and tag the
     ``cultural_moment``.
  2. Performance gaps — SKUs with no post created in the lookback window are
     guaranteed at least one slot so coverage never goes stale.
  3. SKU rotation honoring ``sku_split`` — the remaining slots are distributed
     across SKUs in the proportions declared in ``calendar.yaml`` ``meta``,
     using largest-remainder allocation (deterministic, offline-testable).

Idempotent: ``post_id`` is derived from date + slot, deduped against existing
rows and within the batch, and written with ``INSERT OR IGNORE``. Re-running
the same week adds nothing. ``seed_calendar.py`` / ``new_week.py`` remain as
manual fallbacks.
"""
from __future__ import annotations

import datetime as _dt
import logging
import math
import re
from collections import OrderedDict

import yaml

from utils.db import get_db
from utils import approvals

log = logging.getLogger(__name__)

# Posting cadence: Monday..Saturday (Sundays skipped by default, mirroring
# seed_calendar/new_week). Pillars rotate so the week is varied.
_DAYS = ["MON", "TUE", "WED", "THU", "FRI", "SAT", "SUN"]
_PILLARS = ["educational", "recipe", "product", "social_proof", "founder_bts"]
_POST_TYPES = ["feed_image", "carousel", "reels", "feed_image", "feed_image", "carousel"]


# ── inputs ────────────────────────────────────────────────────────────────────
def _sku_split() -> "OrderedDict[str, float]":
    """Read ``meta.sku_split`` from calendar.yaml; fall back to an even split
    across config SKUS (brand included) when absent."""
    import config
    try:
        data = yaml.safe_load(config.CALENDAR_PATH.read_text(encoding="utf-8")) or {}
        split = (data.get("meta") or {}).get("sku_split") or {}
    except FileNotFoundError:
        split = {}
    split = {k: float(v) for k, v in split.items() if float(v) > 0}
    if not split:
        skus = list(config.SKUS)
        split = {s: 1.0 for s in skus}
    return OrderedDict(sorted(split.items()))


def _next_monday(today: _dt.date | None = None) -> _dt.date:
    today = today or _dt.date.today()
    ahead = (0 - today.weekday()) % 7
    return today + _dt.timedelta(days=ahead or 7)


def _slug(name: str) -> str:
    return re.sub(r"[^a-z0-9]+", "_", name.lower()).strip("_")


def _md(s: str) -> tuple[int, int]:
    m, d = s.split("-")
    return int(m), int(d)


def _event_covers(event: dict, day: _dt.date) -> bool:
    """True if ``day`` falls within the event's [start, end] MM-DD window,
    handling year-wraparound windows (e.g. Wedding Season 11-01 → 01-31)."""
    dates = event.get("dates") or []
    if len(dates) < 2:
        return False
    start, end = _md(dates[0]), _md(dates[1])
    cur = (day.month, day.day)
    if start <= end:
        return start <= cur <= end
    return cur >= start or cur <= end  # wraps past year-end


def _active_events(week: list[_dt.date]) -> dict[_dt.date, dict]:
    """Map each day in the week to the first cultural event covering it."""
    import config
    out: dict[_dt.date, dict] = {}
    for day in week:
        for ev in config.CULTURAL_CALENDAR:
            if _event_covers(ev, day):
                out[day] = ev
                break
    return out


# ── allocation ────────────────────────────────────────────────────────────────
def _allocate(split: dict[str, float], slots: int) -> "OrderedDict[str, int]":
    """Largest-remainder allocation of ``slots`` across SKUs by ``split``."""
    total = sum(split.values()) or 1.0
    raw = {k: v / total * slots for k, v in split.items()}
    alloc = OrderedDict((k, int(math.floor(r))) for k, r in raw.items())
    short = slots - sum(alloc.values())
    order = sorted(split, key=lambda k: (raw[k] - math.floor(raw[k]), k), reverse=True)
    for i in range(short):
        alloc[order[i % len(order)]] += 1
    return alloc


def _ensure_gaps(alloc: "OrderedDict[str, int]", gaps: list[str], slots: int) -> None:
    """Guarantee each performance-gap SKU at least one slot, stealing from the
    most-allocated SKU so the total stays at ``slots``."""
    for sku in gaps:
        if alloc.get(sku, 0) > 0:
            continue
        donor = max(alloc, key=lambda k: alloc[k]) if alloc else None
        if donor is None or alloc[donor] <= 1:
            continue
        alloc[donor] -= 1
        alloc[sku] = alloc.get(sku, 0) + 1


def _perf_gaps(db, lookback_days: int) -> list[str]:
    """SKUs (excluding 'brand') with no post created in the lookback window."""
    import config
    start = (_dt.date.today() - _dt.timedelta(days=lookback_days)).isoformat()
    gaps = []
    for sku in config.SKUS:
        if sku == "brand":
            continue
        recent = db.execute(
            "SELECT 1 FROM posts WHERE sku=? AND created_at >= ? LIMIT 1", (sku, start)
        ).fetchone()
        if not recent:
            gaps.append(sku)
    return gaps


def _order_slots(alloc: "OrderedDict[str, int]") -> list[str]:
    """Flatten the allocation into a slot list, round-robin to avoid the same
    SKU landing on back-to-back days where possible."""
    pools = {k: v for k, v in alloc.items() if v > 0}
    seq: list[str] = []
    while pools:
        for sku in list(pools):
            seq.append(sku)
            pools[sku] -= 1
            if pools[sku] == 0:
                del pools[sku]
    return seq


# ── planner (pure) ────────────────────────────────────────────────────────────
def plan(db, week_start: _dt.date | None = None, slots: int = 6,
         lookback_days: int = 14, include_sundays: bool = False) -> dict:
    """Return the intended draft posts for the week. Writes nothing."""
    import config

    week_start = week_start or _next_monday()
    n_days = 7 if include_sundays else 6
    if slots is None:
        slots = n_days
    week = [week_start + _dt.timedelta(days=i) for i in range(n_days)]

    split = _sku_split()
    gaps = _perf_gaps(db, lookback_days)
    alloc = _allocate(split, slots)
    _ensure_gaps(alloc, gaps, slots)
    events = _active_events(week)

    # Bias slot ordering so cultural-event SKUs surface on their event days.
    slot_skus = _order_slots(alloc)
    days = week[:len(slot_skus)]

    posts = []
    for i, day in enumerate(days):
        sku = slot_skus[i]
        ev = events.get(day)
        # If an event covers this day and features a SKU we still have queued,
        # swap it in so the cultural moment lands on the right product.
        if ev:
            featured = [s for s in (ev.get("skus_to_feature") or []) if s in slot_skus[i:]]
            if featured and sku not in (ev.get("skus_to_feature") or []):
                swap = featured[0]
                j = slot_skus.index(swap, i)
                slot_skus[i], slot_skus[j] = slot_skus[j], slot_skus[i]
                sku = slot_skus[i]

        pillar = _PILLARS[i % len(_PILLARS)]
        post_type = _POST_TYPES[i % len(_POST_TYPES)]
        if ev:
            cultural = _slug(ev["name"])
            topic = " ".join((ev.get("content_angle") or ev["name"]).split())
        else:
            cultural = "none"
            sku_name = config.SKUS.get(sku, {}).get("name", sku)
            topic = f"{pillar.replace('_', ' ').title()} post featuring {sku_name}"

        day_tag = _DAYS[day.weekday()]
        post_id = f"AUTO_{day.isoformat().replace('-', '')}_{day_tag}_{i + 1:02d}"
        posts.append({
            "post_id": post_id,
            "scheduled_at": day.isoformat(),
            "platform": "both",
            "post_type": post_type,
            "content_pillar": pillar,
            "sku": sku,
            "topic": topic,
            "cultural_moment": cultural,
            "source_product_image": f"Files/{sku}/product_front.jpg",
            "is_gap": sku in gaps,
        })

    return {
        "week_start": week_start,
        "posts": posts,
        "split": dict(split),
        "alloc": dict(alloc),
        "gaps": gaps,
        "events": {d.isoformat(): e["name"] for d, e in events.items()},
    }


# ── runner ────────────────────────────────────────────────────────────────────
def run(dry_run: bool = False, week_start: str | None = None, slots: int = 6,
        lookback_days: int = 14, include_sundays: bool = False) -> None:
    db = get_db()
    ws = _dt.date.fromisoformat(week_start) if week_start else None
    p = plan(db, week_start=ws, slots=slots, lookback_days=lookback_days,
             include_sundays=include_sundays)

    print(f"autopilot-calendar: week of {p['week_start'].isoformat()} — "
          f"{len(p['posts'])} posts; sku_split {p['alloc']}; "
          f"gaps {p['gaps'] or 'none'}; events {list(p['events'].values()) or 'none'}")
    for post in p["posts"]:
        flag = " [gap]" if post["is_gap"] else ""
        moment = "" if post["cultural_moment"] == "none" else f"  <{post['cultural_moment']}>"
        print(f"  {post['scheduled_at']}  {post['sku']:<10} {post['post_type']:<10}"
              f"{moment}{flag}")

    if dry_run:
        print("autopilot-calendar dry-run: no posts or proposals written")
        return

    n_new = n_prop = 0
    for post in p["posts"]:
        existing = db.execute(
            "SELECT 1 FROM posts WHERE post_id=?", (post["post_id"],)
        ).fetchone()
        with db:
            db.execute(
                "INSERT OR IGNORE INTO posts "
                "(post_id, scheduled_at, platform, post_type, content_pillar, sku, "
                " topic, cultural_moment, source_product_image, pipeline_status) "
                "VALUES (?,?,?,?,?,?,?,?,?, 'draft')",
                (post["post_id"], post["scheduled_at"], post["platform"],
                 post["post_type"], post["content_pillar"], post["sku"],
                 post["topic"], post["cultural_moment"], post["source_product_image"]),
            )
        if existing:
            continue  # already seeded — dedupe, no duplicate proposal
        n_new += 1
        approvals.propose(
            "publish_post", post["post_id"],
            payload={"sku": post["sku"], "post_id": post["post_id"],
                     "scheduled_at": post["scheduled_at"],
                     "cultural_moment": post["cultural_moment"]},
            expected_impact={"reason": "gap fill" if post["is_gap"] else "weekly autopilot",
                             "week_start": p["week_start"].isoformat()},
            requested_by="autopilot_calendar", db=db,
        )
        n_prop += 1

    log.info("autopilot-calendar: %d new posts, %d proposals (week %s)",
             n_new, n_prop, p["week_start"].isoformat())
    print(f"autopilot-calendar: seeded {n_new} new posts, {n_prop} proposals "
          f"(awaiting founder approval)")
