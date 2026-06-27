#!/usr/bin/env bash
set -uo pipefail

REPO="$HOME/Sync/GPT/CosmOS"
cd "$REPO"

# Check for any changes (tracked modified + untracked)
TRACKED_CHANGES=$(git diff --name-only 2>/dev/null || true)
UNTRACKED=$(git ls-files --others --exclude-standard 2>/dev/null || true)

if [[ -z "$TRACKED_CHANGES" && -z "$UNTRACKED" ]]; then
    # No changes — silent exit (watchdog pattern)
    exit 0
fi

# Stage everything (new + modified, respecting .gitignore)
git add -A

# Count what changed
CHANGED=$(git diff --cached --stat --name-only | wc -l)
DATE=$(date '+%Y-%m-%d %H:%M')

# Commit
git commit -m "chore: auto-sync $DATE" --quiet || true

# Push
git push origin main 2>&1 || echo "WARNING: push failed"

echo "Synced $CHANGED file(s) at $DATE"
