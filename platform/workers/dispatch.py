"""dispatch.py — job-type → automation command registry.

Each Redis ``JobType`` defined in ``platform/apps/web/lib/queue.ts`` maps to a
handler that translates the job payload into the keyword arguments of the
existing ``automation/commands/*`` ``run()`` function and invokes it. Keeping the
mapping here (rather than in the entrypoint) lets it be unit-tested and reused.

Handlers all share the signature ``handler(payload: dict, dry_run: bool) -> None``.
Command modules are imported lazily inside each handler so that importing this
module (and ``--help``) never requires the automation runtime or its env.

Money-safety: dispatching a job is not the same as applying spend. Spend-raising
jobs (``apply_approved``) must already be gated by an approved ``approval_queue``
row before they are enqueued — see docs/plan/moregreen/04. ``dry_run`` forces
every command into no-write mode.
"""
from __future__ import annotations

import logging
from typing import Any, Callable, Dict

log = logging.getLogger(__name__)

Payload = Dict[str, Any]
Handler = Callable[[Payload, bool], None]


def _post_id(payload: Payload) -> str | None:
    """Accept either snake_case or the web's camelCase post id key."""
    return payload.get("post_id") or payload.get("postId")


def _generate(payload: Payload, dry_run: bool) -> None:
    """Generate image/video/caption prompts for a post (doc 02/06)."""
    from commands.generate_prompts import run
    run(week=payload.get("week"), post_id=_post_id(payload), dry_run=dry_run)


def _post_organic(payload: Payload, dry_run: bool) -> None:
    from commands.post_organic import run
    run(platform=payload.get("platform", "both"), post_id=_post_id(payload), dry_run=dry_run)


def _create_ads(payload: Payload, dry_run: bool) -> None:
    """Create a Meta ad campaign — always starts PAUSED (doc 04)."""
    from commands.create_ads import run
    run(post_id=_post_id(payload), dry_run=dry_run)


def _monitor_ads(payload: Payload, dry_run: bool) -> None:
    from commands.monitor_ads import run
    run()


def _tune_ads(payload: Payload, dry_run: bool) -> None:
    """Pause/scale/refresh rules. Dry-run unless payload opts into apply."""
    from commands.tune_ads import run
    apply = bool(payload.get("apply", False))
    run(dry_run=dry_run or not apply)


def _sync_orders(payload: Payload, dry_run: bool) -> None:
    from commands.sync_orders import run
    run(dry_run=dry_run, days=int(payload.get("days", 30)))


def _attribution(payload: Payload, dry_run: bool) -> None:
    from commands.attribution import run
    run(dry_run=dry_run, days=int(payload.get("days", 30)))


def _apply_approved(payload: Payload, dry_run: bool) -> None:
    """The only path that raises budget — gated upstream by approval_queue (doc 04)."""
    from commands.apply_approved import run
    run(dry_run=dry_run)


def _strategize(payload: Payload, dry_run: bool) -> None:
    from commands.strategize import run
    run(dry_run=dry_run, days=int(payload.get("days", 14)))


# Job type names mirror `JobType` in platform/apps/web/lib/queue.ts.
REGISTRY: Dict[str, Handler] = {
    "generate": _generate,
    "post_organic": _post_organic,
    "create_ads": _create_ads,
    "monitor_ads": _monitor_ads,
    "tune_ads": _tune_ads,
    "sync_orders": _sync_orders,
    "attribution": _attribution,
    "apply_approved": _apply_approved,
    "strategize": _strategize,
}


def dispatch(job_type: str, payload: Payload, dry_run: bool = False) -> None:
    """Invoke the handler for ``job_type``. Raises KeyError on unknown types."""
    handler = REGISTRY.get(job_type)
    if handler is None:
        known = ", ".join(sorted(REGISTRY))
        raise KeyError(f"unknown job type {job_type!r} (known: {known})")
    log.info("dispatch job_type=%s payload=%s dry_run=%s", job_type, payload, dry_run)
    handler(payload or {}, dry_run)
