#!/usr/bin/env bash
set -euo pipefail

BASE="$HOME/.codex_multi"
BIN="$BASE/bin"
TARGETS=(
  codex-multi
  codex-profiles
  codex-profile-info
  codex-list-sessions
  codex-projects
  codex-sync-all
  codex-doctor
  codex-diff-resources
  codex-current
  codex-add-profile
  codex-prune-imports
  codex-export-profile
  codex-billing-open
  codex-balance
  codex-usage-open
  codex-copy-skills
  codex-login-profile
  codex-run-profile
  codex-resume-profile
  codex-import-context
  codex-set-meta
)

for name in "${TARGETS[@]}"; do
  rm -f "$BIN/$name"
done

echo "[codex-multi] wrappers removed from: $BIN"
echo "[codex-multi] note: profile directories under $BASE were not deleted"
