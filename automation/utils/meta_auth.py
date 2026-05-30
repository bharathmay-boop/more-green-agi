import logging
import os

import requests

from config import META_GRAPH_BASE

log = logging.getLogger(__name__)

META_UNRECOVERABLE = {
    190: "Access token invalid. Re-generate System User Token in Business Manager.",
    200: "Permission denied. Check system user roles in Business Manager.",
    803: "Page access revoked. Re-add system user to the Page.",
    10:  "App permission missing. Check Meta App Review status.",
}


def validate_meta_token() -> None:
    """Call before any Meta API operation. Raises SystemExit on bad/missing token."""
    token = os.environ.get("META_ACCESS_TOKEN")
    if not token:
        raise SystemExit("META_ACCESS_TOKEN not set in .env")
    r = requests.get(
        f"{META_GRAPH_BASE}/me",
        params={"access_token": token, "fields": "id,name"},
        timeout=10,
    )
    body = r.json()
    if "error" in body:
        code = body["error"].get("code", 0)
        msg = META_UNRECOVERABLE.get(code, f"Meta API error: {body['error']}")
        raise SystemExit(f"Meta token check failed — {msg}")
    log.debug("Meta token valid for: %s (%s)", body.get("name"), body.get("id"))
