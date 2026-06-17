#!/usr/bin/env bash
# More Green Autonomous Build Engine — cron-safe resume wrapper (E0-T3).
#
# This is the cron entry point. It:
#   * holds a portable mkdir lock (no flock dependency; works on Linux/macOS/Git-Bash)
#   * reclaims a stale lock whose holder PID is gone
#   * safeguards a dirty working tree (commits WIP to a build/wip branch — never discards)
#   * runs build/orchestrate.py, and on a usage/rate-limit exit (75) backs off
#     2 -> 4 -> 8 -> 16 minutes and retries, so the build "continues after the
#     limit reset" without manual intervention. cron also re-fires every 15 min.
#
# Usage:
#   bash build/resume.sh                 # cron entry: lock, WIP-safe, run, backoff
#   bash build/resume.sh --once          # single orchestrator pass, then exit
#   bash build/resume.sh --once --dry-run  # exercise lock + backoff path, no dispatch
#
# Install (on a persistent host — laptop or small server, NOT a browser tab):
#   crontab -e
#   */15 * * * * cd /path/to/repo && bash build/resume.sh >> build/logs/cron.log 2>&1
set -uo pipefail

# ── locate repo (this script lives in <repo>/build) ──────────────────────────
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
cd "$REPO_ROOT" || exit 1

LOCK_DIR="$SCRIPT_DIR/.resume.lock"
LOGS_DIR="$SCRIPT_DIR/logs"
STALE_LOCK_SECONDS=$((30 * 60))
mkdir -p "$LOGS_DIR"

ONCE=0
DRY_RUN=0
for arg in "$@"; do
  case "$arg" in
    --once)    ONCE=1 ;;
    --dry-run) DRY_RUN=1 ;;
    *) echo "unknown arg: $arg" >&2; exit 64 ;;
  esac
done

log() { echo "[$(date -u +%Y-%m-%dT%H:%M:%SZ)] resume: $*"; }

# pick a python interpreter
PYTHON="$(command -v python3 || command -v python || true)"
if [ -z "$PYTHON" ]; then
  log "no python found"; exit 1
fi

# ── portable lock with stale reclaim ─────────────────────────────────────────
pid_alive() {
  local pid="$1"
  [ -z "$pid" ] && return 1
  if kill -0 "$pid" 2>/dev/null; then return 0; fi
  # Windows/Git-Bash fallback
  if command -v tasklist >/dev/null 2>&1; then
    tasklist //FI "PID eq $pid" 2>/dev/null | grep -q "$pid" && return 0
  fi
  return 1
}

acquire_lock() {
  if mkdir "$LOCK_DIR" 2>/dev/null; then
    echo "$$" > "$LOCK_DIR/pid"
    date -u +%s > "$LOCK_DIR/ts"
    return 0
  fi
  # lock exists — check staleness
  local held_pid held_ts now age
  held_pid="$(cat "$LOCK_DIR/pid" 2>/dev/null || echo '')"
  held_ts="$(cat "$LOCK_DIR/ts" 2>/dev/null || echo 0)"
  now="$(date -u +%s)"
  age=$(( now - held_ts ))
  if ! pid_alive "$held_pid" && [ "$age" -gt "$STALE_LOCK_SECONDS" ]; then
    log "reclaiming stale resume lock (pid=$held_pid gone, age=${age}s)"
    rm -rf "$LOCK_DIR"
    if mkdir "$LOCK_DIR" 2>/dev/null; then
      echo "$$" > "$LOCK_DIR/pid"; date -u +%s > "$LOCK_DIR/ts"; return 0
    fi
  fi
  log "another resume run holds the lock (pid=$held_pid); exiting"
  return 1
}

release_lock() { rm -rf "$LOCK_DIR"; }

# ── WIP safeguard: never discard a dirty tree from a previous crash ──────────
wip_safeguard() {
  if [ -n "$(git status --porcelain 2>/dev/null)" ]; then
    local branch stamp
    branch="$(git rev-parse --abbrev-ref HEAD 2>/dev/null || echo detached)"
    stamp="$(date -u +%Y%m%d-%H%M%S)"
    log "dirty tree detected; preserving WIP before run"
    git add -A
    git commit -m "build(wip): autosave dirty tree $stamp on $branch" >/dev/null 2>&1 \
      && log "WIP committed on $branch" \
      || log "nothing to commit"
  fi
}

# ── run orchestrator with usage-limit backoff ────────────────────────────────
run_orchestrator() {
  local dispatch="claude"
  local extra=()
  [ "$DRY_RUN" -eq 1 ] && dispatch="mock"
  [ "$ONCE" -eq 1 ] && extra+=(--once)

  # backoff schedule in minutes (2 -> 4 -> 8 -> 16, then cron handles the rest)
  local backoffs=(2 4 8 16)
  local attempt=0
  while :; do
    log "orchestrate.py --dispatch=$dispatch ${extra[*]:-}"
    "$PYTHON" build/orchestrate.py --dispatch="$dispatch" "${extra[@]}"
    local rc=$?
    if [ "$rc" -eq 75 ]; then
      if [ "$attempt" -ge "${#backoffs[@]}" ] || [ "$ONCE" -eq 1 ]; then
        log "usage limit; handing off to next cron tick (rc=75)"
        return 0
      fi
      local mins="${backoffs[$attempt]}"
      log "usage limit hit; backing off ${mins}m then retrying"
      [ "$DRY_RUN" -eq 1 ] && { log "(dry-run: skip real sleep)"; return 0; }
      sleep $(( mins * 60 ))
      attempt=$(( attempt + 1 ))
      continue
    fi
    return "$rc"
  done
}

main() {
  acquire_lock || exit 0
  trap release_lock EXIT
  [ "$DRY_RUN" -eq 0 ] && wip_safeguard
  run_orchestrator
  local rc=$?
  log "done (rc=$rc)"
  exit "$rc"
}

main
