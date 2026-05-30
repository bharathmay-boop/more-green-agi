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
    """Pull Google Sheets content calendar → SQLite."""
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
@click.option("--images-only", is_flag=True, default=False)
@click.option("--video-only", is_flag=True, default=False)
@click.pass_context
def generate_creatives(ctx, week, post, images_only, video_only):
    """Generate images (FLUX Kontext) and videos (Kling 3.0)."""
    dry_run = ctx.obj["dry_run"]
    if not video_only:
        from commands.generate_images import run as run_images
        run_images(week=week, post_id=post, dry_run=dry_run)
    if not images_only:
        from commands.generate_videos import run as run_videos
        run_videos(week=week, post_id=post, dry_run=dry_run)


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


@cli.command("monitor-ads")
@click.pass_context
def monitor_ads(ctx):
    """Fetch and display ad performance insights."""
    from commands.monitor_ads import run
    run()


@cli.command("tune-ads")
@click.option("--apply", is_flag=True, default=False, help="Apply changes (default is dry-run).")
@click.pass_context
def tune_ads(ctx, apply):
    """Apply pause/scale/refresh rules to active ad campaigns."""
    from commands.tune_ads import run
    run(dry_run=not apply)


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
