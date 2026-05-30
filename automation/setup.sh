#!/usr/bin/env bash
set -euo pipefail

HOOK=".git/hooks/pre-commit"

mkdir -p .git/hooks

cat > "$HOOK" << 'HOOK_EOF'
#!/usr/bin/env bash
if git diff --cached --name-only | grep -qE '\.env$|\.env\.|service_account\.json'; then
  echo "ERROR: Attempting to commit a secrets file. Aborting."
  echo "Remove the file from staging: git reset HEAD <file>"
  exit 1
fi
HOOK_EOF

chmod +x "$HOOK"
echo "Pre-commit hook installed."
