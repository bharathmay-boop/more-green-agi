import logging
import os
from utils.db import get_db

log = logging.getLogger(__name__)

def run() -> None:
    try:
        db = get_db()

        # Count by status groups
        all_rows = db.execute("SELECT status, product_shipped, post_live_url FROM influencers").fetchall()

        discovered = sum(1 for r in all_rows if r["status"] in ("discovered", "approved"))
        dm_drafts = sum(1 for r in all_rows if r["status"] == "dm_draft")
        emailed = sum(1 for r in all_rows if r["status"] in ("emailed", "contacted"))
        replied = sum(1 for r in all_rows if r["status"] == "replied")
        address = sum(1 for r in all_rows if r["status"] == "address_collected")
        shipped = sum(1 for r in all_rows if r["product_shipped"])
        post_live = sum(1 for r in all_rows if r["post_live_url"])
        declined = sum(1 for r in all_rows if r["status"] == "declined")
        total = len(all_rows)

        sheet_id = os.environ.get("INFLUENCER_SHEETS_ID", "")
        sheet_url = f"https://docs.google.com/spreadsheets/d/{sheet_id}" if sheet_id else "(set INFLUENCER_SHEETS_ID in .env)"

        separator = "─" * 62
        print(f"\n── More Green Influencer Campaign Status {'─' * 22}")
        print(f"  {'Discovered:':<26} {discovered:>5}")
        if dm_drafts:
            print(f"  {'DM Drafts ready:':<26} {dm_drafts:>5}  → open influencer_dms.txt")
        else:
            print(f"  {'DM Drafts ready:':<26} {dm_drafts:>5}")
        print(f"  {'Emailed:':<26} {emailed:>5}")
        print(f"  {'Replied:':<26} {replied:>5}")
        print(f"  {'Address collected:':<26} {address:>5}")
        print(f"  {'Product shipped:':<26} {shipped:>5}")
        print(f"  {'Post live:':<26} {post_live:>5}")
        print(f"  {'Declined:':<26} {declined:>5}")
        print(separator)
        print(f"  {'Total tracked:':<26} {total:>5}")
        print(f"  Sheet: {sheet_url}")
        print()

    except Exception as e:
        print("\nNo influencer data yet. Run find-influencers first.\n")
        log.debug(f"Error reading influencers table: {e}")
