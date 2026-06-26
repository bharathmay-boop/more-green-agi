"""Pure-logic regression tests for seed_from_sqlite.py — the two things that
must not silently break: the boolean coercion and the ON CONFLICT upsert shape.
No DB needed. Run from automation's env: pytest ../platform/packages/db."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

import seed_from_sqlite as s  # noqa: E402


def test_build_upsert_updates_non_key_columns():
    sql = s._build_upsert("posts", ["post_id", "caption"], ["post_id"])
    assert sql == (
        'INSERT INTO "posts" ("post_id", "caption") VALUES (%s, %s) '
        'ON CONFLICT ("post_id") DO UPDATE SET "caption"=EXCLUDED."caption"'
    )


def test_build_upsert_all_key_columns_does_nothing():
    # When every column is part of the conflict key there is nothing to update.
    sql = s._build_upsert("orders", ["order_id", "sku"], ["order_id", "sku"])
    assert sql.endswith('ON CONFLICT ("order_id", "sku") DO NOTHING')


def test_build_upsert_composite_key_updates_only_non_keys():
    sql = s._build_upsert(
        "ad_spend_daily", ["ad_id", "date", "spend_inr"], ["ad_id", "date"]
    )
    assert 'ON CONFLICT ("ad_id", "date") DO UPDATE SET "spend_inr"=EXCLUDED."spend_inr"' in sql


def test_coerce_booleans_only_for_listed_columns():
    assert s._coerce("posts", "on_hold", 1) is True
    assert s._coerce("posts", "creatives_approved", 0) is False
    assert s._coerce("posts", "caption", 1) == 1          # untyped col left as-is
    assert s._coerce("orders", "order_id", 1) == 1        # other tables untouched
    assert s._coerce("posts", "on_hold", None) is None    # NULL stays NULL
