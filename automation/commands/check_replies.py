"""check_replies — Poll inbound IG conversations, classify intent, draft + send replies.

Only handles INbound messages (after someone has already messaged @moregreen_in).
Cold DMs via API are blocked; IGSID comes from /{ig_id}/conversations, NOT Business Discovery.
"""

import logging
import os
from datetime import datetime, timezone

import anthropic
import requests
from facebook_business.api import FacebookAdsApi
from facebook_business.adobjects.iguser import IGUser  # noqa: F401 — kept for SDK init context

from config import META_GRAPH_BASE, ANTHROPIC_MODEL
from utils.db import get_db
from utils.meta_auth import validate_meta_token

log = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Public entry point
# ---------------------------------------------------------------------------


def run(dry_run: bool = False) -> None:
    if not os.environ.get("IG_MESSAGES_APPROVED"):
        log.warning(
            "instagram_manage_messages not yet approved by Meta — check-replies skipped. "
            "See docs/meta_app_review.md for filing instructions. "
            "Set IG_MESSAGES_APPROVED=1 in .env once approved."
        )
        return

    validate_meta_token()
    db = get_db()

    FacebookAdsApi.init(
        app_id=os.environ["META_APP_ID"],
        app_secret=os.environ["META_APP_SECRET"],
        access_token=os.environ["META_ACCESS_TOKEN"],
    )
    ig_id = os.environ["META_IG_ACCOUNT_ID"]
    token = os.environ["META_ACCESS_TOKEN"]

    threads = _fetch_conversation_threads(ig_id, token)
    if not threads:
        log.info("No conversation threads found.")
        return

    log.info("Found %d conversation thread(s). Checking for new messages...", len(threads))
    processed = 0

    for thread in threads:
        result = _process_thread(db, ig_id, token, thread, dry_run)
        if result:
            processed += 1

    log.info("Processed %d thread(s) with new messages.", processed)
    _sync_db(db)


# ---------------------------------------------------------------------------
# Fetch threads
# ---------------------------------------------------------------------------


def _fetch_conversation_threads(ig_id: str, token: str) -> list:
    """GET /{ig_id}/conversations to get all IG message threads."""
    r = requests.get(
        f"{META_GRAPH_BASE}/{ig_id}/conversations",
        params={
            "platform": "instagram",
            "fields": "id,participants{id,username},messages{message,from,created_time,id}",
            "access_token": token,
        },
        timeout=20,
    )
    data = r.json()
    if "error" in data:
        log.warning("Conversations fetch error: %s", data["error"].get("message", ""))
        return []
    return data.get("data", [])


# ---------------------------------------------------------------------------
# Process a single thread
# ---------------------------------------------------------------------------


def _process_thread(db, ig_id: str, token: str, thread: dict, dry_run: bool) -> bool:
    """
    Returns True if there was a new message that required action.
    """
    thread_id = thread.get("id", "")
    participants_data = thread.get("participants", {}).get("data", [])
    messages_data = thread.get("messages", {}).get("data", [])

    # Find the external participant (not our own IG account)
    handle = None
    igsid = None
    for p in participants_data:
        p_username = p.get("username", "")
        p_id = p.get("id", "")
        # Our own account's ig_id matches META_IG_ACCOUNT_ID
        if p_id != ig_id and p_username.lower() != os.environ.get("META_IG_HANDLE", "moregreen_in").lower():
            handle = p_username
            igsid = p_id
            break

    if not handle or not igsid:
        log.debug("Thread %s: could not identify external participant, skipping.", thread_id)
        return False

    # Find the latest inbound message (from the influencer, not from us)
    inbound_msg = None
    for msg in messages_data:
        sender = msg.get("from", {})
        sender_id = sender.get("id", "")
        if sender_id != ig_id:
            inbound_msg = msg
            break  # messages are newest-first from the API

    if not inbound_msg:
        log.debug("Thread %s (@%s): no inbound messages, skipping.", thread_id, handle)
        return False

    message_text = inbound_msg.get("message", "").strip()
    created_time = inbound_msg.get("created_time", "")
    meta_message_id = inbound_msg.get("id", "")

    if not message_text:
        return False

    # Check last_checked_at — skip if we've already processed this
    row = db.execute(
        "SELECT last_checked_at FROM influencers WHERE handle = ?", (handle,)
    ).fetchone()

    if row and row["last_checked_at"] and created_time:
        try:
            msg_dt = datetime.fromisoformat(created_time.replace("Z", "+00:00"))
            checked_dt = datetime.fromisoformat(row["last_checked_at"].replace(" ", "T") + "+00:00")
            if msg_dt <= checked_dt:
                log.debug("@%s: message not newer than last_checked_at, skipping.", handle)
                return False
        except ValueError:
            pass  # if parsing fails, proceed

    # Upsert IGSID into influencers table (insert if unknown influencer)
    db.execute(
        """INSERT INTO influencers (handle, ig_user_id, status, created_at, updated_at)
           VALUES (?, ?, 'discovered', datetime('now'), datetime('now'))
           ON CONFLICT(handle) DO UPDATE SET
               ig_user_id = excluded.ig_user_id,
               updated_at = datetime('now')""",
        (handle, igsid),
    )
    db.commit()

    # Load conversation history (last 5 messages)
    history_rows = db.execute(
        """SELECT direction, message_text, sent_at
           FROM influencer_conversations
           WHERE handle = ?
           ORDER BY sent_at DESC
           LIMIT 5""",
        (handle,),
    ).fetchall()
    conversation_history = list(reversed([dict(r) for r in history_rows]))

    # Classify intent
    intent = _classify_intent(message_text)
    log.info("@%s intent: %s | message: %.80s", handle, intent, message_text)

    # Draft reply
    draft = _draft_reply(db, handle, message_text, conversation_history, intent)

    # Display to Bharath
    print("\n" + "═" * 38)
    print(f"Reply needed: @{handle}")
    print(f"Their message: {message_text}")
    print(f"Intent: {intent}")
    print("─" * 38)
    print("Suggested reply:")
    print(draft)
    print("═" * 38)
    print("[y] Send  [e] Edit  [s] Skip  (default: skip)")

    try:
        choice = input("> ").strip().lower()
    except (EOFError, KeyboardInterrupt):
        choice = "s"

    send_text = None
    if choice == "y":
        send_text = draft
    elif choice == "e":
        print("Enter your edited reply (press Enter twice to finish):")
        lines = []
        try:
            while True:
                line = input()
                if line == "" and lines and lines[-1] == "":
                    break
                lines.append(line)
        except (EOFError, KeyboardInterrupt):
            pass
        send_text = "\n".join(lines).strip() or draft
    else:
        log.info("@%s: skipped.", handle)
        _update_last_checked(db, handle)
        return False

    # Send (or dry-run)
    if dry_run:
        print(f"[DRY RUN] Would send to @{handle} (IGSID {igsid}): {send_text}")
        meta_sent_id = "dry_run"
    else:
        try:
            meta_sent_id = _send_reply(ig_id, igsid, send_text, token)
            log.info("Sent reply to @%s (meta_message_id=%s)", handle, meta_sent_id)
        except RuntimeError as exc:
            log.error("Failed to send reply to @%s: %s", handle, exc)
            return False

    now_iso = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")

    # Store inbound message
    _store_message(db, handle, thread_id, "inbound", message_text, created_time, meta_message_id)

    # Store outbound reply
    _store_message(db, handle, thread_id, "outbound", send_text, now_iso, meta_sent_id)

    # Update influencer status
    new_status = {
        "interested": "replied",
        "wants_address": "replied",
        "question": "replied",
        "declined": "declined",
        "neutral": "replied",
    }.get(intent, "replied")

    with db:
        db.execute(
            """UPDATE influencers SET
               status=?, ig_user_id=?, last_message_at=datetime('now'),
               last_checked_at=datetime('now'), updated_at=datetime('now')
               WHERE handle=?""",
            (new_status, igsid, handle),
        )

    return True


# ---------------------------------------------------------------------------
# Intent classification
# ---------------------------------------------------------------------------


def _classify_intent(text: str) -> str:
    t = text.lower()
    if any(w in t for w in ["address", "ship", "send", "deliver", "where to"]):
        return "wants_address"
    if any(w in t for w in ["yes", "interested", "love to", "sounds good", "sure", "would love", "definitely"]):
        return "interested"
    if any(w in t for w in ["no", "not interested", "pass", "not for me", "decline"]):
        return "declined"
    if "?" in t:
        return "question"
    return "neutral"


# ---------------------------------------------------------------------------
# Draft reply via Claude
# ---------------------------------------------------------------------------


def _draft_reply(db, handle: str, message_text: str, history: list, intent: str) -> str:
    history_lines = []
    for entry in history:
        direction = entry.get("direction", "unknown")
        text = entry.get("message_text", "")
        prefix = "You" if direction == "outbound" else f"@{handle}"
        history_lines.append(f"{prefix}: {text}")
    history_text = "\n".join(history_lines) if history_lines else "(no prior messages)"

    system_prompt = (
        "You are Bharath, founder of More Green (Indian green powder brand, @moregreen_in).\n"
        "Reply to an influencer's Instagram message. Keep it warm, genuine, under 100 words.\n"
        "Plain text only. No emojis.\n"
        f"Intent classified as: {intent}\n"
        "If intent is 'wants_address': ask for their full shipping address.\n"
        "If intent is 'declined': thank them graciously, no pressure."
    )
    user_msg = (
        f"Thread so far:\n{history_text}\n\n"
        f"Latest message from @{handle}: {message_text}"
    )

    _fallbacks = {
        "interested": f"Hey, so glad you're interested! Would love to send you a sample pack. Can you share your full shipping address?",
        "wants_address": f"Great, please share your full name and shipping address and I'll get it out to you!",
        "question": f"Happy to answer! What would you like to know about More Green?",
        "declined": f"No worries at all, really appreciate you taking the time to reply. Keep up the amazing work!",
        "neutral": f"Thanks for your message! Let me know if you'd like to know more about More Green.",
    }

    try:
        client = anthropic.Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])
        response = client.messages.create(
            model=ANTHROPIC_MODEL,
            max_tokens=200,
            system=system_prompt,
            messages=[{"role": "user", "content": user_msg}],
        )
        return response.content[0].text.strip()
    except Exception as exc:
        log.warning("Claude API error drafting reply for @%s: %s — using fallback", handle, exc)
        return _fallbacks.get(intent, _fallbacks["neutral"])


# ---------------------------------------------------------------------------
# Send reply
# ---------------------------------------------------------------------------


def _send_reply(ig_id: str, igsid: str, text: str, token: str) -> str:
    """POST /{ig_id}/messages to send a reply. Returns meta_message_id."""
    r = requests.post(
        f"{META_GRAPH_BASE}/{ig_id}/messages",
        json={
            "recipient": {"id": igsid},
            "message": {"text": text},
        },
        params={"access_token": token},
        timeout=15,
    )
    data = r.json()
    if "error" in data:
        raise RuntimeError(f"Send reply failed: {data['error'].get('message', '')}")
    return data.get("message_id", "")


# ---------------------------------------------------------------------------
# DB helpers
# ---------------------------------------------------------------------------


def _store_message(
    db,
    handle: str,
    ig_thread_id: str,
    direction: str,
    message_text: str,
    sent_at: str,
    meta_message_id: str = None,
) -> None:
    with db:
        db.execute(
            """INSERT OR IGNORE INTO influencer_conversations
               (handle, ig_thread_id, direction, message_text, sent_at, meta_message_id)
               VALUES (?, ?, ?, ?, ?, ?)""",
            (handle, ig_thread_id, direction, message_text, sent_at, meta_message_id),
        )


def _update_last_checked(db, handle: str) -> None:
    with db:
        db.execute(
            "UPDATE influencers SET last_checked_at=datetime('now'), updated_at=datetime('now') WHERE handle=?",
            (handle,),
        )


def _sync_db(db) -> None:
    """Commit any pending writes (belt-and-suspenders flush)."""
    try:
        db.commit()
    except Exception:
        pass
