#!/usr/bin/env bash
set -euo pipefail

REPO_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
TMPDIR="$(mktemp -d)"
trap 'rm -rf "$TMPDIR"' EXIT

export HOME="$TMPDIR/home"
mkdir -p "$HOME/bin" "$HOME/.codex/skills" "$HOME/.codex/superpowers" "$HOME/.codex/rules" "$HOME/repo"
export PATH="$HOME/bin:$PATH"

cat > "$HOME/bin/codex" <<'STUB'
#!/usr/bin/env bash
set -euo pipefail
CMD="${1:-}"
shift || true
mkdir -p "${CODEX_HOME:?missing CODEX_HOME}"
case "$CMD" in
  login)
    printf '{"fake":true}\n' > "$CODEX_HOME/auth.json"
    ;;
  resume)
    echo "fake-resume $*"
    ;;
  *)
    echo "fake-codex $CMD $*"
    ;;
esac
STUB
chmod +x "$HOME/bin/codex"

cat > "$HOME/.codex/config.toml" <<'EOF2'
model = "gpt-5"
EOF2
printf 'skill-a\n' > "$HOME/.codex/skills/demo.txt"
printf 'superpower-a\n' > "$HOME/.codex/superpowers/demo.txt"
printf 'rule-a\n' > "$HOME/.codex/rules/demo.txt"
mkdir -p "$HOME/.codex/sessions/2026/03/21"
cat > "$HOME/.codex/sessions/2026/03/21/rollout-test.jsonl" <<EOF2
{"type":"session_meta","cwd":"$HOME/repo"}
{"message":"hello from app profile"}
EOF2

cd "$REPO_DIR"
./install.sh >/dev/null
source "$HOME/.bashrc"

codex-multi init --profiles test,aux >/dev/null
codex-multi login test >/dev/null
codex-multi sync test app >/dev/null
codex-copy-skills app test --with-superpowers >/dev/null
codex-multi set-meta test --label "Test CLI" --account-kind chatgpt --billing-url https://example.com/billing --usage-url https://example.com/usage --notes "smoke" >/dev/null
codex-multi import-context app test "$HOME/repo" >/dev/null
codex-multi export-profile test --include-sessions >/dev/null
codex-sync-all app >/dev/null
codex-profiles --json >/dev/null
codex-profile-info test --json >/dev/null
codex-list-sessions test --json >/dev/null
codex-projects app --json >/dev/null
codex-doctor test --json >/dev/null
codex-balance test --json >/dev/null
codex-prune-imports test --all --dry-run >/dev/null
codex-current >/dev/null
codex-diff-resources app test >/dev/null || true

if [[ ! -f "$HOME/.codex_multi/test/auth.json" ]]; then
  echo "auth.json was not created for test profile"
  exit 1
fi

if [[ ! -d "$HOME/.codex_multi/test/skills" ]]; then
  echo "skills were not synced to test profile"
  exit 1
fi

if ! ls "$HOME/.codex_multi/exports"/*.zip >/dev/null 2>&1; then
  echo "export zip was not created"
  exit 1
fi

echo "smoke test passed"
