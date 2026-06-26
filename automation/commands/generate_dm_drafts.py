import logging
import os

import anthropic

from utils.db import get_db

log = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Niche system prompts
# ---------------------------------------------------------------------------

_RECIPE_SYSTEM = (
    "You are a brand partnership manager for More Green, an Indian health supplement brand. "
    "Write a short Instagram DM (under 80 words) to a recipe/cooking creator. "
    "Reference their cooking content naturally. Casual, warm, not salesy. Plain text. No emojis."
)
_NUTRITION_SYSTEM = (
    "You are a brand partnership manager for More Green, an Indian health supplement brand. "
    "Write a short Instagram DM (under 80 words) to a nutrition/health expert creator. "
    "Speak their language — mention nutrients, clean ingredients. Casual, warm. Plain text. No emojis."
)
_FITNESS_SYSTEM = (
    "You are a brand partnership manager for More Green, an Indian health supplement brand. "
    "Write a short Instagram DM (under 80 words) to a fitness/gym creator. "
    "Reference performance, recovery, clean fuel. Casual, direct. Plain text. No emojis."
)
_FAMILY_SYSTEM = (
    "You are a brand partnership manager for More Green, an Indian health supplement brand. "
    "Write a short Instagram DM (under 80 words) to a family/mom creator. "
    "Emphasise ease, kid-friendly options, healthy everyday cooking. Warm, friendly. Plain text. No emojis."
)
_CREATOR_SYSTEM = (
    "You are a brand partnership manager for More Green, an Indian health supplement brand. "
    "Write a short Instagram DM (under 80 words) to a lifestyle/content creator. "
    "Keep it genuine and concise. Casual, warm, not salesy. Plain text. No emojis."
)

# ---------------------------------------------------------------------------
# Product brief
# ---------------------------------------------------------------------------

PRODUCT_BRIEF = (
    "More Green — premium Indian green powders for everyday cooking:\n"
    "- Sunflower Microgreens Powder: earthy, nutrient-dense, great in dals, smoothies, eggs\n"
    "- Blueberry Powder: antioxidant-rich, great for oats, baking, drinks\n"
    "- Moringa Powder: iron-rich superfood staple\n"
    "- Wheatgrass Powder: classic detox green\n"
    "Instagram: @moregreen_in | moregreen.in\n"
    "Offer: Free product pack in exchange for one honest recipe post. Full creative freedom, no scripts."
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _niche_for(hashtag: str) -> tuple[str, str]:
    """Returns (template_name, system_prompt) for the given source hashtag."""
    h = hashtag.lower()
    if any(k in h for k in ["recipe", "cooking", "food", "baking", "kitchen"]):
        return "recipe", _RECIPE_SYSTEM
    if any(k in h for k in ["nutrition", "dietitian", "health", "wellness", "diet"]):
        return "nutrition", _NUTRITION_SYSTEM
    if any(k in h for k in ["fitness", "gym", "workout", "yoga", "athlet"]):
        return "fitness", _FITNESS_SYSTEM
    if any(k in h for k in ["mom", "family", "kids", "parent", "mum"]):
        return "family", _FAMILY_SYSTEM
    return "creator", _CREATOR_SYSTEM  # default


def _fallback_dm(name: str, handle: str) -> str:
    return (
        f"Hey {name}! I'm Bharath from More Green — we make clean green powders (microgreens, moringa, wheatgrass) "
        "for everyday Indian cooking. Would love to send you a free sample pack. "
        "One honest recipe post if you enjoy it, no pressure. Interested?"
    )


def _generate_dm(client: anthropic.Anthropic, inf: dict) -> tuple[str, str]:
    """
    Returns (dm_text, template_name).
    Falls back to _fallback_dm on any API error.
    """
    name = inf["full_name"] or inf["handle"]
    handle = inf["handle"]
    hashtag = inf["source_hashtag"] or ""

    template_name, system_prompt = _niche_for(hashtag)
    user_msg = (
        f"Write a DM for:\nName: {name}\nInstagram: @{handle}\nFound via: #{hashtag}\n\n"
        f"Brand:\n{PRODUCT_BRIEF}\n"
    )

    try:
        response = client.messages.create(
            model="claude-haiku-4-5-20251001",
            max_tokens=200,
            system=system_prompt,
            messages=[{"role": "user", "content": user_msg}],
        )
        dm_text = response.content[0].text.strip()
    except Exception as exc:
        log.warning("Claude API error for @%s: %s — using fallback", handle, exc)
        dm_text = _fallback_dm(name, handle)

    return dm_text, template_name


def _format_block(inf: dict, dm_text: str) -> str:
    handle = inf["handle"]
    follower_count = inf["follower_count"]
    fc_display = f"{follower_count:,}" if follower_count is not None else "?"
    eng_rate = inf["engagement_rate"] or 0.0
    post_url = inf["post_url"] or ""

    return (
        "══════════════════════════════════════\n"
        f"@{handle}  (Followers: {fc_display} | Eng: {eng_rate:.1f}%)\n"
        f"Profile: instagram.com/{handle}\n"
        f"Post that caught our eye: {post_url}\n"
        "──────────────────────────────────────\n"
        "[DM TEXT — copy and paste this]\n"
        f"{dm_text}\n"
        "══════════════════════════════════════\n"
    )


# ---------------------------------------------------------------------------
# Main entry point
# ---------------------------------------------------------------------------


def run(dry_run: bool = False) -> None:
    db = get_db()
    rows = db.execute(
        """
        SELECT handle, full_name, source_hashtag, follower_count, engagement_rate,
               post_url, email
        FROM influencers
        WHERE status IN ('approved', 'dm_draft')
          AND dm_draft_text IS NULL
          AND (email IS NULL OR email = '')
        """
    ).fetchall()

    candidates = [dict(r) for r in rows]

    if not candidates:
        log.info("No influencers needing DM drafts. Nothing to do.")
        return

    log.info("Generating DM drafts for %d influencer(s)…", len(candidates))

    client = anthropic.Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])

    updates: list[tuple[str, str, str]] = []  # (dm_text, template_name, handle)

    for inf in candidates:
        dm_text, template_name = _generate_dm(client, inf)
        updates.append((dm_text, template_name, inf["handle"]))
        log.info("  drafted DM for @%s (template: %s)", inf["handle"], template_name)

    if not dry_run:
        for dm_text, template_name, handle in updates:
            db.execute(
                """
                UPDATE influencers
                SET status = 'dm_draft',
                    dm_draft_text = ?,
                    dm_draft_generated_at = datetime('now'),
                    template_used = ?,
                    updated_at = datetime('now')
                WHERE handle = ?
                """,
                (dm_text, template_name, handle),
            )
        db.commit()
        log.info("DM drafts saved to DB for %d influencers.", len(updates))
    else:
        for dm_text, template_name, handle in updates:
            log.info("[DRY RUN] @%s (%s): %s", handle, template_name, dm_text[:60])

    log.info("Best time to send: 7-10 PM IST. DM text is in the Sheet 'DM Draft' column.")
