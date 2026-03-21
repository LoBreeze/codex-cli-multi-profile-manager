# Testing

This project includes a smoke test that uses:

- a temporary `HOME`
- a fake `codex` executable stub
- a disposable `test` profile

It does **not** use real profiles like `whx`.

## Run locally

```bash
make test
```

## What it covers

- install flow
- wrapper command generation
- profile init
- login via fake codex
- profile listing and info
- shared resource sync
- skill copy
- context import
- export-profile
- doctor
- balance JSON output
- prune-imports dry-run
