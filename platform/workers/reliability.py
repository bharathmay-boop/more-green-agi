"""reliability.py — queue retries, dead-letter, metrics, and retention (E9-T4).

The worker loop in ``run_job.py`` is intentionally thin. This module holds the
operational policy that makes the queue production-grade:

* **Retries with backoff** — a failed job is re-enqueued up to ``max_attempts``
  times; the per-attempt delay grows geometrically (capped).
* **Dead-letter queue (DLQ)** — once retries are exhausted the job is moved to
  a DLQ list and marked ``dead`` (never silently dropped, never retried forever).
* **Observability** — every terminal outcome bumps a counter in a Redis metrics
  hash AND emits a single structured (JSON) log line, so success/failure/retry
  rates and durations are scrapeable without a separate metrics backend.
* **Retention** — completed/dead job hashes are expired and the DLQ is trimmed,
  so Redis memory stays bounded.

Everything here is written against a tiny subset of the Redis protocol
(``hset``/``hincrby``/``lpush``/``ltrim``/``expire``/``llen``), so it is unit
-tested with an in-memory fake and needs no live Redis to verify.
"""
from __future__ import annotations

import json
import logging
import time
from dataclasses import dataclass

log = logging.getLogger("workers.reliability")

# Redis keys (mirror run_job.py conventions).
QUEUE_KEY = "moregreen:jobs:queue"
DLQ_KEY = "moregreen:jobs:dlq"
METRICS_KEY = "moregreen:metrics:jobs"
JOB_KEY_PREFIX = "moregreen:job:"

DEFAULT_MAX_ATTEMPTS = 3
DEFAULT_BASE_DELAY_S = 2.0
DEFAULT_MAX_DELAY_S = 300.0
DONE_TTL_S = 7 * 24 * 3600        # keep terminal job records 7 days
DLQ_MAX_LEN = 1000                # cap dead-letter backlog


@dataclass(frozen=True)
class RetryPolicy:
    max_attempts: int = DEFAULT_MAX_ATTEMPTS
    base_delay_s: float = DEFAULT_BASE_DELAY_S
    max_delay_s: float = DEFAULT_MAX_DELAY_S

    def should_retry(self, attempts: int) -> bool:
        """True while the job has retries left (attempts already includes this try)."""
        return attempts < self.max_attempts

    def next_delay_s(self, attempts: int) -> float:
        """Geometric backoff: base * 2^(attempts-1), capped at max_delay_s."""
        n = max(1, attempts)
        return min(self.base_delay_s * (2 ** (n - 1)), self.max_delay_s)


def emit_metric(r, outcome: str, *, job_type: str = "", duration_s: float | None = None) -> None:
    """Bump a counter and emit one structured log line for a terminal outcome.

    ``outcome`` ∈ {started, done, retried, failed, dead}. Best-effort: metrics
    must never crash a worker, so Redis errors are swallowed (still logged).
    """
    try:
        r.hincrby(METRICS_KEY, outcome, 1)
    except Exception as exc:  # noqa: BLE001 - observability must not break the job
        log.debug("metric increment failed (%s)", exc)
    record = {"event": "job", "outcome": outcome, "type": job_type}
    if duration_s is not None:
        record["duration_s"] = round(duration_s, 3)
    log.info(json.dumps(record, sort_keys=True))


def handle_failure(r, *, job_id: str, job_type: str, attempts: int, error: str,
                   policy: RetryPolicy = RetryPolicy()) -> str:
    """Decide a failed job's fate and apply it. Returns ``"retried"`` or ``"dead"``.

    * retry → record attempts + status ``queued`` and re-enqueue (caller may
      honour ``next_delay_s`` before the job becomes visible again).
    * dead  → move to the DLQ, status ``dead``, and trim the DLQ.
    """
    key = JOB_KEY_PREFIX + job_id
    if policy.should_retry(attempts):
        r.hset(key, mapping={"status": "queued", "attempts": attempts, "error": error})
        r.lpush(QUEUE_KEY, job_id)
        emit_metric(r, "retried", job_type=job_type)
        log.warning("job %s (%s) retry %d/%d in %.1fs: %s",
                    job_id, job_type, attempts, policy.max_attempts,
                    policy.next_delay_s(attempts), error[:200])
        return "retried"

    r.hset(key, mapping={"status": "dead", "attempts": attempts, "error": error})
    r.lpush(DLQ_KEY, job_id)
    try:
        r.ltrim(DLQ_KEY, 0, DLQ_MAX_LEN - 1)
        r.expire(key, DONE_TTL_S)
    except Exception as exc:  # noqa: BLE001
        log.debug("dlq retention op failed (%s)", exc)
    emit_metric(r, "dead", job_type=job_type)
    log.error("job %s (%s) dead-lettered after %d attempts: %s",
              job_id, job_type, attempts, error[:200])
    return "dead"


def mark_done(r, *, job_id: str, job_type: str, started_at: float | None = None) -> None:
    """Mark a job done, set retention TTL, and emit the success metric."""
    key = JOB_KEY_PREFIX + job_id
    r.hset(key, mapping={"status": "done", "error": ""})
    try:
        r.expire(key, DONE_TTL_S)
    except Exception as exc:  # noqa: BLE001
        log.debug("done retention op failed (%s)", exc)
    dur = (time.time() - started_at) if started_at else None
    emit_metric(r, "done", job_type=job_type, duration_s=dur)


def read_metrics(r) -> dict[str, int]:
    """Return the current counter snapshot (for a /metrics endpoint or report)."""
    try:
        raw = r.hgetall(METRICS_KEY) or {}
    except Exception:  # noqa: BLE001
        return {}
    out: dict[str, int] = {}
    for k, v in raw.items():
        try:
            out[k] = int(v)
        except (TypeError, ValueError):
            continue
    return out
