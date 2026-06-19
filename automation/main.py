import click
from dotenv import load_dotenv

load_dotenv()


@click.group()
@click.option("--dry-run", is_flag=True, default=False, help="Log actions without API calls or spend.")
@click.option("--verbose", is_flag=True, default=False, help="Debug-level logging.")
@click.pass_context
def cli(ctx, dry_run, verbose):
    ctx.ensure_object(dict)
    ctx.obj["dry_run"] = dry_run
    ctx.obj["verbose"] = verbose
    from utils.logging_config import configure
    configure(verbose=verbose)


@cli.command()
@click.pass_context
def check(ctx):
    """Validate all service credentials."""
    from commands.check_credentials import run
    run()


@cli.command()
@click.pass_context
def onboard(ctx):
    """Interactive first-time setup wizard."""
    from commands.onboard import run
    run()


@cli.command("sync-sheets")
@click.pass_context
def sync_sheets(ctx):
    """Pull Google Sheets content calendar into SQLite."""
    from commands.sync_sheets import run
    run(dry_run=ctx.obj["dry_run"])


@cli.command("generate-prompts")
@click.option("--week", default=None, help="ISO week e.g. 2026-W24")
@click.option("--post", default=None, help="Specific post ID e.g. W24_MON_01")
@click.pass_context
def generate_prompts(ctx, week, post):
    """Generate image/video/caption prompts via Claude API."""
    from commands.generate_prompts import run
    run(week=week, post_id=post, dry_run=ctx.obj["dry_run"])


@cli.command("approve-prompts")
@click.option("--post", default=None, help="Specific post ID")
@click.option("--all", "approve_all", is_flag=True, default=False, help="Approve all pending prompts.")
@click.pass_context
def approve_prompts(ctx, post, approve_all):
    """Mark prompts approved (CLI shortcut; dashboard preferred)."""
    from utils.db import get_db
    import logging
    log = logging.getLogger(__name__)
    db = get_db()
    if approve_all:
        with db:
            db.execute("UPDATE posts SET prompts_approved=1, prompts_approved_at=datetime('now') WHERE prompts_approved=0")
        log.info("All pending prompts approved.")
    elif post:
        with db:
            db.execute("UPDATE posts SET prompts_approved=1, prompts_approved_at=datetime('now') WHERE post_id=?", (post,))
        log.info("Prompts approved for %s", post)
    else:
        raise click.UsageError("Provide --post <id> or --all")


@cli.command("generate-creatives")
@click.option("--week", default=None)
@click.option("--post", default=None)
@click.option("--strength", default=0.75, show_default=True, type=click.FloatRange(0.1, 1.0),
              help="FLUX Kontext img2img strength. Lower = product label sharper. "
                   "0.65 if label is blurry, 0.75 default, 0.85+ if scene needs more change.")
@click.option("--aspect-ratio", default="3:4", show_default=True,
              type=click.Choice(["1:1", "3:4", "4:3", "9:16", "16:9"]),
              help="Output image aspect ratio. 3:4 for feed posts, 9:16 for Stories.")
@click.pass_context
def generate_creatives(ctx, week, post, strength, aspect_ratio):
    """Generate images or videos per post_type set in Google Sheets.
    reels → Kling video. feed_image / static / carousel / story → FLUX image."""
    import logging
    from utils.db import get_db
    log = logging.getLogger(__name__)
    dry_run = ctx.obj["dry_run"]

    VIDEO_TYPES = {"reels"}
    IMAGE_TYPES = {"feed_image", "static", "carousel", "story"}

    db = get_db()
    query = "SELECT post_id, post_type FROM posts WHERE prompts_approved=1 AND on_hold=0"
    params = []
    if week:
        query += " AND post_id LIKE ?"
        params.append(f"{week}%")
    if post:
        query += " AND post_id = ?"
        params.append(post)
    posts = db.execute(query, params).fetchall()

    image_ids = [r["post_id"] for r in posts if r["post_type"] in IMAGE_TYPES]
    video_ids = [r["post_id"] for r in posts if r["post_type"] in VIDEO_TYPES]
    unknown = [r for r in posts if r["post_type"] not in IMAGE_TYPES | VIDEO_TYPES]

    for r in unknown:
        log.warning("Unknown post_type '%s' for %s — skipping. Set to feed_image or reels in Sheet.",
                    r["post_type"], r["post_id"])

    if image_ids:
        from commands.generate_images import run as run_images
        for pid in image_ids:
            run_images(post_id=pid, dry_run=dry_run, strength=strength, aspect_ratio=aspect_ratio)

    if video_ids:
        from commands.generate_videos import run as run_videos
        for pid in video_ids:
            run_videos(post_id=pid, dry_run=dry_run)


@cli.command("upload-media")
@click.option("--week", default=None)
@click.option("--post", default=None)
@click.pass_context
def upload_media(ctx, week, post):
    """Upload local creatives to Cloudinary."""
    from commands.upload_media import run
    run(week=week, post_id=post, dry_run=ctx.obj["dry_run"])


@cli.command("post-organic")
@click.option("--week", default=None)
@click.option("--post", default=None)
@click.option("--platform", default="both", type=click.Choice(["instagram", "facebook", "both"]))
@click.pass_context
def post_organic(ctx, week, post, platform):
    """Post approved creatives to Instagram and/or Facebook."""
    from commands.post_organic import run
    run(platform=platform, post_id=post, dry_run=ctx.obj["dry_run"])


@cli.command("post-youtube")
@click.option("--post", default=None)
@click.pass_context
def post_youtube(ctx, post):
    """Cross-post Reels to YouTube Shorts."""
    from commands.post_youtube import run
    run(post_id=post, dry_run=ctx.obj["dry_run"])


@cli.command("create-ads")
@click.option("--post", default=None)
@click.pass_context
def create_ads(ctx, post):
    """Create Meta ad campaign (always starts PAUSED)."""
    from commands.create_ads import run
    run(post_id=post, dry_run=ctx.obj["dry_run"])


@cli.command("score-creatives")
@click.pass_context
def score_creatives(ctx):
    """Score creatives by ad CTR and mark promote-worthy ones selected (E5-T3)."""
    from commands.score_creatives import run
    run(dry_run=ctx.obj["dry_run"])


@cli.command("sync-orders")
@click.option("--days", default=30, show_default=True, type=int,
              help="On first run, look back this many days for orders.")
@click.pass_context
def sync_orders(ctx, days):
    """Ingest Shopify orders into the orders table (per-SKU, for attribution)."""
    from commands.sync_orders import run
    run(dry_run=ctx.obj["dry_run"], days=days)


@cli.command("monitor-ads")
@click.pass_context
def monitor_ads(ctx):
    """Fetch and display ad performance insights."""
    from commands.monitor_ads import run
    run()


@cli.command("compute-attribution")
@click.option("--days", default=30, show_default=True, type=int,
              help="Compute ROAS rollups for the last N days.")
@click.pass_context
def compute_attribution(ctx, days):
    """Compute blended/paid ROAS rollups by sku/campaign/blended into attribution."""
    from commands.attribution import run
    run(dry_run=ctx.obj["dry_run"], days=days)


@cli.command("tune-ads")
@click.option("--apply", is_flag=True, default=False, help="Apply changes (default is dry-run).")
@click.pass_context
def tune_ads(ctx, apply):
    """Apply pause/scale/refresh rules to active ad campaigns."""
    from commands.tune_ads import run
    run(dry_run=not apply)


@cli.command("strategize")
@click.option("--days", default=14, show_default=True, type=int,
              help="Look back this many days of blended-ROAS attribution.")
@click.pass_context
def strategize(ctx, days):
    """Rank SKUs by blended ROAS and write spend/content proposals (no autonomous spend)."""
    from commands.strategize import run
    run(dry_run=ctx.obj["dry_run"], days=days)


@cli.command("apply-approved")
@click.pass_context
def apply_approved(ctx):
    """Apply human-approved spend proposals to Meta (only path that raises budget)."""
    from commands.apply_approved import run
    run(dry_run=ctx.obj["dry_run"])


@cli.command("resume-video-jobs")
@click.pass_context
def resume_video_jobs(ctx):
    """Poll pending fal.ai video jobs from pending_video_jobs.json."""
    from commands.generate_videos import resume_pending
    resume_pending()


@cli.command("verify-media")
@click.pass_context
def verify_media(ctx):
    """Check all Cloudinary URLs return HTTP 200."""
    from commands.verify_media import run
    run()


@cli.command("new-week")
@click.pass_context
def new_week(ctx):
    """Scaffold next week's rows in Google Sheets."""
    from commands.new_week import run
    run()


@cli.command("seed-calendar")
@click.option("--include-sundays", is_flag=True, default=False,
              help="Include Sunday story posts (skipped by default).")
@click.option("--sprint", default=None,
              help="Only seed posts on or after this date e.g. 2026-06-10")
@click.pass_context
def seed_calendar(ctx, include_sundays, sprint):
    """Push all calendar.yaml posts to Google Sheets for review."""
    from commands.seed_calendar import run
    run(dry_run=ctx.obj["dry_run"], include_sundays=include_sundays, sprint=sprint)


@cli.command("find-influencers")
@click.option("--hashtag", multiple=True, help="Override default hashtags (repeatable).")
@click.pass_context
def find_influencers(ctx, hashtag):
    """Search Instagram hashtags to discover micro-influencers, store in DB, export CSV."""
    from commands.find_influencers import run
    run(hashtags=list(hashtag) or None, dry_run=ctx.obj["dry_run"])


@cli.command("chrome-find-influencers")
@click.option("--hashtag", multiple=True, help="Override default hashtags (repeatable).")
@click.option("--limit", default=None, type=int, help="Max profiles to check per hashtag (default 20).")
@click.option("--total", default=None, type=int, help="Stop once this many new influencers are saved.")
@click.pass_context
def chrome_find_influencers(ctx, hashtag, limit, total):
    """Discover influencers via Playwright browser — no Meta API needed.
    Opens Chrome, log in to Instagram manually on first run.
    Session is saved automatically for subsequent runs."""
    from commands.chrome_find_influencers import run
    run(hashtags=list(hashtag) or None, dry_run=ctx.obj["dry_run"], limit=limit, total=total)


@cli.command("outreach-email")
@click.pass_context
def outreach_email(ctx):
    """Send personalised collab emails (SendGrid) + write DM templates for manual Instagram outreach."""
    from commands.outreach_email import run
    run(dry_run=ctx.obj["dry_run"])


@cli.command("generate-dm-drafts")
@click.pass_context
def generate_dm_drafts(ctx):
    """Generate personalised DM text file for manual Instagram sends."""
    from commands.generate_dm_drafts import run
    run(dry_run=ctx.obj["dry_run"])


@cli.command("check-replies")
@click.pass_context
def check_replies(ctx):
    """Poll IG conversation threads, draft replies, wait for approval before sending."""
    from commands.check_replies import run
    run(dry_run=ctx.obj["dry_run"])


@cli.command("update-tracker")
@click.pass_context
def update_tracker(ctx):
    """Sync influencer DB to Google Sheet tracker (first run migrates Excel data)."""
    from commands.update_tracker import run
    run(dry_run=ctx.obj["dry_run"])


@cli.command("influencer-status")
@click.pass_context
def influencer_status(ctx):
    """Print a quick summary of the influencer campaign pipeline."""
    from commands.influencer_status import run
    run()


@cli.command("seedance-video")
@click.option("--prompt", required=True, help="Text prompt describing the video.")
@click.option("--image", "images", multiple=True, help="Reference image URL (repeatable, max 2).")
@click.option("--video", default=None, help="Reference video URL.")
@click.option("--audio", default=None, help="Reference audio URL.")
@click.option("--ratio", default="9:16", show_default=True, help="Aspect ratio e.g. 9:16 or 16:9.")
@click.option("--duration", default=8, show_default=True, type=int, help="Video length in seconds (max 11).")
@click.option("--out", default=None, help="Output filename (saved to creatives/seedance/).")
@click.pass_context
def seedance_video(ctx, prompt, images, video, audio, ratio, duration, out):
    """Generate a video with BytePlus SeeDance 2.0."""
    from commands.generate_seedance import run
    run(
        prompt=prompt,
        images=images,
        video=video,
        audio=audio,
        ratio=ratio,
        duration=duration,
        out=out,
        dry_run=ctx.obj["dry_run"],
    )


@cli.command("sync-audience")
@click.pass_context
def sync_audience(ctx):
    """Sync Shopify customer emails to Meta Custom Audience."""
    from commands.sync_audience import run
    run(dry_run=ctx.obj["dry_run"])


@cli.command("export-report")
@click.pass_context
def export_report(ctx):
    """Export weekly performance summary."""
    from commands.export_report import run
    run()


@cli.command("storefront-audit")
@click.pass_context
def storefront_audit(ctx):
    """Read live Shopify products + landing performance (read-only)."""
    from commands.storefront_audit import run
    run(dry_run=ctx.obj["dry_run"])


@cli.command("storefront-propose")
@click.pass_context
def storefront_propose(ctx):
    """Propose product-copy / margin-guardrailed price tests (write-gated via approval queue)."""
    from commands.storefront_propose import run
    run(dry_run=ctx.obj["dry_run"])


@cli.command("autopilot-calendar")
@click.option("--week-start", default=None, help="ISO date of week start e.g. 2026-06-22.")
@click.option("--slots", default=6, show_default=True, type=int, help="Posts to plan for the week.")
@click.option("--include-sundays", is_flag=True, default=False, help="Include Sunday story posts.")
@click.pass_context
def autopilot_calendar(ctx, week_start, slots, include_sundays):
    """Auto-seed posts from cultural calendar + perf gaps honoring sku_split (founder approves)."""
    from commands.autopilot_calendar import run
    run(dry_run=ctx.obj["dry_run"], week_start=week_start, slots=slots,
        include_sundays=include_sundays)


@cli.command("dashboard")
def dashboard():
    """Launch the Streamlit dashboard (or visit the deployed URL)."""
    import subprocess, sys
    subprocess.run(
        [sys.executable, "-m", "streamlit", "run", "commands/_dashboard_app.py"],
        check=True,
    )


if __name__ == "__main__":
    cli()
