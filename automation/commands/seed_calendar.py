import logging
import os
from datetime import date

import gspread
import yaml

from config import CALENDAR_PATH

log = logging.getLogger(__name__)


def run(dry_run: bool = False, include_sundays: bool = False, sprint: str = None) -> None:
    data = yaml.safe_load(CALENDAR_PATH.read_text(encoding="utf-8"))
    posts = data["posts"]

    posts = _filter_posts(posts, include_sundays=include_sundays, sprint=sprint)

    sheets_id = os.environ.get("GOOGLE_SHEETS_ID")
    if not sheets_id:
        raise SystemExit("GOOGLE_SHEETS_ID not set in .env")

    gc = gspread.service_account(filename="service_account.json")
    spreadsheet = gc.open_by_key(sheets_id)
    try:
        sheet = spreadsheet.worksheet("Content Calendar")
    except gspread.exceptions.WorksheetNotFound:
        sheet = spreadsheet.add_worksheet("Content Calendar", rows=200, cols=20)
        sheet.append_row([
            "post_id", "scheduled_date", "scheduled_time", "platform",
            "post_type", "content_pillar", "sku", "topic", "theme", "tone",
            "cultural_moment", "source_product_image", "source_lifestyle_image",
            "reference_notes", "pipeline_status", "on_hold",
        ])
        log.info("Created 'Content Calendar' tab with headers.")

    existing_ids = set(sheet.col_values(1)[1:])
    posts = _deduplicate(posts, existing_ids)

    if not posts:
        log.info("Nothing to add — all posts already in Sheet.")
        return

    if dry_run:
        log.info("[DRY RUN] Would add %d rows:", len(posts))
        for p in posts:
            log.info("  %s  %-12s  %s", p["post_id"], p["sku"], p["topic"][:60])
        return

    rows = [_build_row(p) for p in posts]
    sheet.append_rows(rows, value_input_option="USER_ENTERED")
    log.info("Done. Added %d posts to Sheets. Review -> approve -> run generate-prompts.", len(rows))


def _filter_posts(posts: list, include_sundays: bool, sprint: str = None) -> list:
    result = []
    for p in posts:
        post_date = date.fromisoformat(p["scheduled_date"])
        if sprint and p["scheduled_date"] < sprint:
            continue
        if not include_sundays and post_date.weekday() == 6:
            continue
        result.append(p)
    return result


def _deduplicate(posts: list, existing_ids: set) -> list:
    new_posts = []
    for p in posts:
        if p["post_id"] in existing_ids:
            log.info("SKIP %s — already in Sheet", p["post_id"])
            continue
        new_posts.append(p)
    return new_posts


def _build_row(post: dict) -> list:
    return [
        post["post_id"],
        post["scheduled_date"],
        post.get("scheduled_time", "09:00"),
        post.get("platform", "both"),
        post.get("post_type", "feed_image"),
        post.get("content_pillar", "product"),
        post["sku"],
        post.get("topic", ""),
        post.get("theme", ""),
        post.get("tone", "warm_inspirational"),
        post.get("cultural_moment", "none"),
        post.get("source_product_image", ""),
        post.get("source_lifestyle_image", ""),
        post.get("reference_notes", ""),
        "draft",
        "",
    ]
