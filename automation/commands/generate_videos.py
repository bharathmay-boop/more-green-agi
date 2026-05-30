import json
import logging
import time

import requests

import fal_client

from config import FAL_KLING_ENDPOINT, VIDEO_DURATION_SECONDS, PROJECT_ROOT
from utils.db import get_db
from utils.guards import require_approval

log = logging.getLogger(__name__)

PENDING_JOBS = PROJECT_ROOT / "creatives" / "pending_video_jobs.json"


@require_approval("prompts_approved", "prompts")
def run(week: str = None, post_id: str = None, dry_run: bool = False) -> None:
    db = get_db()
    posts = _fetch_posts(db, week, post_id)

    if not posts:
        log.info("No posts ready for video generation.")
        return

    for post in posts:
        _process_post(db, post, dry_run)


def resume_pending() -> None:
    """Poll any video jobs saved in pending_video_jobs.json."""
    pending = _load_pending()
    if not pending:
        log.info("No pending video jobs.")
        return

    db = get_db()
    for request_id, meta in list(pending.items()):
        pid = meta["post_id"]
        log.info("Resuming video job %s for %s...", request_id, pid)
        try:
            result = _poll(request_id)
            _save_video(db, pid, result)
            pending.pop(request_id)
            _save_pending(pending)
            log.info("  ✓ Resumed and saved video for %s", pid)
        except Exception as e:
            log.error("  ✗ Failed to resume %s: %s", request_id, e)

    _save_pending(pending)


def _fetch_posts(db, week, post_id):
    query = "SELECT * FROM posts WHERE prompts_approved=1 AND (video_path IS NULL OR video_path='') AND on_hold=0"
    params = []
    if week:
        query += " AND post_id LIKE ?"
        params.append(f"{week}%")
    if post_id:
        query += " AND post_id = ?"
        params.append(post_id)
    return db.execute(query, params).fetchall()


def _process_post(db, post, dry_run: bool) -> None:
    pid = post["post_id"]

    # Need a Cloudinary URL for the source image
    urls = json.loads(post["cloudinary_urls"] or "[]")
    source_url = urls[0] if urls else None

    if not source_url:
        log.warning("No Cloudinary URL for %s — run upload-media first", pid)
        return

    if dry_run:
        log.info("[DRY RUN] Would call Kling 3.0 for %s", pid)
        return

    log.info("Submitting video job for %s...", pid)
    handler = fal_client.submit(
        FAL_KLING_ENDPOINT,
        arguments={
            "image_url": source_url,
            "prompt": post["video_prompt"],
            "duration": str(VIDEO_DURATION_SECONDS),
            "aspect_ratio": "9:16",
        },
    )
    request_id = handler.request_id

    # Persist BEFORE polling — crash-safe
    pending = _load_pending()
    pending[request_id] = {"post_id": pid, "submitted_at": time.time()}
    _save_pending(pending)
    log.info("  Job submitted: %s (persisted)", request_id)

    try:
        result = _poll(request_id)
        _save_video(db, pid, result)
        pending.pop(request_id, None)
        _save_pending(pending)
        log.info("COST fal.ai kling post=%s duration=%ds $%.2f", pid, VIDEO_DURATION_SECONDS, VIDEO_DURATION_SECONDS * 0.035)
    except Exception as e:
        log.error("Video generation failed for %s: %s", pid, e)
        # Job stays in pending for resume-video-jobs


def _save_video(db, pid: str, result: dict) -> None:
    out_dir = PROJECT_ROOT / "creatives" / "videos"
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / f"{pid}.mp4"
    out_path.write_bytes(requests.get(result["video"]["url"], timeout=60).content)
    log.info("  ✓ Video saved: %s", out_path.name)
    with db:
        db.execute(
            "UPDATE posts SET video_path=? WHERE post_id=?",
            (str(out_path.relative_to(PROJECT_ROOT)), pid),
        )


def _poll(request_id: str, timeout: int = 360) -> dict:
    deadline = time.time() + timeout
    while time.time() < deadline:
        status = fal_client.status(FAL_KLING_ENDPOINT, request_id, with_logs=False)
        if status.status == "COMPLETED":
            return fal_client.result(FAL_KLING_ENDPOINT, request_id)
        if status.status in ("FAILED", "CANCELLED"):
            raise RuntimeError(f"Video job {request_id} failed: {status}")
        log.debug("  ... video status=%s, waiting 15s", status.status)
        time.sleep(15)
    raise TimeoutError(
        f"Video job {request_id} timed out after {timeout}s. "
        "Run: python main.py resume-video-jobs"
    )


def _load_pending() -> dict:
    PENDING_JOBS.parent.mkdir(parents=True, exist_ok=True)
    if not PENDING_JOBS.exists():
        return {}
    try:
        return json.loads(PENDING_JOBS.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return {}


def _save_pending(data: dict) -> None:
    PENDING_JOBS.write_text(json.dumps(data, indent=2), encoding="utf-8")
