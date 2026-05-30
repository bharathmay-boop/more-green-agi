import json
import logging
import os

import requests

from config import META_GRAPH_BASE
from utils.db import get_db
from utils.guards import require_approval
from utils.meta_auth import validate_meta_token
from utils.retry import check_meta_rate_limit

log = logging.getLogger(__name__)


@require_approval("creatives_approved", "creatives")
def run(platform: str = "both", post_id: str = None, dry_run: bool = False) -> None:
    validate_meta_token()
    db = get_db()
    token = os.environ["META_ACCESS_TOKEN"]
    ig_id = os.environ["META_IG_ACCOUNT_ID"]
    page_id = os.environ["META_PAGE_ID"]

    posts = _fetch_approved_posts(db, post_id)
    if not posts:
        log.info("No approved posts to publish.")
        return

    for post in posts:
        urls = json.loads(post["cloudinary_urls"] or "[]")
        if not urls:
            log.error("No Cloudinary URL for %s — run upload-media first", post["post_id"])
            continue

        image_url = urls[0]

        if dry_run:
            log.info("[DRY RUN] Would post %s to %s (image: %s)", post["post_id"], platform, image_url)
            continue

        if platform in ("instagram", "both"):
            ig_post_id = _post_instagram(ig_id, image_url, post["caption_instagram"], token, post["post_id"])
            if ig_post_id:
                with db:
                    db.execute(
                        "UPDATE posts SET ig_post_id=?, pipeline_status='posted', status='posted' WHERE post_id=?",
                        (ig_post_id, post["post_id"]),
                    )

        if platform in ("facebook", "both"):
            fb_post_id = _post_facebook(page_id, image_url, post["caption_facebook"], token, post["post_id"])
            if fb_post_id:
                with db:
                    db.execute(
                        "UPDATE posts SET fb_post_id=? WHERE post_id=?",
                        (fb_post_id, post["post_id"]),
                    )

        from utils.notifications import notify_founder
        notify_founder(
            subject=f"{post['sku'].title()} post published",
            body=f"Post {post['post_id']} went live on {platform}.",
        )


def _fetch_approved_posts(db, post_id):
    query = "SELECT * FROM posts WHERE creatives_approved=1 AND (ig_post_id IS NULL OR ig_post_id='') AND on_hold=0"
    params = []
    if post_id:
        query += " AND post_id = ?"
        params.append(post_id)
    return db.execute(query, params).fetchall()


def _post_instagram(ig_id: str, image_url: str, caption: str, token: str, pid: str) -> str:
    r = requests.post(
        f"{META_GRAPH_BASE}/{ig_id}/media",
        data={"image_url": image_url, "caption": caption, "access_token": token},
        timeout=30,
    )
    check_meta_rate_limit(r)
    r.raise_for_status()
    container_id = r.json()["id"]

    r2 = requests.post(
        f"{META_GRAPH_BASE}/{ig_id}/media_publish",
        data={"creation_id": container_id, "access_token": token},
        timeout=30,
    )
    check_meta_rate_limit(r2)
    r2.raise_for_status()
    post_id = r2.json()["id"]
    log.info("  ✓ Instagram post published: %s (post: %s)", post_id, pid)
    return post_id


def _post_facebook(page_id: str, image_url: str, caption: str, token: str, pid: str) -> str:
    r = requests.post(
        f"{META_GRAPH_BASE}/{page_id}/photos",
        data={"url": image_url, "caption": caption, "access_token": token},
        timeout=30,
    )
    check_meta_rate_limit(r)
    r.raise_for_status()
    post_id = r.json().get("post_id", r.json().get("id", ""))
    log.info("  ✓ Facebook photo posted: %s (post: %s)", post_id, pid)
    return post_id
