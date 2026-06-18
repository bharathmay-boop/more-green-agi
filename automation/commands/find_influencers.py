import csv
import logging
import os
from datetime import date, datetime

import requests

from config import META_GRAPH_BASE
from utils.db import get_db
from utils.meta_auth import validate_meta_token

log = logging.getLogger(__name__)

TARGET_HASHTAGS = [
    "healthyindianfood",
    "indianhealthyfood",
    "healthycookingindia",
    "indiannutritionist",
    "desihealth",
    "microgreens",
    "greenpowder",
    "superfoods",
    "healthyrecipesindia",
    "plantbasedindian",
    "indianfitnessfood",
    "healthyeatingindia",
    "nutritionistindia",
    "cleaneatingindia",
    "greensmoothie",
]

POSTS_PER_HASHTAG = 70
OUR_HANDLE = "moregreen_in"


def run(hashtags: list = None, dry_run: bool = False) -> None:
    validate_meta_token()
    db = get_db()
    _ensure_table(db)

    token = os.environ["META_ACCESS_TOKEN"]
    ig_id = os.environ["META_IG_ACCOUNT_ID"]

    tags = hashtags or TARGET_HASHTAGS
    new_count = 0

    for tag in tags:
        usage_count = _track_hashtag_usage(db, tag)
        log.info("Searching #%s ... (hashtag usage last 7d: %d)", tag, usage_count)
        hashtag_id = _get_hashtag_id(tag, ig_id, token)
        if not hashtag_id:
            log.warning("  Could not resolve #%s — skipping", tag)
            continue

        posts = _get_recent_posts(hashtag_id, ig_id, token)
        log.info("  %d posts found", len(posts))

        for post in posts:
            media_id = post["id"]
            permalink = post.get("permalink", "")

            details = _get_media_details(media_id, token)
            username = details.get("username", "")
            like_count = details.get("like_count") or 0
            comments_count = details.get("comments_count") or 0

            if not username or username.lower() == OUR_HANDLE:
                continue

            # Skip very low-engagement posts (likely bots or inactive accounts)
            if like_count < 30:
                continue

            existing = db.execute(
                "SELECT handle FROM influencers WHERE handle=?", (username,)
            ).fetchone()
            if existing:
                continue

            # Enrich with Business Discovery (follower count + IG user ID for DMs)
            profile = lookup_business_profile(username, ig_id, token)
            ig_user_id = profile.get("id", "")
            follower_count = profile.get("followers_count")
            full_name = profile.get("name", "")

            # Micro-influencer filter: 5k–150k followers (skip if known and outside range)
            if follower_count is not None and not (5_000 <= follower_count <= 150_000):
                log.debug("  @%s followers=%d outside micro range — skipping", username, follower_count)
                continue

            # Calculate engagement rate; skip if below playbook minimum
            eng_rate = 0.0
            if follower_count and follower_count > 0:
                eng_rate = (like_count + comments_count) / follower_count
            if eng_rate < 0.03:
                log.debug("  @%s eng_rate=%.1f%% below 3%% — skipping", username, eng_rate * 100)
                continue

            if not dry_run:
                with db:
                    db.execute(
                        """INSERT INTO influencers
                           (handle, full_name, ig_user_id, follower_count, engagement_rate,
                            source_hashtag, post_url, like_count, comments_count,
                            status, created_at, updated_at)
                           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 'discovered', datetime('now'), datetime('now'))""",
                        (username, full_name, ig_user_id, follower_count, eng_rate,
                         tag, permalink, like_count, comments_count),
                    )
            log.info(
                "  + @%s  followers=%s  eng=%.1f%%  likes=%d",
                username, f"{follower_count:,}" if follower_count else "?", eng_rate * 100, like_count,
            )
            new_count += 1

    csv_path = f"influencers_{datetime.now().strftime('%Y%m%d_%H%M')}.csv"
    _export_csv(db, csv_path)
    log.info("Done. New influencers added: %d", new_count)
    log.info("CSV exported: %s", csv_path)
    log.info("Next: open CSV, add emails + set status='approved', then run outreach-email")


def _get_hashtag_id(tag: str, ig_id: str, token: str) -> str:
    r = requests.get(
        f"{META_GRAPH_BASE}/ig-hashtag-search",
        params={"user_id": ig_id, "q": tag, "access_token": token},
        timeout=15,
    )
    data = r.json()
    if "error" in data:
        log.warning("Hashtag search error for #%s: %s", tag, data["error"].get("message", ""))
        return ""
    results = data.get("data", [])
    return results[0]["id"] if results else ""


def _get_recent_posts(hashtag_id: str, ig_id: str, token: str) -> list:
    r = requests.get(
        f"{META_GRAPH_BASE}/{hashtag_id}/recent_media",
        params={
            "user_id": ig_id,
            "fields": "id,permalink,timestamp",
            "limit": POSTS_PER_HASHTAG,
            "access_token": token,
        },
        timeout=20,
    )
    data = r.json()
    if "error" in data:
        log.warning("recent_media error: %s", data["error"].get("message", ""))
        return []
    return data.get("data", [])


def _get_media_details(media_id: str, token: str) -> dict:
    r = requests.get(
        f"{META_GRAPH_BASE}/{media_id}",
        params={"fields": "username,like_count,comments_count", "access_token": token},
        timeout=10,
    )
    data = r.json()
    if "error" in data:
        return {}
    return data


def lookup_business_profile(username: str, ig_id: str, token: str) -> dict:
    """Business Discovery API: resolve username to IG user ID + follower count."""
    r = requests.get(
        f"{META_GRAPH_BASE}/{ig_id}",
        params={
            "fields": f"business_discovery.fields(id,username,name,followers_count,media_count)",
            "username": username,
            "access_token": token,
        },
        timeout=10,
    )
    data = r.json()
    if "error" in data or "business_discovery" not in data:
        return {}
    return data["business_discovery"]


def _track_hashtag_usage(db, tag: str) -> int:
    """Insert today's hashtag use and warn if approaching Meta's 30-hashtag/7-day limit."""
    today = date.today().isoformat()
    db.execute(
        "CREATE TABLE IF NOT EXISTS hashtag_usage (hashtag TEXT, queried_date TEXT, PRIMARY KEY (hashtag, queried_date))"
    )
    db.execute(
        "INSERT OR IGNORE INTO hashtag_usage (hashtag, queried_date) VALUES (?, ?)",
        (tag, today),
    )
    db.commit()
    cutoff = date.fromordinal(date.today().toordinal() - 7).isoformat()
    row = db.execute(
        "SELECT COUNT(DISTINCT hashtag) FROM hashtag_usage WHERE queried_date >= ?",
        (cutoff,),
    ).fetchone()
    count = row[0] if row else 0
    if count >= 25:
        log.warning(
            "Hashtag usage in last 7 days: %d — approaching Meta's 30-hashtag limit!", count
        )
    return count


def _ensure_table(db) -> None:
    db.execute("""
        CREATE TABLE IF NOT EXISTS influencers (
            handle                  TEXT PRIMARY KEY,
            full_name               TEXT,
            email                   TEXT,
            ig_user_id              TEXT,
            follower_count          INTEGER,
            engagement_rate         REAL,
            source_hashtag          TEXT,
            post_url                TEXT,
            like_count              INTEGER,
            comments_count          INTEGER,
            status                  TEXT DEFAULT 'discovered',
            notes                   TEXT,
            outreach_sent_at        TEXT,
            dm_sent_at              TEXT,
            reply_received_at       TEXT,
            collab_agreed           INTEGER DEFAULT 0,
            product_shipped         INTEGER DEFAULT 0,
            tracking_code           TEXT,
            template_used           TEXT,
            last_reply_preview      TEXT,
            last_message_at         TEXT,
            last_checked_at         TEXT,
            shipping_address        TEXT,
            product_dispatched_at   TEXT,
            agreed_post_date        TEXT,
            post_live_url           TEXT,
            dm_draft_generated_at   TEXT,
            created_at              TEXT DEFAULT (datetime('now')),
            updated_at              TEXT DEFAULT (datetime('now'))
        )
    """)


def _export_csv(db, path: str) -> None:
    rows = db.execute(
        """SELECT handle, full_name, email, follower_count, source_hashtag,
                  post_url, like_count, comments_count, status
           FROM influencers ORDER BY like_count DESC"""
    ).fetchall()
    fields = ["handle", "full_name", "email", "follower_count", "source_hashtag",
              "post_url", "like_count", "comments_count", "status"]
    with open(path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fields)
        writer.writeheader()
        writer.writerows([dict(r) for r in rows])
