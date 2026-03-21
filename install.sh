#!/usr/bin/env bash
set -euo pipefail

REPO_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BASE="$HOME/.codex_multi"
BIN="$BASE/bin"
TARGET="$BIN/codex-multi"

mkdir -p "$BIN"
cp "$REPO_DIR/codex_multi_manager.py" "$TARGET"
chmod +x "$TARGET"

make_wrapper() {
  local name="$1"
  local subcommand="$2"
  cat > "$BIN/$name" <<WRAP
#!/usr/bin/env bash
exec "\$HOME/.codex_multi/bin/codex-multi" $subcommand "\$@"
WRAP
  chmod +x "$BIN/$name"
}

make_wrapper "codex-profiles" "profiles"
make_wrapper "codex-profile-info" "info"
make_wrapper "codex-list-sessions" "sessions"
make_wrapper "codex-projects" "projects"
make_wrapper "codex-sync-all" "sync-all"
make_wrapper "codex-doctor" "doctor"
make_wrapper "codex-diff-resources" "diff"
make_wrapper "codex-current" "current"
make_wrapper "codex-add-profile" "add"
make_wrapper "codex-prune-imports" "prune-imports"
make_wrapper "codex-export-profile" "export-profile"
make_wrapper "codex-billing-open" "billing-open"
make_wrapper "codex-balance" "balance"
make_wrapper "codex-usage-open" "usage-open"
make_wrapper "codex-copy-skills" "copy-skills"
make_wrapper "codex-login-profile" "login"
make_wrapper "codex-run-profile" "run"
make_wrapper "codex-resume-profile" "resume"
make_wrapper "codex-import-context" "import-context"
make_wrapper "codex-set-meta" "set-meta"
make_wrapper "codex-sync" "sync"

SHELL_RC=""
if [[ -n "${ZSH_VERSION:-}" ]] || [[ "${SHELL:-}" == *"zsh" ]]; then
  SHELL_RC="$HOME/.zshrc"
elif [[ -n "${BASH_VERSION:-}" ]] || [[ "${SHELL:-}" == *"bash" ]]; then
  SHELL_RC="$HOME/.bashrc"
else
  SHELL_RC="$HOME/.profile"
fi

LINE='export PATH="$HOME/.codex_multi/bin:$PATH"'
if [[ -f "$SHELL_RC" ]]; then
  if ! grep -Fq "$LINE" "$SHELL_RC"; then
    printf '\n%s\n' "$LINE" >> "$SHELL_RC"
  fi
else
  printf '%s\n' "$LINE" > "$SHELL_RC"
fi

echo "[codex-multi] installed to: $TARGET"
echo "[codex-multi] wrapper commands installed under: $BIN"
echo "[codex-multi] shell rc updated: $SHELL_RC"
echo "[codex-multi] next steps:"
echo "  source $SHELL_RC"
echo "  codex-multi init --profiles test,vut"
echo "  codex-multi login test"
echo "  codex-profiles"
echo "  codex-doctor"
