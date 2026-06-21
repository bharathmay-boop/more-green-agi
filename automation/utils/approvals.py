"""Approval queue — the money-safety boundary (docs/plan/moregreen/04).

Producers (tune_ads, strategize, create_ads) call `propose()` to write a
`pending` row. They NEVER act on spend directly. A human approves via the web
UI / email / CLI, and only `apply_approved.py` consumes `approved` rows and
touches Meta. Status transitions are guarded HERE (in code, not just the UI):
any illegal transition raises and is left unrecorded as a state change.

Invariant: no code path activates or increases ad budget without an
`approval_queue` row in `approved` state. Pausing/stopping spend bypasses this
queue (it only ever reduces waste) — see tune_ads.
"""
from __future__ import annotations

import datetime as _dt
import json
import sqlite3
from typing import Any, Optional

from utils.db import get_db, IntegrityError

VALID_ACTIONS = {
    "activate_ad", "scale_budget", "reallocate", "price_test",
    "publish_post", "product_copy_change",
}

# Guarded status machine. Source status -> set of allowed destinations.
ALLOWED_TRANSITIONS: dict[str, set[str]] = {
    "pending": {"approved", "rejected", "expired"},
    "approved": {"applied", "failed"},
    "failed": {"approved"},          # manual retry
    "rejected": set(),
    "applied": set(),
    "expired": set(),
}


class IllegalTransition(Exception):
    """Raised when a status change is not permitted by the state machine."""


def _now() -> str:
    return _dt.datetime.now(_dt.timezone.utc).strftime("%Y-%m-%d %H:%M:%S")


def _dumps(obj: Any) -> Optional[str]:
    return json.dumps(obj, sort_keys=True) if obj is not None else None


def _audit(db, actor: str, action: str, entity_id: Any,
           before: Any = None, after: Any = None) -> None:
    db.execute(
        "INSERT INTO audit_log(actor,action,entity,entity_id,before_json,after_json) "
        "VALUES(?,?,?,?,?,?)",
        (actor, action, "approval_queue", str(entity_id), _dumps(before), _dumps(after)),
    )


# ── producer ─────────────────────────────────────────────────────────────────
def propose(action_type: str, entity_ref: str, payload: dict | None = None,
            expected_impact: dict | None = None, requested_by: str = "orchestrator",
            ttl_hours: int | None = None, db: sqlite3.Connection | None = None) -> int:
    """Insert a pending proposal. Dedupes identical pending rows
    (same action_type + entity_ref + payload) and returns the existing id."""
    if action_type not in VALID_ACTIONS:
        raise ValueError(f"unknown action_type: {action_type}")
    db = db or get_db()
    payload_json = _dumps(payload) or _dumps({})
    expires_at = None
    if ttl_hours is None:
        try:
            from config import APPROVAL_TTL_HOURS
            ttl_hours = APPROVAL_TTL_HOURS
        except Exception:
            ttl_hours = 48
    if ttl_hours:
        expires_at = (_dt.datetime.now(_dt.timezone.utc)
                      + _dt.timedelta(hours=ttl_hours)).strftime("%Y-%m-%d %H:%M:%S")

    # dedupe: identical pending proposal already queued?
    existing = db.execute(
        "SELECT id FROM approval_queue WHERE status='pending' AND action_type=? "
        "AND entity_ref=? AND payload_json=?",
        (action_type, entity_ref, payload_json),
    ).fetchone()
    if existing:
        return existing[0]

    try:
        with db:
            cur = db.execute(
                "INSERT INTO approval_queue"
                "(action_type,entity_ref,payload_json,expected_impact_json,"
                " status,requested_by,requested_at,expires_at) "
                "VALUES(?,?,?,?, 'pending', ?, ?, ?) RETURNING id",
                (action_type, entity_ref, payload_json, _dumps(expected_impact),
                 requested_by, _now(), expires_at),
            )
            new_id = cur.fetchone()[0]  # RETURNING: valid on SQLite 3.35+ and PG
            _audit(db, requested_by, "propose", new_id, None,
                   {"action_type": action_type, "entity_ref": entity_ref,
                    "payload": payload})
        return new_id
    except IntegrityError:
        # lost a race against the unique pending index — return the winner
        row = db.execute(
            "SELECT id FROM approval_queue WHERE status='pending' AND action_type=? "
            "AND entity_ref=? AND payload_json=?",
            (action_type, entity_ref, payload_json),
        ).fetchone()
        return row[0] if row else -1


# ── guarded transitions ──────────────────────────────────────────────────────
def _get(db, proposal_id: int) -> sqlite3.Row:
    row = db.execute("SELECT * FROM approval_queue WHERE id=?", (proposal_id,)).fetchone()
    if not row:
        raise ValueError(f"approval {proposal_id} not found")
    return row


def _transition(proposal_id: int, to_status: str, *, actor: str,
                decided: bool = False, applied: bool = False,
                error: str | None = None,
                db: sqlite3.Connection | None = None) -> None:
    db = db or get_db()
    row = _get(db, proposal_id)
    frm = row["status"]
    if to_status not in ALLOWED_TRANSITIONS.get(frm, set()):
        _audit(db, actor, f"illegal_transition:{frm}->{to_status}", proposal_id,
               {"status": frm}, {"status": to_status})
        db.commit()
        raise IllegalTransition(f"{frm} -> {to_status} (id={proposal_id})")

    sets = ["status=?"]
    params: list[Any] = [to_status]
    if decided:
        sets += ["decided_by=?", "decided_at=?"]
        params += [actor, _now()]
    if applied:
        sets += ["applied_at=?"]
        params += [_now()]
    if error is not None:
        sets += ["error=?"]
        params += [error]
    params.append(proposal_id)

    # optimistic guard: for the first human decision, require decided_at IS NULL
    where = "id=?"
    if decided:
        where += " AND decided_at IS NULL"
    with db:
        cur = db.execute(f"UPDATE approval_queue SET {', '.join(sets)} WHERE {where}",
                         params)
        if cur.rowcount == 0 and decided:
            raise IllegalTransition(f"already decided (id={proposal_id})")
        _audit(db, actor, f"transition:{frm}->{to_status}", proposal_id,
               {"status": frm}, {"status": to_status, "error": error})


def approve(proposal_id: int, decided_by: str = "founder",
            db: sqlite3.Connection | None = None) -> None:
    _transition(proposal_id, "approved", actor=decided_by, decided=True, db=db)


def reject(proposal_id: int, decided_by: str = "founder",
           db: sqlite3.Connection | None = None) -> None:
    _transition(proposal_id, "rejected", actor=decided_by, decided=True, db=db)


def mark_applied(proposal_id: int, actor: str = "apply_approved",
                 db: sqlite3.Connection | None = None) -> None:
    _transition(proposal_id, "applied", actor=actor, applied=True, db=db)


def mark_failed(proposal_id: int, error: str, actor: str = "apply_approved",
                db: sqlite3.Connection | None = None) -> None:
    _transition(proposal_id, "failed", actor=actor, error=error, db=db)


def retry(proposal_id: int, actor: str = "founder",
          db: sqlite3.Connection | None = None) -> None:
    """failed -> approved (manual retry)."""
    _transition(proposal_id, "approved", actor=actor, db=db)


# ── reads / maintenance ──────────────────────────────────────────────────────
def list_pending(db: sqlite3.Connection | None = None) -> list[sqlite3.Row]:
    db = db or get_db()
    return db.execute(
        "SELECT * FROM approval_queue WHERE status='pending' ORDER BY requested_at"
    ).fetchall()


def list_approved(db: sqlite3.Connection | None = None) -> list[sqlite3.Row]:
    db = db or get_db()
    return db.execute(
        "SELECT * FROM approval_queue WHERE status='approved' ORDER BY decided_at"
    ).fetchall()


def expire_stale(db: sqlite3.Connection | None = None) -> int:
    """Set pending proposals past their TTL to expired. Returns count."""
    db = db or get_db()
    rows = db.execute(
        "SELECT id FROM approval_queue WHERE status='pending' "
        "AND expires_at IS NOT NULL AND expires_at < ?", (_now(),)
    ).fetchall()
    for r in rows:
        try:
            _transition(r[0], "expired", actor="system", db=db)
        except IllegalTransition:
            pass
    return len(rows)
