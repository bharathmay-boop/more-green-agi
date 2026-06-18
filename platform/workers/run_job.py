#!/usr/bin/env python3
"""run_job.py — Python worker entrypoint for the More Green platform.

Consumes jobs enqueued by the Next.js control plane
(``platform/apps/web/lib/queue.ts``) and dispatches each to the matching
``automation/commands/*`` integration via :mod:`dispatch`.

Two modes:

* **Single dispatch** (testing / cron / manual) — run one named job and exit::

      python platform/workers/run_job.py --job sync_orders --payload '{"days":7}' --dry-run

* **Queue worker** (default) — BRPOP from Redis, mark the job ``running``,
  dispatch it, then mark ``done`` / ``failed`` and persist any error::

      python platform/workers/run_job.py            # loop forever
      python platform/workers/run_job.py --once      # drain one job then exit

Money-safety: consuming a job is not the same as applying spend. Spend-raising
jobs (``apply_approved``) must already be gated by an approved ``approval_queue``
row before they are enqueued — see docs/plan/moregreen/04. ``--dry-run`` forces
every command into no-write mode.
"""
from __future__ import annotations

import argparse
import json
import logging
import os
import sys
import time
from pathlib import Path

# --- Path bootstrap -------------------------------------------------------
# automation/commands/* import as `from commands.X import run`, `import config`,
# and `from utils.db import get_db`, so the automation dir must be importable.
REPO_ROOT = Path(__file__).resolve().parents[2]
AUTOMATION_DIR = REPO_ROOT / "automation"
if str(AUTOMATION_DIR) not in sys.path:
    sys.path.insert(0, str(AUTOMATION_DIR))

from dispatch import REGISTRY, dispatch  # noqa: E402  (after sys.path setup)
import reliability  # noqa: E402  (sibling module; retries/DLQ/metrics/retention)

log = logging.getLogger("workers.run_job")

# Mirror the keys used by platform/apps/web/lib/queue.ts.
QUEUE_KEY = "moregreen:jobs:queue"
JOB_KEY_PREFIX = "moregreen:job:"


def _configure_logging() -> None:
    try:  # reuse the automation logging config when available
        from utils.logging_config import configure
        configure(verbose=False)
    except Exception:
        logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")


def run_worker(redis_url: str, dry_run: bool, once: bool) -> int:
    """Consume jobs from Redis until interrupted (or one job when ``once``)."""
    import redis  # lazy — keeps --help / --job usable without the dependency

    r = redis.Redis.from_url(redis_url, decode_responses=True)
    log.info("worker online; waiting on %s (dry_run=%s, once=%s)", QUEUE_KEY, dry_run, once)
    while True:
        item = r.brpop(QUEUE_KEY, timeout=5)
        if item is None:
            if once:
                log.info("no jobs queued; exiting (--once)")
                return 0
            continue
        _, job_id = item
        key = JOB_KEY_PREFIX + job_id
        data = r.hgetall(key)
        job_type = data.get("type")
        try:
            payload = json.loads(data.get("payload") or "{}")
        except json.JSONDecodeError as exc:
            log.error("job %s has invalid payload: %s", job_id, exc)
            r.hset(key, mapping={"status": "failed", "error": f"invalid payload: {exc}"})
            payload = None

        if payload is not None:
            try:
                attempts = int(data.get("attempts") or 0) + 1
            except (TypeError, ValueError):
                attempts = 1
            r.hset(key, mapping={"status": "running", "attempts": attempts})
            reliability.emit_metric(r, "started", job_type=job_type)
            started = time.time()
            try:
                dispatch(job_type, payload, dry_run)
                reliability.mark_done(r, job_id=job_id, job_type=job_type, started_at=started)
                log.info("job %s (%s) done", job_id, job_type)
            except Exception as exc:  # never let one bad job kill the worker
                log.exception("job %s (%s) failed (attempt %d)", job_id, job_type, attempts)
                reliability.handle_failure(r, job_id=job_id, job_type=job_type,
                                           attempts=attempts, error=str(exc))

        if once:
            return 0


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="run_job.py",
        description="More Green platform worker: dispatch a named job to automation/commands/*.",
    )
    p.add_argument("--job", metavar="TYPE",
                   help="Run a single named job and exit (skips Redis). "
                        f"One of: {', '.join(sorted(REGISTRY))}.")
    p.add_argument("--payload", default="{}", metavar="JSON",
                   help="JSON payload for --job (default: '{}').")
    p.add_argument("--dry-run", action="store_true",
                   help="Force all commands into no-write mode (no spend, no posts).")
    p.add_argument("--once", action="store_true",
                   help="Queue mode: process a single job then exit.")
    p.add_argument("--list", action="store_true",
                   help="List known job types and exit.")
    p.add_argument("--redis-url", default=os.environ.get("REDIS_URL", "redis://localhost:6379"),
                   help="Redis URL for queue mode (default: $REDIS_URL or redis://localhost:6379).")
    return p


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    _configure_logging()

    if args.list:
        for name in sorted(REGISTRY):
            print(name)
        return 0

    if args.job:
        try:
            payload = json.loads(args.payload)
        except json.JSONDecodeError as exc:
            raise SystemExit(f"--payload is not valid JSON: {exc}")
        try:
            dispatch(args.job, payload, args.dry_run)
        except KeyError as exc:
            raise SystemExit(str(exc).strip('"'))
        return 0

    return run_worker(args.redis_url, args.dry_run, args.once)


if __name__ == "__main__":
    sys.exit(main())
