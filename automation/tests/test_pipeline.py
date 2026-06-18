"""Pipeline unit tests (E9-T3): attribution math/rollups, order mapping, and the
build orchestrator's ready-set. These are pure/offline — no network, no Meta, no
Shopify — and complement test_money_safety.py.
"""
import datetime as _dt
import hashlib
import importlib.util
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest

ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT))

from commands import attribution            # noqa: E402
from commands import sync_orders            # noqa: E402


# ── attribution.roas: ÷0-safe ────────────────────────────────────────────────
def test_roas_basic_and_div0():
    assert attribution.roas(1000, 250) == 4.0
    assert attribution.roas(0, 100) == 0.0
    assert attribution.roas(500, 0) is None      # no spend → undefined, never crashes
    assert attribution.roas(500, None) is None


# ── attribution.ist_date: tz normalisation ───────────────────────────────────
def test_ist_date_utc_to_ist_rollover():
    # 2026-06-01T20:00Z + 5h30m IST = 2026-06-02 IST
    assert attribution.ist_date("2026-06-01T20:00:00Z") == "2026-06-02"
    assert attribution.ist_date("2026-06-01") == "2026-06-01"   # bare date passthrough
    assert attribution.ist_date(None) is None


# ── attribution.compute: blended vs paid rollups, refund-safe ─────────────────
def test_compute_rollups_blended_paid_and_refund(db):
    today = attribution.ist_date(_dt.datetime.now(_dt.timezone.utc).isoformat())
    # paid: ad spent 100 → 400 purchase value attributed to moringa
    db.execute(
        "INSERT INTO ad_spend_daily(ad_id,date,campaign_id,sku,spend_inr,purchase_value_inr)"
        " VALUES('ad1',?, 'camp1','moringa',100,400)", (today,))
    # orders: one 700 sale + one -100 refund line for moringa (blended revenue = 600)
    db.execute("INSERT INTO orders(order_id,sku,created_at,revenue_inr) VALUES('o1','moringa',?,700)",
               (today + "T08:00:00Z",))
    db.execute("INSERT INTO orders(order_id,sku,created_at,revenue_inr) VALUES('o2','moringa',?,-100)",
               (today + "T09:00:00Z",))
    db.commit()

    rows = attribution.compute(db, days=2)
    sku = next(r for r in rows if r["scope"] == "sku" and r["scope_id"] == "moringa")
    assert sku["spend_inr"] == 100
    assert sku["revenue_inr"] == 600                 # 700 - 100 refund honoured
    assert sku["paid_roas"] == 4.0                   # 400/100
    assert sku["blended_roas"] == 6.0                # 600/100
    assert sku["organic_assist_inr"] == 200          # blended 600 - paid 400

    camp = next(r for r in rows if r["scope"] == "campaign")
    assert camp["scope_id"] == "camp1" and camp["paid_roas"] == 4.0

    blended = next(r for r in rows if r["scope"] == "blended")
    assert blended["scope_id"] == "all" and blended["blended_roas"] == 6.0


def test_compute_zero_spend_organic_only(db):
    """An organic-only SKU (orders but no spend) gets a row with null ROAS, no crash."""
    today = attribution.ist_date(_dt.datetime.now(_dt.timezone.utc).isoformat())
    db.execute("INSERT INTO orders(order_id,sku,created_at,revenue_inr) VALUES('o9','wheatgrass',?,300)",
               (today + "T06:00:00Z",))
    db.commit()
    rows = attribution.compute(db, days=2)
    wg = next(r for r in rows if r["scope"] == "sku" and r["scope_id"] == "wheatgrass")
    assert wg["spend_inr"] == 0 and wg["revenue_inr"] == 300
    assert wg["blended_roas"] is None                # ÷0 spend → None


# ── sync_orders mapping helpers ───────────────────────────────────────────────
def test_sku_for_maps_by_sku_then_title():
    ids = ["moringa", "wheatgrass"]
    slug = {"moringa-powder": "moringa"}
    assert sync_orders._sku_for(SimpleNamespace(sku="MORINGA", title="x", handle=""), ids, slug) == "moringa"
    assert sync_orders._sku_for(SimpleNamespace(sku="", title="x", handle="moringa-powder-250g"), ids, slug) == "moringa"
    assert sync_orders._sku_for(SimpleNamespace(sku="", title="Wheatgrass tin", handle=""), ids, slug) == "wheatgrass"
    assert sync_orders._sku_for(SimpleNamespace(sku="", title="mystery", handle=""), ids, slug) == "unmapped"


def test_customer_hash_is_sha256_of_lower_email():
    o = SimpleNamespace(email="Foo@Bar.com", customer=None)
    assert sync_orders._customer_hash(o) == hashlib.sha256(b"foo@bar.com").hexdigest()
    assert sync_orders._customer_hash(SimpleNamespace(email=None, customer=None)) is None


# ── orchestrator ready-set respects dependencies ─────────────────────────────
def _load_orchestrate():
    path = ROOT.parent / "build" / "orchestrate.py"
    spec = importlib.util.spec_from_file_location("orchestrate", path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def test_ready_tasks_blocks_on_unfinished_deps():
    orch = _load_orchestrate()
    data = {"tasks": [
        {"id": "A", "status": "done", "depends_on": []},
        {"id": "B", "status": "todo", "depends_on": ["A"]},        # ready: dep done
        {"id": "C", "status": "todo", "depends_on": ["D"]},        # blocked: D not done
        {"id": "D", "status": "todo", "depends_on": []},           # ready: no deps
    ]}
    ready = {t["id"] for t in orch.ready_tasks(data)}
    assert ready == {"B", "D"}
