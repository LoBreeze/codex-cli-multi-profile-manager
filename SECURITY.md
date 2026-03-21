# Security Policy

## Scope

This project manages local Codex profile state. It does not attempt to break or bypass official authentication flows.

## Safe defaults

- `auth.json` is **not** copied implicitly
- context migration copies rollout/session files only
- export excludes `auth.json` unless `--include-auth` is explicitly set

## Reporting

If you find a bug that could expose credentials or authentication state across profiles, open a private report if possible and do not post tokens or local secrets publicly.
