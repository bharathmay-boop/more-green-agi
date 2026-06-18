"""Money-safety invariants (docs/plan/moregreen/04 + 09).

These tests are the guardrail behind the one rule that must never regress:
no code activates or raises ad budget without an approved approval_queue row,
and only apply_approved.py touches Meta for spend. They are intentionally
strict — if a future change (human or autonomous agent) breaks the boundary,
one of these fails loudly.
"""
import re
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT))

from utils import approvals          # noqa: E402
from commands import apply_approved  # noqa: E402
from commands import tune_ads        # noqa: E402

CMD_DIR = ROOT / "commands"


# ── 1. Static boundary: spend-raising Meta calls live only in apply_approved ──
def test_only_apply_approved_raises_budget_or_activates():
    offenders = []
    for path in CMD_DIR.glob("*.py"):
        if path.name == "apply_approved.py":
            continue
        src = path.read_text(encoding="utf-8")
        # api_update that sets status ACTIVE  → activation (spend)
        if re.search(r"api_update\([^)]*ACTIVE", src, re.S):
            offenders.append(f"{path.name}: activates ad via api_update")
        # api_update that raises an existing adset's daily_budget → spend
        for m in re.finditer(r"api_update\((.*?)\)", src, re.S):
            if "daily_budget" in m.group(1):
                offenders.append(f"{path.name}: raises daily_budget via api_update")
    assert not offenders, "money-safety boundary breached: " + "; ".join(offenders)


# ── 2. tune_ads SCALE proposes, never spends; PAUSE is immediate ──────────────
def _campaign():
    return {
        "campaign_key": "MG-moringa-1", "sku": "moringa",
        "ad_id": "ad_1", "adset_id": "adset_1", "daily_budget_inr": 500,
    }


def test_tune_ads_scale_writes_proposal_not_meta(db):
    with patch.object(tune_ads, "AdSet") as MAdSet, \
         patch.object(tune_ads, "Ad") as MAd, \
         patch.object(tune_ads, "notify_founder"):
        tune_ads._apply_action(_campaign(), "SCALE", db,
                               metrics={"roas": 4.0, "spend": 800})
        MAdSet.assert_not_called()   # no budget mutation on Meta
        MAd.assert_not_called()
    row = db.execute(
        "SELECT * FROM approval_queue WHERE action_type='scale_budget' AND status='pending'"
    ).fetchone()
    assert row is not None, "SCALE must enqueue a scale_budget proposal"


def test_tune_ads_pause_is_immediate(db):
    db.execute("INSERT INTO ad_campaigns(campaign_key,sku,campaign_date,campaign_phase,"
               "ad_id,status,daily_budget_inr) VALUES('MG-moringa-1','moringa','2026-06-01',1,"
               "'ad_1','ACTIVE',500)")
    db.commit()
    with patch.object(tune_ads, "Ad") as MAd:
        tune_ads._apply_action(_campaign(), "PAUSE_LOW_CTR", db, metrics={})
        MAd.assert_called_once()
        MAd.return_value.api_update.assert_called_once_with(params={"status": "PAUSED"})
    assert db.execute("SELECT status FROM ad_campaigns WHERE campaign_key='MG-moringa-1'"
                      ).fetchone()["status"] == "PAUSED"
    # pausing creates no approval row
    assert db.execute("SELECT COUNT(*) c FROM approval_queue").fetchone()["c"] == 0


# ── 3. apply_approved only consumes approved rows ─────────────────────────────
def test_apply_approved_ignores_pending(db):
    approvals.propose("scale_budget", "MG-x-1",
                      payload={"adset_id": "a1", "proposed_inr": 100}, db=db)
    with patch.object(apply_approved, "_meta_init") as minit:
        apply_approved.run(dry_run=False)
        minit.assert_not_called()          # nothing approved → Meta never touched
    assert db.execute("SELECT status FROM approval_queue").fetchone()["status"] == "pending"


# ── 4. cap breach blocks the apply and marks it failed, untouched on Meta ─────
def test_cap_breach_blocks_apply(db):
    pid = approvals.propose("scale_budget", "MG-moringa-1",
                            payload={"adset_id": "adset_1", "proposed_inr": 999999}, db=db)
    approvals.approve(pid, "test", db=db)
    with patch.object(apply_approved, "_meta_init") as minit:
        apply_approved.run(dry_run=False)
        minit.assert_not_called()          # cap check fires before any Meta init
    row = db.execute("SELECT status,error FROM approval_queue WHERE id=?", (pid,)).fetchone()
    assert row["status"] == "failed"
    assert "MAX_CAMPAIGN_BUDGET_INR" in (row["error"] or "")


# ── 5. approval state machine forbids illegal transitions ─────────────────────
def test_illegal_transition_raises(db):
    pid = approvals.propose("scale_budget", "MG-y-1",
                            payload={"adset_id": "a1", "proposed_inr": 100}, db=db)
    # pending -> applied is illegal (must be approved first)
    with pytest.raises(approvals.IllegalTransition):
        approvals.mark_applied(pid, db=db)


def test_double_decision_blocked(db):
    pid = approvals.propose("scale_budget", "MG-z-1",
                            payload={"adset_id": "a1", "proposed_inr": 100}, db=db)
    approvals.approve(pid, "founder", db=db)
    with pytest.raises(approvals.IllegalTransition):
        approvals.reject(pid, "founder", db=db)   # already decided
