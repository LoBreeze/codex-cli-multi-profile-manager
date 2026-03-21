# Commands

## Core

- `codex-multi init --profiles test,vut`
- `codex-profiles`
- `codex-profile-info test`
- `codex-multi login test`
- `codex-multi run test -- -C ~/repo`
- `codex-multi resume test --last`

## Resource sync

- `codex-multi sync test app`
- `codex-sync-all app`
- `codex-copy-skills app test --with-superpowers`
- `codex-diff-resources app test`

## Sessions and projects

- `codex-list-sessions test --limit 20`
- `codex-list-sessions test --project ~/repo`
- `codex-projects test`
- `codex-import-context app test ~/repo`
- `codex-prune-imports test --days 30 --dry-run`

## Export and inspection

- `codex-export-profile test --include-sessions`
- `codex-current`
- `codex-doctor`

## Metadata

- `codex-set-meta test --label "Test" --account-kind chatgpt`
- `codex-balance test`
- `codex-billing-open test`
- `codex-usage-open test`
