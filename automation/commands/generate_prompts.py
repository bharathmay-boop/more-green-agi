import json
import logging
import random
import threading
import time
from concurrent.futures import ThreadPoolExecutor, as_completed

import anthropic

from config import ANTHROPIC_MODEL, BANNED_PHRASES, BRAND_VOICE, SKUS
from utils.db import get_db

log = logging.getLogger(__name__)

_SEMAPHORE = threading.Semaphore(2)

_SYSTEM_BASE = f"""You are a senior creative director for More Green — an Indian microgreens powder brand.

## Brand Voice
{BRAND_VOICE}

## Banned Phrases (never use these)
{', '.join(BANNED_PHRASES)}

## FLUX Kontext Image Prompt Rules
Write an EDIT INSTRUCTION, not a product description. The real product photo is the input.
Describe only what to CHANGE or ADD in the scene around the product.
Never describe the product label, text, or design — it is preserved from the input photo.
Include: scene setting, lighting (precise terms), camera angle. Max 100 words.
End with: "Keep the product pouch, label, and design completely unchanged."

## Caption Rules — Instagram
1-2 punchy lines + specific fact + max 8 hashtags.
Open with a pattern interrupt: a specific surprising fact or a relatable pain point.
Never open with a generic aspirational statement.

CTA rules by content_pillar:
- product, social_proof → include a direct CTA with the placeholder {{link}} (e.g. "Get yours at {{link}}")
- educational, recipe, founder_bts → soft close only: "Save this", "Try it this week", or nothing. No {{link}}.

## Caption Rules — Facebook
2-3 sentences. Slightly more educational. Max 6 hashtags. No "Discover the power of..."
"""

_AD_COPY_RULES = """
## Ad Copy Rules
Headline: max 40 chars, benefit-led. No punctuation at end.
Primary text: max 125 chars, one specific claim, no fluff, no exclamation marks.
Return ONLY valid JSON with these exact keys: ad_headline, ad_primary_text"""

_VIDEO_RULES = """
## Kling Video Prompt Rules
Describe scene motion in layers: primary action → secondary details → camera move.
Specify pace: "slow motion" / "real-time". Max 80 words.
End with: "Product label remains sharp and fully readable throughout." """

_IMAGE_KEYS = "image_prompt, caption, alt_text"
_VIDEO_KEYS = "video_prompt, caption, alt_text"

VIDEO_TYPES = {"reels"}


def banned_in(*texts: str) -> list[str]:
    """Return brand banned phrases found (case-insensitive) across the given texts."""
    blob = " ".join(t for t in texts if t).lower()
    return [p for p in BANNED_PHRASES if p.lower() in blob]


def _build_system_prompt(post_type: str) -> tuple[str, list[str]]:
    """Return (system_prompt, expected_json_keys) based on post type."""
    if post_type in VIDEO_TYPES:
        prompt = _SYSTEM_BASE + _VIDEO_RULES + f"\n\nReturn ONLY valid JSON with these exact keys:\n{_VIDEO_KEYS}"
        keys = ["video_prompt", "caption", "alt_text"]
    else:
        prompt = _SYSTEM_BASE + f"\n\nReturn ONLY valid JSON with these exact keys:\n{_IMAGE_KEYS}"
        keys = ["image_prompt", "caption", "alt_text"]
    return prompt, keys


def run(week: str = None, post_id: str = None, dry_run: bool = False) -> None:
    db = get_db()
    query = "SELECT * FROM posts WHERE prompts_approved = 0 AND pipeline_status = 'draft'"
    params = []
    if week:
        query += " AND post_id LIKE ?"
        params.append(f"{week}%")
    if post_id:
        query += " AND post_id = ?"
        params.append(post_id)
    posts = db.execute(query, params).fetchall()

    if not posts:
        log.info("No posts needing prompts.")
        return

    log.info("Generating prompts for %d posts (max 2 concurrent)...", len(posts))
    client = anthropic.Anthropic()
    results, errors = {}, {}

    with ThreadPoolExecutor(max_workers=2) as ex:
        futures = {
            ex.submit(_generate_one, client, dict(p), dry_run): p["post_id"]
            for p in posts
        }
        for future in as_completed(futures):
            pid = futures[future]
            try:
                results[pid] = future.result()
                log.info("  ✓ %s", pid)
            except Exception as e:
                errors[pid] = str(e)
                log.error("  ✗ %s: %s", pid, e)

    with db:
        for pid, data in results.items():
            caption = data.get("caption")
            db.execute(
                """
                UPDATE posts SET
                    image_prompt=?, video_prompt=?, caption_instagram=?,
                    caption_facebook=?, alt_text=?, pipeline_status='prompts_ready',
                    updated_at=datetime('now')
                WHERE post_id=?
                """,
                (
                    data.get("image_prompt"),
                    data.get("video_prompt"),
                    caption,
                    caption,
                    data.get("alt_text"),
                    pid,
                ),
            )

    if errors:
        log.error("Failed posts: %s", errors)
    log.info("Done. Review prompts in dashboard → approve to proceed.")


def _generate_one(client: anthropic.Anthropic, post: dict, dry_run: bool) -> dict:
    with _SEMAPHORE:
        time.sleep(random.uniform(0.5, 1.5))
        system_prompt, expected_keys = _build_system_prompt(post.get("post_type", "feed_image"))

        if dry_run:
            return {k: "[DRY RUN]" for k in expected_keys}

        sku = SKUS[post["sku"]]
        price_suffix = f" (₹{sku['price_inr']})" if sku.get('price_inr') else ""
        user_msg = (
            f"Generate creative prompts for this content brief:\n\n"
            f"Post type: {post.get('post_type', 'feed_image')}\n"
            f"SKU: {sku['name']}{price_suffix}\n"
            f"Product facts: {json.dumps(sku['product_facts'])}\n"
            f"Differentiation: {sku['differentiation_angle']}\n"
            f"Content pillar: {post.get('content_pillar', 'product')}\n"
            f"Topic: {post['topic']}\n"
            f"Theme: {post.get('theme', '')}\n"
            f"Tone: {post.get('tone', 'warm_inspirational')}\n"
            f"Cultural moment: {post.get('cultural_moment', 'none')}\n"
            f"Reference notes: {post.get('reference_notes', 'None')}\n"
            f"Source image: {post['source_product_image']}"
        )

        relinted = False
        for attempt in range(3):
            response = client.messages.create(
                model=ANTHROPIC_MODEL,
                max_tokens=900,
                system=system_prompt,
                messages=[{"role": "user", "content": user_msg}],
            )
            text = response.content[0].text
            log.info(
                "COST anthropic prompt post=%s input_tokens=%d output_tokens=%d",
                post["post_id"],
                response.usage.input_tokens,
                response.usage.output_tokens,
            )
            try:
                # Strip markdown code fences if Claude wrapped the JSON
                stripped = text.strip()
                if stripped.startswith("```"):
                    stripped = stripped.split("\n", 1)[-1].rsplit("```", 1)[0].strip()
                data = json.loads(stripped)
            except json.JSONDecodeError:
                if attempt < 2:
                    log.warning("JSON parse failed for %s — retrying with stricter prompt", post["post_id"])
                    user_msg += "\n\nIMPORTANT: Return ONLY a JSON object. No markdown, no explanation."
                    continue
                raise ValueError(f"Claude returned non-JSON for {post['post_id']}: {text[:200]}")

            # Brand-safety lint: reject + regenerate once if a banned phrase slipped through.
            hits = banned_in(data.get("caption"), data.get("alt_text"))
            if hits and not relinted:
                relinted = True
                log.warning("banned phrase(s) %s in %s — regenerating", hits, post["post_id"])
                user_msg += (
                    "\n\nREJECTED: your last caption used banned phrases: "
                    f"{', '.join(hits)}. Rewrite WITHOUT any of these or close variants."
                )
                continue
            if hits:
                log.error("banned phrase(s) still present in %s after regenerate: %s",
                          post["post_id"], hits)
            return data

        raise RuntimeError("Unreachable")


def generate_ad_copy(post_id: str) -> dict:
    """Generate ad_headline + ad_primary_text for a single post on demand."""
    db = get_db()
    post = db.execute("SELECT * FROM posts WHERE post_id=?", (post_id,)).fetchone()
    if not post:
        raise ValueError(f"Post {post_id} not found.")

    sku = SKUS[post["sku"]]
    client = anthropic.Anthropic()
    system = _SYSTEM_BASE + _AD_COPY_RULES
    price_suffix = f" (₹{sku['price_inr']})" if sku.get('price_inr') else ""
    user_msg = (
        f"Write ad copy for this post:\n\n"
        f"SKU: {sku['name']}{price_suffix}\n"
        f"Product facts: {json.dumps(sku['product_facts'])}\n"
        f"Differentiation: {sku['differentiation_angle']}\n"
        f"Caption: {post.get('caption_instagram', '')}\n"
        f"Content pillar: {post.get('content_pillar', 'product')}"
    )

    response = client.messages.create(
        model=ANTHROPIC_MODEL,
        max_tokens=200,
        system=system,
        messages=[{"role": "user", "content": user_msg}],
    )
    log.info("COST anthropic ad_copy post=%s input=%d output=%d",
             post_id, response.usage.input_tokens, response.usage.output_tokens)

    text = response.content[0].text.strip()
    if text.startswith("```"):
        text = text.split("\n", 1)[-1].rsplit("```", 1)[0].strip()
    data = json.loads(text)

    with db:
        db.execute(
            "UPDATE posts SET ad_headline=?, ad_primary_text=?, updated_at=datetime('now') WHERE post_id=?",
            (data.get("ad_headline"), data.get("ad_primary_text"), post_id),
        )
    return data
