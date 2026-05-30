import logging
import sys

from config import LOG_PATH


def configure(verbose: bool = False) -> None:
    LOG_PATH.parent.mkdir(exist_ok=True)
    level = logging.DEBUG if verbose else logging.INFO
    fmt = "%(asctime)s %(levelname)-8s %(name)-30s %(message)s"
    logging.basicConfig(
        level=level,
        format=fmt,
        handlers=[
            logging.FileHandler(str(LOG_PATH), encoding="utf-8"),
            logging.StreamHandler(sys.stdout),
        ],
    )
    for noisy in ("httpx", "anthropic._base_client", "fal_client", "urllib3"):
        logging.getLogger(noisy).setLevel(logging.WARNING)
