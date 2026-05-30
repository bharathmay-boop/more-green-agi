import os
import sys


def require(key: str) -> str:
    """Return env var value or exit with a clear message."""
    val = os.environ.get(key)
    if not val:
        sys.exit(
            f"ERROR: {key} is not set.\n"
            f"Add it to your .env file. See .env.example for the correct format."
        )
    return val


def get(key: str, default: str = "") -> str:
    """Return env var value or default — for optional secrets."""
    return os.environ.get(key, default)
