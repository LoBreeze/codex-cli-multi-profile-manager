# codex-cli-multi-profile-manager

A local **multi-profile manager for Codex CLI** on macOS and Linux.

`codex-multi` keeps **Codex App** on the default `~/.codex` profile and isolates **Codex CLI** accounts under `~/.codex_multi/<profile>`.

It is designed for people who want a conda-like workflow for local Codex state management:

- keep Codex App on one account
- run Codex CLI under multiple separate profiles
- isolate `CODEX_HOME` per profile
- sync shared resources like `skills`, `superpowers`, `rules`, and `config.toml`
- copy skills between profiles
- migrate project-specific session context without copying `auth.json`
- inspect local profiles, sessions, projects, billing metadata, and exports

## Why this exists

Codex App uses the default local state under `~/.codex`, while Codex CLI local state can be isolated by changing `CODEX_HOME`. This repository turns that pattern into a reusable local manager with discoverable commands, help output, testing, and release-ready docs. The operating model is to keep **Codex App** on `~/.codex` and run **Codex CLI** through separate profiles under `~/.codex_multi/<profile>`. This matches current public guidance that Codex App consumes local Codex session history and configuration, and that repository topics help users find relevant projects on GitHub. citeturn547698search0turn547698search3

## Features

- `init` starter profiles under `~/.codex_multi`
- `profiles` overview table and JSON output
- `info` detailed profile inspection and metadata
- `run`, `login`, `resume` with profile-scoped `CODEX_HOME`
- `sync` and `sync-all` for shared resources
- `copy-skills` with optional `superpowers`
- `sessions` and `projects` views
- `import-context` project-specific rollout handoff
- `prune-imports` maintenance for imported session bundles
- `export-profile` zip export
- `doctor` health checks
- `set-meta`, `balance`, `billing-open`, `usage-open`
- standalone wrapper commands installed into `~/.codex_multi/bin`
- `--help` and `--version`

## Repository layout

```text
~/.codex                     # reserved for Codex App
~/.codex_multi/
  ├── bin/
  │   ├── codex-multi
  │   ├── codex-profiles
  │   ├── codex-profile-info
  │   ├── codex-list-sessions
  │   ├── codex-projects
  │   ├── codex-sync-all
  │   ├── codex-doctor
  │   ├── codex-diff-resources
  │   ├── codex-current
  │   ├── codex-add-profile
  │   ├── codex-prune-imports
  │   ├── codex-export-profile
  │   ├── codex-billing-open
  │   ├── codex-balance
  │   ├── codex-usage-open
  │   ├── codex-copy-skills
  │   ├── codex-login-profile
  │   ├── codex-run-profile
  │   ├── codex-resume-profile
  │   ├── codex-import-context
  │   └── codex-set-meta
  ├── exports/
  ├── test/
  ├── vut/
  └── alice/
```

Reserved profile name:

- `app` = maps to `~/.codex`

## Install

```bash
./install.sh
source ~/.zshrc
```

Initialize profiles. The safe example uses `test`, not a real account name:

```bash
codex-multi init --profiles test,vut
```

## Quick start

```bash
codex-multi login test
# Run `codex login` with CODEX_HOME=~/.codex_multi/test.

codex-multi run test -- -C ~/repo
# Start Codex CLI in ~/repo under the test profile.

codex-multi resume test --last
# Resume the latest session for test.

codex-profiles
# List all local profiles and summary stats.

codex-profile-info test
# Show detailed information about the test profile.
```

## Core commands

```bash
codex-profiles
codex-profile-info test
codex-list-sessions test --limit 10
codex-projects test
codex-sync-all app
codex-doctor
```

## Workflow and maintenance

```bash
codex-diff-resources app test
codex-current
codex-add-profile alice --clone
codex-prune-imports test --days 30 --dry-run
codex-export-profile test --include-sessions
```

## Billing and usage metadata

These commands work from **local profile metadata**. They do not fetch official balance or usage automatically.

```bash
codex-set-meta test \
  --label "Test CLI" \
  --account-kind chatgpt \
  --billing-url https://chatgpt.com/admin/billing \
  --usage-url https://chatgpt.com/admin/billing \
  --notes "Local test profile"

codex-balance test
codex-balance test --json
codex-billing-open test
codex-usage-open test
```

## Skills and resource management

```bash
codex-multi sync test app
# Copy config.toml, skills, superpowers, and rules from app to test.

codex-multi copy-skills app test
# Copy only skills from app to test.

codex-multi copy-skills app test --with-superpowers
# Copy skills and superpowers from app to test.

codex-copy-skills app test --with-superpowers
# Same action via a standalone wrapper command.
```

## Context migration

```bash
codex-multi import-context app test ~/repo
# Copy project-specific rollout history from app into test.
```

`import-context` writes two copies:

- a profile copy under `~/.codex_multi/<target>/sessions/imported/...`
- a project handoff copy under `~/repo/.codex_handoff/...`

It **does not** copy `auth.json`.

## Standalone commands installed by `install.sh`

The installer writes wrapper commands into `~/.codex_multi/bin`. Topics on GitHub are also useful for discovery, and GitHub recommends lowercase hyphenated topics with no more than 20 total topics. citeturn547698search0

```bash
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
```

## Testing

Smoke tests use a temporary `HOME` and a `test` profile. They do not touch your real `whx` or `vut` profiles.

```bash
make test
```

See `docs/TESTING.md` for details.

## Release checklist

- [x] install script
- [x] uninstall script
- [x] wrapper commands
- [x] README
- [x] CHANGELOG
- [x] CONTRIBUTING
- [x] command reference
- [x] profile-adding guide
- [x] testing guide
- [x] GitHub metadata guide
- [x] smoke test
- [x] CI workflow

## Requirements

- Python 3.9+
- `codex` available on `PATH`
- macOS or Linux

## Notes

- `app` is a reserved alias for `~/.codex`.
- This tool is local-state management only; it does not provide official OpenAI multi-account support.
- `codex-balance` reads local metadata only. It does not fetch account credits automatically.
