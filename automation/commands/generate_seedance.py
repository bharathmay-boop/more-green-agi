"""SeeDance 2.0 video generation via BytePlus ModelArk.

Usage:
    python main.py seedance-video --prompt "..." [--image <url>] [--image <url>]
                                                 [--video <url>] [--audio <url>]
                                                 [--ratio 9:16] [--duration 8]
                                                 [--out my_video.mp4]
"""
import logging
import os
import time
from pathlib import Path

import requests

from config import BYTEPLUS_ARK_BASE, SEEDANCE_MODEL, PROJECT_ROOT

log = logging.getLogger(__name__)

_TASKS_URL = f"{BYTEPLUS_ARK_BASE}/contents/generations/tasks"
_POLL_INTERVAL = 15  # seconds
_TIMEOUT = 600       # 10 minutes


def run(
    prompt: str,
    images: tuple = (),
    video: str = None,
    audio: str = None,
    ratio: str = "9:16",
    duration: int = 8,
    out: str = None,
    dry_run: bool = False,
) -> str | None:
    """Submit a SeeDance 2.0 job and download the result. Returns local file path."""
    api_key = os.environ.get("BYTEPLUS_ARK_API_KEY")
    if not api_key:
        raise EnvironmentError("BYTEPLUS_ARK_API_KEY not set in .env")

    content = [{"type": "text", "text": prompt}]
    for url in images:
        content.append({"type": "image_url", "image_url": {"url": url}, "role": "reference_image"})
    if video:
        content.append({"type": "video_url", "video_url": {"url": video}, "role": "reference_video"})
    if audio:
        content.append({"type": "audio_url", "audio_url": {"url": audio}, "role": "reference_audio"})

    payload = {
        "model": SEEDANCE_MODEL,
        "content": content,
        "generate_audio": True,
        "ratio": ratio,
        "duration": duration,
        "watermark": False,
    }

    if dry_run:
        log.info("[DRY RUN] Would POST to SeeDance 2.0: ratio=%s duration=%ds prompt=%s…", ratio, duration, prompt[:80])
        return None

    headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}

    log.info("Submitting SeeDance 2.0 job (ratio=%s, duration=%ds)…", ratio, duration)
    resp = requests.post(_TASKS_URL, json=payload, headers=headers, timeout=30)
    resp.raise_for_status()
    task = resp.json()
    task_id = task.get("id") or task.get("task_id")
    if not task_id:
        raise RuntimeError(f"No task_id in response: {task}")
    log.info("  Job submitted: %s", task_id)

    video_url = _poll(task_id, headers)
    out_path = _download(video_url, out, task_id)
    log.info("  Saved to %s", out_path)
    return str(out_path)


def _poll(task_id: str, headers: dict) -> str:
    poll_url = f"{_TASKS_URL}/{task_id}"
    deadline = time.time() + _TIMEOUT
    while time.time() < deadline:
        r = requests.get(poll_url, headers=headers, timeout=15)
        r.raise_for_status()
        data = r.json()
        status = (data.get("status") or "").lower()
        log.debug("  … SeeDance status=%s", status)
        if status in ("succeeded", "completed", "success"):
            return _extract_video_url(data)
        if status in ("failed", "cancelled", "error"):
            raise RuntimeError(f"SeeDance job {task_id} failed: {data}")
        time.sleep(_POLL_INTERVAL)
    raise TimeoutError(f"SeeDance job {task_id} timed out after {_TIMEOUT}s")


def _extract_video_url(data: dict) -> str:
    # Shape 1: data.content.video_url (string)
    content = data.get("content")
    if isinstance(content, dict):
        url = content.get("video_url") or content.get("url")
        if url:
            return url
    # Shape 2: data.content[].video_url.url (list of dicts)
    if isinstance(content, list):
        for item in content:
            if isinstance(item, dict) and item.get("type") == "video_url":
                v = item.get("video_url")
                return v["url"] if isinstance(v, dict) else v
    # Shape 3: data.output.video_url
    output = data.get("output") or {}
    url = output.get("video_url") or output.get("url")
    if url:
        return url
    raise RuntimeError(f"Cannot find video URL in response: {data}")


def _download(url: str, out: str | None, task_id: str) -> Path:
    out_dir = PROJECT_ROOT / "creatives" / "seedance"
    out_dir.mkdir(parents=True, exist_ok=True)
    filename = out if out else f"seedance_{task_id}.mp4"
    path = out_dir / filename
    with requests.get(url, stream=True, timeout=120) as r:
        r.raise_for_status()
        path.write_bytes(r.content)
    return path
