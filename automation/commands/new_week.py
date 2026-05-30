import logging
import os
from datetime import date, timedelta

import gspread

log = logging.getLogger(__name__)

_SKUS = ["sunflower", "blueberry", "moringa", "wheatgrass"]
_PILLARS = ["educational", "recipe", "product", "social_proof", "founder_bts"]
_PLATFORMS = ["Both", "Instagram", "Facebook"]
_POST_TYPES = ["feed_image", "reels", "carousel", "story"]


def run() -> None:
    sheets_id = os.environ.get("GOOGLE_SHEETS_ID")
    if not sheets_id:
        raise SystemExit("GOOGLE_SHEETS_ID not set in .env")

    gc = gspread.service_account(filename="service_account.json")
    sheet = gc.open_by_key(sheets_id).sheet1

    # Find next Monday
    today = date.today()
    days_ahead = 0 - today.weekday()
    if days_ahead <= 0:
        days_ahead += 7
    next_monday = today + timedelta(days=days_ahead)

    week_label = next_monday.strftime("W%W")
    days = ["MON", "TUE", "WED", "THU", "FRI", "SAT"]

    new_rows = []
    for i, day in enumerate(days):
        post_date = next_monday + timedelta(days=i)
        sku = _SKUS[i % len(_SKUS)]
        pillar = _PILLARS[i % len(_PILLARS)]
        post_id = f"{week_label}_{day}_01"
        new_rows.append([
            post_id,
            post_date.isoformat(),
            "09:00",
            "Both",
            "feed_image",
            pillar,
            sku,
            "",  # topic — founder fills in
            "",  # theme
            "warm_inspirational",
            "none",
            f"Files/{sku}/product_front.jpg",
            "",
            "",
            "draft",
            "",
        ])

    sheet.append_rows(new_rows)
    log.info("Scaffolded %d rows for week starting %s", len(new_rows), next_monday.isoformat())
    print(f"Added {len(new_rows)} rows to Google Sheets for week of {next_monday.isoformat()}")
