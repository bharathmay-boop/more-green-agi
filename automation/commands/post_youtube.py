import logging
import os

from utils.db import get_db

log = logging.getLogger(__name__)


def run(post_id: str = None, dry_run: bool = False) -> None:
    db = get_db()
    posts = _fetch_posts(db, post_id)

    if not posts:
        log.info("No posts with videos ready for YouTube.")
        return

    from googleapiclient.discovery import build
    from googleapiclient.http import MediaFileUpload

    youtube = build("youtube", "v3", developerKey=os.environ.get("YOUTUBE_API_KEY", ""))

    for post in posts:
        from config import PROJECT_ROOT
        video_path = PROJECT_ROOT / post["video_path"]
        if not video_path.exists():
            log.warning("Video file not found for %s: %s", post["post_id"], video_path)
            continue

        if dry_run:
            log.info("[DRY RUN] Would upload %s to YouTube Shorts", post["post_id"])
            continue

        body = {
            "snippet": {
                "title": (post["topic"] or post["post_id"])[:100],
                "description": post["caption_instagram"] or "",
                "tags": ["microgreens", "moregreenin", "healthyindia"],
                "categoryId": "26",
            },
            "status": {
                "privacyStatus": "public",
                "selfDeclaredMadeForKids": False,
            },
        }
        media = MediaFileUpload(str(video_path), chunksize=-1, resumable=True)
        request = youtube.videos().insert(part="snippet,status", body=body, media_body=media)
        response = request.execute()
        yt_id = response["id"]
        with db:
            db.execute(
                "UPDATE posts SET youtube_video_id=? WHERE post_id=?",
                (yt_id, post["post_id"]),
            )
        log.info("  ✓ YouTube Shorts: https://youtube.com/shorts/%s (post: %s)", yt_id, post["post_id"])


def _fetch_posts(db, post_id):
    query = (
        "SELECT * FROM posts WHERE creatives_approved=1 "
        "AND video_path IS NOT NULL AND video_path != '' "
        "AND (youtube_video_id IS NULL OR youtube_video_id='') AND on_hold=0"
    )
    params = []
    if post_id:
        query += " AND post_id = ?"
        params.append(post_id)
    return db.execute(query, params).fetchall()
