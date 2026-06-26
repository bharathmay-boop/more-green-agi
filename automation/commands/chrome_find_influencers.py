"""
Brave-based Instagram influencer discovery (Level A).

Flow:
  1. Hashtag explore page  -> intercept ALL JSON responses -> extract usernames
  2. Profile page          -> intercept web_profile_info  -> follower + engagement
  3. Filter (5k-50k, 3%+ eng) and save to DB

First run: opens Brave, you log in manually (browser waits silently).
Subsequent runs: pw_profile/ keeps the session alive automatically.
"""

import asyncio
import logging
import random
import re
from contextlib import asynccontextmanager
from pathlib import Path

from utils.db import get_db

log = logging.getLogger(__name__)

CHROME_PROFILE_DIR = Path(__file__).parent.parent / "pw_profile"
IG_BASE = "https://www.instagram.com"
OUR_HANDLE = "moregreen_in"

TARGET_HASHTAGS = [
    "healthyindianfood",
    "indianhealthyfood",
    "healthycookingindia",
    "indiannutritionist",
    "desihealth",
    "microgreens",
    "greenpowder",
    "superfoods",
    "healthyrecipesindia",
    "plantbasedindian",
    "indianfitnessfood",
    "healthyeatingindia",
    "nutritionistindia",
    "cleaneatingindia",
    "greensmoothie",
]

MIN_FOLLOWERS     = 5_000
MAX_FOLLOWERS     = 50_000
MIN_ENGAGEMENT    = 0.03
POSTS_TO_SAMPLE   = 12
MAX_NAMES_PER_TAG = 40   # max usernames collected per hashtag
MAX_PROFILES_PER_TAG = 20  # max profiles actually visited per hashtag

# Instagram system accounts to ignore
SYSTEM_ACCOUNTS = {
    OUR_HANDLE, "instagram", "instagramforbusiness", "creators",
    "shop", "explore",
}


# ---------------------------------------------------------------------------
# Public entry point
# ---------------------------------------------------------------------------

def run(hashtags: list = None, dry_run: bool = False,
        limit: int = None, total: int = None) -> None:
    asyncio.run(_main(hashtags=hashtags, dry_run=dry_run,
                      limit=limit, total=total))


# ---------------------------------------------------------------------------
# Main loop
# ---------------------------------------------------------------------------

async def _main(hashtags=None, dry_run=False, limit=None, total=None):
    tags          = hashtags or TARGET_HASHTAGS
    per_tag_limit = limit or MAX_PROFILES_PER_TAG
    global_cap    = total

    db = get_db()
    _ensure_table(db)

    async with _browser_context() as context:
        page = await context.new_page()
        await _apply_stealth(page)
        await _ensure_logged_in(page)

        total_new    = 0
        done         = False
        visited_run: set[str] = set()   # cross-hashtag dedup within this run

        for tag in tags:
            if done:
                break

            log.info("-- #%s ----------------------------------", tag)

            # Step 1: get usernames from hashtag explore page
            usernames = await _collect_usernames_from_hashtag(page, tag)
            log.info("  %d usernames collected", len(usernames))

            profiles_checked = 0
            for username in usernames:
                if profiles_checked >= per_tag_limit:
                    break
                if global_cap and total_new >= global_cap:
                    log.info("Target of %d reached -- stopping.", global_cap)
                    done = True
                    break
                if username.lower() in SYSTEM_ACCOUNTS:
                    continue
                if username in visited_run:
                    log.debug("  @%s already visited this run", username)
                    continue
                if _already_in_db(db, username):
                    log.debug("  @%s already in DB", username)
                    continue
                visited_run.add(username)

                # Step 2: visit profile page
                profile = await _scrape_profile(page, username)
                profiles_checked += 1

                if not profile:
                    await _delay(2, 4)
                    continue

                followers = profile.get("follower_count", 0)
                eng       = profile.get("engagement_rate", 0.0)

                if not (MIN_FOLLOWERS <= followers <= MAX_FOLLOWERS):
                    log.debug("  @%s followers=%s outside range",
                              username, f"{followers:,}")
                    await _delay(1, 3)
                    continue
                # Only enforce engagement filter when we have actual post data
                if eng > 0 and eng < MIN_ENGAGEMENT:
                    log.debug("  @%s eng=%.1f%% below 3%%", username, eng * 100)
                    await _delay(1, 3)
                    continue

                log.info("  + @%-28s  followers=%7s  eng=%5.1f%%",
                         username, f"{followers:,}", eng * 100)

                if not dry_run:
                    _save(db, profile, source_hashtag=tag)
                    total_new += 1

                await _delay(3, 7)

            await _delay(5, 12)

        await context.close()
        log.info("Session saved -> %s", CHROME_PROFILE_DIR)

    log.info("Done. New influencers saved: %d", total_new)
    if not dry_run and total_new:
        log.info("Next: python main.py update-tracker")


# ---------------------------------------------------------------------------
# Browser setup
# ---------------------------------------------------------------------------

@asynccontextmanager
async def _browser_context():
    from playwright.async_api import async_playwright
    CHROME_PROFILE_DIR.mkdir(parents=True, exist_ok=True)

    BRAVE_PATH = r"C:\Program Files\BraveSoftware\Brave-Browser\Application\brave.exe"

    common = {
        "user_data_dir": str(CHROME_PROFILE_DIR),
        "executable_path": BRAVE_PATH,
        "headless": False,
        "args": ["--disable-blink-features=AutomationControlled"],
        "viewport": {"width": 1280, "height": 900},
        "locale": "en-US",
        "timezone_id": "Asia/Kolkata",
        "extra_http_headers": {"Accept-Language": "en-US,en;q=0.9"},
    }

    async with async_playwright() as p:
        try:
            context = await p.chromium.launch_persistent_context(**common)
            log.info("Browser: Brave")
        except Exception as e:
            raise RuntimeError(f"Could not launch browser: {e}")

        try:
            yield context
        finally:
            pass


async def _apply_stealth(page) -> None:
    try:
        from playwright_stealth import stealth_async
        await stealth_async(page)
    except ImportError:
        pass


async def _ensure_logged_in(page) -> None:
    """
    Navigate to login page once and wait silently. No further navigation
    until the user completes login — prevents form resets.
    """
    try:
        await page.goto(
            f"{IG_BASE}/accounts/login/",
            wait_until="domcontentloaded",
            timeout=30_000,
        )
    except Exception:
        pass

    await asyncio.sleep(2)

    if "accounts/login" not in page.url:
        log.info("Session active -- skipping login")
        return

    print()
    print("=" * 60)
    print("  Log in to Instagram in the browser window.")
    print("  Take your time -- up to 5 minutes.")
    print("  DO NOT close the browser or navigate away.")
    print("=" * 60)
    print()

    for _ in range(100):
        await asyncio.sleep(3)
        try:
            url = page.url
        except Exception:
            continue
        if "instagram.com" in url and "accounts/login" not in url:
            log.info("Login confirmed -- continuing")
            return

    raise RuntimeError("Login not completed within 5 minutes. Run again.")


# ---------------------------------------------------------------------------
# Step 1: collect usernames from hashtag page
# ---------------------------------------------------------------------------

async def _collect_usernames_from_hashtag(page, hashtag: str) -> list[str]:
    """
    Visit the hashtag explore page and intercept all JSON responses.
    Recursively digs through any JSON structure looking for 'username' fields.
    This captures usernames from whichever internal API Instagram happens to use.
    """
    seen:      set[str]  = set()
    usernames: list[str] = []

    def _dig(obj, depth=0):
        if depth > 12 or not obj:
            return
        if isinstance(obj, dict):
            uname = obj.get("username", "")
            if uname and isinstance(uname, str) and uname not in seen:
                seen.add(uname)
                usernames.append(uname)
            for v in obj.values():
                _dig(v, depth + 1)
        elif isinstance(obj, list):
            for item in obj:
                _dig(item, depth + 1)

    async def on_response(response):
        ct = response.headers.get("content-type", "")
        if "json" not in ct:
            return
        try:
            data = await response.json()
            _dig(data)
        except Exception:
            pass

    page.on("response", on_response)
    try:
        await page.goto(
            f"{IG_BASE}/explore/tags/{hashtag}/",
            wait_until="domcontentloaded",
            timeout=30_000,
        )
        await asyncio.sleep(4)

        if await _is_rate_limited(page):
            log.warning("  Rate-limited on #%s -- pausing 60s", hashtag)
            await asyncio.sleep(60)
            return []

        for _ in range(5):
            await page.evaluate("window.scrollBy(0, window.innerHeight * 2)")
            await _delay(2, 3)

    except Exception as e:
        log.warning("  Error loading #%s: %s", hashtag, e)
    finally:
        page.remove_listener("response", on_response)

    # DOM fallback: extract profile hrefs Instagram renders in the post grid.
    # Catches usernames the JSON intercept misses when the page serves HTML-embedded data.
    if len(usernames) < MAX_NAMES_PER_TAG:
        try:
            dom_names = await page.evaluate(r"""
                () => {
                    const pat = /^\/([A-Za-z0-9._]{1,30})\/?$/;
                    const skip = new Set([
                        'explore','p','reel','reels','tv','stories','accounts',
                        'login','signup','direct','about','legal','privacy',
                        'safety','help','press','api','contact','blog',
                        'hashtag','share','fbid',
                    ]);
                    const found = new Set();
                    document.querySelectorAll('a[href]').forEach(a => {
                        try {
                            const path = new URL(a.href, location.origin).pathname;
                            const m = path.match(pat);
                            if (m && !skip.has(m[1].toLowerCase())) found.add(m[1]);
                        } catch(_) {}
                    });
                    return [...found];
                }
            """)
            for u in (dom_names or []):
                if u not in seen and u.lower() not in SYSTEM_ACCOUNTS:
                    seen.add(u)
                    usernames.append(u)
            if dom_names:
                log.debug("  DOM fallback added %d extra usernames", len(dom_names))
        except Exception as e:
            log.debug("  DOM fallback error: %s", e)

    result = [u for u in usernames if u.lower() not in SYSTEM_ACCOUNTS]
    return result[:MAX_NAMES_PER_TAG]


# ---------------------------------------------------------------------------
# Step 2: scrape profile page
# ---------------------------------------------------------------------------

async def _scrape_profile(page, username: str) -> dict | None:
    """
    Navigate to the profile page and extract follower count + engagement.

    Uses page.route() to intercept web_profile_info BEFORE the response body
    is consumed by Chrome — the only reliable way to read XHR bodies in
    Playwright with a persistent Chrome context.

    Falls back to DOM text (follower count only, eng=0) if route intercept misses.
    """
    import json as _json

    result: dict = {}
    profile_url_pattern = f"{IG_BASE}/api/v1/users/web_profile_info/**"

    async def handle_route(route):
        try:
            response = await route.fetch()
            body     = await response.body()
            data     = _json.loads(body)
            user     = data.get("data", {}).get("user") or {}
            if user:
                followers = user.get("edge_followed_by", {}).get("count", 0)
                edges     = user.get("edge_owner_to_timeline_media",
                                     {}).get("edges", [])
                eng       = _calc_engagement(edges, followers)
                last_url  = ""
                if edges:
                    sc = edges[0].get("node", {}).get("shortcode", "")
                    last_url = f"{IG_BASE}/p/{sc}/" if sc else ""
                result.update({
                    "username":        user.get("username", username),
                    "full_name":       user.get("full_name", ""),
                    "follower_count":  followers,
                    "engagement_rate": eng,
                    "post_url":        last_url,
                })
                log.debug("  @%s  API: followers=%s  eng=%.1f%%  posts=%d",
                          username, f"{followers:,}", eng * 100, len(edges))
            await route.fulfill(response=response, body=body)
        except Exception as e:
            log.debug("  route error @%s: %s", username, e)
            await route.continue_()

    await page.route(profile_url_pattern, handle_route)
    try:
        await page.goto(
            f"{IG_BASE}/{username}/",
            wait_until="domcontentloaded",
            timeout=20_000,
        )
        await asyncio.sleep(3)

        if await _is_rate_limited(page):
            log.warning("  Rate-limited @%s -- pausing 90s", username)
            await asyncio.sleep(90)
            return None

        # Fallback: DOM text for follower count (no engagement data)
        if not result:
            try:
                body_text = await page.inner_text("body")
                m = re.search(r"([\d,.]+[KkMm]?)\s+followers", body_text, re.I)
                if m:
                    fc = _parse_count(m.group(1))
                    result.update({
                        "username":        username,
                        "full_name":       "",
                        "follower_count":  fc,
                        "engagement_rate": 0.0,
                        "post_url":        f"{IG_BASE}/{username}/",
                    })
                    log.debug("  @%s  DOM fallback: followers=%s (no eng data)",
                              username, f"{fc:,}")
            except Exception:
                pass

        return result if result.get("username") else None

    except Exception as e:
        log.warning("  Network error @%s: %s", username, e)
        return None
    finally:
        await page.unroute(profile_url_pattern, handle_route)


def _parse_count(s: str) -> int:
    """Parse '12.5K', '1.2M', '8,500' etc into an integer."""
    s = s.replace(",", "").strip()
    if s[-1].lower() == "k":
        return int(float(s[:-1]) * 1_000)
    if s[-1].lower() == "m":
        return int(float(s[:-1]) * 1_000_000)
    try:
        return int(float(s))
    except ValueError:
        return 0


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _calc_engagement(edges: list, followers: int) -> float:
    if not edges or followers <= 0:
        return 0.0
    sample   = edges[:POSTS_TO_SAMPLE]
    likes    = sum(e["node"].get("edge_liked_by",         {}).get("count", 0) for e in sample)
    comments = sum(e["node"].get("edge_media_to_comment", {}).get("count", 0) for e in sample)
    return ((likes + comments) / len(sample)) / followers


async def _is_rate_limited(page) -> bool:
    try:
        body = (await page.inner_text("body")).lower()
        return "try again later" in body or "something went wrong" in body
    except Exception:
        return False


async def _delay(min_s: float, max_s: float) -> None:
    await asyncio.sleep(random.uniform(min_s, max_s))


# ---------------------------------------------------------------------------
# DB helpers
# ---------------------------------------------------------------------------

def _already_in_db(db, username: str) -> bool:
    return db.execute(
        "SELECT 1 FROM influencers WHERE handle=?", (username,)
    ).fetchone() is not None


def _save(db, profile: dict, source_hashtag: str) -> None:
    with db:
        db.execute(
            """INSERT OR IGNORE INTO influencers
               (handle, full_name, ig_user_id, follower_count, engagement_rate,
                source_hashtag, post_url, status, created_at, updated_at)
               VALUES (?, ?, '', ?, ?, ?, ?, 'discovered', datetime('now'), datetime('now'))""",
            (
                profile["username"],
                profile.get("full_name", ""),
                profile.get("follower_count", 0),
                profile.get("engagement_rate", 0.0),
                source_hashtag,
                profile.get("post_url", ""),
            ),
        )


def _ensure_table(db) -> None:
    db.execute("""
        CREATE TABLE IF NOT EXISTS influencers (
            handle                  TEXT PRIMARY KEY,
            full_name               TEXT,
            email                   TEXT,
            ig_user_id              TEXT,
            follower_count          INTEGER,
            engagement_rate         REAL,
            source_hashtag          TEXT,
            post_url                TEXT,
            like_count              INTEGER,
            comments_count          INTEGER,
            status                  TEXT DEFAULT 'discovered',
            notes                   TEXT,
            outreach_sent_at        TEXT,
            dm_sent_at              TEXT,
            reply_received_at       TEXT,
            collab_agreed           INTEGER DEFAULT 0,
            product_shipped         INTEGER DEFAULT 0,
            tracking_code           TEXT,
            template_used           TEXT,
            last_reply_preview      TEXT,
            last_message_at         TEXT,
            last_checked_at         TEXT,
            shipping_address        TEXT,
            product_dispatched_at   TEXT,
            agreed_post_date        TEXT,
            post_live_url           TEXT,
            dm_draft_generated_at   TEXT,
            created_at              TEXT DEFAULT (datetime('now')),
            updated_at              TEXT DEFAULT (datetime('now'))
        )
    """)
