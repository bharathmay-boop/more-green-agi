import hashlib
import logging
import os

from utils.db import get_db

log = logging.getLogger(__name__)


def run(dry_run: bool = False) -> None:
    """Sync Shopify customer emails to Meta Custom Audience (SHA-256 hashed)."""
    import shopify
    from facebook_business.api import FacebookAdsApi
    from facebook_business.adobjects.customaudience import CustomAudience

    audience_id = os.environ.get("META_CUSTOMER_AUDIENCE_ID")
    if not audience_id:
        raise SystemExit("META_CUSTOMER_AUDIENCE_ID not set in .env")

    shopify.ShopifyResource.set_site(
        f"{os.environ['SHOPIFY_STORE_URL']}/admin/api/2024-01"
    )
    shopify.ShopifyResource.headers["X-Shopify-Access-Token"] = os.environ["SHOPIFY_ACCESS_TOKEN"]

    customers = shopify.Customer.find(limit=250)
    hashed = [
        hashlib.sha256(c.email.lower().strip().encode()).hexdigest()
        for c in customers
        if getattr(c, "email", None)
    ]
    log.info("Hashed %d customer emails", len(hashed))

    if dry_run:
        log.info("[DRY RUN] Would sync %d hashed emails to Meta Custom Audience %s", len(hashed), audience_id)
        return

    FacebookAdsApi.init(
        app_id=os.environ["META_APP_ID"],
        app_secret=os.environ["META_APP_SECRET"],
        access_token=os.environ["META_ACCESS_TOKEN"],
    )
    audience = CustomAudience(audience_id)
    audience.add_users(
        schema=CustomAudience.Schema.email_sha256,
        data=hashed,
    )
    log.info("Synced %d customers to Meta Custom Audience %s", len(hashed), audience_id)
