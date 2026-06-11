import sys
from pathlib import Path
from datetime import date
from unittest.mock import MagicMock, patch

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))


# ── fixtures ──────────────────────────────────────────────────────────────────

SAMPLE_POSTS = [
    {
        "post_id": "2026-06-10_01",
        "scheduled_date": "2026-06-10",  # Wednesday
        "scheduled_time": "09:00",
        "platform": "both",
        "post_type": "feed_image",
        "content_pillar": "product",
        "sku": "sunflower",
        "topic": "Test topic",
        "theme": "monsoon_reset",
        "tone": "bold_direct",
        "cultural_moment": "monsoon_immunity",
        "source_product_image": "Files/sunflower/product_front.jpg",
        "source_lifestyle_image": "",
        "reference_notes": "Test note",
    },
    {
        "post_id": "2026-06-14_01",
        "scheduled_date": "2026-06-14",  # Sunday
        "scheduled_time": "09:00",
        "platform": "both",
        "post_type": "story",
        "content_pillar": "product",
        "sku": "brand",
        "topic": "Sunday story topic",
        "theme": "monsoon_reset",
        "tone": "transparent_expert",
        "cultural_moment": "none",
        "source_product_image": "Files/brand/brand_lifestyle.jpg",
        "source_lifestyle_image": "",
        "reference_notes": "",
    },
]


# ── tests ─────────────────────────────────────────────────────────────────────

def test_filter_sundays_removes_sunday_posts():
    from commands.seed_calendar import _filter_posts
    result = _filter_posts(SAMPLE_POSTS, include_sundays=False)
    assert len(result) == 1
    assert result[0]["post_id"] == "2026-06-10_01"


def test_include_sundays_keeps_all_posts():
    from commands.seed_calendar import _filter_posts
    result = _filter_posts(SAMPLE_POSTS, include_sundays=True)
    assert len(result) == 2


def test_build_row_returns_16_columns():
    from commands.seed_calendar import _build_row
    row = _build_row(SAMPLE_POSTS[0])
    assert len(row) == 16


def test_build_row_maps_fields_correctly():
    from commands.seed_calendar import _build_row
    row = _build_row(SAMPLE_POSTS[0])
    assert row[0] == "2026-06-10_01"      # post_id
    assert row[1] == "2026-06-10"          # scheduled_date
    assert row[2] == "09:00"               # scheduled_time
    assert row[3] == "both"                # platform
    assert row[4] == "feed_image"          # post_type
    assert row[5] == "product"             # content_pillar
    assert row[6] == "sunflower"           # sku
    assert row[7] == "Test topic"          # topic
    assert row[8] == "monsoon_reset"       # theme
    assert row[9] == "bold_direct"         # tone
    assert row[10] == "monsoon_immunity"   # cultural_moment
    assert row[11] == "Files/sunflower/product_front.jpg"  # source_product_image
    assert row[12] == ""                   # source_lifestyle_image
    assert row[13] == "Test note"          # reference_notes
    assert row[14] == "draft"              # pipeline_status (hardcoded)
    assert row[15] == ""                   # on_hold (hardcoded empty)


def test_deduplicate_skips_existing_post_ids():
    from commands.seed_calendar import _deduplicate
    existing = {"2026-06-10_01"}
    result = _deduplicate(SAMPLE_POSTS, existing)
    assert len(result) == 1
    assert result[0]["post_id"] == "2026-06-14_01"


def test_deduplicate_keeps_all_when_no_existing():
    from commands.seed_calendar import _deduplicate
    result = _deduplicate(SAMPLE_POSTS, set())
    assert len(result) == 2


def test_filter_by_sprint_date():
    from commands.seed_calendar import _filter_posts
    result = _filter_posts(SAMPLE_POSTS, include_sundays=True, sprint="2026-06-14")
    assert len(result) == 1
    assert result[0]["post_id"] == "2026-06-14_01"
