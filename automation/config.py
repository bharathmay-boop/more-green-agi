import yaml
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.resolve()


def _load(filename: str) -> dict:
    return yaml.safe_load((PROJECT_ROOT / "config" / filename).read_text(encoding="utf-8"))


_brand    = _load("brand.yaml")
_hashtags = _load("hashtags.yaml")
_calendar = _load("cultural_calendar.yaml")

# ── Paths ─────────────────────────────────────────────────────────────────────
STRATEGY_DIR  = PROJECT_ROOT / "strategy"
CREATIVES_DIR = PROJECT_ROOT / "creatives"
CALENDAR_PATH = STRATEGY_DIR / "calendar.yaml"
DB_PATH       = PROJECT_ROOT / "db" / "pipeline.db"
LOG_PATH      = PROJECT_ROOT / "logs" / "moregreen.log"

# ── Brand ─────────────────────────────────────────────────────────────────────
BRAND_NAME     = _brand["brand"]["name"]
BRAND_WEBSITE  = _brand["brand"]["website"]
BRAND_HANDLE   = _brand["brand"]["instagram_handle"]
BRAND_VOICE    = _brand["brand"]["voice_brief"]
BANNED_PHRASES = _brand["brand"]["banned_phrases"]

# ── SKUs ──────────────────────────────────────────────────────────────────────
SKUS = {sku["id"]: sku for sku in _brand["skus"]}

# ── Hashtags ──────────────────────────────────────────────────────────────────
HASHTAGS = _hashtags

# ── Cultural Calendar ─────────────────────────────────────────────────────────
CULTURAL_CALENDAR = _calendar["events"]

# ── Image / Video Generation ──────────────────────────────────────────────────
IMAGE_VARIANTS_PER_POST  = 3
IMAGE_ASPECT_RATIO_FEED  = "1:1"
IMAGE_ASPECT_RATIO_REELS = "9:16"
VIDEO_DURATION_SECONDS   = 5
VIDEO_RESOLUTION         = "720p"

# ── Meta Ads ──────────────────────────────────────────────────────────────────
META_GRAPH_VERSION = "v22.0"
META_GRAPH_BASE    = f"https://graph.facebook.com/{META_GRAPH_VERSION}"
META_CURRENCY      = "INR"
META_CAMPAIGN_PHASE = 1  # 1=traffic, 2=atc, 3=purchase — change per phase

META_TARGETING_LAUNCH = {
    "geo_locations": {
        "cities": [
            {"key": "2264456", "name": "Bengaluru"},
            {"key": "2271168", "name": "Pune"},
        ]
    },
    "age_min": 24,
    "age_max": 42,
    "publisher_platforms": ["facebook", "instagram"],
    "facebook_positions": ["feed", "reels"],
    "instagram_positions": ["stream", "reels"],
}

META_TARGETING_GROWTH = {
    "geo_locations": {
        "countries": ["IN"],
        "cities": [
            {"key": "2295424", "name": "Mumbai"},
            {"key": "2264456", "name": "Bengaluru"},
            {"key": "2276893", "name": "Delhi"},
            {"key": "2281955", "name": "Hyderabad"},
            {"key": "2271168", "name": "Pune"},
        ],
    },
    "age_min": 22,
    "age_max": 45,
}

META_BUDGET_PHASE = {
    1: 500,
    2: 700,
    3: 1500,
}

META_CAMPAIGN_OBJECTIVE_PHASE = {
    1: "OUTCOME_TRAFFIC",
    2: "OUTCOME_CONVERSIONS",
    3: "OUTCOME_SALES",
}

# ── Optimisation Thresholds ───────────────────────────────────────────────────
LEARNING_PHASE_DAYS          = 14
MIN_SPEND_INR_BEFORE_JUDGE   = 2000
PAUSE_CTR_FEED_BELOW         = 0.008
PAUSE_CTR_REELS_BELOW        = 0.012
SCALE_ROAS_ABOVE_WARM        = 3.0
SCALE_ROAS_ABOVE_COLD        = 2.0
SCALE_BUDGET_MULTIPLIER      = 1.20
CREATIVE_REFRESH_FREQUENCY   = 3.5
MAX_CPM_INR                  = 400

# ── API Endpoints ─────────────────────────────────────────────────────────────
FAL_FLUX_KONTEXT_ENDPOINT = "fal-ai/flux-pro/kontext"
FAL_KLING_ENDPOINT        = "fal-ai/kling-video/v2.1/standard/image-to-video"
FAL_NANO_BANANA_ENDPOINT  = "fal-ai/flux/dev"
ANTHROPIC_MODEL           = "claude-sonnet-4-6"
CLOUDINARY_FOLDER         = "more-green"

# ── Credential Rotation Notes ─────────────────────────────────────────────────
CREDENTIAL_NOTES = {
    "META_SYSTEM_USER_TOKEN": "No expiry. Page access can be silently revoked. Check monthly.",
    "FAL_KEY":                "No expiry. Rotate if anomalous usage detected.",
    "ANTHROPIC_API_KEY":      "No expiry. Rotate immediately if leaked.",
    "GOOGLE_API_KEY":         "No expiry. Quota resets daily.",
    "CLOUDINARY":             "No expiry. Tied to account. Never delete account.",
}
