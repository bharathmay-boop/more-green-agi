import logging
import os
import sys
from pathlib import Path

log = logging.getLogger(__name__)

_ENV_KEYS = [
    ("ANTHROPIC_API_KEY",       "Anthropic API key",       "https://console.anthropic.com/settings/keys"),
    ("FAL_KEY",                 "fal.ai API key",           "https://fal.ai/dashboard/keys"),
    ("GOOGLE_API_KEY",          "Google AI API key",        "https://aistudio.google.com"),
    ("CLOUDINARY_CLOUD_NAME",   "Cloudinary cloud name",    "https://cloudinary.com → Dashboard"),
    ("CLOUDINARY_API_KEY",      "Cloudinary API key",       "https://cloudinary.com → Dashboard"),
    ("CLOUDINARY_API_SECRET",   "Cloudinary API secret",    "https://cloudinary.com → Dashboard"),
    ("META_APP_ID",             "Meta App ID",              "https://developers.facebook.com → your app → Settings → Basic"),
    ("META_APP_SECRET",         "Meta App Secret",          "https://developers.facebook.com → your app → Settings → Basic"),
    ("META_ACCESS_TOKEN",       "Meta System User Token",   "Business Manager → System Users → Generate Token"),
    ("META_AD_ACCOUNT_ID",      "Meta Ad Account ID",       "Business Manager → Ad Accounts (starts with act_)"),
    ("META_PAGE_ID",            "Facebook Page ID",         "Your Facebook Page → About → Page ID"),
    ("META_IG_ACCOUNT_ID",      "Instagram Account ID",     "Business Manager → Instagram Accounts"),
    ("SENDGRID_API_KEY",        "SendGrid API key",         "https://app.sendgrid.com/settings/api_keys"),
    ("GOOGLE_SHEETS_ID",        "Google Sheets ID",         "Your sheet URL: .../spreadsheets/d/<THIS_PART>/"),
]

_ENV_PATH = Path(__file__).parent.parent / ".env"


def run() -> None:
    print("\nMore Green Automation — First-Time Setup\n")
    print("This wizard will help you fill in your .env file.")
    print("Press Enter to keep an existing value.\n")

    existing = _load_existing()
    updates = {}

    for key, label, url in _ENV_KEYS:
        current = existing.get(key, "")
        prompt = f"{label}\n  → {url}\n  {key}"
        if current:
            prompt += f" [{current[:8]}...]"
        prompt += ": "
        value = input(prompt).strip()
        if value:
            updates[key] = value
        elif current:
            updates[key] = current

    _write_env(updates, existing)
    print(f"\n.env written to {_ENV_PATH}")
    print("Run: python main.py check")


def _load_existing() -> dict:
    if not _ENV_PATH.exists():
        return {}
    result = {}
    for line in _ENV_PATH.read_text(encoding="utf-8").splitlines():
        if "=" in line and not line.startswith("#"):
            k, _, v = line.partition("=")
            result[k.strip()] = v.strip()
    return result


def _write_env(updates: dict, existing: dict) -> None:
    merged = {**existing, **updates}
    lines = []
    for k, v in merged.items():
        lines.append(f"{k}={v}")
    _ENV_PATH.write_text("\n".join(lines) + "\n", encoding="utf-8")
