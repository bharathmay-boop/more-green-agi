#!/usr/bin/env python3
"""More Green Autonomous Build Engine — orchestrator (E0-T2 / E0-T4).

Reads build/backlog.yaml (the single source of truth), computes the ready set
(tasks whose status is `todo` and whose `depends_on` are all `done`), dispatches
each ready task to a code-writing agent, runs the task's `verify` command, marks
it `done`/`blocked`, regenerates BUILD_PLAN.md, writes state.json, and commits
its own artifacts to git after every task.

All state lives on disk (backlog.yaml + git), so a fresh process resumes from the
next ready task after a usage-limit reset, context reset, or crash. See
docs/plan/moregreen/02-build-engine.md.

Cross-platform: uses an atomic mkdir-based lock (no flock dependency) and runs
`verify` strings through bash when available (they are POSIX one-liners).

Usage:
    python build/orchestrate.py --dry-run                 # list ready tasks, dispatch nothing
    python build/orchestrate.py --dispatch=mock           # run loop with no-op dispatch (sandbox)
    python build/orchestrate.py --parallel 2              # real dispatch, 2 concurrent agents
    python build/orchestrate.py --once                    # one batch of ready tasks, then exit
    python build/orchestrate.py --task E1-T2              # force-run a single task
"""
from __future__ import annotations

import argparse
import datetime as _dt
import json
import os
import shutil
import socket
import subprocess
import sys
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

try:
    import yaml
except ImportError:  # pragma: no cover - dependency is declared in requirements
    sys.stderr.write("PyYAML is required: pip install pyyaml\n")
    raise

# ── paths ────────────────────────────────────────────────────────────────────
BUILD_DIR = Path(__file__).resolve().parent
REPO_ROOT = BUILD_DIR.parent
BACKLOG = BUILD_DIR / "backlog.yaml"
BUILD_PLAN = BUILD_DIR / "BUILD_PLAN.md"
STATE_FILE = BUILD_DIR / "state.json"
LOCK_DIR = BUILD_DIR / ".lock"
LOGS_DIR = BUILD_DIR / "logs"

STALE_LOCK_SECONDS = 30 * 60  # reclaim a lock whose holder is gone and stale
MAX_ATTEMPTS = 3              # blocked + founder alert after this many failures
DISPATCH_TIMEOUT = 60 * 30   # per-task headless agent timeout (seconds)

# Substrings that mean "stop now and let cron back off + retry later" rather than
# "this task failed". Matched case-insensitively against dispatch output.
USAGE_LIMIT_MARKERS = (
    "usage limit",
    "rate limit",
    "rate_limit",
    "429",
    "too many requests",
    "overloaded",
    "context_length_exceeded",
    "quota",
)


# ── small utilities ──────────────────────────────────────────────────────────
def now_iso() -> str:
    return _dt.datetime.now(_dt.timezone.utc).isoformat()


def log(msg: str) -> None:
    line = f"[{now_iso()}] {msg}"
    print(line, flush=True)


class UsageLimitHit(Exception):
    """Raised when a dispatch hits a usage/rate limit; caller backs off + exits."""


# ── backlog I/O ──────────────────────────────────────────────────────────────
def load_backlog() -> dict:
    if not BACKLOG.exists():
        raise SystemExit(f"backlog not found: {BACKLOG}")
    with BACKLOG.open("r", encoding="utf-8") as fh:
        data = yaml.safe_load(fh) or {}
    data.setdefault("meta", {})
    data.setdefault("tasks", [])
    return data


def save_backlog(data: dict) -> None:
    data.setdefault("meta", {})["updated_at"] = now_iso()
    with BACKLOG.open("w", encoding="utf-8") as fh:
        yaml.safe_dump(data, fh, sort_keys=False, default_flow_style=False, width=100)


def task_index(data: dict) -> dict[str, dict]:
    return {t["id"]: t for t in data["tasks"]}


def ready_tasks(data: dict) -> list[dict]:
    """Tasks that are todo and whose every dependency is done, in file order."""
    idx = task_index(data)
    out = []
    for t in data["tasks"]:
        if t.get("status") != "todo":
            continue
        deps = t.get("depends_on") or []
        if all(idx.get(d, {}).get("status") == "done" for d in deps):
            out.append(t)
    return out


def remaining_todo(data: dict) -> list[dict]:
    return [t for t in data["tasks"] if t.get("status") in ("todo", "in_progress")]


# ── portable lock (atomic mkdir, PID + heartbeat) ────────────────────────────
def _pid_alive(pid: int) -> bool:
    if pid <= 0:
        return False
    try:
        if os.name == "nt":
            out = subprocess.run(
                ["tasklist", "/FI", f"PID eq {pid}"],
                capture_output=True, text=True,
            ).stdout
            return str(pid) in out
        os.kill(pid, 0)
        return True
    except (OSError, ValueError):
        return False


def acquire_lock() -> bool:
    """Atomic mkdir lock. Reclaims a stale lock (holder gone AND old heartbeat)."""
    info = {"pid": os.getpid(), "host": socket.gethostname(),
            "started_at": now_iso(), "heartbeat": now_iso()}
    try:
        LOCK_DIR.mkdir()
    except FileExistsError:
        held = _read_lock_info()
        pid = held.get("pid", -1)
        hb = held.get("heartbeat", "")
        age = _age_seconds(hb)
        if not _pid_alive(pid) or age > STALE_LOCK_SECONDS:
            log(f"reclaiming stale lock (pid={pid} gone or stale, age={int(age)}s)")
            shutil.rmtree(LOCK_DIR, ignore_errors=True)
            try:
                LOCK_DIR.mkdir()
            except FileExistsError:
                return False
        else:
            log(f"lock held (pid={pid}, host={held.get('host')}); exiting")
            return False
    (LOCK_DIR / "info.json").write_text(json.dumps(info), encoding="utf-8")
    return True


def heartbeat() -> None:
    info = _read_lock_info()
    info["heartbeat"] = now_iso()
    try:
        (LOCK_DIR / "info.json").write_text(json.dumps(info), encoding="utf-8")
    except OSError:
        pass


def release_lock() -> None:
    shutil.rmtree(LOCK_DIR, ignore_errors=True)


def _read_lock_info() -> dict:
    try:
        return json.loads((LOCK_DIR / "info.json").read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}


def _age_seconds(iso: str) -> float:
    try:
        then = _dt.datetime.fromisoformat(iso)
        if then.tzinfo is None:
            then = then.replace(tzinfo=_dt.timezone.utc)
        return (_dt.datetime.now(_dt.timezone.utc) - then).total_seconds()
    except (ValueError, TypeError):
        return float("inf")


# ── git helpers (targeted, never global force) ───────────────────────────────
def git(*args: str, check: bool = False) -> subprocess.CompletedProcess:
    return subprocess.run(["git", *args], cwd=REPO_ROOT,
                          capture_output=True, text=True, check=check)


def git_commit_artifacts(paths: list[str], message: str) -> None:
    """Stage only the given paths plus build state, then commit if anything changed."""
    staged = list(paths) + ["build/backlog.yaml", "build/BUILD_PLAN.md", "build/state.json"]
    for p in staged:
        git("add", "--", p)
    status = git("status", "--porcelain").stdout.strip()
    if not status:
        return
    git("commit", "-m", message)
    log(f"committed: {message}")


def git_restore_artifacts(paths: list[str]) -> None:
    """Revert only this task's artifacts (tracked changes) — never global reset."""
    for p in paths:
        git("checkout", "--", p)        # tracked: revert to HEAD
        git("clean", "-fd", "--", p)    # untracked under that path: remove


# ── verify + dispatch ────────────────────────────────────────────────────────
def _run_shell(cmd: str, timeout: int) -> subprocess.CompletedProcess:
    """Run a POSIX one-liner through bash when available, else the native shell."""
    bash = shutil.which("bash")
    if bash:
        return subprocess.run([bash, "-lc", cmd], cwd=REPO_ROOT,
                              capture_output=True, text=True, timeout=timeout)
    return subprocess.run(cmd, cwd=REPO_ROOT, shell=True,
                          capture_output=True, text=True, timeout=timeout)


def run_verify(task: dict) -> tuple[bool, str]:
    cmd = task.get("verify")
    if not cmd:
        return True, "(no verify command)"
    try:
        cp = _run_shell(cmd, timeout=DISPATCH_TIMEOUT)
    except subprocess.TimeoutExpired:
        return False, "verify timed out"
    out = (cp.stdout or "") + (cp.stderr or "")
    return cp.returncode == 0, out.strip()[-2000:]


def _dispatch_prompt(task: dict) -> str:
    arts = ", ".join(task.get("artifacts") or [])
    return (
        f"You are a build agent for the More Green marketing platform. "
        f"Implement this task and nothing else.\n\n"
        f"Task {task['id']}: {task['title']}\n"
        f"Epic: {task.get('epic')}\nStory: {task.get('story')}\n"
        f"Acceptance: {task.get('acceptance')}\n"
        f"Files to create/modify (stay within these): {arts}\n\n"
        f"Follow the specs in docs/plan/ and the repo conventions in CLAUDE.md. "
        f"Make minimal, idempotent edits (create-or-update; additive migrations). "
        f"Do not touch .env or secrets. Do not apply ad spend. "
        f"When done, ensure this passes: {task.get('verify')}"
    )


def dispatch(task: dict, mode: str, log_fh) -> None:
    """Produce the task's code change. Raises UsageLimitHit to trigger backoff."""
    if mode == "mock":
        log_fh.write(f"[mock] would implement {task['id']}\n")
        return
    if mode == "claude":
        claude = shutil.which("claude")
        if not claude:
            raise RuntimeError("claude CLI not found; use --dispatch=mock")
        cmd = [claude, "-p", _dispatch_prompt(task),
               "--output-format", "json", "--permission-mode", "acceptEdits"]
        try:
            cp = subprocess.run(cmd, cwd=REPO_ROOT, capture_output=True,
                                text=True, timeout=DISPATCH_TIMEOUT)
        except subprocess.TimeoutExpired:
            raise RuntimeError(f"dispatch timed out after {DISPATCH_TIMEOUT}s")
        blob = ((cp.stdout or "") + (cp.stderr or ""))
        log_fh.write(blob + "\n")
        low = blob.lower()
        if any(m in low for m in USAGE_LIMIT_MARKERS):
            raise UsageLimitHit(task["id"])
        if cp.returncode != 0:
            raise RuntimeError(f"dispatch exited {cp.returncode}")
        return
    raise ValueError(f"unknown dispatch mode: {mode}")


# ── follow-up + alerts ───────────────────────────────────────────────────────
def open_followup(data: dict, task: dict, error: str) -> None:
    fix_id = f"{task['id']}-FIX"
    if any(t["id"] == fix_id for t in data["tasks"]):
        return
    data["tasks"].append({
        "id": fix_id,
        "epic": task.get("epic"),
        "story": task.get("story"),
        "title": f"Fix failing task {task['id']}: {task['title']}",
        "depends_on": [],
        "status": "todo",
        "agent": task.get("agent", "general-purpose"),
        "acceptance": task.get("acceptance"),
        "verify": task.get("verify"),
        "artifacts": task.get("artifacts", []),
        "attempts": 0,
        "last_error": error[-500:],
    })
    log(f"opened follow-up task {fix_id}")


def alert_founder(message: str) -> None:
    try:
        sys.path.insert(0, str(REPO_ROOT / "automation"))
        from utils.notifications import notify_founder  # type: ignore
        notify_founder(message)
    except Exception as exc:  # best-effort; never crash the loop on alerting
        log(f"(founder alert skipped: {exc})")


# ── state.json + BUILD_PLAN.md (E0-T4) ───────────────────────────────────────
def read_state() -> dict:
    try:
        return json.loads(STATE_FILE.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {"run_count": 0}


def write_state(**fields) -> None:
    st = read_state()
    st.update(fields)
    STATE_FILE.write_text(json.dumps(st, indent=2), encoding="utf-8")


def regen_build_plan(data: dict) -> None:
    tasks = data["tasks"]
    counts: dict[str, int] = {}
    for t in tasks:
        counts[t.get("status", "todo")] = counts.get(t.get("status", "todo"), 0) + 1
    total = len(tasks)
    done = counts.get("done", 0)
    pct = int(round(100 * done / total)) if total else 0

    # group by epic, preserve order
    epics: dict[str, list[dict]] = {}
    for t in tasks:
        epics.setdefault(t.get("epic", "(unassigned)"), []).append(t)

    icon = {"done": "✅", "in_progress": "🔄", "blocked": "⛔", "todo": "⬜"}
    lines = [
        "# Build Plan — auto-generated by build/orchestrate.py",
        "",
        f"_Last updated: {now_iso()}_",
        "",
        f"**Progress: {done}/{total} tasks done ({pct}%)** · "
        + " · ".join(f"{k}: {v}" for k, v in sorted(counts.items())),
        "",
    ]
    ready_ids = {t["id"] for t in ready_tasks(data)}
    for epic, items in epics.items():
        ed = sum(1 for t in items if t.get("status") == "done")
        lines.append(f"## {epic}  ({ed}/{len(items)})")
        lines.append("")
        for t in items:
            mark = icon.get(t.get("status", "todo"), "⬜")
            deps = ", ".join(t.get("depends_on") or []) or "—"
            tag = " _(ready)_" if t["id"] in ready_ids else ""
            lines.append(f"- {mark} **{t['id']}** {t['title']}{tag}  ")
            lines.append(f"    deps: {deps}")
            if t.get("last_error"):
                lines.append(f"    last_error: `{str(t['last_error'])[:160]}`")
        lines.append("")
    BUILD_PLAN.write_text("\n".join(lines), encoding="utf-8")


# ── core loop ────────────────────────────────────────────────────────────────
def process_task(task: dict, data: dict, mode: str) -> str:
    """Dispatch + verify one task. Returns new status. Raises UsageLimitHit."""
    LOGS_DIR.mkdir(parents=True, exist_ok=True)
    logpath = LOGS_DIR / f"run-{task['id']}-{int(time.time())}.log"
    arts = task.get("artifacts") or []
    with logpath.open("w", encoding="utf-8") as fh:
        try:
            dispatch(task, mode, fh)
        except UsageLimitHit:
            raise
        except Exception as exc:
            fh.write(f"dispatch error: {exc}\n")
            task["last_error"] = f"dispatch: {exc}"
            git_restore_artifacts(arts)
            return "blocked"
    ok, out = run_verify(task)
    with logpath.open("a", encoding="utf-8") as fh:
        fh.write(f"\n--- verify (ok={ok}) ---\n{out}\n")
    if ok:
        task["last_error"] = None
        return "done"
    task["last_error"] = f"verify failed: {out[:400]}"
    if mode != "mock":
        git_restore_artifacts(arts)  # keep tree clean; agent change reverted
    return "blocked"


def run(mode: str, parallel: int, once: bool, only_task: str | None,
        max_tasks: int | None) -> int:
    data = load_backlog()
    st = read_state()
    write_state(run_count=st.get("run_count", 0) + 1, started_at=now_iso(),
                last_error=None)
    processed = 0

    while True:
        heartbeat()
        if only_task:
            batch = [t for t in data["tasks"]
                     if t["id"] == only_task and t.get("status") != "done"]
        else:
            batch = ready_tasks(data)[:max(1, parallel)]

        if not batch:
            todo = remaining_todo(data)
            if todo:
                ids = ", ".join(t["id"] for t in todo)
                log(f"no ready tasks but {len(todo)} unfinished (blocked/cycle): {ids}")
                write_state(last_error=f"stalled: {ids}", finished_at=now_iso())
                regen_build_plan(data)
                git_commit_artifacts([], "build: stalled — no ready tasks")
                return 2
            log("all tasks done 🎉")
            write_state(last_error=None, finished_at=now_iso(), last_task=None)
            regen_build_plan(data)
            git_commit_artifacts([], "build: backlog complete")
            return 0

        # mark batch in_progress, checkpoint
        for t in batch:
            t["status"] = "in_progress"
            t["attempts"] = t.get("attempts", 0) + 1
        save_backlog(data)
        regen_build_plan(data)
        git_commit_artifacts([], "build: start " + ", ".join(t["id"] for t in batch))

        # dispatch (parallel) + verify
        try:
            if parallel > 1 and len(batch) > 1 and mode != "mock":
                with ThreadPoolExecutor(max_workers=parallel) as ex:
                    results = list(ex.map(
                        lambda t: (t, process_task(t, data, mode)), batch))
            else:
                results = [(t, process_task(t, data, mode)) for t in batch]
        except UsageLimitHit as hit:
            # roll the whole batch back to todo so a fresh run retries cleanly
            for t in batch:
                t["status"] = "todo"
            save_backlog(data)
            regen_build_plan(data)
            write_state(last_error=f"usage_limit:{hit}", last_task=str(hit),
                        finished_at=now_iso())
            git_commit_artifacts([], f"build: usage limit on {hit} — will resume")
            log(f"USAGE LIMIT hit on {hit}; exiting 75 for backoff")
            return 75  # EX_TEMPFAIL — resume.sh backs off on this

        # commit each result
        for t, status in results:
            t["status"] = status
            if status == "blocked":
                if t.get("attempts", 0) >= MAX_ATTEMPTS:
                    alert_founder(
                        f"Build task {t['id']} blocked after {t['attempts']} "
                        f"attempts: {t.get('last_error')}")
                else:
                    open_followup(data, t, str(t.get("last_error", "")))
            save_backlog(data)
            regen_build_plan(data)
            git_commit_artifacts(t.get("artifacts") or [],
                                 f"build: {t['id']} {status}")
            write_state(last_task=t["id"], last_error=t.get("last_error"))
            processed += 1
            log(f"{t['id']} -> {status}")

        if max_tasks and processed >= max_tasks:
            log(f"reached --max-tasks {max_tasks}; exiting")
            return 0
        if once or only_task:
            return 0


# ── CLI ──────────────────────────────────────────────────────────────────────
def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="More Green build orchestrator")
    ap.add_argument("--dry-run", action="store_true",
                    help="list ready tasks in dependency order; dispatch nothing")
    ap.add_argument("--dispatch", choices=["claude", "mock"], default="claude",
                    help="how to produce code changes (default: claude)")
    ap.add_argument("--parallel", type=int, default=1,
                    help="max concurrent ready tasks per batch")
    ap.add_argument("--once", action="store_true",
                    help="process a single batch of ready tasks, then exit")
    ap.add_argument("--task", default=None, help="force-run one task by id")
    ap.add_argument("--max-tasks", type=int, default=None,
                    help="stop after N tasks complete")
    args = ap.parse_args(argv)

    data = load_backlog()

    if args.dry_run:
        ready = ready_tasks(data)
        regen_build_plan(data)
        if not ready:
            todo = remaining_todo(data)
            print("No ready tasks." + (f" {len(todo)} unfinished (blocked/cycle)."
                                       if todo else " Backlog complete."))
            return 0
        print(f"Ready tasks ({len(ready)}), dependency order:")
        for t in ready:
            print(f"  {t['id']:<10} {t['title']}")
            print(f"             verify: {t.get('verify')}")
        return 0

    if not acquire_lock():
        return 0  # another run holds the lock; cron-safe no-op
    try:
        return run(args.dispatch, args.parallel, args.once, args.task,
                   args.max_tasks)
    finally:
        release_lock()


if __name__ == "__main__":
    raise SystemExit(main())
