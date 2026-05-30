import json
import logging

import requests

from utils.db import get_db

log = logging.getLogger(__name__)


def run() -> None:
    db = get_db()
    posts = db.execute(
        "SELECT post_id, cloudinary_urls FROM posts WHERE cloudinary_urls IS NOT NULL AND cloudinary_urls != ''"
    ).fetchall()

    if not posts:
        log.info("No posts with Cloudinary URLs to verify.")
        return

    total, ok, failed = 0, 0, 0
    for post in posts:
        urls = json.loads(post["cloudinary_urls"] or "[]")
        for url in urls:
            total += 1
            try:
                r = requests.head(url, timeout=10, allow_redirects=True)
                if r.status_code == 200:
                    ok += 1
                else:
                    failed += 1
                    log.warning("  ✗ %s returned HTTP %d (post: %s)", url, r.status_code, post["post_id"])
                    with db:
                        db.execute(
                            "UPDATE posts SET last_error=?, last_error_at=datetime('now') WHERE post_id=?",
                            (f"Cloudinary URL returned {r.status_code}", post["post_id"]),
                        )
            except requests.RequestException as e:
                failed += 1
                log.error("  ✗ %s request failed: %s", url, e)

    log.info("Verified %d URLs: %d OK, %d failed", total, ok, failed)
    if failed == 0:
        print(f"All {total} URLs return 200 ✓")
    else:
        print(f"{failed} URLs failed — check logs for details.")
