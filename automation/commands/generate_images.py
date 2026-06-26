import json
import logging

import requests

import fal_client

from config import (
    FAL_FLUX_KONTEXT_ENDPOINT,
    IMAGE_VARIANTS_PER_POST,
    PROJECT_ROOT,
)
from utils.db import get_db
from utils.guards import require_approval

log = logging.getLogger(__name__)


@require_approval("prompts_approved", "prompts")
def run(week: str = None, post_id: str = None, dry_run: bool = False, strength: float = 0.75, aspect_ratio: str = "3:4") -> None:
    db = get_db()
    posts = _fetch_posts(db, week, post_id)

    if not posts:
        log.info("No posts ready for image generation.")
        return

    for post in posts:
        _process_post(db, post, dry_run, strength, aspect_ratio)


def _fetch_posts(db, week, post_id):
    query = "SELECT * FROM posts WHERE prompts_approved=1 AND (image_paths IS NULL OR image_paths='') AND on_hold=0"
    params = []
    if week:
        query += " AND post_id LIKE ?"
        params.append(f"{week}%")
    if post_id:
        query += " AND post_id = ?"
        params.append(post_id)
    return db.execute(query, params).fetchall()


def _process_post(db, post, dry_run: bool, strength: float = 0.75, aspect_ratio: str = "3:4") -> None:
    pid = post["post_id"]
    source = PROJECT_ROOT / post["source_product_image"]

    if not source.exists():
        log.error("Source image not found: %s", source)
        with db:
            db.execute(
                "UPDATE posts SET pipeline_status='creative_failed', last_error=?, last_error_at=datetime('now') WHERE post_id=?",
                ("Source image not found", pid),
            )
        return

    # Upload source image to Cloudinary to get a public URL for fal.ai
    from commands.upload_media import upload_single
    source_url = upload_single(str(source), f"source_{pid}")

    if dry_run:
        log.info("[DRY RUN] Would call FLUX Kontext for %s (source: %s, strength=%.2f, aspect=%s)", pid, source_url, strength, aspect_ratio)
        return

    log.info("Generating %d images for %s (strength=%.2f, aspect=%s)...", IMAGE_VARIANTS_PER_POST, pid, strength, aspect_ratio)
    with db:
        db.execute("UPDATE posts SET pipeline_status='creative_generating' WHERE post_id=?", (pid,))

    try:
        result = fal_client.run(
            FAL_FLUX_KONTEXT_ENDPOINT,
            arguments={
                "prompt": post["image_prompt"],
                "image_url": source_url,
                "num_images": IMAGE_VARIANTS_PER_POST,
                "aspect_ratio": aspect_ratio,
                "safety_tolerance": "2",
                "strength": strength,
            },
        )

        out_dir = PROJECT_ROOT / "creatives" / "images"
        out_dir.mkdir(parents=True, exist_ok=True)
        saved_paths = []

        cost_each = 0.04
        for i, img in enumerate(result["images"]):
            out_path = out_dir / f"{pid}_{i}.jpg"
            out_path.write_bytes(requests.get(img["url"], timeout=30).content)
            rel = str(out_path.relative_to(PROJECT_ROOT))
            saved_paths.append(rel)
            log.info("  ✓ Saved %s (%dKB)", out_path.name, out_path.stat().st_size // 1024)
            # E5-T1: one creatives row per variant so score_creatives can rank them.
            with db:
                db.execute(
                    """INSERT INTO creatives (post_id, kind, variant_index, local_path, status, cost_usd)
                       VALUES (?, 'image', ?, ?, 'ready', ?)""",
                    (pid, i, rel, cost_each),
                )

        log.info("COST fal.ai flux_kontext post=%s variants=%d $%.2f", pid, IMAGE_VARIANTS_PER_POST, IMAGE_VARIANTS_PER_POST * cost_each)

        with db:
            db.execute(
                "UPDATE posts SET image_paths=?, pipeline_status='creative_ready', last_error=NULL WHERE post_id=?",
                (json.dumps(saved_paths), pid),
            )

    except Exception as e:
        log.error("Image generation failed for %s: %s", pid, e, exc_info=True)
        with db:
            db.execute(
                "UPDATE posts SET pipeline_status='creative_failed', last_error=?, last_error_at=datetime('now') WHERE post_id=?",
                (str(e), pid),
            )
