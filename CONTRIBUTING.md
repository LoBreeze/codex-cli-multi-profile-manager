# Contributing

Thanks for contributing.

## Development principles

- Keep `~/.codex` reserved for Codex App semantics.
- Keep Codex CLI profiles isolated under `~/.codex_multi/<profile>`.
- Never copy `auth.json` implicitly.
- Prefer explicit commands over hidden side effects.
- Keep smoke tests runnable on a clean machine with a fake `codex` stub.

## Local development

```bash
make lint
make test
```

## Pull request checklist

- [ ] `python3 -m py_compile codex_multi_manager.py` passes
- [ ] `make test` passes
- [ ] README/docs updated for any new command
- [ ] New command has `-h` help text
- [ ] Release notes added to `CHANGELOG.md` if needed

## Style

- Python standard library only
- shell examples should be copy-paste friendly
- use `test` for examples when demonstrating smoke tests or disposable profiles
