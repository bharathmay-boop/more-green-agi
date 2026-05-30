import json
import logging
import os
from pathlib import Path

import cloudinary
import cloudinary.uploader

from config import CLOUDINARY_FOLDER, PROJECT_ROOT
from utils.db import get_db

log = logging.getLogger(__name__)


def _init_cloudinary() -> None:
    cloudinary.config(
        cloud_name=os.environ["CLOUDINARY_CLOUD_NAME"],
        api_key=os.environ["CLOUDINARY_API_KEY"],
        api_secret=os.environ["CLOUDINARY_API_SECRET"],
        secure=True,
    )


def upload_single(local_path: str, public_id: str) -> str:
    """Upload one file to Cloudinary and return its secure URL."""
    _init_cloudinary()
    result = cloudinary.uploader.upload(
        local_path,
        folder=CLOUDINARY_FOLDER,
        public_id=public_id,
        overwrite=True,
        resource_type="auto",
    )
    return result["secure_url"]


def run(week: str = None, post_id: str = None, dry_run: bool = False) -> None:
    _init_cloudinary()
    db = get_db()
    posts = _fetch_posts(db, week, post_id)

    if not posts:
        log.info("No posts with local images to upload.")
        return

    for post in posts:
        _upload_post(db, post, dry_run)


def _fetch_posts(db, week, post_id):
    query = (
        "SELECT * FROM posts WHERE image_paths IS NOT NULL AND image_paths != '' "
        "AND (cloudinary_urls IS NULL OR cloudinary_urls = '') AND on_hold=0"
    )
    params = []
    if week:
        query += " AND post_id LIKE ?"
        params.append(f"{week}%")
    if post_id:
        query += " AND post_id = ?"
        params.append(post_id)
    return db.execute(query, params).fetchall()


def _upload_post(db, post, dry_run: bool) -> None:
    pid = post["post_id"]
    paths = json.loads(post["image_paths"] or "[]")

    if dry_run:
        log.info("[DRY RUN] Would upload %d images for %s to Cloudinary", len(paths), pid)
        return

    urls, public_ids = [], []
    for local_path in paths:
        full_path = PROJECT_ROOT / local_path
        if not full_path.exists():
            log.error("Local file missing: %s", full_path)
            continue
        public_id = f"{pid}_{Path(local_path).stem}"
        result = cloudinary.uploader.upload(
            str(full_path),
            folder=CLOUDINARY_FOLDER,
            public_id=public_id,
            overwrite=True,
            resource_type="image",
        )
        urls.append(result["secure_url"])
        public_ids.append(result["public_id"])
        log.info("  ✓ Uploaded %s → %s", Path(local_path).name, result["secure_url"])

    if urls:
        with db:
            db.execute(
                "UPDATE posts SET cloudinary_urls=?, cloudinary_public_ids=? WHERE post_id=?",
                (json.dumps(urls), json.dumps(public_ids), pid),
            )
