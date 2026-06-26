# More Green AGI — Complete Automation Plan
### Social Media Creatives, Organic Posting & Meta Ads for a Non-Technical Solo Founder

> Three independent audits (UX/UI · Software Architecture · Marketing Strategy) were run in parallel to produce this plan. Every recommendation below is the synthesised output of those audits applied to the original design.

---

## Table of Contents

1. [The Guiding Principle](#1-the-guiding-principle)
2. [Validated Tool Stack](#2-validated-tool-stack)
3. [System Architecture](#3-system-architecture)
4. [Directory Structure](#4-directory-structure)
5. [The Master Strategy Interface](#5-the-master-strategy-interface)
6. [Database Design (SQLite)](#6-database-design-sqlite)
7. [Full `config.py`](#7-full-configpy)
8. [Complete CLI Reference](#8-complete-cli-reference)
9. [Script Implementations](#9-script-implementations)
10. [The Streamlit Dashboard](#10-the-streamlit-dashboard)
11. [Data Flow & Dependency Map](#11-data-flow--dependency-map)
12. [Error Handling Strategy](#12-error-handling-strategy)
13. [Security & Secrets Management](#13-security--secrets-management)
14. [Structured Logging](#14-structured-logging)
15. [Content Strategy Framework](#15-content-strategy-framework)
16. [Ad Campaign Phase Structure](#16-ad-campaign-phase-structure)
17. [Optimisation Logic](#17-optimisation-logic)
18. [Customer Journey Closure](#18-customer-journey-closure)
19. [Platform Expansion Roadmap](#19-platform-expansion-roadmap)
20. [Cultural Calendar](#20-cultural-calendar)
21. [Onboarding Checklist](#21-onboarding-checklist)
22. [Verification Commands](#22-verification-commands)
23. [Phase Roadmap](#23-phase-roadmap)
24. [Parallel Agent Architecture & Token Budget](#24-parallel-agent-architecture--token-budget)
25. [Monthly Cost Summary](#25-monthly-cost-summary)
26. [Critical Pre-Launch Checklist](#26-critical-pre-launch-checklist)
27. [Full `requirements.txt`](#27-full-requirementstxt)
28. [`.env.example`](#28-envexample)

---

## 1. The Guiding Principle

**The product photo is always the input, never the output.**

AI generates the *world around* the product — the scene, the light, the background, the motion. The label, pouch design, lid, and font are untouched in every single output. This one constraint separates professional brand work from AI slop and is enforced at the tool selection level (FLUX Kontext and Kling both accept a reference image as an anchor).

**The second principle: the system works for the founder, not the other way around.**

Every interface element is designed for a non-technical solo founder operating from their phone during a morning commute. No YAML editing. No CLI commands. One browser tab, two approval buttons, and a weekly 15-minute review session.

---

## 2. Validated Tool Stack

### Tool Decisions (Post-Audit)

| Original | Problem | Replacement | Reason |
|---|---|---|---|
| Nano Banana text-to-image | Generates product from scratch; label hallucination | **FLUX Kontext Pro** (fal.ai, $0.04/img) | img2img: real photo in, scene out, label intact |
| Nano Banana 2 | Still text-only for product | **Nano Banana 2** for backgrounds/props only | Generate scene elements, not the product |
| Higgsfield AI direct | Subscription + credit expiry complexity | **Kling 3.0** via fal.ai ($0.03–0.05/sec) | img2video with 3D spatio-temporal consistency; product identity preserved frame-to-frame |
| `meta-ads-cli` pip package | v0.1.0, Beta, April 2026 release | **`facebook-business`** v22.0 | Official Meta SDK, GA, Marketing API v22 |
| 8 separate scripts | Hard to orchestrate, no shared state | **Unified Click CLI + Streamlit dashboard** | CLI for cron/dev; dashboard for founder |
| YAML as primary input | Syntax errors, no validation, no mobile access | **Google Sheets → auto-generated YAML** | Familiar UX, dropdowns, mobile, undo |
| YAML as state store | Race conditions, crash corruption | **SQLite** (Python built-in, no install) | Atomic transactions, concurrent-safe, queryable |

### Full Stack

```
Input Interface:    Google Sheets (founder edits) → sync → SQLite (pipeline state)
Image Generation:   FLUX Kontext Pro via fal.ai     ($0.04/image, img2img)
Background Gen:     Nano Banana 2 via Gemini API    ($0.045/image, for scene elements)
Video Generation:   Kling 3.0 via fal.ai            ($0.18/5s video, img2video)
Prompt Generation:  Claude Sonnet 4.6 via Anthropic ($0.017/post brief)
Media Hosting:      Cloudinary free tier            (25GB storage, 25GB/month CDN)
Organic Posting:    Meta Graph API v22              (free)
Paid Ads:           facebook-business SDK v22.0     (free)
Dashboard:          Streamlit Community Cloud       (free, mobile-accessible)
Notifications:      SendGrid (email) / Twilio       (WhatsApp)
Logging:            Python logging → logs/          (local + cron-safe)
```

---

## 3. System Architecture

### The Founder's Daily Interaction

```
Sunday Evening (15 min total):

1. Open Google Sheets content calendar
   → Fill in next week's rows: date, SKU, topic, theme, source image path
   → Takes ~5 minutes

2. Open dashboard.moregreen.app (Streamlit Cloud)
   → Click "Sync from Sheets + Generate Prompts"
   → Claude generates image prompts, video prompts, captions for all posts
   → Takes 10–15 seconds (parallel agents)

3. Review prompts in dashboard (one post at a time, phone-friendly)
   → Edit any caption directly in the UI
   → Click "Approve & Generate Creatives"
   → FLUX Kontext + Kling run in background (~4 minutes total)
   → Dashboard sends WhatsApp/email when done

4. Later that day: approve creatives from phone
   → See Instagram-frame preview: image + caption as it will appear
   → Tap Approve or Regenerate per post
   → Posts go live automatically at scheduled times via cron
```

No YAML editing. No terminal. No `pip install`.

### The Full Pipeline

```
Google Sheets (founder input)
       ↓ [python main.py sync-sheets]
   SQLite DB (pipeline state)
       ↓ [python main.py generate-prompts --week W24]
   Claude API → prompts written to DB
       ↓ [founder approves in dashboard]
   SQLite: prompts_approved = 1
       ↓ [python main.py generate-creatives --week W24]
   FLUX Kontext → images saved to creatives/images/
   Kling 3.0   → videos saved to creatives/videos/
       ↓ [python main.py upload-media --week W24]
   Cloudinary  → public URLs written to DB
       ↓ [founder approves creatives in dashboard]
   SQLite: creatives_approved = 1
       ↓ [cron: python main.py post-due --time now]
   Meta Graph API → Instagram + Facebook posts live
       ↓ [cron: python main.py create-ads --week W24]
   facebook-business SDK → campaigns created (PAUSED)
   founder activates manually in Ads Manager
       ↓ [cron: python main.py monitor-ads, tune-ads]
   Insights → pause losers, scale winners
```

---

## 4. Directory Structure

```
automation/
├── main.py                    # Click CLI entrypoint
├── .env                       # secrets (gitignored, never committed)
├── .env.example               # template committed to repo
├── .gitignore                 # includes .env, *.db, logs/
├── requirements.txt           # pinned exact versions (generated by pip-compile)
├── requirements.in            # human-maintained loose constraints
├── config.py                  # loads config/brand.yaml, exposes typed constants
│
├── config/
│   ├── brand.yaml             # SKU data, brand voice, product facts (human-editable)
│   ├── cultural_calendar.yaml # Indian festival/seasonal content angles
│   └── hashtags.yaml          # tiered hashtag database by SKU + pillar
│
├── strategy/
│   └── calendar.yaml          # auto-generated from Google Sheets; do not edit manually
│
├── db/
│   └── pipeline.db            # SQLite — all pipeline state lives here
│
├── commands/
│   ├── __init__.py
│   ├── sync_sheets.py         # Google Sheets → SQLite sync
│   ├── generate_prompts.py    # Claude API → structured prompts → DB
│   ├── generate_images.py     # FLUX Kontext (img2img)
│   ├── generate_videos.py     # Kling 3.0 (img2video)
│   ├── upload_media.py        # Cloudinary uploader
│   ├── post_organic.py        # Meta Graph API (Instagram + Facebook)
│   ├── post_youtube.py        # YouTube Shorts cross-posting (Week 4)
│   ├── create_ads.py          # facebook-business SDK
│   ├── monitor_ads.py         # insights fetcher
│   ├── tune_ads.py            # budget optimiser (multi-signal)
│   ├── check_credentials.py   # validates all 5 service credentials
│   ├── onboard.py             # interactive first-time setup wizard
│   └── _dashboard_app.py      # Streamlit UI (run via `streamlit run`)
│
├── utils/
│   ├── __init__.py
│   ├── db.py                  # SQLite connection + schema helpers
│   ├── retry.py               # tenacity wrappers with API-error-body detection
│   ├── meta_auth.py           # Meta API session + token validator
│   ├── logging_config.py      # structured logging setup
│   ├── guards.py              # pipeline state enforcement decorators
│   ├── secrets.py             # OS keyring + .env fallback
│   └── notifications.py      # SendGrid email + Twilio WhatsApp
│
├── Files/                     # your existing product photos (unchanged)
│   ├── sunflower/
│   ├── blueberry/
│   ├── moringa/
│   └── wheatgrass/
│
├── creatives/
│   ├── images/
│   ├── videos/
│   └── pending_video_jobs.json  # fal.ai job IDs persisted before polling
│
├── logs/
│   └── moregreen.log          # structured log, rotated daily
│
└── ads_log.json               # ad campaign IDs (idempotency-keyed)
```

---

## 5. The Master Strategy Interface

### Google Sheets as Input (Not YAML)

The founder never edits YAML. The Google Sheets template is the content calendar. YAML is generated from it and treated as a build artifact.

**Sheet columns (one row = one post):**

| Column | Type | Values |
|---|---|---|
| Post ID | Auto | `W24_MON_01` |
| Scheduled Date | Date | `2026-06-09` |
| Scheduled Time | Time | `09:00` |
| Platform | Dropdown | Instagram / Facebook / Both / YouTube |
| Post Type | Dropdown | feed_image / reels / carousel / story |
| Content Pillar | Dropdown | educational / recipe / product / social_proof / founder_bts |
| SKU | Dropdown | sunflower / blueberry / moringa / wheatgrass |
| Topic | Text | "Monday motivation — energy for the week" |
| Theme | Text | "Ayurvedic wellness, busy Indian professional, morning ritual" |
| Tone | Dropdown | warm_inspirational / educational / humorous / urgent |
| Cultural Moment | Dropdown | none / diwali / navratri / monsoon / newyear / holi / summer |
| Source Product Image | Text | `Files/moringa/product_front.jpg` |
| Source Lifestyle Image | Text | `Files/moringa/lifestyle_bowl.jpg` |
| Reference Notes | Text | "Want earthy Ayurvedic aesthetic, terracotta and brass" |
| Status | Auto | draft / prompts_ready / approved / scheduled / posted |
| Output URL | Auto | populated after posting |

**`commands/sync_sheets.py`** pulls the sheet via `gspread`, validates each row against a schema, and writes to SQLite. Invalid rows are flagged with a comment in the sheet cell, not silently dropped.

```python
# commands/sync_sheets.py (key logic)
import gspread, sqlite3
from utils.db import get_db

REQUIRED_COLUMNS = ["scheduled_date", "sku", "topic", "source_product_image"]

def run():
    gc = gspread.service_account(filename="service_account.json")
    sheet = gc.open("More Green Content Calendar").sheet1
    rows = sheet.get_all_records()

    db = get_db()
    validated, skipped = 0, 0

    for row in rows:
        missing = [c for c in REQUIRED_COLUMNS if not row.get(c)]
        if missing:
            log.warning("Skipping row %s — missing: %s", row.get("post_id"), missing)
            skipped += 1
            continue

        db.execute("""
            INSERT OR IGNORE INTO posts (post_id, scheduled_at, platform, post_type,
                content_pillar, sku, topic, theme, tone, cultural_moment,
                source_product_image, source_lifestyle_image, reference_notes, status)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'draft')
        """, (row["post_id"], ...))
        validated += 1

    db.commit()
    log.info("Synced %d posts (%d skipped) from Google Sheets", validated, skipped)
```

---

## 6. Database Design (SQLite)

All pipeline state lives in SQLite. The founder's input (Google Sheets) is the human interface. YAML is generated for legacy compatibility. SQLite is the authoritative store.

```sql
-- db/schema.sql

CREATE TABLE IF NOT EXISTS posts (
    post_id             TEXT PRIMARY KEY,
    scheduled_at        TEXT NOT NULL,              -- ISO 8601
    platform            TEXT NOT NULL,              -- instagram|facebook|both|youtube
    post_type           TEXT NOT NULL,              -- feed_image|reels|carousel|story
    content_pillar      TEXT,                       -- educational|recipe|product|social_proof|founder_bts
    sku                 TEXT NOT NULL,
    topic               TEXT NOT NULL,
    theme               TEXT,
    tone                TEXT,
    cultural_moment     TEXT DEFAULT 'none',
    source_product_image TEXT NOT NULL,
    source_lifestyle_image TEXT,
    reference_notes     TEXT,

    -- Generated prompts (written by generate-prompts)
    image_prompt        TEXT,
    video_prompt        TEXT,
    caption_instagram   TEXT,
    caption_facebook    TEXT,
    ad_headline         TEXT,
    ad_primary_text     TEXT,
    alt_text            TEXT,

    -- Approval gates (2, not 3 — UX audit recommendation)
    prompts_approved    INTEGER DEFAULT 0,          -- 0=no, 1=yes
    prompts_approved_at TEXT,
    creatives_approved  INTEGER DEFAULT 0,
    creatives_approved_at TEXT,
    on_hold             INTEGER DEFAULT 0,          -- HOLD state

    -- Generated outputs
    image_paths         TEXT,                       -- JSON array of local paths
    video_path          TEXT,
    cloudinary_urls     TEXT,                       -- JSON array of public URLs
    cloudinary_public_ids TEXT,                     -- JSON array for re-upload recovery

    -- Post results
    ig_post_id          TEXT,
    fb_post_id          TEXT,
    youtube_video_id    TEXT,
    meta_scheduled_post_id TEXT,                    -- for edit/cancel support

    -- Error tracking (UX audit: no silent failures)
    pipeline_status     TEXT DEFAULT 'draft',
    last_error          TEXT,
    last_error_at       TEXT,

    created_at          TEXT DEFAULT (datetime('now')),
    updated_at          TEXT DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS ad_campaigns (
    campaign_key        TEXT PRIMARY KEY,           -- "{sku}_{campaign_date}" idempotency key
    sku                 TEXT NOT NULL,
    campaign_date       TEXT NOT NULL,
    campaign_phase      INTEGER NOT NULL,           -- 1=traffic, 2=atc, 3=purchase
    campaign_id         TEXT,
    adset_id            TEXT,
    creative_id         TEXT,
    ad_id               TEXT,
    status              TEXT DEFAULT 'PAUSED',
    daily_budget_inr    INTEGER,
    created_at          TEXT DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS insights_cache (
    ad_id               TEXT NOT NULL,
    fetched_date        TEXT NOT NULL,
    impressions         INTEGER,
    clicks              INTEGER,
    ctr                 REAL,
    spend_inr           REAL,
    frequency           REAL,
    cost_per_atc_inr    REAL,
    roas                REAL,
    action_taken        TEXT,                       -- none|paused|scaled|refreshed
    PRIMARY KEY (ad_id, fetched_date)
);
```

**`utils/db.py`** — atomic writes via WAL mode:

```python
# utils/db.py
import sqlite3
from pathlib import Path
from config import PROJECT_ROOT

DB_PATH = PROJECT_ROOT / "db" / "pipeline.db"

def get_db() -> sqlite3.Connection:
    DB_PATH.parent.mkdir(exist_ok=True)
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")     # concurrent-safe
    conn.execute("PRAGMA foreign_keys=ON")
    _ensure_schema(conn)
    return conn

def _ensure_schema(conn):
    schema = (PROJECT_ROOT / "db" / "schema.sql").read_text()
    conn.executescript(schema)
    conn.commit()
```

---

## 7. Full `config.py`

```python
# config.py — loads brand.yaml, exposes typed constants
import yaml
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.resolve()

def _load(filename: str) -> dict:
    return yaml.safe_load((PROJECT_ROOT / "config" / filename).read_text(encoding="utf-8"))

_brand   = _load("brand.yaml")
_hashtags = _load("hashtags.yaml")
_calendar = _load("cultural_calendar.yaml")

# ── Paths ────────────────────────────────────────────────────────────────────
STRATEGY_DIR   = PROJECT_ROOT / "strategy"
CREATIVES_DIR  = PROJECT_ROOT / "creatives"
CALENDAR_PATH  = STRATEGY_DIR / "calendar.yaml"
DB_PATH        = PROJECT_ROOT / "db" / "pipeline.db"
LOG_PATH       = PROJECT_ROOT / "logs" / "moregreen.log"

# ── Brand ────────────────────────────────────────────────────────────────────
BRAND_NAME     = _brand["brand"]["name"]
BRAND_WEBSITE  = _brand["brand"]["website"]
BRAND_HANDLE   = _brand["brand"]["instagram_handle"]
BRAND_VOICE    = _brand["brand"]["voice_brief"]
BANNED_PHRASES = _brand["brand"]["banned_phrases"]

# ── SKUs ─────────────────────────────────────────────────────────────────────
SKUS = {sku["id"]: sku for sku in _brand["skus"]}

# ── Hashtags (by SKU + pillar) ────────────────────────────────────────────────
HASHTAGS = _hashtags   # dict keyed by sku and pillar

# ── Cultural Calendar ────────────────────────────────────────────────────────
CULTURAL_CALENDAR = _calendar["events"]

# ── Image / Video Generation ─────────────────────────────────────────────────
IMAGE_VARIANTS_PER_POST   = 3
IMAGE_ASPECT_RATIO_FEED   = "1:1"
IMAGE_ASPECT_RATIO_REELS  = "9:16"
VIDEO_DURATION_SECONDS    = 5
VIDEO_RESOLUTION          = "720p"

# ── Meta Ads ─────────────────────────────────────────────────────────────────
META_GRAPH_VERSION        = "v22.0"
META_GRAPH_BASE           = f"https://graph.facebook.com/{META_GRAPH_VERSION}"
META_CURRENCY             = "INR"
META_CAMPAIGN_PHASE       = 1   # 1=traffic, 2=atc, 3=purchase — change per phase

META_TARGETING_LAUNCH = {        # Phase 1: Bengaluru + Pune, lower CPM
    "geo_locations": {
        "cities": [
            {"key": "2264456", "name": "Bengaluru"},
            {"key": "2271168", "name": "Pune"},
        ]
    },
    "age_min": 24, "age_max": 42,
    "publisher_platforms": ["facebook", "instagram"],
    "facebook_positions": ["feed", "reels"],
    "instagram_positions": ["stream", "reels"],
}

META_TARGETING_GROWTH = {        # Phase 2-3: all 5 metros split by age
    "geo_locations": {
        "countries": ["IN"],
        "cities": [
            {"key": "2295424", "name": "Mumbai"},
            {"key": "2264456", "name": "Bengaluru"},
            {"key": "2276893", "name": "Delhi"},
            {"key": "2281955", "name": "Hyderabad"},
            {"key": "2271168", "name": "Pune"},
        ]
    },
    "age_min": 22, "age_max": 45,
}

META_BUDGET_PHASE = {
    1: 500,    # ₹500/day total, 1 campaign
    2: 700,    # ₹500 acquisition + ₹200 retargeting
    3: 1500,   # ₹1000 LAL + ₹500 retargeting
}

META_CAMPAIGN_OBJECTIVE_PHASE = {
    1: "OUTCOME_TRAFFIC",
    2: "OUTCOME_CONVERSIONS",  # optimise for AddToCart
    3: "OUTCOME_SALES",        # optimise for Purchase
}

# ── Optimisation Thresholds (multi-signal, format-aware) ─────────────────────
LEARNING_PHASE_DAYS       = 14
MIN_SPEND_INR_BEFORE_JUDGE = 2000    # ₹2,000 minimum (not ₹200)
PAUSE_CTR_FEED_BELOW      = 0.008   # 0.8% — benchmark for Indian feed ads
PAUSE_CTR_REELS_BELOW     = 0.012   # 1.2% — benchmark for Indian Reels
SCALE_ROAS_ABOVE_WARM     = 3.0     # scale warm audience if ROAS > 3x
SCALE_ROAS_ABOVE_COLD     = 2.0     # scale cold LAL if ROAS > 2x
SCALE_BUDGET_MULTIPLIER   = 1.20    # +20%
CREATIVE_REFRESH_FREQUENCY = 3.5    # flag creative fatigue at frequency > 3.5
MAX_CPM_INR               = 400     # pause ad set if CPM > ₹400

# ── API Versions and Endpoint Anchors ────────────────────────────────────────
FAL_FLUX_KONTEXT_ENDPOINT    = "fal-ai/flux-pro/kontext"
FAL_KLING_ENDPOINT           = "fal-ai/kling-video/v2.1/standard/image-to-video"
FAL_NANO_BANANA_ENDPOINT     = "fal-ai/flux/dev"      # for backgrounds only
ANTHROPIC_MODEL              = "claude-sonnet-4-6"
CLOUDINARY_FOLDER            = "more-green"

# ── Credential Rotation Notes (for operator reference) ───────────────────────
CREDENTIAL_NOTES = {
    "META_SYSTEM_USER_TOKEN": "No expiry. Page access can be silently revoked. Check monthly.",
    "FAL_KEY":                "No expiry. Rotate if anomalous usage detected.",
    "ANTHROPIC_API_KEY":      "No expiry. Rotate immediately if leaked.",
    "GOOGLE_API_KEY":         "No expiry. Quota resets daily.",
    "CLOUDINARY":             "No expiry. Tied to account. Never delete account.",
}
```

**`config/brand.yaml`** (human-editable, no Python required):

```yaml
brand:
  name: "More Green"
  website: "https://moregreen.in"
  instagram_handle: "@moregreen.in"
  voice_brief: >
    More Green sounds like a knowledgeable friend who happens to know a lot about
    nutrition — warm, specific, never preachy. We never say "superfood." We never
    say "morning ritual." We never use the word "journey." We cite real numbers
    ("40x more nutrients than mature plants") not vague claims ("packed with
    goodness"). We acknowledge scepticism rather than ignoring it. We are proud
    of being Indian without leaning on nostalgia clichés.
  banned_phrases:
    - "morning ritual"
    - "superfood"
    - "packed with goodness"
    - "your wellness journey"
    - "unlock your potential"
    - "dadi swore by"          # cliché — earn the cultural reference, don't shortcut it
    - "transform your life"
    - "natural glow"           # too generic

skus:
  - id: sunflower
    name: "Sunflower Microgreens Powder"
    price_inr: 499
    shopify_url: "https://moregreen.in/products/sunflower"
    product_facts:
      - "Contains up to 40x more Vitamin E than mature sunflower seeds"
      - "Rich in zinc — 1 tsp = 15% daily zinc requirement"
      - "Cold-pressed, no heat treatment, nutrients intact"
    differentiation_angle: >
      Sunflower microgreens are harvested at peak nutrient density — 7 days after
      germination, when the plant has concentrated everything it needs to grow into
      a full plant. Mature sunflower seeds don't come close.
    image_prompt_base: >
      The More Green Sunflower pouch sits on [SCENE]. Keep the product pouch,
      label typography, and design completely unchanged. Add [LIGHTING]. [CAMERA].
    video_prompt_base: >
      The More Green Sunflower pouch is visible throughout. [ACTION]. Product
      label remains sharp and fully readable throughout. [MOOD].

  - id: blueberry
    name: "Blueberry Microgreens Powder"
    price_inr: 549
    shopify_url: "https://moregreen.in/products/blueberry"
    product_facts:
      - "Blueberry microgreens contain 4-6x more anthocyanins than ripe blueberries"
      - "One of the few Indian powders using microgreens, not dried fruit"
      - "Purple pigment = pterostilbene, a compound linked to cognitive function"
    differentiation_angle: >
      There is no other blueberry microgreens powder widely available in India.
      Dried blueberry powder is common. This is categorically different — the
      plant at peak anthocyanin production, not the fruit after harvest decline.
    image_prompt_base: >
      The More Green Blueberry pouch sits on [SCENE]. Keep the product pouch,
      label typography, and design completely unchanged. Add [LIGHTING]. [CAMERA].
    video_prompt_base: >
      The More Green Blueberry pouch is visible throughout. [ACTION]. Product
      label remains sharp and fully readable throughout. [MOOD].

  - id: moringa
    name: "Moringa Microgreens Powder"
    price_inr: 449
    shopify_url: "https://moregreen.in/products/moringa"
    product_facts:
      - "Moringa microgreens: 3x more iron than mature moringa leaves"
      - "More absorbable iron than spinach — no oxalate interference"
      - "Suitable for Navratri fasting — pure plant, no additives"
    differentiation_angle: >
      Everyone knows moringa. Very few people know that moringa at the microgreens
      stage has 3x more nutrients than the mature leaf that most powders use.
      More Green is not a moringa powder. It is moringa at its peak.
    image_prompt_base: >
      The More Green Moringa pouch sits on [SCENE]. Keep the product pouch,
      label typography, and design completely unchanged. Add [LIGHTING]. [CAMERA].
    video_prompt_base: >
      The More Green Moringa pouch is visible throughout. [ACTION]. Product
      label remains sharp and fully readable throughout. [MOOD].

  - id: wheatgrass
    name: "Wheatgrass Microgreens Powder"
    price_inr: 399
    shopify_url: "https://moregreen.in/products/wheatgrass"
    product_facts:
      - "More chlorophyll per gram than any other green food"
      - "70% chlorophyll by dry weight — pure plant energy"
      - "Lowest price in the More Green range — best entry product"
    differentiation_angle: >
      Wheatgrass shots cost ₹150-200 at a juice bar. One pack of More Green
      Wheatgrass Powder makes 30 shots at ₹13 each. Same chlorophyll, no queue,
      no commute to Bandra.
    image_prompt_base: >
      The More Green Wheatgrass pouch sits on [SCENE]. Keep the product pouch,
      label typography, and design completely unchanged. Add [LIGHTING]. [CAMERA].
    video_prompt_base: >
      The More Green Wheatgrass pouch is visible throughout. [ACTION]. Product
      label remains sharp and fully readable throughout. [MOOD].
```

---

## 8. Complete CLI Reference

```
python main.py --help

Usage: main.py [OPTIONS] COMMAND [ARGS]...

Options:
  --dry-run    Log actions without API calls or spend
  --verbose    Debug-level logging
  --help       Show this message and exit

Commands:
  check              Validate all 5 service credentials
  onboard            Interactive first-time setup wizard
  sync-sheets        Pull Google Sheets → SQLite
  generate-prompts   Claude API → prompts per post
  approve-prompts    Mark prompts approved (CLI shortcut; dashboard preferred)
  generate-creatives FLUX Kontext (images) + Kling 3.0 (videos)
  upload-media       Upload local creatives to Cloudinary
  post-organic       Post to Instagram + Facebook (requires creatives_approved)
  post-youtube       Cross-post Reels to YouTube Shorts
  create-ads         Create Meta ad campaign → PAUSED (requires creatives_approved)
  monitor-ads        Fetch and display ad performance insights
  tune-ads           Apply pause/scale/refresh rules (--apply to execute)
  resume-video-jobs  Poll pending fal.ai video jobs from pending_video_jobs.json
  verify-media       Check all Cloudinary URLs return 200
  new-week           Scaffold a week's template in Google Sheets
  dashboard          Launch Streamlit UI (or visit dashboard URL on Cloud)
  export-report      Weekly performance PDF/markdown report

Options per command (examples):
  --week 2026-W24      Target a specific ISO week
  --post W24_MON_01    Target a specific post ID
  --sku moringa        Run for one SKU only
  --apply              Actually apply mutations (tune-ads default is dry-run)
  --platform both      instagram|facebook|both|youtube
```

---

## 9. Script Implementations

### `utils/guards.py` — Approval State Enforcement

```python
# utils/guards.py
import functools, click
from utils.db import get_db

def require_approval(field: str, friendly_name: str):
    """Decorator: abort command if any target post lacks the required approval."""
    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            db = get_db()
            post_id = kwargs.get("post_id") or kwargs.get("post")
            query = f"SELECT post_id FROM posts WHERE {field} = 0 AND on_hold = 0"
            if post_id:
                query += f" AND post_id = '{post_id}'"
            blocked = [r["post_id"] for r in db.execute(query).fetchall()]
            if blocked:
                raise click.ClickException(
                    f"Cannot proceed — {friendly_name} not approved for: {blocked}\n"
                    f"Approve in the dashboard or run: python main.py approve-prompts --all"
                )
            return func(*args, **kwargs)
        return wrapper
    return decorator
```

### `utils/retry.py` — Retry with Body-Error Detection

```python
# utils/retry.py
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type
import requests, logging

log = logging.getLogger(__name__)

class APIBodyError(Exception):
    """HTTP 200 but error payload in body."""

@retry(
    retry=retry_if_exception_type((APIBodyError, requests.ConnectionError,
                                   requests.Timeout, requests.HTTPError)),
    wait=wait_exponential(multiplier=1, min=3, max=45),
    stop=stop_after_attempt(4),
    reraise=True,
)
def checked_post(url: str, **kwargs) -> dict:
    """POST that raises on both HTTP errors and application-level error bodies."""
    r = requests.post(url, **kwargs, timeout=30)
    r.raise_for_status()
    body = r.json() if "application/json" in r.headers.get("content-type", "") else {}
    if body.get("status") in ("FAILED", "error") or body.get("error"):
        raise APIBodyError(f"API returned error body: {body}")
    return body

def check_meta_rate_limit(response: requests.Response) -> None:
    """Parse X-App-Usage header and sleep if approaching limit."""
    import json, time
    usage = response.headers.get("X-App-Usage")
    if usage:
        data = json.loads(usage)
        pct = data.get("call_count", 0)
        if pct > 75:
            sleep_s = (100 - pct)
            log.warning("Meta rate limit at %d%% — sleeping %ds", pct, sleep_s)
            time.sleep(sleep_s)
```

### `commands/generate_prompts.py`

```python
# commands/generate_prompts.py
import anthropic, json, threading, time, random, logging
from concurrent.futures import ThreadPoolExecutor, as_completed
from utils.db import get_db
from config import ANTHROPIC_MODEL, SKUS, BRAND_VOICE, BANNED_PHRASES, PROJECT_ROOT

log = logging.getLogger(__name__)

_SEMAPHORE = threading.Semaphore(2)   # max 2 simultaneous Claude calls

SYSTEM_PROMPT = f"""You are a senior creative director for More Green — an Indian microgreens powder brand.

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

def run(week: str = None, post_id: str = None, dry_run: bool = False):
    db = get_db()
    query = "SELECT * FROM posts WHERE prompts_approved = 0 AND status = 'draft'"
    if week:
        query += f" AND post_id LIKE '{week}%'"
    if post_id:
        query += f" AND post_id = '{post_id}'"
    posts = db.execute(query).fetchall()

    if not posts:
        log.info("No posts needing prompts.")
        return

    log.info("Generating prompts for %d posts (parallel, max 2 concurrent)...", len(posts))
    client = anthropic.Anthropic()
    results, errors = {}, {}

    with ThreadPoolExecutor(max_workers=2) as ex:
        futures = {ex.submit(_generate_one, client, dict(p), dry_run): p["post_id"]
                   for p in posts}
        for future in as_completed(futures):
            pid = futures[future]
            try:
                results[pid] = future.result()
                log.info("  ✓ %s", pid)
            except Exception as e:
                errors[pid] = str(e)
                log.error("  ✗ %s: %s", pid, e)

    # Single write after all threads complete (no race condition)
    with db:
        for pid, data in results.items():
            db.execute("""
                UPDATE posts SET
                  image_prompt=?, video_prompt=?, caption_instagram=?,
                  caption_facebook=?, ad_headline=?, ad_primary_text=?,
                  alt_text=?, pipeline_status='prompts_ready', updated_at=datetime('now')
                WHERE post_id=?
            """, (data.get("image_prompt"), data.get("video_prompt"),
                  data.get("caption_instagram"), data.get("caption_facebook"),
                  data.get("ad_headline"), data.get("ad_primary_text"),
                  data.get("alt_text"), pid))

    if errors:
        log.error("Failed posts: %s", errors)
    log.info("Done. Review prompts at dashboard → approve to proceed.")

def _generate_one(client, post: dict, dry_run: bool) -> dict:
    with _SEMAPHORE:
        time.sleep(random.uniform(0.5, 1.5))   # jitter to avoid burst
        if dry_run:
            return {"image_prompt": "[DRY RUN]", "video_prompt": "[DRY RUN]",
                    "caption_instagram": "[DRY RUN]", "caption_facebook": "[DRY RUN]",
                    "ad_headline": "[DRY RUN]", "ad_primary_text": "[DRY RUN]",
                    "alt_text": "[DRY RUN]"}
        sku = SKUS[post["sku"]]
        user_msg = f"""Generate creative prompts for this content brief:

SKU: {sku['name']} (₹{sku['price_inr']})
Product facts: {json.dumps(sku['product_facts'])}
Differentiation: {sku['differentiation_angle']}
Content pillar: {post.get('content_pillar', 'product')}
Topic: {post['topic']}
Theme: {post.get('theme', '')}
Tone: {post.get('tone', 'warm_inspirational')}
Cultural moment: {post.get('cultural_moment', 'none')}
Reference notes: {post.get('reference_notes', 'None')}
Source image: {post['source_product_image']}"""

        response = client.messages.create(
            model=ANTHROPIC_MODEL,
            max_tokens=900,
            system=SYSTEM_PROMPT,
            messages=[{"role": "user", "content": user_msg}]
        )
        return json.loads(response.content[0].text)
```

### `commands/generate_images.py` — FLUX Kontext (img2img)

```python
# commands/generate_images.py
import fal_client, pathlib, requests, logging
from utils.db import get_db
from utils.guards import require_approval
from utils.retry import checked_post
from config import FAL_FLUX_KONTEXT_ENDPOINT, IMAGE_VARIANTS_PER_POST, PROJECT_ROOT

log = logging.getLogger(__name__)

@require_approval("prompts_approved", "prompts")
def run(week: str = None, post_id: str = None, dry_run: bool = False):
    db = get_db()
    posts = _fetch_posts(db, week, post_id)

    for post in posts:
        source = PROJECT_ROOT / post["source_product_image"]
        if not source.exists():
            log.error("Source image not found: %s", source)
            db.execute("UPDATE posts SET pipeline_status='creative_failed', "
                       "last_error='Source image not found' WHERE post_id=?", (post["post_id"],))
            continue

        # Upload source to Cloudinary for fal.ai URL reference
        from commands.upload_media import upload_single
        source_url = upload_single(str(source), f"source_{post['post_id']}")

        if dry_run:
            log.info("[DRY RUN] Would call FLUX Kontext for %s", post["post_id"])
            continue

        log.info("Generating %d images for %s...", IMAGE_VARIANTS_PER_POST, post["post_id"])
        db.execute("UPDATE posts SET pipeline_status='creative_generating' WHERE post_id=?",
                   (post["post_id"],))
        db.commit()

        try:
            result = fal_client.run(
                FAL_FLUX_KONTEXT_ENDPOINT,
                arguments={
                    "prompt": post["image_prompt"],
                    "image_url": source_url,
                    "num_images": IMAGE_VARIANTS_PER_POST,
                    "aspect_ratio": "1:1",
                    "safety_tolerance": "2",
                }
            )

            saved_paths = []
            out_dir = PROJECT_ROOT / "creatives" / "images"
            out_dir.mkdir(parents=True, exist_ok=True)

            for i, img in enumerate(result["images"]):
                out_path = out_dir / f"{post['post_id']}_{i}.jpg"
                out_path.write_bytes(requests.get(img["url"], timeout=30).content)
                saved_paths.append(str(out_path.relative_to(PROJECT_ROOT)))
                log.info("  ✓ Saved %s (%dKB)", out_path.name,
                         out_path.stat().st_size // 1024)
                log.info("COST fal.ai flux_kontext post=%s $0.04", post["post_id"])

            with db:
                db.execute("""UPDATE posts SET image_paths=?, pipeline_status='creative_ready',
                              last_error=NULL WHERE post_id=?""",
                           (json.dumps(saved_paths), post["post_id"]))

        except Exception as e:
            log.error("Image generation failed for %s: %s", post["post_id"], e, exc_info=True)
            with db:
                db.execute("""UPDATE posts SET pipeline_status='creative_failed',
                              last_error=?, last_error_at=datetime('now') WHERE post_id=?""",
                           (str(e), post["post_id"]))
```

### `commands/generate_videos.py` — Kling 3.0 (img2video)

```python
# commands/generate_videos.py
import fal_client, pathlib, requests, json, time, logging
from utils.db import get_db
from utils.guards import require_approval
from config import FAL_KLING_ENDPOINT, VIDEO_DURATION_SECONDS, PROJECT_ROOT

log = logging.getLogger(__name__)
PENDING_JOBS = PROJECT_ROOT / "creatives" / "pending_video_jobs.json"

@require_approval("prompts_approved", "prompts")
def run(week: str = None, post_id: str = None, dry_run: bool = False):
    db = get_db()
    posts = _fetch_posts(db, week, post_id)

    for post in posts:
        source_url = _get_cloudinary_url(db, post["post_id"])
        if not source_url:
            log.warning("No Cloudinary URL for %s — run upload-media first", post["post_id"])
            continue

        if dry_run:
            log.info("[DRY RUN] Would call Kling 3.0 for %s", post["post_id"])
            continue

        log.info("Submitting video job for %s...", post["post_id"])
        handler = fal_client.submit(
            FAL_KLING_ENDPOINT,
            arguments={
                "image_url": source_url,
                "prompt": post["video_prompt"],
                "duration": str(VIDEO_DURATION_SECONDS),
                "aspect_ratio": "9:16",
            }
        )
        request_id = handler.request_id

        # Persist BEFORE polling — crash-safe
        pending = _load_pending()
        pending[request_id] = {"post_id": post["post_id"], "submitted_at": time.time()}
        _save_pending(pending)
        log.info("  Job submitted: %s (persisted to pending_video_jobs.json)", request_id)

        result = _poll(request_id)

        out_dir = PROJECT_ROOT / "creatives" / "videos"
        out_dir.mkdir(parents=True, exist_ok=True)
        out_path = out_dir / f"{post['post_id']}.mp4"
        out_path.write_bytes(requests.get(result["video"]["url"], timeout=60).content)
        log.info("  ✓ Video saved: %s", out_path.name)
        log.info("COST fal.ai kling post=%s $0.18", post["post_id"])

        # Remove from pending, update DB
        pending.pop(request_id, None)
        _save_pending(pending)
        with db:
            db.execute("UPDATE posts SET video_path=? WHERE post_id=?",
                       (str(out_path.relative_to(PROJECT_ROOT)), post["post_id"]))

def _poll(request_id: str, timeout: int = 360) -> dict:
    deadline = time.time() + timeout
    while time.time() < deadline:
        status = fal_client.status(FAL_KLING_ENDPOINT, request_id, with_logs=False)
        if status.status == "COMPLETED":
            return fal_client.result(FAL_KLING_ENDPOINT, request_id)
        if status.status in ("FAILED", "CANCELLED"):
            raise RuntimeError(f"Video job {request_id} failed: {status}")
        log.debug("  ... video status=%s, waiting 15s", status.status)
        time.sleep(15)
    raise TimeoutError(f"Video job {request_id} timed out. "
                       "Run `python main.py resume-video-jobs` to check.")
```

### `commands/post_organic.py` — Meta Graph API

```python
# commands/post_organic.py
import os, requests, logging
from utils.db import get_db
from utils.guards import require_approval
from utils.retry import check_meta_rate_limit
from utils.meta_auth import validate_meta_token
from config import META_GRAPH_BASE

log = logging.getLogger(__name__)

@require_approval("creatives_approved", "creatives")
def run(platform: str = "both", post_id: str = None, dry_run: bool = False):
    validate_meta_token()   # fail fast on bad/revoked token
    db = get_db()
    token = os.environ["META_ACCESS_TOKEN"]
    ig_id = os.environ["META_IG_ACCOUNT_ID"]
    page_id = os.environ["META_PAGE_ID"]

    posts = _fetch_approved_posts(db, post_id)
    for post in posts:
        urls = json.loads(post["cloudinary_urls"] or "[]")
        if not urls:
            log.error("No Cloudinary URL for %s — run upload-media first", post["post_id"])
            continue

        image_url = urls[0]
        caption = post["caption_instagram"]

        if dry_run:
            log.info("[DRY RUN] Would post %s to %s", post["post_id"], platform)
            continue

        # Pre-post confirmation is enforced by creatives_approved gate above.
        # The dashboard shows a preview modal before setting creatives_approved.

        if platform in ("instagram", "both"):
            ig_post_id = _post_instagram(ig_id, image_url, caption, token)
            with db:
                db.execute("UPDATE posts SET ig_post_id=?, status='posted' WHERE post_id=?",
                           (ig_post_id, post["post_id"]))

        if platform in ("facebook", "both"):
            fb_post_id = _post_facebook(page_id, image_url,
                                         post["caption_facebook"], token)
            with db:
                db.execute("UPDATE posts SET fb_post_id=? WHERE post_id=?",
                           (fb_post_id, post["post_id"]))

def _post_instagram(ig_id, image_url, caption, token):
    # Step 1: Container
    r = requests.post(f"{META_GRAPH_BASE}/{ig_id}/media",
                      data={"image_url": image_url, "caption": caption,
                            "access_token": token}, timeout=30)
    check_meta_rate_limit(r)
    r.raise_for_status()
    container_id = r.json()["id"]

    # Step 2: Publish
    r2 = requests.post(f"{META_GRAPH_BASE}/{ig_id}/media_publish",
                       data={"creation_id": container_id,
                             "access_token": token}, timeout=30)
    check_meta_rate_limit(r2)
    r2.raise_for_status()
    post_id = r2.json()["id"]
    log.info("  ✓ Instagram post published: %s", post_id)
    return post_id

def _post_facebook(page_id, image_url, caption, token):
    r = requests.post(f"{META_GRAPH_BASE}/{page_id}/photos",
                      data={"url": image_url, "caption": caption,
                            "access_token": token}, timeout=30)
    check_meta_rate_limit(r)
    r.raise_for_status()
    post_id = r.json()["post_id"]
    log.info("  ✓ Facebook photo posted: %s", post_id)
    return post_id
```

### `commands/create_ads.py` — Idempotent Campaign Creation

```python
# commands/create_ads.py
import os, json, logging
from datetime import datetime
from facebook_business.api import FacebookAdsApi
from facebook_business.adobjects.adaccount import AdAccount
from facebook_business.adobjects.campaign import Campaign
from facebook_business.adobjects.adset import AdSet
from facebook_business.adobjects.adcreative import AdCreative
from facebook_business.adobjects.ad import Ad
from utils.db import get_db
from utils.guards import require_approval
from utils.meta_auth import validate_meta_token
from config import (META_CAMPAIGN_PHASE, META_CAMPAIGN_OBJECTIVE_PHASE,
                    META_BUDGET_PHASE, META_TARGETING_LAUNCH, META_TARGETING_GROWTH, SKUS)

log = logging.getLogger(__name__)

@require_approval("creatives_approved", "creatives")
def run(post_id: str = None, dry_run: bool = False):
    validate_meta_token()
    FacebookAdsApi.init(
        app_id=os.environ["META_APP_ID"],
        app_secret=os.environ["META_APP_SECRET"],
        access_token=os.environ["META_ACCESS_TOKEN"],
    )
    account = AdAccount(os.environ["META_AD_ACCOUNT_ID"])
    db = get_db()

    posts = _fetch_approved_posts(db, post_id)
    for post in posts:
        campaign_date = datetime.now().strftime("%Y-%m-%d")
        campaign_key = f"{post['sku']}_{campaign_date}"

        # Idempotency check — never create duplicates
        existing = db.execute(
            "SELECT * FROM ad_campaigns WHERE campaign_key=?", (campaign_key,)
        ).fetchone()
        if existing:
            log.info("Campaign already exists for %s (%s) — skipping. Use --force to override.",
                     post["sku"], campaign_date)
            continue

        urls = json.loads(post["cloudinary_urls"] or "[]")
        image_url = urls[0] if urls else None
        if not image_url:
            log.error("No image URL for %s", post["post_id"])
            continue

        objective = META_CAMPAIGN_OBJECTIVE_PHASE[META_CAMPAIGN_PHASE]
        budget_inr = META_BUDGET_PHASE[META_CAMPAIGN_PHASE]
        targeting = META_TARGETING_LAUNCH if META_CAMPAIGN_PHASE == 1 else META_TARGETING_GROWTH

        if dry_run:
            log.info("[DRY RUN] Would create %s campaign for %s, ₹%d/day, objective=%s",
                     campaign_date, post["sku"], budget_inr, objective)
            continue

        log.info("Creating campaign: %s %s (Phase %d)", post["sku"],
                 campaign_date, META_CAMPAIGN_PHASE)

        campaign = account.create_campaign(fields=[], params={
            Campaign.Field.name: f"MG_{post['sku']}_{campaign_date}_P{META_CAMPAIGN_PHASE}",
            Campaign.Field.objective: objective,
            Campaign.Field.status: Campaign.Status.paused,  # ALWAYS start paused
            Campaign.Field.special_ad_categories: [],
        })

        adset = account.create_ad_set(fields=[], params={
            AdSet.Field.name: f"MG_{post['sku']}_adset_P{META_CAMPAIGN_PHASE}",
            AdSet.Field.campaign_id: campaign["id"],
            AdSet.Field.daily_budget: budget_inr * 100,   # paise
            AdSet.Field.billing_event: AdSet.BillingEvent.impressions,
            AdSet.Field.optimization_goal: (AdSet.OptimizationGoal.reach
                                            if META_CAMPAIGN_PHASE == 1
                                            else AdSet.OptimizationGoal.offsite_conversions),
            AdSet.Field.targeting: targeting,
            AdSet.Field.status: AdSet.Status.paused,
        })

        creative = account.create_ad_creative(fields=[], params={
            AdCreative.Field.name: f"MG_{post['sku']}_creative",
            AdCreative.Field.object_story_spec: {
                "page_id": os.environ["META_PAGE_ID"],
                "link_data": {
                    "image_url": image_url,
                    "link": SKUS[post["sku"]]["shopify_url"],
                    "message": post["ad_primary_text"],
                    "call_to_action": {
                        "type": "SHOP_NOW",
                        "value": {"link": SKUS[post["sku"]]["shopify_url"]},
                    },
                },
            },
        })

        ad = account.create_ad(fields=[], params={
            Ad.Field.name: f"MG_{post['sku']}_ad",
            Ad.Field.adset_id: adset["id"],
            Ad.Field.creative: {"creative_id": creative["id"]},
            Ad.Field.status: Ad.Status.paused,
        })

        with db:
            db.execute("""
                INSERT INTO ad_campaigns
                (campaign_key, sku, campaign_date, campaign_phase,
                 campaign_id, adset_id, creative_id, ad_id, daily_budget_inr)
                VALUES (?,?,?,?,?,?,?,?,?)
            """, (campaign_key, post["sku"], campaign_date, META_CAMPAIGN_PHASE,
                  campaign["id"], adset["id"], creative["id"], ad["id"], budget_inr))

        log.info("  ✓ Campaign %s created (PAUSED) — activate manually in Ads Manager",
                 campaign["id"])
```

### `commands/tune_ads.py` — Multi-Signal Optimiser

```python
# commands/tune_ads.py
import os, logging
from datetime import datetime, timedelta
from facebook_business.api import FacebookAdsApi
from facebook_business.adobjects.adset import AdSet
from facebook_business.adobjects.ad import Ad
from utils.db import get_db
from config import (LEARNING_PHASE_DAYS, MIN_SPEND_INR_BEFORE_JUDGE,
                    PAUSE_CTR_FEED_BELOW, PAUSE_CTR_REELS_BELOW,
                    SCALE_ROAS_ABOVE_WARM, SCALE_BUDGET_MULTIPLIER,
                    CREATIVE_REFRESH_FREQUENCY, MAX_CPM_INR)

log = logging.getLogger(__name__)

def run(dry_run: bool = True):
    if dry_run:
        log.info("DRY RUN — pass --apply to commit changes")

    FacebookAdsApi.init(
        app_id=os.environ["META_APP_ID"],
        app_secret=os.environ["META_APP_SECRET"],
        access_token=os.environ["META_ACCESS_TOKEN"],
    )
    db = get_db()
    campaigns = db.execute(
        "SELECT * FROM ad_campaigns WHERE status != 'ARCHIVED'"
    ).fetchall()

    for c in campaigns:
        # Skip if in learning phase
        created = datetime.fromisoformat(c["created_at"])
        days_live = (datetime.utcnow() - created).days
        if days_live < LEARNING_PHASE_DAYS:
            log.info("  %s: Day %d < %d learning phase — skip",
                     c["sku"], days_live, LEARNING_PHASE_DAYS)
            continue

        ins = _fetch_insights(c["ad_id"])
        if not ins:
            continue

        spend = float(ins.get("spend", 0))
        if spend < MIN_SPEND_INR_BEFORE_JUDGE:
            log.info("  %s: ₹%.0f spend < ₹%d minimum — skip",
                     c["sku"], spend, MIN_SPEND_INR_BEFORE_JUDGE)
            continue

        ctr        = float(ins.get("ctr", 1)) / 100    # Meta returns % as float
        frequency  = float(ins.get("frequency", 0))
        cpm        = float(ins.get("cpm", 0))
        roas       = _extract_roas(ins)
        ad_format  = "reels"    # TODO: derive from creative type

        ctr_floor  = PAUSE_CTR_REELS_BELOW if ad_format == "reels" else PAUSE_CTR_FEED_BELOW

        # Decision matrix
        if cpm > MAX_CPM_INR:
            action = "PAUSE_HIGH_CPM"
        elif frequency > CREATIVE_REFRESH_FREQUENCY:
            action = "REFRESH_CREATIVE"
        elif ctr < ctr_floor and spend >= MIN_SPEND_INR_BEFORE_JUDGE:
            action = "PAUSE_LOW_CTR"
        elif roas and roas >= SCALE_ROAS_ABOVE_WARM:
            action = "SCALE"
        else:
            action = "OK"

        log.info("  %s: CTR=%.2f%% Freq=%.1f CPM=₹%.0f ROAS=%.1fx → %s",
                 c["sku"], ctr * 100, frequency, cpm, roas or 0, action)

        if not dry_run:
            _apply_action(c, action, db)
        with db:
            db.execute("UPDATE insights_cache SET action_taken=? WHERE ad_id=? AND fetched_date=?",
                       (action, c["ad_id"], datetime.utcnow().date().isoformat()))

def _apply_action(campaign: dict, action: str, db):
    if action in ("PAUSE_HIGH_CPM", "PAUSE_LOW_CTR"):
        Ad(campaign["ad_id"]).api_update(params={"status": "PAUSED"})
        with db:
            db.execute("UPDATE ad_campaigns SET status='PAUSED' WHERE campaign_key=?",
                       (campaign["campaign_key"],))
        log.info("    Paused ad %s", campaign["ad_id"])

    elif action == "SCALE":
        adset = AdSet(campaign["adset_id"]).api_get(fields=["daily_budget"])
        new_budget = int(float(adset["daily_budget"]) * SCALE_BUDGET_MULTIPLIER)
        AdSet(campaign["adset_id"]).api_update(params={"daily_budget": new_budget})
        log.info("    Scaled adset budget to ₹%.0f", new_budget / 100)

    elif action == "REFRESH_CREATIVE":
        log.warning("    Creative refresh needed for %s — add new creative in dashboard",
                    campaign["sku"])
        # Notification sent via notifications.py
        from utils.notifications import notify_founder
        notify_founder(
            subject=f"Creative fatigue: {campaign['sku']} ad needs new creative",
            body=f"Frequency is above {CREATIVE_REFRESH_FREQUENCY}. "
                 f"Open the dashboard to generate a new creative variant."
        )
```

---

## 10. The Streamlit Dashboard

**Deployed to Streamlit Community Cloud** — accessible from any browser, any device, no localhost required. URL: `https://moregreen.streamlit.app`

### Key Screens

**Screen 1 — Weekly Overview**
```
┌─────────────────────────────────────────────────────────────────────────────┐
│ 🌿 More Green Studio         Week of 2 June 2026      [Sync + Generate ▶]  │
├─────────────┬─────────────┬─────────────┬─────────────┬─────────────────────┤
│ MON Jun 2   │ WED Jun 4   │ FRI Jun 6   │ MON Jun 9   │                     │
│ 📗 MORINGA  │ ☀️ SUNFLOWER │ 🫐 BLUEBERRY│ 🌾 WHEATGRS │  + Add Post         │
│ Educational │ Product     │ Recipe      │ Educational │                     │
│             │             │             │             │                     │
│ ✍️ Prompts  │ ✅ Approved  │ 🖼️ Creative │ ⏳ Pending  │                     │
│ [Approve]   │ [View]      │ [Approve]   │ [Generate]  │                     │
│             │             │             │             │                     │
│ ⚠️ Error    │             │             │             │                     │
│ Tap to view │             │             │             │                     │
└─────────────┴─────────────┴─────────────┴─────────────┴─────────────────────┘
```

**Screen 2 — Post Detail (tap any post)**
```
┌─────────────────────────────────────────────────────────────────────────────┐
│ ← Back    More Green Moringa — Mon Jun 2, 9:00 AM    Status: Prompts Ready │
├────────────────────────────┬────────────────────────────────────────────────┤
│  📸 IMAGE PROMPT           │  📱 INSTAGRAM PREVIEW                         │
│  ┌────────────────────┐    │  ┌─────────────────────────────────────────┐  │
│  │ The More Green     │    │  │ @moregreen.in                       ···  │  │
│  │ Moringa pouch sits │    │  │ ┌─────────────────────────────────────┐  │  │
│  │ on a terracotta    │    │  │ │                                     │  │  │
│  │ floor surrounded   │    │  │ │  [product image preview here]       │  │  │
│  │ by fresh moringa   │    │  │ │                                     │  │  │
│  │ leaves. Keep the   │    │  │ │                                     │  │  │
│  │ pouch label...     │    │  │ └─────────────────────────────────────┘  │  │
│  └────────────────────┘    │  │ ♡ 🗨 ↗  🔖                              │  │
│  [Edit prompt]             │  │ more-greens.in  Your moringa powder...   │  │
│                            │  └─────────────────────────────────────────┘  │
│  📝 INSTAGRAM CAPTION      │                                               │
│  ┌────────────────────┐    │  [Edit caption]                               │
│  │ Your moringa has   │    │                                               │
│  │ 3x more iron than  │    │  🎬 VIDEO PROMPT                             │
│  │ the leaves...      │    │  ┌────────────────────────────────────────┐  │
│  └────────────────────┘    │  │ The More Green Moringa pouch sits...   │  │
│                            │  └────────────────────────────────────────┘  │
├────────────────────────────┴────────────────────────────────────────────────┤
│  [✅ Approve & Generate Creatives]    [⏸ Hold Post]    [🗑 Delete]          │
└─────────────────────────────────────────────────────────────────────────────┘
```

**Screen 3 — Creative Approval (after generation)**
```
┌─────────────────────────────────────────────────────────────────────────────┐
│ Approve Creatives: Moringa — Mon Jun 2                                      │
├───────────────────┬───────────────────┬───────────────────┬─────────────────┤
│  Variant 1        │  Variant 2        │  Variant 3        │  Video Preview  │
│  [image]          │  [image]          │  [image]          │  [video thumb]  │
│                   │                   │                   │                 │
│  [✅ Use this]    │  [✅ Use this]    │  [✅ Use this]    │  [▶ Preview]   │
│  [🔄 Regen]       │  [🔄 Regen]       │  [🔄 Regen]       │  [🔄 Regen]    │
└───────────────────┴───────────────────┴───────────────────┴─────────────────┘
│  Selected: Variant 2 + Video                                                │
│                                                                             │
│  [🚀 Approve Selected & Schedule Post]    [← Back to Prompts]              │
└─────────────────────────────────────────────────────────────────────────────┘
```

**System Health Panel** (persistent sidebar):
```
┌─────────────────────┐
│ System Health       │
├─────────────────────┤
│ ✅ Anthropic API    │
│ ✅ fal.ai           │
│ ✅ Cloudinary       │
│ ✅ Meta Token       │
│                     │
│ 📋 Recent Activity  │
│ ✓ W24_MON posted    │
│ ✓ W24_WED generated │
│ ✗ W24_FRI failed    │
│   [View error]      │
│                     │
│ 💸 This week: ₹0.45 │
│    gen costs        │
└─────────────────────┘
```

### Dashboard Deployment (Streamlit Community Cloud)

```bash
# One-time setup:
# 1. Push automation/ to a GitHub repo
# 2. Log in to share.streamlit.io
# 3. Deploy from GitHub → commands/_dashboard_app.py
# 4. Add all .env variables as Streamlit Secrets
# → App is live at https://yourappname.streamlit.app
# → Accessible from any phone browser
```

---

## 11. Data Flow & Dependency Map

```
Google Sheets (human input)
    │
    ▼ sync-sheets
SQLite: posts table (status='draft')
    │
    ▼ generate-prompts (Claude API, 2 parallel threads, ~10s)
SQLite: image_prompt, video_prompt, captions written
Status: 'prompts_ready' | pipeline_status: 'prompts_ready'
    │
    ▼ [HUMAN: approve prompts in dashboard — 5 min]
SQLite: prompts_approved=1
    │
    ├──▶ generate-images (FLUX Kontext, source photo → scene image, ~25s/post)
    │    Local: creatives/images/{post_id}_{variant}.jpg
    │    SQLite: image_paths, pipeline_status='creative_ready'
    │
    └──▶ generate-videos (Kling 3.0, source photo → 5s video, ~90s/post)
         Local: creatives/videos/{post_id}.mp4
         SQLite: video_path
    │
    ▼ upload-media (Cloudinary, ~5s)
SQLite: cloudinary_urls, cloudinary_public_ids
    │
    ▼ [HUMAN: approve creatives in dashboard — 5 min, phone-friendly]
SQLite: creatives_approved=1  (dashboard shows IG preview before this button appears)
    │
    ├──▶ cron: post-organic (Meta Graph API, Instagram + Facebook)
    │    SQLite: ig_post_id, fb_post_id, status='posted'
    │    Notification: "Post went live ✓"
    │
    ├──▶ cron: post-youtube (YouTube Data API, Reels cross-post)
    │    SQLite: youtube_video_id
    │
    └──▶ create-ads (facebook-business SDK, starts PAUSED)
         SQLite: ad_campaigns table populated
         ads_log.json: backup record
         Human activates manually in Meta Ads Manager
    │
    ▼ cron: monitor-ads (daily 6pm)
SQLite: insights_cache populated
    │
    ▼ cron: tune-ads (daily 7pm, --apply)
SQLite: insights_cache.action_taken updated
Meta API: budgets adjusted, ads paused/scaled
Notification sent if creative refresh needed
```

**Key dependency rule:** No command proceeds unless its upstream approval is set. Guards in `utils/guards.py` enforce this at runtime — not just by convention.

---

## 12. Error Handling Strategy

### Per-Scenario Playbook

| Scenario | Detection | Action | User Sees |
|---|---|---|---|
| FLUX returns 200 + error body | `APIBodyError` in `retry.py` | Retry 3× with backoff | Dashboard: red badge "Image failed — tap retry" |
| Kling job interrupted (Ctrl+C / cron kill) | `pending_video_jobs.json` not cleared | `resume-video-jobs` polls the saved request_id | Log: "Pending job found — resuming" |
| Meta token revoked | OAuthException code 190/200/803 | `MetaAuthError` raised, pipeline stops | Notification: "Meta token invalid — check Business Manager" |
| Meta rate limit | `X-App-Usage` header >75% | Sleep `(100-pct)` seconds, retry | Log: "Rate limit at 82% — sleeping 18s" |
| Cloudinary URL 404 | `verify-media` command | Flag in DB, re-upload from local backup | Dashboard: amber badge "Media needs re-upload" |
| Claude malformed JSON | `json.JSONDecodeError` | Retry once with stricter prompt, then fail | Dashboard: "Prompt generation failed — edit manually" |
| Google Sheets sync fails | `gspread.exceptions` | Log error, do not overwrite existing DB rows | Log: "Sheets sync failed — using existing DB state" |
| SQLite write crash (mid-write) | WAL mode + OS-level atomicity | WAL journal rolls back incomplete transaction | No data loss; next run retries the write |
| fal.ai video timeout (>6 min) | `TimeoutError` in `_poll()` | job_id saved to `pending_video_jobs.json` | Log: "Timed out — run resume-video-jobs" |

### `utils/notifications.py`

```python
# utils/notifications.py — SendGrid email (primary) + Twilio WhatsApp (optional)
import os, logging
from sendgrid import SendGridAPIClient
from sendgrid.helpers.mail import Mail

log = logging.getLogger(__name__)

def notify_founder(subject: str, body: str) -> None:
    """Send email notification. Falls back silently if SendGrid not configured."""
    key = os.environ.get("SENDGRID_API_KEY")
    if not key:
        log.debug("SENDGRID_API_KEY not set — notification skipped: %s", subject)
        return
    try:
        msg = Mail(
            from_email="automation@moregreen.in",
            to_emails=os.environ.get("FOUNDER_EMAIL", "bs.moregreen@gmail.com"),
            subject=f"[More Green] {subject}",
            plain_text_content=body
        )
        SendGridAPIClient(key).send(msg)
        log.info("Notification sent: %s", subject)
    except Exception as e:
        log.warning("Notification failed: %s", e)
```

**Notification triggers:**
- Creatives ready for review → "4 creatives for W24 are ready. Open dashboard."
- Pipeline error → "Image generation failed for W24_MON_01. Tap to retry."
- Post published → "Moringa post went live on Instagram. [link]"
- Scheduled post in 24h, not yet approved → "Reminder: Tuesday's post needs approval in 18 hours."
- Creative fatigue → "Frequency >3.5 for sunflower ad — new creative needed."

---

## 13. Security & Secrets Management

### `.gitignore` (non-negotiable entries)

```gitignore
.env
.env.*
*.env
!.env.example
db/pipeline.db
db/*.db
logs/
service_account.json        # Google Sheets OAuth credential
creatives/images/
creatives/videos/
pending_video_jobs.json
```

### Pre-commit hook (prevents accidental `.env` commits)

```bash
# .git/hooks/pre-commit  (chmod +x this file)
#!/bin/bash
if git diff --cached --name-only | grep -qE '\.env$|\.env\.|service_account\.json'; then
  echo "ERROR: Attempting to commit a secrets file. Aborting."
  echo "If intentional, use: git commit --no-verify (not recommended)"
  exit 1
fi
```

Install automatically for new clones:

```bash
# setup.sh (run once after cloning)
cp .git/hooks/pre-commit.sample .git/hooks/pre-commit
cat >> .git/hooks/pre-commit << 'EOF'
if git diff --cached --name-only | grep -qE '\.env$|service_account'; then
  echo "ERROR: Secrets file detected. Aborting commit."; exit 1
fi
EOF
chmod +x .git/hooks/pre-commit
```

### Secret Blast Radius Classification

| Secret | Risk if leaked | Rotation |
|---|---|---|
| `META_SYSTEM_USER_TOKEN` | Posts content, spends ad budget | Revoke immediately if leaked |
| `META_APP_SECRET` | Can generate tokens for any user who authorised the app | Rotate immediately |
| `FAL_KEY` | GPU bill fraud | Rotate monthly |
| `ANTHROPIC_API_KEY` | API bill | Rotate if leaked |
| `CLOUDINARY_API_SECRET` | Delete all hosted media | Rotate if leaked |
| `GOOGLE_API_KEY` | API quota exhaustion | Rotate if leaked |
| `SENDGRID_API_KEY` | Spam via your domain | Rotate if leaked |

### `utils/meta_auth.py` — Token Validator

```python
# utils/meta_auth.py
import os, requests, logging
from config import META_GRAPH_BASE

log = logging.getLogger(__name__)

META_UNRECOVERABLE = {
    190: "Access token invalid. Re-generate System User Token in Business Manager.",
    200: "Permission denied. Check system user roles in Business Manager.",
    803: "Page access revoked. Re-add system user to the Page.",
    10:  "App permission missing. Check Meta App Review status.",
}

def validate_meta_token() -> None:
    """Call before any Meta API operation. Raises MetaAuthError on bad token."""
    token = os.environ.get("META_ACCESS_TOKEN")
    if not token:
        raise SystemExit("META_ACCESS_TOKEN not set in .env")
    r = requests.get(f"{META_GRAPH_BASE}/me",
                     params={"access_token": token, "fields": "id,name"}, timeout=10)
    body = r.json()
    if "error" in body:
        code = body["error"].get("code", 0)
        msg = META_UNRECOVERABLE.get(code, f"Meta API error: {body['error']}")
        raise SystemExit(f"Meta token check failed — {msg}")
    log.debug("Meta token valid for: %s (%s)", body.get("name"), body.get("id"))
```

---

## 14. Structured Logging

```python
# utils/logging_config.py
import logging, sys
from pathlib import Path
from config import LOG_PATH

def configure(verbose: bool = False) -> None:
    LOG_PATH.parent.mkdir(exist_ok=True)
    level  = logging.DEBUG if verbose else logging.INFO
    fmt    = "%(asctime)s %(levelname)-8s %(name)-30s %(message)s"
    logging.basicConfig(
        level=level, format=fmt,
        handlers=[
            logging.FileHandler(LOG_PATH, encoding="utf-8"),
            logging.StreamHandler(sys.stdout),
        ]
    )
    for noisy in ("httpx", "anthropic._base_client", "fal_client", "urllib3"):
        logging.getLogger(noisy).setLevel(logging.WARNING)
```

**Cost event logging** (lets you reconstruct API spend from logs):

```python
# Every API call that costs money logs a COST line:
log.info("COST anthropic prompt post=%s input_tokens=%d output_tokens=%d",
         post_id, input_t, output_t)
log.info("COST fal.ai flux_kontext post=%s variants=%d $%.2f",
         post_id, n, n * 0.04)
log.info("COST fal.ai kling post=%s duration=%ds $%.2f",
         post_id, duration, duration * 0.035)
```

**Cron job logging (redirect to rotating daily log):**

```
# crontab -e
0 9 * * 1,3,5 cd /home/user/automation && python main.py post-organic --due-now >> logs/cron.log 2>&1
0 18 * * *    cd /home/user/automation && python main.py monitor-ads >> logs/cron.log 2>&1
0 19 * * *    cd /home/user/automation && python main.py tune-ads --apply >> logs/cron.log 2>&1
```

---

## 15. Content Strategy Framework

### The 5-Pillar System

| Pillar | % of Posts | Format | Funnel Stage | Automatable |
|---|---|---|---|---|
| **Educational** | 30% | Carousel 5-7 slides, short Reel | Awareness | Full (Claude + FLUX) |
| **Recipe / How-To** | 25% | Reel, step carousel | Consideration | Full |
| **Product Truth** | 20% | Feed image | Consideration/conversion | Full |
| **Social Proof** | 15% | Quote card, screenshot carousel | Trust | Semi (aggregation manual) |
| **Founder / BTS** | 10% | Phone Reel (face-to-camera) | Trust/loyalty | **Not automatable** |

### Weekly Posting Schedule (6 posts/week)

```
Mon 9am  — Educational carousel (what microgreens actually are + the science)
Tue 9am  — Recipe Reel (60s: "3-ingredient moringa smoothie bowl")
Wed 9am  — Product Truth feed image (SKU in scene, specific claim)
Thu 9am  — Founder/BTS Reel (phone camera — system creates reminder, founder records)
Fri 9am  — Recipe or Educational carousel
Sat 9am  — Social Proof / customer spotlight (or skip in first 30 days)
```

### Caption Architecture (replaces generic templates)

Every caption generated by Claude must follow this structure:

```
1. Pattern interrupt — specific surprising fact OR relatable pain point
   ✓ "Moringa microgreens have 3x more iron than the mature leaf in every other powder."
   ✗ "Your skin's new morning ritual."

2. Why it matters — one practical sentence
   ✓ "That means your afternoon slump might be an iron problem, not a coffee problem."

3. How More Green fits — one sentence, concrete, not aspirational
   ✓ "One teaspoon in your dal. Done."

4. CTA — low-friction
   ✓ "Save this for tomorrow morning. Link in bio."
   ✗ "Shop now! Limited stock!"
```

### Hashtag System (per-post contextual, not hardcoded)

```yaml
# config/hashtags.yaml
branded:
  - "#moregreenin"
  - "#moregreen"

by_sku:
  moringa:    ["#moringa", "#moringapowder", "#moringhamicrogreens"]
  sunflower:  ["#sunflowermicrogreens", "#vitamine", "#skinfood"]
  blueberry:  ["#blueberrymicrogreens", "#anthocyanins", "#brainfood"]
  wheatgrass: ["#wheatgrass", "#chlorophyll", "#greenjuice"]

by_pillar:
  educational:   ["#nutritionfacts", "#foodscience", "#healthtips"]
  recipe:        ["#healthyrecipe", "#indianhealthyrecipe", "#smoothiebowl"]
  product:       ["#superfoodpowder", "#cleaningredients", "#plantbased"]
  social_proof:  ["#customerreview", "#healthtransformation"]

by_city:
  mumbai:     ["#mumbaifoodie", "#mumbaiwellness", "#bombayhealth"]
  bengaluru:  ["#bangalorewellness", "#bangalorefitness", "#nammabengaluru"]
  delhi:      ["#delhifoodie", "#delhihealth", "#ncrdiet"]
  hyderabad:  ["#hyderabadfoodie", "#hyderabadwellness"]
  pune:       ["#punefoodie", "#punewellness"]

cultural:
  navratri:   ["#navratri2026", "#fastingfood", "#navratridiet"]
  monsoon:    ["#monsoonhealth", "#immunityboost", "#monsoonwellness"]
  diwali:     ["#diwalihealth", "#giftsofhealth", "#diwali2026"]
```

Claude picks 6-8 tags per post: 1-2 branded + 2-3 SKU/pillar-specific + 1-2 city + 0-1 cultural. Different combination each time.

---

## 16. Ad Campaign Phase Structure

### Phase 1 — Pixel Warming (Weeks 1-4)

**Goal:** Get 1,000+ unique Shopify visitors. Build Custom Audiences. No sales pressure.

```
Campaign: MG_Phase1_Traffic
  Budget: ₹500/day TOTAL (not per SKU — concentrate spend)
  Objective: OUTCOME_TRAFFIC
  Optimization: Landing page views

  Ad Set A: Advantage+ Audience, Bengaluru + Pune, 24-42
    Creative: Educational Reel ("What are microgreens?")

  Ad Set B: Interest targeting (health/wellness/yoga), Bengaluru + Pune, 28-38
    Creative: Founder story Reel (if available) OR brand intro video
```

No sales campaigns. No 4-SKU split. One campaign, maximum signal.

### Phase 2 — First Conversions (Weeks 5-8)

**Goal:** 50 AddToCart events (to exit learning phase). First purchases.

```
Campaign A: MG_Phase2_ATC
  Budget: ₹500/day
  Objective: OUTCOME_CONVERSIONS → AddToCart event
  Audience: Advantage+ (all 5 metros now, 22-45)
  Creative: Moringa product post + specific iron claim

Campaign B: MG_Phase2_Retarget
  Budget: ₹200/day
  Objective: OUTCOME_CONVERSIONS → Purchase
  Audience: Website visitors (30-day) + Video viewers (50%+)
  Creative: Reminder + offer ("₹50 off your first pack — link in bio")
```

### Phase 3 — Scale (Month 3+)

**Goal:** ROAS > 2x sustained on cold traffic. Expand to all SKUs.

```
Campaign A: MG_Phase3_LAL_Moringa
  Budget: ₹800/day (scale from winning Phase 2 campaign)
  Objective: OUTCOME_SALES → Purchase
  Audience: 1% Lookalike of Shopify purchasers (India)
  Creative: Best-performing Phase 2 creative + new testimonial variant

Campaign B: MG_Phase3_Retarget_Full
  Budget: ₹400/day
  Audiences: 7-day visitors / 14-day ATC / 30-day visitors (separate ad sets)
  Creative: Urgency + social proof

Campaign C: MG_Phase3_SKU2  (add when Phase 1 budget > ₹1,000/day)
  SKU: wheatgrass (lowest price, easiest trial)
```

### `config.py` campaign phase switch

```python
# Change this one variable to switch all campaign logic:
META_CAMPAIGN_PHASE = 1   # → 2 after 1,000 visitors, → 3 after 50 purchases
```

---

## 17. Optimisation Logic

### Multi-Signal Decision Matrix

The `tune_ads.py` command applies this logic daily after the learning phase:

| Signal | Threshold | Action |
|---|---|---|
| Days since creation | < 14 | Skip (learning phase) |
| Total spend | < ₹2,000 | Skip (insufficient data) |
| CPM | > ₹400 | PAUSE ad set, review audience |
| Frequency | > 3.5 (7-day) | REFRESH_CREATIVE (notify founder) |
| CTR (feed format) | < 0.8% after ₹2K spend | PAUSE |
| CTR (reels format) | < 1.2% after ₹2K spend | PAUSE |
| Cost per ATC | > ₹150 | FLAG for review |
| ROAS (warm audience) | > 3.0x sustained 7 days | SCALE +20% |
| ROAS (cold LAL) | > 2.0x sustained 7 days | SCALE +20% |

### ROAS Prerequisite

**ROAS figures are unreliable until the Meta Pixel is correctly firing purchase events with revenue values.** The Shopify-Meta integration (native or via the Meta Sales Channel app) must be verified before any ROAS-based decisions are made. The `check` command should include a pixel health test.

---

## 18. Customer Journey Closure

The automation system handles top-of-funnel. These components complete the customer journey and should be set up before the first paid ad runs.

### Shopify Store Prerequisites

```
□ FSSAI registration number displayed prominently on all PDPs
  (legally required for food products in India; its absence = trust killer)
□ Return/refund policy: clear, generous (30-day, no questions for health products)
□ FAQ section per PDP: "Is this safe?", "What does it taste like?", "How do I use it?"
□ WhatsApp chat button (Interakt or Wati app, ₹2,000/month)
□ Pop-up: ₹50 off first order in exchange for email or WhatsApp number
□ Abandoned cart email: activate Shopify's native flow (free)
□ Meta Pixel: verify all 5 events firing (PageView, ViewContent, AddToCart,
  InitiateCheckout, Purchase) with revenue values
```

### Post-Purchase Sequence (Shopify Email / Klaviyo)

```
Day 1:  Order confirmation
        + "How to use your [SKU] powder" — 3 quick recipe ideas
        + WhatsApp link for questions

Day 3:  Usage tip specific to their SKU
        "Try it in your morning dal this week. Here's how."

Day 7:  Review request
        "You've had it for a week — what do you think?"
        Direct link to Google Reviews + Shopify review form

Day 14: Cross-sell
        "You have Moringa. Here's why Wheatgrass completes it."
        ₹75 off second SKU

Day 30: Repurchase
        "Your pack should be running low."
        10% loyalty discount, direct checkout link
```

### Shopify → Meta Custom Audience Sync

```python
# commands/sync_audience.py (add in Week 4)
# Pulls Shopify customer emails → hashes → uploads to Meta Custom Audience
# Enables Phase 3 Lookalike campaigns
import shopify, hashlib
from facebook_business.adobjects.customaudience import CustomAudience

def run():
    customers = shopify.Customer.find(limit=250)
    hashed_emails = [
        hashlib.sha256(c.email.lower().strip().encode()).hexdigest()
        for c in customers if c.email
    ]
    audience = CustomAudience(os.environ["META_CUSTOMER_AUDIENCE_ID"])
    audience.add_users(schema=CustomAudience.Schema.email_sha256,
                       data=hashed_emails)
    log.info("Synced %d customers to Meta Custom Audience", len(hashed_emails))
```

---

## 19. Platform Expansion Roadmap

| Platform | When | Module | Effort |
|---|---|---|---|
| Instagram + Facebook | Week 1 | `post_organic.py` | Done |
| YouTube Shorts | Week 4 | `post_youtube.py` | 1 day |
| Pinterest boards | Month 2 | `post_pinterest.py` | 1 day |
| WhatsApp Business | Month 2 | Via Interakt/Wati app | Setup, no code |
| Shopify Blog | Month 2 | `write_blog.py` | 2 hours |

**`commands/post_youtube.py`** (Week 4 addition):

```python
# Cross-post Reels to YouTube Shorts via YouTube Data API v3
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload

def run(post_id: str = None):
    youtube = build("youtube", "v3", developerKey=os.environ["YOUTUBE_API_KEY"])
    db = get_db()
    posts = _fetch_posted(db, post_id)
    for post in posts:
        video_path = PROJECT_ROOT / post["video_path"]
        if not video_path.exists():
            continue
        body = {
            "snippet": {
                "title": post["topic"][:100],
                "description": post["caption_instagram"],
                "tags": ["microgreens", "moregreenin", "healthyindia"],
                "categoryId": "26",   # How-to & Style
            },
            "status": {"privacyStatus": "public", "selfDeclaredMadeForKids": False}
        }
        media = MediaFileUpload(str(video_path), chunksize=-1, resumable=True)
        request = youtube.videos().insert(part="snippet,status", body=body, media_body=media)
        response = request.execute()
        with db:
            db.execute("UPDATE posts SET youtube_video_id=? WHERE post_id=?",
                       (response["id"], post["post_id"]))
        log.info("  ✓ YouTube Shorts: https://youtube.com/shorts/%s", response["id"])
```

**Shopify Blog Post Generation:**

```bash
python main.py write-blog --sku moringa
# Claude generates a 500-word SEO article:
# "Moringa Microgreens vs Moringa Leaf Powder: What No One Tells You"
# Posts via Shopify Admin API to blog
# Takes 30 seconds, costs ~$0.02
```

---

## 20. Cultural Calendar

```yaml
# config/cultural_calendar.yaml
events:
  - name: "New Year Reset"
    dates: ["01-01", "01-15"]
    content_angle: >
      New Year resolution content. "Make your resolution stick this time —
      one teaspoon, every morning. That's it."
    skus_to_feature: [moringa, wheatgrass]
    ad_boost: true

  - name: "Holi Skin Prep"
    dates: ["03-10", "03-20"]
    content_angle: >
      "Protect your skin before the colour hits. Load up on Vitamin E."
    skus_to_feature: [sunflower]
    ad_boost: true

  - name: "Pre-Summer Energy"
    dates: ["04-01", "05-15"]
    content_angle: >
      "Bengaluru heat is one thing. Mumbai humidity is another. Both drain you.
      Here's what we're adding to water bottles."
    skus_to_feature: [wheatgrass, moringa]

  - name: "Monsoon Immunity"
    dates: ["06-01", "09-30"]
    content_angle: >
      "Monsoon means mango, chai, and — if you're smart — microgreens powder.
      Your gut needs the most support right now."
    skus_to_feature: [moringa, blueberry]
    ad_boost: true

  - name: "Navratri Fasting"
    dates: ["10-01", "10-10"]
    content_angle: >
      "Fasting doesn't have to mean low energy. Moringa microgreens powder —
      pure plant, no additives, Navratri-safe."
    skus_to_feature: [moringa]
    ad_boost: true

  - name: "Diwali Health Gift"
    dates: ["10-15", "11-05"]
    content_angle: >
      "Balance the mithai. Gift health this Diwali — a 4-pack bundle
      for the family member who has everything."
    skus_to_feature: [sunflower, moringa, wheatgrass, blueberry]
    ad_boost: true
    budget_multiplier: 1.5

  - name: "Wedding Season Glow"
    dates: ["11-01", "01-31"]
    content_angle: >
      "Shaadi season. Four months of functions. Your skin and energy
      will need backup."
    skus_to_feature: [sunflower, blueberry]
    ad_boost: true
```

The `generate-prompts` command reads this calendar and automatically adjusts the Claude brief when the post date falls within a cultural window — no manual override needed.

---

## 21. Onboarding Checklist

### One-Time Setup (run `python main.py onboard`)

The `onboard` command is an interactive wizard that walks through every step:

```
□ Python 3.10+ installed
□ Virtual environment created and activated
□ pip install -r requirements.txt successful
□ .env populated (wizard prompts for each value with direct links)

Service accounts to create:
□ Google AI Studio → GOOGLE_API_KEY
    https://aistudio.google.com → Get API key
□ fal.ai → FAL_KEY (add payment method required)
    https://fal.ai/dashboard/keys
□ Anthropic → ANTHROPIC_API_KEY (add payment method required)
    https://console.anthropic.com/settings/keys
□ Cloudinary → CLOUDINARY_CLOUD_NAME, CLOUDINARY_API_KEY, CLOUDINARY_API_SECRET
    https://cloudinary.com → free account
□ SendGrid → SENDGRID_API_KEY (free tier, 100 emails/day)
    https://app.sendgrid.com/settings/api_keys

Meta setup (allow 2-3 hours for first-time):
□ Facebook Developer account created
    https://developers.facebook.com
□ App created → Marketing API + Instagram Graph API products added
□ System User created in Business Manager
    Business Settings → Users → System Users → Add
□ System User assigned roles:
    → Ad Account: Advertiser
    → Facebook Page: Admin
    → Instagram Account: Admin
□ System User Token generated with permissions:
    ads_management, ads_read, pages_manage_posts,
    instagram_basic, instagram_content_publish,
    pages_read_engagement, business_management
□ META_ACCESS_TOKEN, META_AD_ACCOUNT_ID, META_PAGE_ID, META_IG_ACCOUNT_ID set in .env
□ Meta App Review: apply for Standard Access (Marketing API) — do this in Week 1
    (takes 3-7 days; development access is sufficient for testing)

Google Sheets:
□ Google Sheets template copied to your Drive
    (link: [share template URL here])
□ service_account.json created and saved to project root
□ Sheet shared with service account email

Shopify:
□ FSSAI number displayed on all PDPs
□ Meta Pixel installed (via Meta Sales Channel app)
□ Pixel purchase event verified firing with revenue values
□ Abandoned cart email activated
□ Post-purchase email sequence created

Verification:
□ python main.py check    → all 5 services show ✓
□ python main.py --dry-run generate-prompts --post TEST_01  → no errors
□ python main.py dashboard  → Streamlit loads at localhost:8501
□ Deploy dashboard to Streamlit Community Cloud  → mobile-accessible
```

---

## 22. Verification Commands

```bash
# 1. Verify all credentials
python main.py check
# Expected: ✓ anthropic ✓ fal_ai ✓ cloudinary ✓ meta ✓ google

# 2. Sync Google Sheets → SQLite
python main.py sync-sheets
# Expected: "Synced 6 posts (0 skipped) from Google Sheets"
# Verify: sqlite3 db/pipeline.db "SELECT post_id, status FROM posts;"

# 3. Generate prompts (dry-run first)
python main.py --dry-run generate-prompts --week 2026-W24
# Expected: "[DRY RUN] Would call Claude for W24_MON_01" × n posts

# 4. Generate prompts (live)
python main.py generate-prompts --week 2026-W24
# Expected: "✓ W24_MON_01  ✓ W24_WED_01  ✓ W24_FRI_01  (11.3s)"
# Verify: sqlite3 db/pipeline.db "SELECT post_id, image_prompt FROM posts LIMIT 1;"

# 5. Generate one image (dry-run)
python main.py --dry-run generate-creatives --post W24_MON_01 --images-only
# Expected: "[DRY RUN] Would call FLUX Kontext for W24_MON_01"
# NOTE: prompts must be approved first — expects error if not

# 6. Approve prompts (simulates dashboard action)
python main.py approve-prompts --post W24_MON_01
python main.py generate-creatives --post W24_MON_01 --images-only
# Expected: "✓ Saved W24_MON_01_0.jpg (312KB)  ✓ W24_MON_01_1.jpg  ✓ W24_MON_01_2.jpg"
# Verify: ls -lh creatives/images/W24_MON_01_*.jpg

# 7. Upload to Cloudinary
python main.py upload-media --post W24_MON_01
# Expected: "✓ Uploaded → https://res.cloudinary.com/moregreen/..."
# Verify: open URL in browser — image should be visible

# 8. Post organic (dry-run)
python main.py --dry-run post-organic --post W24_MON_01 --platform instagram
# Expected: "[DRY RUN] POST .../media with image_url=https://..."
# NOTE: creatives must be approved first

# 9. Post organic (live)
python main.py post-organic --post W24_MON_01 --platform instagram
# Expected: "✓ Instagram post published: 17841..."
# Verify: check @moregreen.in Instagram profile manually

# 10. Create ads (dry-run)
python main.py --dry-run create-ads --post W24_MON_01
# Expected: "[DRY RUN] Would create 2026-MM-DD campaign for moringa, ₹500/day"

# 11. Create ads (live — starts PAUSED, no spend)
python main.py create-ads --post W24_MON_01
# Expected: "Campaign 12345 created (PAUSED) — activate manually in Ads Manager"
# Verify: Meta Ads Manager shows paused campaign

# 12. Monitor ads (before spend — structural check)
python main.py monitor-ads
# Expected: table with all SKU rows, "N/A" ROAS, "Skip (learning phase)" notes

# 13. Tune ads (dry-run)
python main.py tune-ads
# Expected: shows decision per ad, "DRY RUN — pass --apply to commit"

# 14. Verify Cloudinary URLs
python main.py verify-media
# Expected: "All 3 URLs return 200 ✓"
```

---

## 23. Phase Roadmap

### Phase 1 — Trust Foundation (Days 1-30)

**Week 1 (2 days of setup + 5 days content):**
```bash
# Day 1-2: Setup
python main.py onboard       # walks through all 5 services
python main.py check         # verify everything works
# Fill out Google Sheets template with 6 posts for W1
# Photos: add Files/ product images (all 4 SKUs)

# Day 3
python main.py sync-sheets && python main.py generate-prompts --week 2026-W23
# Review prompts in dashboard — approve 3 posts for the week
python main.py generate-creatives --week 2026-W23
python main.py upload-media --week 2026-W23
# Approve creatives in dashboard (phone-friendly)

# Day 4+: Posts go live at scheduled times via cron
# ONE paid ad — educational Reel, ₹500/day, TRAFFIC objective, Advantage+ audience
# Bengaluru + Pune only (lower CPM)
```

**Content mix this phase (trust-first):**
- 40% Educational ("What are microgreens, why do they beat supplements")
- 25% Founder/origin story (non-automatable — phone Reel)
- 20% Process/sourcing (where the plants come from)
- 15% Product (gentle, no hard sell)

**Week 2-4:** Repeat with new topics per week. Refine brand voice in `config/brand.yaml` based on which captions feel most authentic.

### Phase 2 — Community + Conversion (Days 31-90)

```bash
# Activate when: 500+ website visitors OR 20+ organic followers
META_CAMPAIGN_PHASE = 2   # change in config.py
python main.py create-ads   # creates AddToCart-objective campaign

# New content types activated:
# - Recipe carousels (highest share rate in India)
# - Social proof cards (first reviews from beta users)
# - YouTube Shorts cross-posting
python main.py post-youtube --week 2026-W28
```

**Content mix this phase:**
- 25% Educational
- 25% Recipe/How-To
- 20% Product Truth
- 20% Social Proof (once reviews exist)
- 10% Founder/BTS

### Phase 3 — Scale (Days 91-180)

```bash
# Activate when: 50+ purchases logged by Meta Pixel
META_CAMPAIGN_PHASE = 3   # change in config.py
python main.py sync-audience  # Shopify → Meta Custom Audience for LAL
python main.py create-ads     # LAL + retargeting campaigns

# Enable auto-scaling in tune-ads
python main.py tune-ads --apply  # runs daily via cron
```

**Phase 3 weekly cadence:**
- All 5 content pillars running
- Cultural calendar overrides active for festivals
- YouTube Shorts + Pinterest active
- Shopify blog posts weekly
- Budget: ₹1,500-2,000/day blended

---

## 24. Parallel Agent Architecture & Token Budget

### How Parallelism is Used

**In `generate_prompts.py`:** ThreadPoolExecutor with max 2 concurrent Claude calls (not 4 — rate limit protection). All results collected after all threads complete before a single SQLite write. Total time for 6 posts: ~15-20 seconds vs ~50 seconds sequential.

```
main thread
    │
    ├─ Thread-1: Claude(moringa brief)    ─→ result_1
    ├─ Thread-2: Claude(sunflower brief)  ─→ result_2
    │  [Thread-3 waits for semaphore]
    │  [Thread-4 waits for semaphore]
    ├─ Thread-3: Claude(blueberry brief)  ─→ result_3
    └─ Thread-4: Claude(wheatgrass brief) ─→ result_4
    │
    └─ Single SQLite write with all 4 results
```

### Token Breakdown per Post Brief

| Component | Tokens (input) |
|---|---|
| System prompt (brand voice, FLUX rules, Kling rules, caption rules) | ~680 |
| SKU data (name, facts, differentiation, prompts) | ~450 |
| Post brief (topic, theme, tone, cultural moment, notes) | ~380 |
| **Total input per call** | **~1,510** |
| **Output (7 fields: image, video, 2 captions, ad copy, alt text)** | **~840** |

### Weekly Cost Table (6 posts)

| Run | Parallel | Wall Clock | Input Tokens | Output Tokens | Cost (Sonnet 4.6) |
|---|---|---|---|---|---|
| 2 threads × 3 rounds | Yes | ~18s | 9,060 | 5,040 | **$0.10** |
| 6 posts sequential | No | ~55s | 9,060 | 5,040 | **$0.10** |
| Full month (24 posts) | Yes | ~70s total | 36,240 | 20,160 | **$0.41** |

*Cost is identical parallel vs sequential — parallelism saves time, not money.*

### Full Weekly Creative Pipeline Cost

| Step | Tool | Time | Cost |
|---|---|---|---|
| generate-prompts (6 posts) | Claude | 18s | $0.10 |
| generate-images (6 posts × 3) | FLUX Kontext | 45s | $0.72 |
| generate-videos (6 posts) | Kling 3.0 | 90s | $1.08 |
| upload-media | Cloudinary | 8s | free |
| post-organic (12 posts) | Meta Graph API | 10s | free |
| **Total API time (parallelised)** | | **~3 min** | **$1.90/week** |

### Monthly Total

| Line | Monthly |
|---|---|
| Claude prompts (24 posts) | $0.41 |
| FLUX Kontext (24 × 3 images) | $2.88 |
| Kling 3.0 (24 videos) | $4.32 |
| Cloudinary hosting | free |
| Meta posting | free |
| SendGrid email | free (100/day tier) |
| **Total creative pipeline** | **$7.61/month (~₹635)** |
| vs. freelance content creator (India) | ₹15,000–40,000/month |
| **Savings** | **96–98%** |

---

## 25. Monthly Cost Summary

### API Pricing Reference (verified May 2026)

| Service | Rate | Source |
|---|---|---|
| FLUX Kontext Pro (fal.ai) | $0.04/image | fal.ai/models/fal-ai/flux-pro/kontext |
| Kling 3.0 img2video (fal.ai) | ~$0.18/5s video | fal.ai pricing |
| Claude Sonnet 4.6 | $3/M input, $15/M output | Anthropic console |
| Nano Banana 2 (Gemini) | $0.045/image | Google AI Studio |
| Cloudinary free tier | 25GB storage, 25GB/month CDN | cloudinary.com |
| facebook-business SDK | free | Meta |
| Meta Graph API (organic) | free | Meta |
| SendGrid | free (100 emails/day) | sendgrid.com |
| Streamlit Community Cloud | free | share.streamlit.io |
| fal.ai (FLUX + Kling) | pay-as-you-go | fal.ai |

### Budget Scenarios

| Scenario | Weekly Creative Cost | Weekly Ad Spend | Total/Week |
|---|---|---|---|
| Phase 1 (1 campaign) | $1.90 | ₹3,500 ($42) | ~₹3,660 |
| Phase 2 (2 campaigns) | $1.90 | ₹4,900 ($59) | ~₹5,060 |
| Phase 3 (3 campaigns) | $2.20 | ₹10,500 ($126) | ~₹10,685 |

---

## 26. Critical Pre-Launch Checklist

These must be completed before any real money is spent on Meta ads:

```
SECURITY (do before anything else):
□ .gitignore includes .env and service_account.json
□ pre-commit hook installed (blocks .env commits)
□ All secrets tested with python main.py check

DATA INTEGRITY:
□ SQLite WAL mode enabled (in utils/db.py)
□ All file paths use PROJECT_ROOT anchor (not relative)
□ ads_log.json idempotency check active in create_ads.py
□ fal.ai video jobs persist to pending_video_jobs.json before polling

PIPELINE GUARDS:
□ generate_images.py requires prompts_approved=1
□ post_organic.py requires creatives_approved=1
□ create_ads.py requires creatives_approved=1
□ create_ads.py checks for existing campaign before creating

SHOPIFY / META:
□ FSSAI number visible on all product pages
□ Meta Pixel installed and all 5 events verified firing
□ Abandoned cart email active in Shopify
□ System User Token has correct permissions (not over-permissioned)
□ Meta App Review submitted for Standard Access

MARKETING:
□ Phase 1 objective = OUTCOME_TRAFFIC (not OUTCOME_SALES)
□ Budget concentrated on 1 campaign (not split across 4 SKUs)
□ Hashtags use contextual per-post generation (not hardcoded set)
□ #indiantiktok removed from all hashtag pools
□ MIN_SPEND_INR_BEFORE_JUDGE = 2000 (not 200)
□ LEARNING_PHASE_DAYS = 14 (no optimisation before this)

FOUNDER UX:
□ Dashboard deployed to Streamlit Community Cloud (mobile access)
□ SendGrid API key set → notifications will fire
□ At least 1 founder face-to-camera Reel filmed and scheduled (Week 1)
□ 10+ beta product samples sent to trusted contacts for early reviews
```

---

## 27. Full `requirements.txt`

```
# Generated by pip-compile — do not edit manually
# Edit requirements.in and run: pip-compile requirements.in

anthropic==0.40.0
fal-client==0.5.2
google-generativeai==0.8.3
facebook-business==22.0.0
cloudinary==1.40.0
gspread==6.1.2
google-auth==2.29.0
requests==2.32.3
click==8.1.7
python-dotenv==1.0.1
tenacity==9.0.0
streamlit==1.45.1
pyyaml==6.0.2
tabulate==0.9.0
sendgrid==6.11.0
keyring==25.2.1
youtube-discovery==2.0.0     # Week 4 only
```

**`requirements.in`** (human-maintained, loose):

```
anthropic>=0.40.0
fal-client>=0.5.0
google-generativeai>=0.8.0
facebook-business>=22.0.0,<23.0.0   # pin major — SDK has breaking changes between majors
cloudinary>=1.40.0
gspread>=6.0.0
requests>=2.32.0
click>=8.1.0
python-dotenv>=1.0.0
tenacity>=9.0.0
streamlit>=1.45.0
pyyaml>=6.0.1
tabulate>=0.9.0
sendgrid>=6.11.0
keyring>=25.0.0
```

```bash
# Regenerate pinned requirements.txt after updating requirements.in:
pip install pip-tools
pip-compile requirements.in --output-file requirements.txt
```

---

## 28. `.env.example`

```dotenv
# More Green Automation — Environment Variables
# Copy to .env and fill in real values. NEVER commit .env to git.

# ── Anthropic (Claude — prompt generation) ───────────────────────────────────
# https://console.anthropic.com/settings/keys
ANTHROPIC_API_KEY=sk-ant-...

# ── fal.ai (FLUX Kontext + Kling 3.0) ────────────────────────────────────────
# https://fal.ai/dashboard/keys  (add payment method first)
FAL_KEY=fal-...

# ── Google AI (Nano Banana 2 — backgrounds only) ─────────────────────────────
# https://aistudio.google.com  → Get API key
GOOGLE_API_KEY=AIza...

# ── Cloudinary (media hosting) ───────────────────────────────────────────────
# https://cloudinary.com → free account → Dashboard
CLOUDINARY_CLOUD_NAME=
CLOUDINARY_API_KEY=
CLOUDINARY_API_SECRET=

# ── Meta (posting + ads) ─────────────────────────────────────────────────────
# developers.facebook.com → your app → Settings → Basic
META_APP_ID=
META_APP_SECRET=
# Business Manager → System Users → Generate Token (never expires)
META_ACCESS_TOKEN=
# Business Manager → Ad Accounts → your account ID (starts with act_)
META_AD_ACCOUNT_ID=act_
# Your Facebook Page numeric ID
META_PAGE_ID=
# Your Instagram Professional Account numeric ID
META_IG_ACCOUNT_ID=
# Meta Pixel ID (from Events Manager)
META_PIXEL_ID=
# Custom Audience ID for Shopify customer sync (create empty audience first)
META_CUSTOMER_AUDIENCE_ID=

# ── Notifications ─────────────────────────────────────────────────────────────
# https://app.sendgrid.com/settings/api_keys  (free tier: 100 emails/day)
SENDGRID_API_KEY=
FOUNDER_EMAIL=bs.moregreen@gmail.com

# ── YouTube (Week 4 expansion) ────────────────────────────────────────────────
YOUTUBE_API_KEY=

# ── Shopify (for audience sync + blog posts) ──────────────────────────────────
SHOPIFY_STORE_URL=https://moregreen.myshopify.com
SHOPIFY_ACCESS_TOKEN=

# ── Google Sheets (content calendar input) ────────────────────────────────────
# service_account.json file in project root (gitignored)
GOOGLE_SHEETS_ID=your_sheet_id_here
```

---

*Plan version: 1.0 — Synthesised from parallel UX/UI, Software Architecture, and Marketing Strategy audits.*
*Total audit tokens: ~61,500 input + ~19,100 output across 3 agents, runtime: ~6 minutes parallel.*
*Estimated time to implement Phase 1 (Week 1 MVP): 2 focused days.*
*Estimated monthly running cost at Phase 1: $7.61 creative pipeline + ₹15,400 ad spend.*
