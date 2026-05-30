import logging
import os

log = logging.getLogger(__name__)


def notify_founder(subject: str, body: str) -> None:
    """Send email via SendGrid. Silent no-op if SENDGRID_API_KEY is not set."""
    key = os.environ.get("SENDGRID_API_KEY")
    if not key:
        log.debug("SENDGRID_API_KEY not set — notification skipped: %s", subject)
        return
    try:
        from sendgrid import SendGridAPIClient
        from sendgrid.helpers.mail import Mail

        msg = Mail(
            from_email="automation@moregreen.in",
            to_emails=os.environ.get("FOUNDER_EMAIL", "bs.moregreen@gmail.com"),
            subject=f"[More Green] {subject}",
            plain_text_content=body,
        )
        SendGridAPIClient(key).send(msg)
        log.info("Notification sent: %s", subject)
    except Exception as e:
        log.warning("Notification failed (non-fatal): %s", e)
