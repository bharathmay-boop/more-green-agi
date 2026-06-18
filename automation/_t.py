import os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from commands import storefront_propose as sp

f = sp.margin_floor_price(500, 0.40, 0.50)   # cost=200, floor=400
assert abs(f - 400) < 1e-6, f

prods = [
    {"id": 1, "title": "Sunflower", "handle": "sunflower",
     "body_html": "<p>short</p>", "body_len": 5, "min_price": 499, "max_price": 499},
    {"id": 2, "title": "Cheap", "handle": "none",
     "body_html": "<p>" + "x" * 500 + "</p>", "body_len": 500,
     "min_price": 100, "max_price": 100},
]
p = sp.plan(prods)
print("copy   ", [c["handle"] for c in p["copy_changes"]])
print("price  ", [(t["handle"], t["current_price"], t["proposed_price"]) for t in p["price_tests"]])
print("blocked", [(b["handle"], b["proposed_price"], round(b["min_price_floor"])) for b in p["blocked"]])
print("OK")
