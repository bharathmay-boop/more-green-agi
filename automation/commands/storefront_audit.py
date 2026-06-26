"""storefront-audit — read Shopify product pages + landing performance (E7-T1).

The "Read" half of the Storefront / Product-Page Loop (docs/plan/moregreen/06,
flow F5). This command is strictly read-only:

* Pulls live `shopify.Product` records (title, body_html, handle, variant price)
  so a later strategist task can propose copy / price-test changes.
* Rolls up local `orders` by `landing_ref` (utm / referrer) to surface which
  landing paths actually convert.

It never calls `Product.save()`. All storefront writes stay gated behind
`apply_approved` after human approval (doc 04). Re-runnable and side-effect free.
"""
from __future__ import annotations

import logging
import os

from utils.db import get_db

log = logging.getLogger(__name__)

# Shopify Admin REST page size for product paging.
_PAGE = 250

# Product fields we read — enough for copy/price proposals, nothing more.
_PRODUCT_FIELDS = "id,title,handle,body_html,status,variants"


def _connect_shopify(dry_run: bool) -> bool:
    """Point pyactiveresource at the store. Return False if not runnable.

    Mirrors sync_orders' credential handling so behaviour is consistent: a
    dry-run with missing creds / library is a soft no-op, a real run raises.
    """
    store = os.environ.get("SHOPIFY_STORE_URL")
    token = os.environ.get("SHOPIFY_ACCESS_TOKEN")
    if not store or not token:
        if dry_run:
            log.info("[DRY RUN] SHOPIFY_* not set; would read products once configured.")
            print("storefront-audit dry-run: Shopify creds not configured")
            return False
        raise SystemExit("SHOPIFY_STORE_URL / SHOPIFY_ACCESS_TOKEN not set (needs read_products scope).")

    try:
        import shopify  # noqa: F401
    except ModuleNotFoundError:
        if dry_run:
            print("storefront-audit dry-run: shopify lib not installed; "
                  "would read products once `pip install ShopifyAPI`")
            return False
        raise SystemExit("ShopifyAPI not installed: pip install ShopifyAPI")

    import shopify
    shopify.ShopifyResource.set_site(f"{store}/admin/api/2024-01")
    shopify.ShopifyResource.headers["X-Shopify-Access-Token"] = token
    return True


def _iter_products():
    """Yield Shopify products, paginating defensively across library versions."""
    import shopify
    try:
        page = shopify.Product.find(limit=_PAGE, fields=_PRODUCT_FIELDS)
    except Exception as exc:
        # 401/403 → missing read_products scope; surface a clear message.
        raise SystemExit(f"Could not read Shopify products ({exc}). "
                         "Confirm the access token has the read_products scope.")
    while page:
        for p in page:
            yield p
        nxt = None
        try:
            if hasattr(page, "has_next_page") and page.has_next_page():
                nxt = page.next_page()
        except Exception as exc:  # pagination unsupported / exhausted
            log.debug("product pagination stopped: %s", exc)
        page = nxt


def fetch_products() -> list[dict]:
    """Return a lightweight dict per live product for downstream proposals."""
    products: list[dict] = []
    for p in _iter_products():
        variants = getattr(p, "variants", None) or []
        prices = []
        for v in variants:
            raw = getattr(v, "price", None)
            try:
                prices.append(float(raw))
            except (TypeError, ValueError):
                continue
        body = (getattr(p, "body_html", "") or "")
        products.append({
            "id": str(getattr(p, "id", "") or ""),
            "title": getattr(p, "title", "") or "",
            "handle": getattr(p, "handle", "") or "",
            "status": getattr(p, "status", "") or "",
            "body_len": len(body),
            "variant_count": len(variants),
            "min_price": min(prices) if prices else None,
            "max_price": max(prices) if prices else None,
        })
    return products


def landing_performance(db, days: int) -> list[dict]:
    """Roll up local orders by landing_ref over the last `days` days.

    Reads the `orders` table only — no Shopify call — so this also works when
    products can't be fetched. `landing_ref` is normalised so NULL/empty paths
    bucket together as '(direct/unknown)'.
    """
    rows = db.execute(
        """
        SELECT COALESCE(NULLIF(TRIM(landing_ref), ''), '(direct/unknown)') AS landing,
               COUNT(DISTINCT order_id)                                    AS orders,
               COALESCE(SUM(quantity), 0)                                  AS units,
               COALESCE(SUM(revenue_inr), 0.0)                             AS revenue_inr
          FROM orders
         WHERE created_at >= datetime('now', ?)
         GROUP BY landing
         ORDER BY revenue_inr DESC
        """,
        (f"-{int(days)} days",),
    ).fetchall()
    return [dict(r) for r in rows]


def run(dry_run: bool = False, days: int = 30) -> dict:
    """Fetch product pages + landing metrics. Read-only; returns a summary dict."""
    db = get_db()

    # Landing metrics come from the local orders table and never need Shopify.
    landing = landing_performance(db, days)

    products: list[dict] = []
    if _connect_shopify(dry_run):
        products = fetch_products()
        log.info("Read %d Shopify products.", len(products))

    _print_products(products)
    _print_landing(landing, days)

    return {"products": products, "landing": landing}


def _print_products(products: list[dict]) -> None:
    if not products:
        print("Products: none fetched.")
        return
    try:
        from tabulate import tabulate
    except ModuleNotFoundError:
        tabulate = None
    headers = ["Title", "Handle", "Status", "Variants", "Price (min–max)", "Copy len"]
    rows = []
    for p in products:
        lo, hi = p["min_price"], p["max_price"]
        if lo is None:
            price = "—"
        elif lo == hi:
            price = f"₹{lo:.0f}"
        else:
            price = f"₹{lo:.0f}–₹{hi:.0f}"
        rows.append([p["title"], p["handle"], p["status"],
                     p["variant_count"], price, p["body_len"]])
    print(f"\nProducts fetched: {len(products)}")
    if tabulate:
        print(tabulate(rows, headers=headers, tablefmt="simple"))
    else:
        for r in rows:
            print("  " + " | ".join(str(c) for c in r))


def _print_landing(landing: list[dict], days: int) -> None:
    print(f"\nLanding performance (orders by landing_ref, last {days}d):")
    if not landing:
        print("  no orders in window.")
        return
    try:
        from tabulate import tabulate
    except ModuleNotFoundError:
        tabulate = None
    headers = ["Landing ref", "Orders", "Units", "Revenue"]
    rows = [[l["landing"], l["orders"], l["units"], f"₹{l['revenue_inr']:.0f}"]
            for l in landing]
    if tabulate:
        print(tabulate(rows, headers=headers, tablefmt="simple"))
    else:
        for r in rows:
            print("  " + " | ".join(str(c) for c in r))
