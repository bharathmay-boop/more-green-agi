"""Unit tests for the worker reliability layer (E9-T4) — retries, DLQ, metrics,
retention. Uses an in-memory fake Redis so no live broker is required.

Run: cd platform/workers && python -m pytest test_reliability.py -q
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import reliability as rel


class FakeRedis:
    """Minimal Redis stand-in: hashes + lists + expirations."""
    def __init__(self):
        self.h: dict[str, dict] = {}
        self.lists: dict[str, list] = {}
        self.ttl: dict[str, int] = {}

    def hset(self, key, field=None, value=None, mapping=None):
        d = self.h.setdefault(key, {})
        if mapping:
            d.update({k: str(v) for k, v in mapping.items()})
        elif field is not None:
            d[field] = str(value)

    def hgetall(self, key):
        return dict(self.h.get(key, {}))

    def hincrby(self, key, field, amount=1):
        d = self.h.setdefault(key, {})
        d[field] = str(int(d.get(field, 0)) + amount)
        return int(d[field])

    def lpush(self, key, *vals):
        lst = self.lists.setdefault(key, [])
        for v in vals:
            lst.insert(0, v)
        return len(lst)

    def ltrim(self, key, start, end):
        self.lists[key] = self.lists.get(key, [])[start:end + 1]

    def llen(self, key):
        return len(self.lists.get(key, []))

    def expire(self, key, ttl):
        self.ttl[key] = ttl


def test_backoff_is_geometric_and_capped():
    p = rel.RetryPolicy(max_attempts=5, base_delay_s=2, max_delay_s=20)
    assert [p.next_delay_s(n) for n in (1, 2, 3, 4, 5)] == [2, 4, 8, 16, 20]
    assert p.should_retry(4) and not p.should_retry(5)


def test_failure_retries_then_dead_letters():
    r = FakeRedis()
    policy = rel.RetryPolicy(max_attempts=3)

    # attempts 1 and 2 → re-enqueued for retry
    assert rel.handle_failure(r, job_id="j1", job_type="sync_orders",
                              attempts=1, error="boom", policy=policy) == "retried"
    assert rel.handle_failure(r, job_id="j1", job_type="sync_orders",
                              attempts=2, error="boom", policy=policy) == "retried"
    assert r.llen(rel.QUEUE_KEY) == 2                      # re-enqueued twice
    assert r.h[rel.JOB_KEY_PREFIX + "j1"]["status"] == "queued"

    # attempt 3 exhausts retries → DLQ + dead
    assert rel.handle_failure(r, job_id="j1", job_type="sync_orders",
                              attempts=3, error="boom", policy=policy) == "dead"
    assert r.llen(rel.DLQ_KEY) == 1
    assert r.h[rel.JOB_KEY_PREFIX + "j1"]["status"] == "dead"
    assert rel.JOB_KEY_PREFIX + "j1" in r.ttl             # retention TTL set


def test_mark_done_sets_ttl_and_metric():
    r = FakeRedis()
    rel.mark_done(r, job_id="j2", job_type="monitor_ads", started_at=None)
    assert r.h[rel.JOB_KEY_PREFIX + "j2"]["status"] == "done"
    assert rel.JOB_KEY_PREFIX + "j2" in r.ttl


def test_metrics_counters_accumulate():
    r = FakeRedis()
    rel.emit_metric(r, "started", job_type="x")
    rel.emit_metric(r, "done", job_type="x")
    rel.emit_metric(r, "done", job_type="x")
    rel.emit_metric(r, "dead", job_type="x")
    snap = rel.read_metrics(r)
    assert snap == {"started": 1, "done": 2, "dead": 1}
