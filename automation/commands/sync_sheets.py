import logging

import gspread

from utils.db import get_db

log = logging.getLogger(__name__)

REQUIRED_COLUMNS = ["post_id", "scheduled_date", "sku", "topic", "source_product_image"]

PLATFORM_VALUES  = {"Instagram", "Facebook", "Both", "YouTube"}
POST_TYPE_VALUES = {"feed_image", "reels", "carousel", "story"}
PILLAR_VALUES    = {"educational", "recipe", "product", "social_proof", "founder_bts"}
SKU_VALUES       = {"sunflower", "blueberry", "moringa", "wheatgrass", "brand"}
TONE_VALUES      = {"warm_inspirational", "educational", "humorous", "urgent"}


def run(dry_run: bool = False) -> None:
    import os
    sheets_id = os.environ.get("GOOGLE_SHEETS_ID")
    if not sheets_id:
        raise SystemExit("GOOGLE_SHEETS_ID not set in .env")

    gc = gspread.service_account(filename="service_account.json")
    sheet = gc.open_by_key(sheets_id).sheet1
    rows = sheet.get_all_records()
    log.info("Fetched %d rows from Google Sheets", len(rows))

    db = get_db()
    validated, skipped = 0, 0

    for row in rows:
        post_id = row.get("post_id") or row.get("Post ID", "")
        missing = [c for c in REQUIRED_COLUMNS if not row.get(c)]
        if missing:
            log.warning("Skipping row %s — missing: %s", post_id, missing)
            skipped += 1
            continue

        # Normalise column names (sheet uses Title Case)
        scheduled_at    = _parse_datetime(row.get("scheduled_date", ""), row.get("scheduled_time", "09:00"))
        platform        = (row.get("platform") or "Both").lower()
        post_type       = row.get("post_type") or "feed_image"
        content_pillar  = row.get("content_pillar") or "product"
        sku             = (row.get("sku") or "").lower()
        topic           = row.get("topic", "")
        theme           = row.get("theme", "")
        tone            = row.get("tone") or "warm_inspirational"
        cultural_moment = row.get("cultural_moment") or "none"
        source_product  = row.get("source_product_image", "")
        source_lifestyle= row.get("source_lifestyle_image", "")
        reference_notes = row.get("reference_notes", "")

        if sku not in SKU_VALUES:
            log.warning("Skipping %s — unknown SKU: %s", post_id, sku)
            skipped += 1
            continue

        if dry_run:
            log.info("[DRY RUN] Would upsert post %s", post_id)
            validated += 1
            continue

        with db:
            db.execute(
                """
                INSERT OR IGNORE INTO posts (
                    post_id, scheduled_at, platform, post_type,
                    content_pillar, sku, topic, theme, tone,
                    cultural_moment, source_product_image,
                    source_lifestyle_image, reference_notes, pipeline_status
                ) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,'draft')
                """,
                (
                    post_id, scheduled_at, platform, post_type,
                    content_pillar, sku, topic, theme, tone,
                    cultural_moment, source_product,
                    source_lifestyle, reference_notes,
                ),
            )
        validated += 1

    log.info("Sync complete: %d inserted/ignored, %d skipped", validated, skipped)


def _parse_datetime(date_str: str, time_str: str) -> str:
    """Combine date and time into ISO 8601 string."""
    date_str = str(date_str).strip()
    time_str = str(time_str).strip() or "09:00"
    if not date_str:
        return ""
    return f"{date_str}T{time_str}:00"
