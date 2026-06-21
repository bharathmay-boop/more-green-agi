"""expire-approvals CLI (plan 02 T1.4) — flips pending proposals past their TTL
to 'expired' so the queue doesn't accumulate stale rows. Thin wrapper over
utils.approvals.expire_stale; this locks the end-to-end behaviour."""
import sys
from pathlib import Path

ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT))


def test_expire_approvals_expires_past_ttl_pending(db):
    from utils import approvals
    from commands import expire_approvals

    pid = approvals.propose("scale_budget", "ad:1", {"x": 1}, requested_by="system", db=db)
    db.execute("UPDATE approval_queue SET expires_at=? WHERE id=?", ("2000-01-01 00:00:00", pid))
    db.commit()

    assert expire_approvals.run(db=db) == 1
    row = db.execute("SELECT status FROM approval_queue WHERE id=?", (pid,)).fetchone()
    assert row["status"] == "expired"


def test_expire_approvals_leaves_unexpired_pending_alone(db):
    from utils import approvals
    from commands import expire_approvals

    pid = approvals.propose("scale_budget", "ad:2", {"x": 2}, requested_by="system", db=db)
    db.execute("UPDATE approval_queue SET expires_at=? WHERE id=?", ("2999-01-01 00:00:00", pid))
    db.commit()

    assert expire_approvals.run(db=db) == 0
    row = db.execute("SELECT status FROM approval_queue WHERE id=?", (pid,)).fetchone()
    assert row["status"] == "pending"
