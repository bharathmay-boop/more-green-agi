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

_SYSTEM_PROMPT = f"""You are a senior creative director for More Green — an Indian microgreens powder brand.

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

## Kling Video Prompt Rules
Describe scene motion in layers: primary action → secondary details → camera move.
Specify pace: "slow motion" / "real-time". Max 80 words.
End with: "Product label remains sharp and fully readable throughout."

## Caption Rules — Instagram
1-2 punchy lines + specific fact + CTA + max 8 hashtags.
Open with a pattern interrupt: a specific surprising fact or a relatable pain point.
Never open with a generic aspirational statement.
Placeholder for product URL: {{link}}

## Caption Rules — Facebook
2-3 sentences. Slightly more educational. Max 6 hashtags. No "Discover the power of..."

## Ad Copy Rules
Headline: max 40 chars, benefit-led. Primary text: max 125 chars, no fluff.

Return ONLY valid JSON with these exact keys:
image_prompt, video_prompt, caption_instagram, caption_facebook,
ad_headline, ad_primary_text, alt_text"""


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
            db.execute(
                """
                UPDATE posts SET
                    image_prompt=?, video_prompt=?, caption_instagram=?,
                    caption_facebook=?, ad_headline=?, ad_primary_text=?,
                    alt_text=?, pipeline_status='prompts_ready',
                    updated_at=datetime('now')
                WHERE post_id=?
                """,
                (
                    data.get("image_prompt"),
                    data.get("video_prompt"),
                    data.get("caption_instagram"),
                    data.get("caption_facebook"),
                    data.get("ad_headline"),
                    data.get("ad_primary_text"),
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
        if dry_run:
            stub = "[DRY RUN]"
            return {k: stub for k in [
                "image_prompt", "video_prompt", "caption_instagram",
                "caption_facebook", "ad_headline", "ad_primary_text", "alt_text",
            ]}

        sku = SKUS[post["sku"]]
        user_msg = (
            f"Generate creative prompts for this content brief:\n\n"
            f"SKU: {sku['name']} (₹{sku['price_inr']})\n"
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

        for attempt in range(2):
            response = client.messages.create(
                model=ANTHROPIC_MODEL,
                max_tokens=900,
                system=_SYSTEM_PROMPT,
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
                return json.loads(text)
            except json.JSONDecodeError:
                if attempt == 0:
                    log.warning("JSON parse failed for %s — retrying with stricter prompt", post["post_id"])
                    user_msg += "\n\nIMPORTANT: Return ONLY a JSON object. No markdown, no explanation."
                else:
                    raise ValueError(f"Claude returned non-JSON for {post['post_id']}: {text[:200]}")

        raise RuntimeError("Unreachable")
