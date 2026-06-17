# More Green — Autonomous Build Engine

This directory drives the autonomous construction of the More Green marketing
platform. It turns the master plan (`docs/plan/`) into an executable, **resumable**
backlog and works it task-by-task, checkpointing to git after each one so it
survives usage-limit resets, context-window resets, and crashes.

## Files
- `backlog.yaml` — the task DAG (single source of truth). `status`, `depends_on`,
  `acceptance`, and `verify` per task.
- `orchestrate.py` — the runner: selects ready tasks (deps `done`), dispatches each
  to a headless Claude Code agent, runs its `verify`, marks `done`/`blocked`,
  regenerates `BUILD_PLAN.md`, and commits. *(E0-T2 — being implemented)*
- `resume.sh` — cron-safe wrapper: file lock, stale-lock reclaim, exponential
  backoff on usage-limit/rate-limit errors, WIP safeguard. *(E0-T3)*
- `BUILD_PLAN.md` — auto-generated human view, regenerated after every task. *(E0-T4)*
- `state.json` — last-run metadata (started_at, last_task, last_error, run_count).
- `logs/` — per-run logs.

## How continuation works (the important part)
All progress lives on disk (`backlog.yaml` + git history). Each task is atomic and
idempotent. If a run dies — usage limit hit, context reset, container reclaimed —
a fresh process simply reads `backlog.yaml` and continues from the next `todo`
whose dependencies are all `done`. Nothing is lost.

### Install the cron (on a persistent host: your laptop or a small server)
A browser tab or an ephemeral cloud container is **not** a durable host. Run the
cron where it can keep firing:

```bash
crontab -e
# then add:
*/15 * * * * cd /path/to/repo && bash build/resume.sh >> build/logs/cron.log 2>&1
```

`resume.sh` no-ops while a run holds the lock, and on usage-limit errors it backs
off (2→4→8→16 min) before the next cron tick continues. This is what makes the
build "continue after the limit reset time" without manual intervention.

## Running manually
```bash
python build/orchestrate.py --dry-run            # list ready tasks, dispatch nothing
python build/orchestrate.py --dispatch=mock      # run loop with no-op dispatch (sandbox)
python build/orchestrate.py --parallel 2         # real dispatch, 2 concurrent agents
bash   build/resume.sh --once --dry-run          # exercise lock + backoff path
```

## Sandbox fallback
In environments without the `claude` CLI / network / Postgres, use
`--dispatch=mock`. The state machine, verify, commit, and `BUILD_PLAN.md`
regeneration all run; only the code-writing dispatch is stubbed.

## Safety
The orchestrator never force-pushes, never edits `.env`/secrets, never deletes
user data, and never applies ad spend (all spend goes through the human
`approval_queue` — see `docs/plan/moregreen/04-approval-and-spend.md`). Every
state change is recorded; failed tasks are reverted to a clean tree and a
follow-up FIX task is opened.
