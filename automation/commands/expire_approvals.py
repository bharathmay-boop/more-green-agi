"""expire-approvals — flip pending proposals past their TTL to 'expired'.

Thin wrapper over utils.approvals.expire_stale so the GitHub Actions cron can
keep the approval queue tidy (plan 02 T1.4). Touches no spend: 'expired' is a
terminal, non-applying status.
"""
from __future__ import annotations

from utils import approvals


def run(dry_run: bool = False, db=None) -> int:
    if dry_run:
        # Count what would expire without writing.
        db = db or approvals.get_db()
        from utils.approvals import _now
        n = db.execute(
            "SELECT COUNT(*) FROM approval_queue WHERE status='pending' "
            "AND expires_at IS NOT NULL AND expires_at < ?", (_now(),)
        ).fetchone()[0]
        print(f"[dry-run] {n} pending proposal(s) past TTL would be expired.")
        return n
    n = approvals.expire_stale(db=db)
    print(f"expired {n} stale pending proposal(s).")
    return n
