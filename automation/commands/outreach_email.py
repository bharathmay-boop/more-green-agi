import logging
import os

from utils.db import get_db

log = logging.getLogger(__name__)

PRODUCT_BRIEF = """
More Green makes premium green powders for everyday healthy cooking:
- Sunflower Microgreens Powder: earthy, nutrient-dense, great in dals, smoothies, eggs
- Blueberry Powder: antioxidant-rich, great for oats, baking, drinks
- Moringa Powder: iron-rich superfood staple
- Wheatgrass Powder: classic detox green

Website: moregreen.in | Instagram: @moregreen_in | Based in India
"""

_EMAIL_SYSTEM = (
    "You are a brand partnership manager for More Green, an Indian health supplement brand. "
    "Write a short, warm, genuine collab outreach email to a healthy-cooking micro-influencer. "
    "Under 130 words. Plain text only, no markdown, no emojis. "
    "Avoid generic openers like 'I love your content'. End with a simple yes/no ask."
)

_DM_SYSTEM = (
    "You are a brand partnership manager for More Green, an Indian health supplement brand. "
    "Write a short Instagram DM (under 80 words) to a healthy-cooking micro-influencer. "
    "Casual, warm, not salesy. Plain text. No emojis."
)


def run(dry_run: bool = False) -> None:
    db = get_db()
    _ensure_table(db)

    # Email outreach for influencers with known email
    email_candidates = db.execute(
        "SELECT * FROM influencers WHERE status='approved' AND email IS NOT NULL AND email != ''"
    ).fetchall()

    sent = 0
    for inf in email_candidates:
        handle = inf["handle"]
        name = inf["full_name"] or f"@{handle}"
        body = _generate_copy(_EMAIL_SYSTEM, name, handle, inf.get("source_hashtag") or "healthy cooking", mode="email")
        subject = f"Free More Green products for @{handle}?"

        if dry_run:
            log.info("[DRY RUN] Email → %s (%s)\nSubject: %s\n%s\n", handle, inf["email"], subject, body)
        else:
            _send_email(inf["email"], subject, body)
            with db:
                db.execute(
                    "UPDATE influencers SET status='emailed', outreach_sent_at=datetime('now'), updated_at=datetime('now') WHERE handle=?",
                    (handle,),
                )
            log.info("✓ Email sent → @%s (%s)", handle, inf["email"])
            sent += 1

    if not email_candidates:
        log.info("No approved influencers with email. Add emails to DB and set status='approved'.")

    # DM templates for approved influencers without email
    dm_candidates = db.execute(
        "SELECT * FROM influencers WHERE status='approved' AND (email IS NULL OR email='')"
    ).fetchall()
    if dm_candidates:
        _write_dm_file(dm_candidates)

    log.info("Emails sent: %d | DM templates: %d (see influencer_dms.txt)", sent, len(dm_candidates))


def _generate_copy(system: str, name: str, handle: str, hashtag: str, mode: str) -> str:
    try:
        import anthropic
        client = anthropic.Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])
        user_msg = (
            f"Write a {mode} for:\n"
            f"Name: {name}\n"
            f"Instagram: @{handle}\n"
            f"Found via: #{hashtag}\n\n"
            f"Brand:\n{PRODUCT_BRIEF}\n\n"
            "Offer: Free product pack in exchange for one honest recipe post. Full creative freedom, no scripts."
        )
        msg = client.messages.create(
            model="claude-haiku-4-5-20251001",
            max_tokens=250,
            system=system,
            messages=[{"role": "user", "content": user_msg}],
        )
        return msg.content[0].text.strip()
    except Exception as e:
        log.warning("Claude generation failed (%s) — using fallback template", e)
        return _fallback(name, handle, mode)


def _fallback(name: str, handle: str, mode: str) -> str:
    if mode == "email":
        return (
            f"Hi {name},\n\n"
            "I'm Bharath from More Green — we make clean green powders (microgreens, moringa, wheatgrass) "
            "designed for everyday Indian cooking.\n\n"
            "We'd love to send you a free sample pack. All we'd ask is one honest recipe post if you enjoy it. "
            "No scripts, full creative freedom.\n\n"
            "Interested? Just reply and I'll get a pack out this week.\n\n"
            "Warmly,\nBharath\nMore Green | moregreen.in"
        )
    return (
        f"Hey {name}! I'm Bharath from More Green — we make green powders for everyday cooking. "
        "Would love to send you a free sample pack. One honest recipe post if you like it, no pressure. "
        "Interested? 🌿"
    )


def _send_email(to_email: str, subject: str, body: str) -> None:
    key = os.environ.get("SENDGRID_API_KEY")
    if not key:
        raise SystemExit("SENDGRID_API_KEY not set in .env")
    from sendgrid import SendGridAPIClient
    from sendgrid.helpers.mail import Mail
    msg = Mail(
        from_email="founders@moregreen.in",
        to_emails=to_email,
        subject=subject,
        plain_text_content=body,
    )
    SendGridAPIClient(key).send(msg)


def _write_dm_file(candidates: list) -> None:
    with open("influencer_dms.txt", "w", encoding="utf-8") as f:
        f.write("# More Green — Instagram DM Templates\n")
        f.write("# Send these manually on Instagram to influencers without a public email\n\n")
        for inf in candidates:
            handle = inf["handle"]
            name = inf["full_name"] or f"@{handle}"
            hashtag = inf.get("source_hashtag") or "healthy cooking"
            dm = _generate_copy(_DM_SYSTEM, name, handle, hashtag, mode="DM")
            f.write(f"{'─' * 50}\n")
            f.write(f"To: @{handle}  |  Post: {inf.get('post_url', '')}\n\n")
            f.write(dm)
            f.write("\n\n")
    log.info("DM templates written to influencer_dms.txt")


def _ensure_table(db) -> None:
    db.execute("""
        CREATE TABLE IF NOT EXISTS influencers (
            handle TEXT PRIMARY KEY, full_name TEXT, email TEXT,
            follower_count INTEGER, source_hashtag TEXT, post_url TEXT,
            like_count INTEGER, comments_count INTEGER,
            status TEXT DEFAULT 'discovered', notes TEXT,
            outreach_sent_at TEXT, reply_received_at TEXT,
            collab_agreed INTEGER DEFAULT 0, product_shipped INTEGER DEFAULT 0,
            tracking_code TEXT,
            created_at TEXT DEFAULT (datetime('now')),
            updated_at TEXT DEFAULT (datetime('now'))
        )
    """)
