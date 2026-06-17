# 02 — Self-Continuing Build Engine

The engine turns the master plan into an executable, resumable backlog and works it autonomously. All state on disk → survives usage limits / context resets / crashes.

## Files
- `build/backlog.yaml` — task DAG (see schema below), the single source of truth.
- `build/orchestrate.py` — the runner loop.
- `build/resume.sh` — cron-safe wrapper (lock, backoff, restart).
- `build/BUILD_PLAN.md` — auto-generated human view (regenerated after every task).
- `build/state.json` — last run metadata (started_at, last_task, last_error, run_count).
- `build/logs/run-*.log` — per-run logs.
- `build/README.md` — install + cron + sandbox-fallback docs.

## `backlog.yaml` task schema
```yaml
- id: E2-S1-T3
  epic: E2 Profit loop
  story: Ingest Shopify orders
  title: Implement automation/commands/sync_orders.py
  depends_on: [E1-S2-T1]            # task ids
  status: todo                      # todo | in_progress | done | blocked
  agent: general-purpose            # subagent type to dispatch
  acceptance: "orders table upserts by order_id; --dry-run prints N orders, writes none"
  verify: "python automation/main.py --dry-run sync-orders"
  artifacts: [automation/commands/sync_orders.py]
  attempts: 0
  last_error: null
```

## Orchestrator state machine (per task)
```
todo --select--> in_progress --dispatch+verify--> done
                      |                              ^
                      |--verify fail / exception-----+--> blocked (attempts++, follow-up task opened)
blocked --(deps fixed or manual reset)--> todo
```

## Happy flow
1. Acquire `build/.lock` (flock). If held → exit 0 (another run active).
2. Load `backlog.yaml`; compute **ready set** = tasks with `status=todo` and all `depends_on` `done`.
3. For up to `--parallel N` ready tasks: set `in_progress`, commit backlog (`git commit -m "build: start <id>"`).
4. Dispatch each: headless `claude -p "<task title + acceptance + repo conventions>" --output-format json` (Agent-SDK call as fallback), scoped to that task's artifacts.
5. Run `verify` shell command. Exit 0 → `done`; else → `blocked`.
6. Regenerate `BUILD_PLAN.md`; `git add -A && git commit -m "build: <id> <status>"`.
7. Update `build_task` table (best-effort; skip if no Postgres). Loop to step 2 until ready set empty or time/usage budget exceeded.
8. Release lock; write `state.json`.

## Unhappy flows & handling
- **Usage limit / 429 / context exhausted** mid-dispatch → catch, mark task back to `todo` (not partially-done; rely on idempotent edits), record in `state.json`, exit non-zero. `resume.sh` backs off (2→4→8→16 min, capped) and re-runs; cron also re-fires every 15 min.
- **Agent produced bad/failing change** → `verify` fails → `blocked`; orchestrator runs `git restore`/`git reset --hard` of *only that task's uncommitted artifacts* (never global), opens follow-up task `E?-FIX-<id>`, continues with other ready tasks. After 3 `attempts` → `blocked` + founder alert via `notify_founder`.
- **Dependency cycle / no ready tasks but todos remain** → detect cycle, log offending ids, alert, exit.
- **Dirty working tree from a previous crash** → `resume.sh` stashes/commits WIP under `build/wip` branch before continuing; never discards silently.
- **Lock held by dead process** → lock file stores PID + heartbeat; stale (>30 min, PID gone) → reclaimed.
- **Concurrent agents editing same file** → backlog `depends_on` must serialize file-overlapping tasks; the seed backlog encodes these deps so parallel tasks are file-disjoint.
- **Git push fails (network)** → retry 2/4/8/16s ×4 (matches repo guidance); if still failing, keep committing locally and continue (push later).
- **Verify command itself missing deps** → task `blocked` with "env not ready", and a prerequisite env-setup task is surfaced.

## Cron / resume
- `resume.sh --once` runs a single pass; bare `resume.sh` is the cron entry.
- Add to `automation/crontab.example`:
  `*/15 * * * * cd <repo> && bash build/resume.sh >> build/logs/cron.log 2>&1`
- `build/README.md` documents `crontab -e` install. We **provide** the cron line; we do **not** silently mutate the user's crontab.
- Sandbox fallback: `--dispatch=mock` runs the loop and verifies without calling Claude (for environments without API/network), proving the state machine.

## Idempotency & safety
- Every task edit is designed to be re-applied safely (create-or-update, additive migrations).
- Orchestrator never: force-pushes, edits `.env`/secrets, deletes user content, or applies ad spend (that path goes through `approval_queue`, doc 04).
- All actions append `audit_log` (actor=`orchestrator`).
