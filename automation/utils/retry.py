import json
import logging
import time

import requests
from tenacity import retry, retry_if_exception_type, stop_after_attempt, wait_exponential

log = logging.getLogger(__name__)


class APIBodyError(Exception):
    """HTTP 200 but error payload in response body."""


@retry(
    retry=retry_if_exception_type(
        (APIBodyError, requests.ConnectionError, requests.Timeout, requests.HTTPError)
    ),
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
        raise APIBodyError(f"API error body: {body}")
    return body


def check_meta_rate_limit(response: requests.Response) -> None:
    """Parse X-App-Usage header and sleep if approaching limit."""
    usage = response.headers.get("X-App-Usage")
    if not usage:
        return
    try:
        data = json.loads(usage)
        pct = data.get("call_count", 0)
        if pct > 75:
            sleep_s = 100 - pct
            log.warning("Meta rate limit at %d%% — sleeping %ds", pct, sleep_s)
            time.sleep(sleep_s)
    except (json.JSONDecodeError, TypeError):
        pass
