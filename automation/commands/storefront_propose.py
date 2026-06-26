"""storefront-propose — the "Propose" half of the Storefront / Product-Page Loop
(E7-T2, docs/plan/moregreen/06 §E7, flow F5).

Reads live products + local landing performance (via the read-only `storefront_audit`
command) and turns the read into ACTION *proposals* — never autonomous storefront
writes:

  * Thin product copy / banned-phrase usage → a `product_copy_change` proposal
    carrying the current body and a concrete proposed rewrite.
  * Underperforming landing paths / a configured discount test → a `price_test`
    proposal, but ONLY after a margin guardrail confirms the proposed price keeps
    gross margin at/above the floor. A breach is blocked and reported, never queued.

Write-gating (doc 04 / 06): this command's only side effect is inserting `pending`
rows in `approval_queue`. It NEVER calls `Product.save()`. The storefront mutation
happens later, exclusively in `apply_approved` after a human approves (F5). Until
that applier exists, an approved row simply skips cleanly in apply_approved.

The decision MATH (which products, which guardrails) is deterministic and
offline-testable. Claude is used only to draft human-readable replacement copy and
is skipped in dry-run / when no API key is set — a deterministic skeleton built
from the SKU's own facts is used as the fallback so every proposal stays actionable.
"""
from __future__ import annotations

import logging
import re

from utils.db import get_db
from utils import approvals

log = logging.getLogger(__name__)

_TAG_RE = re.compile(r"<[^>]+>")


# ── config-driven guardrails (overridable in config.py without touching this file) ──
def _settings() -> dict:
    """Read storefront guardrail settings, falling back to safe defaults.

    No COGS column exists in the data model, so the margin floor is modelled from
    an assumed cost basis expressed as a fraction of the current list price.
    """
    import config
    return {
        # assumed cost = this fraction of the current live price
        "cogs_pct": float(getattr(config, "STOREFRONT_COGS_PCT", 0.40)),
        # gross margin must stay at/above this after any price test
        "min_margin_pct": float(getattr(config, "STOREFRONT_MIN_MARGIN_PCT", 0.50)),
        # the discount a price test probes (e.g. 0.10 = 10% off)
        "discount_pct": float(getattr(config, "PRICE_TEST_DISCOUNT_PCT", 0.10)),
        # product bodies shorter than this (visible text) are flagged as thin
        "body_min_len": int(getattr(config, "PRODUCT_BODY_MIN_LEN", 400)),
    }


# ── margin guardrail (the money-safety check for price_test) ────────────────────
def margin_floor_price(current_price: float, cogs_pct: float, min_margin_pct: float) -> float:
    """Lowest price that still keeps gross margin >= ``min_margin_pct``.

    margin(p) = (p - cost) / p ; require margin >= m  ⇒  p >= cost / (1 - m).
    """
    if not 0.0 < min_margin_pct < 1.0:
        raise ValueError(f"min_margin_pct must be in (0,1), got {min_margin_pct}")
    cost = current_price * cogs_pct
    return cost / (1.0 - min_margin_pct)


def _margin_at(price: float, cost: float) -> float | None:
    return (price - cost) / price if price else None


# ── product reads (reuse the read-only audit fetcher, but keep body text) ───────
def _visible_text(body_html: str | None) -> str:
    return _TAG_RE.sub(" ", body_html or "").strip()


def fetch_products_full() -> list[dict]:
    """Live products with body text retained (audit's fetcher drops it for brevity)."""
    from commands import storefront_audit

    products: list[dict] = []
    for p in storefront_audit._iter_products():
        variants = getattr(p, "variants", None) or []
        prices: list[float] = []
        for v in variants:
            try:
                prices.append(float(getattr(v, "price", None)))
            except (TypeError, ValueError):
                continue
        body = getattr(p, "body_html", "") or ""
        products.append({
            "id": getattr(p, "id", None),
            "title": getattr(p, "title", "") or "",
            "handle": getattr(p, "handle", "") or "",
            "body_html": body,
            "body_len": len(_visible_text(body)),
            "min_price": min(prices) if prices else None,
            "max_price": max(prices) if prices else None,
        })
    return products


def _sku_by_handle() -> dict[str, dict]:
    """Map Shopify handle → config SKU dict, via each SKU's shopify_url tail."""
    import config
    out: dict[str, dict] = {}
    for sku in config.SKUS.values():
        url = (sku.get("shopify_url") or "").rstrip("/")
        if url:
            out[url.rsplit("/", 1)[-1]] = sku
    return out


# ── copy drafting (Claude best-effort, deterministic skeleton fallback) ─────────
def _skeleton_body(sku: dict) -> str:
    """Deterministic, grounded replacement body from the SKU's own config facts."""
    facts = "".join(f"<li>{f}</li>" for f in sku.get("product_facts", []))
    angle = (sku.get("differentiation_angle") or "").strip()
    return (
        f"<p>{angle}</p>\n<ul>{facts}</ul>"
        if (angle or facts)
        else f"<p>{sku.get('name', 'More Green')}.</p>"
    )


def _draft_copy(sku: dict, current_body: str, issues: list[str], dry_run: bool) -> str:
    """Proposed replacement copy. Claude when available, skeleton otherwise."""
    if dry_run:
        return "[DRY RUN]"
    try:
        import anthropic
        from config import ANTHROPIC_MODEL, BANNED_PHRASES, BRAND_VOICE

        client = anthropic.Anthropic()
        system = (
            "You write Shopify product-page body copy for the brand below. "
            "Return ONLY the HTML body (no markdown fences, no commentary).\n\n"
            f"Brand voice: {BRAND_VOICE}\n"
            f"NEVER use these phrases: {', '.join(BANNED_PHRASES)}"
        )
        user = (
            f"Rewrite the product description for {sku['name']} (₹{sku.get('price_inr')}).\n"
            f"Issues to fix: {', '.join(issues)}.\n"
            f"Ground every claim in these facts: {sku.get('product_facts')}\n"
            f"Differentiation: {sku.get('differentiation_angle')}\n\n"
            f"Current body:\n{current_body[:2000]}"
        )
        resp = client.messages.create(
            model=ANTHROPIC_MODEL, max_tokens=800,
            system=system, messages=[{"role": "user", "content": user}],
        )
        log.info("COST anthropic storefront_copy sku=%s input=%d output=%d",
                 sku.get("id"), resp.usage.input_tokens, resp.usage.output_tokens)
        text = resp.content[0].text.strip()
        if text.startswith("```"):
            text = text.split("\n", 1)[-1].rsplit("```", 1)[0].strip()
        return text or _skeleton_body(sku)
    except Exception as exc:  # no key, import error, API error → grounded fallback
        log.info("storefront copy: Claude unavailable (%s) — using skeleton body", exc)
        return _skeleton_body(sku)


def _copy_issues(product: dict, sku: dict | None, body_min_len: int) -> list[str]:
    import config
    issues: list[str] = []
    if product["body_len"] < body_min_len:
        issues.append(f"thin copy ({product['body_len']} < {body_min_len} chars)")
    low = _visible_text(product["body_html"]).lower()
    hits = [p for p in config.BANNED_PHRASES if p.lower() in low]
    if hits:
        issues.append("banned phrase: " + ", ".join(hits))
    return issues


# ── planner (pure: decides proposals + guardrail outcomes, writes nothing) ──────
def plan(products: list[dict]) -> dict:
    cfg = _settings()
    by_handle = _sku_by_handle()

    copy_changes: list[dict] = []
    price_tests: list[dict] = []
    blocked: list[dict] = []

    for p in products:
        sku = by_handle.get(p["handle"])

        # ── copy change ──
        issues = _copy_issues(p, sku, cfg["body_min_len"])
        if issues:
            copy_changes.append({
                "handle": p["handle"], "product_id": p["id"],
                "sku": sku["id"] if sku else None,
                "title": p["title"], "issues": issues,
                "current_body": p["body_html"],
            })

        # ── price test (margin-guardrailed) ──
        current = p["min_price"]
        if current and current > 0:
            cost = current * cfg["cogs_pct"]
            floor = margin_floor_price(current, cfg["cogs_pct"], cfg["min_margin_pct"])
            proposed = round(current * (1.0 - cfg["discount_pct"]))
            rec = {
                "handle": p["handle"], "product_id": p["id"],
                "sku": sku["id"] if sku else None, "title": p["title"],
                "current_price": current, "proposed_price": proposed,
                "discount_pct": cfg["discount_pct"],
                "assumed_cost": round(cost, 2),
                "min_price_floor": round(floor, 2),
                "margin_at_proposed": _margin_at(proposed, cost),
                "min_margin_pct": cfg["min_margin_pct"],
            }
            if proposed >= floor:
                price_tests.append(rec)
            else:
                rec["reason"] = (
                    f"margin floor breach: ₹{proposed} < floor ₹{floor:.0f} "
                    f"(min margin {cfg['min_margin_pct']:.0%})"
                )
                blocked.append(rec)

    return {"copy_changes": copy_changes, "price_tests": price_tests,
            "blocked": blocked}


# ── runner ──────────────────────────────────────────────────────────────────────
def run(dry_run: bool = False) -> dict:
    db = get_db()

    from commands import storefront_audit
    products: list[dict] = []
    if storefront_audit._connect_shopify(dry_run):
        products = fetch_products_full()
        log.info("storefront-propose: read %d products", len(products))

    p = plan(products)
    print(f"storefront-propose: {len(p['copy_changes'])} copy-change, "
          f"{len(p['price_tests'])} price-test proposals, "
          f"{len(p['blocked'])} price-test(s) blocked by margin guardrail")
    for c in p["copy_changes"]:
        print(f"  COPY   {c['title'][:32]:<32} {', '.join(c['issues'])}")
    for t in p["price_tests"]:
        print(f"  PRICE  {t['title'][:32]:<32} ₹{t['current_price']:.0f}->₹{t['proposed_price']:.0f}"
              f"  margin {t['margin_at_proposed']:.0%}")
    for b in p["blocked"]:
        print(f"  BLOCK  {b['title'][:32]:<32} {b['reason']}")

    if dry_run:
        print("storefront-propose dry-run: no proposals written")
        return p

    n = 0
    for c in p["copy_changes"]:
        sku = None
        if c["sku"]:
            import config
            sku = config.SKUS.get(c["sku"])
        proposed_body = (_draft_copy(sku, c["current_body"], c["issues"], dry_run)
                         if sku else _skeleton_body({"name": c["title"]}))
        approvals.propose(
            "product_copy_change", c["handle"],
            payload={"product_id": c["product_id"], "sku": c["sku"],
                     "issues": c["issues"], "proposed_body": proposed_body},
            expected_impact={"reason": "; ".join(c["issues"])},
            requested_by="storefront_propose", db=db,
        )
        n += 1
    for t in p["price_tests"]:
        approvals.propose(
            "price_test", t["handle"],
            payload={"product_id": t["product_id"], "sku": t["sku"],
                     "current_price": t["current_price"],
                     "proposed_price": t["proposed_price"],
                     "discount_pct": t["discount_pct"],
                     "assumed_cost": t["assumed_cost"],
                     "min_price_floor": t["min_price_floor"],
                     "min_margin_pct": t["min_margin_pct"]},
            expected_impact={"margin_at_proposed": t["margin_at_proposed"]},
            requested_by="storefront_propose", db=db,
        )
        n += 1

    log.info("storefront-propose: wrote %d proposals (%d copy, %d price)",
             n, len(p["copy_changes"]), len(p["price_tests"]))
    print(f"storefront-propose: wrote {n} proposals (awaiting approval)")
    return p
