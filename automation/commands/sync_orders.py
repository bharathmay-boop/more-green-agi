"""sync-orders — ingest Shopify orders into the `orders` table for attribution.

One row per (order_id, sku) line item so multi-SKU orders split cleanly. Upsert
by the composite key → safe to re-run. See docs/plan/moregreen/03.

Money-safety: read-only against Shopify; writes only the local financial record.
"""
from __future__ import annotations

import hashlib
import json
import logging
import os
from datetime import datetime, timedelta, timezone

from utils.db import get_db

log = logging.getLogger(__name__)

_PAGE = 250


def _sku_for(line_item, sku_ids: list[str], slug_to_id: dict[str, str]) -> str:
    """Best-effort map a Shopify line item to a config SKU id, else 'unmapped'."""
    raw_sku = (getattr(line_item, "sku", "") or "").strip().lower()
    if raw_sku in sku_ids:
        return raw_sku
    title = (getattr(line_item, "title", "") or "").lower()
    handle = (getattr(line_item, "handle", "") or "").lower()
    for slug, sid in slug_to_id.items():
        if slug and (slug in handle or slug in title):
            return sid
    for sid in sku_ids:
        if sid in title:
            return sid
    return "unmapped"


def _customer_hash(order) -> str | None:
    email = (getattr(order, "email", None) or "").strip().lower()
    if not email:
        cust = getattr(order, "customer", None)
        email = (getattr(cust, "email", "") or "").strip().lower() if cust else ""
    return hashlib.sha256(email.encode()).hexdigest() if email else None


def _last_ingest(db, days: int) -> str:
    row = db.execute("SELECT MAX(ingested_at) FROM orders").fetchone()
    if row and row[0]:
        return row[0]
    return (datetime.now(timezone.utc) - timedelta(days=days)).strftime("%Y-%m-%dT%H:%M:%SZ")


def _iter_orders(updated_at_min: str):
    """Yield Shopify orders, paginating defensively across pyactiveresource versions."""
    import shopify
    page = shopify.Order.find(status="any", limit=_PAGE, updated_at_min=updated_at_min)
    while page:
        for o in page:
            yield o
        nxt = None
        try:
            if hasattr(page, "has_next_page") and page.has_next_page():
                nxt = page.next_page()
        except Exception as exc:  # pagination unsupported / exhausted
            log.debug("pagination stopped: %s", exc)
        page = nxt


def run(dry_run: bool = False, days: int = 30) -> None:
    import config
    db = get_db()
    sku_ids = list(config.SKUS.keys())
    slug_to_id = {}
    for sid, meta in config.SKUS.items():
        url = (meta.get("shopify_url") or "").rstrip("/")
        slug_to_id[url.rsplit("/", 1)[-1].lower()] = sid

    store = os.environ.get("SHOPIFY_STORE_URL")
    token = os.environ.get("SHOPIFY_ACCESS_TOKEN")
    if not store or not token:
        if dry_run:
            log.info("[DRY RUN] SHOPIFY_* not set; would ingest orders once configured.")
            print("sync-orders dry-run: 0 orders (Shopify creds not configured)")
            return
        raise SystemExit("SHOPIFY_STORE_URL / SHOPIFY_ACCESS_TOKEN not set (needs read_orders scope).")

    try:
        import shopify
    except ModuleNotFoundError:
        if dry_run:
            print("sync-orders dry-run: shopify lib not installed; "
                  "would fetch + upsert once `pip install ShopifyAPI`")
            return
        raise SystemExit("ShopifyAPI not installed: pip install ShopifyAPI")
    shopify.ShopifyResource.set_site(f"{store}/admin/api/2024-01")
    shopify.ShopifyResource.headers["X-Shopify-Access-Token"] = token

    since = _last_ingest(db, days)
    log.info("Fetching Shopify orders updated since %s", since)

    rows: list[tuple] = []
    n_orders = 0
    try:
        for order in _iter_orders(since):
            n_orders += 1
            oid = str(getattr(order, "id", "") or getattr(order, "order_number", ""))
            created = getattr(order, "created_at", None)
            chash = _customer_hash(order)
            landing = getattr(order, "landing_site", None) or getattr(order, "referring_site", None)
            # per line-item split
            for li in (getattr(order, "line_items", []) or []):
                sku = _sku_for(li, sku_ids, slug_to_id)
                if sku == "unmapped":
                    log.warning("Order %s line '%s' did not map to a SKU", oid,
                                getattr(li, "title", "?"))
                qty = int(getattr(li, "quantity", 1) or 1)
                price = float(getattr(li, "price", 0) or 0)
                disc = 0.0
                for da in (getattr(li, "discount_allocations", []) or []):
                    try:
                        disc += float(da.amount if hasattr(da, "amount") else da.get("amount", 0))
                    except Exception:
                        pass
                revenue = price * qty - disc
                rows.append((oid, sku, created, qty, revenue, disc, chash, landing,
                             json.dumps(_order_dict(order, li))))
    except Exception as exc:
        msg = str(exc)
        if "401" in msg or "403" in msg or "Unauthorized" in msg:
            raise SystemExit("Shopify auth failed — token missing or lacks read_orders scope.")
        log.error("Order fetch error: %s", exc)
        if not rows:
            raise

    if dry_run:
        print(f"sync-orders dry-run: {n_orders} orders -> {len(rows)} line rows (writes none)")
        return

    new, updated = 0, 0
    for r in rows:
        exists = db.execute("SELECT 1 FROM orders WHERE order_id=? AND sku=?",
                            (r[0], r[1])).fetchone()
        with db:
            db.execute(
                "INSERT INTO orders"
                "(order_id,sku,created_at,quantity,revenue_inr,discount_inr,"
                " customer_hash,landing_ref,raw_json,ingested_at) "
                "VALUES(?,?,?,?,?,?,?,?,?,datetime('now')) "
                "ON CONFLICT(order_id,sku) DO UPDATE SET "
                " created_at=excluded.created_at, quantity=excluded.quantity, "
                " revenue_inr=excluded.revenue_inr, discount_inr=excluded.discount_inr, "
                " customer_hash=excluded.customer_hash, landing_ref=excluded.landing_ref, "
                " raw_json=excluded.raw_json, ingested_at=datetime('now')",
                r,
            )
        updated += 1 if exists else 0
        new += 0 if exists else 1
    log.info("Orders upserted: %d new, %d updated (%d line rows)", new, updated, len(rows))
    print(f"sync-orders: {new} new, {updated} updated ({len(rows)} line rows)")


def _order_dict(order, line_item) -> dict:
    return {
        "order_id": str(getattr(order, "id", "")),
        "financial_status": getattr(order, "financial_status", None),
        "line_title": getattr(line_item, "title", None),
        "line_price": getattr(line_item, "price", None),
        "total_price": getattr(order, "total_price", None),
    }
