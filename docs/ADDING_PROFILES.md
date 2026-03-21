# Adding Profiles

## Add a new profile from app resources

```bash
codex-add-profile alice --clone
# Create ~/.codex_multi/alice and clone config.toml / skills / superpowers / rules from app.

codex-login-profile alice
# Log in to the alice profile.

codex-run-profile alice -- -C ~/repo
# Run Codex CLI under alice in ~/repo.
```

## Add a new profile from another CLI profile

```bash
codex-multi add client-b --clone-from test
# Create client-b and clone shared resources from test.
```

## Copy only skills between profiles

```bash
codex-copy-skills test alice
# Copy only the skills directory.

codex-copy-skills test alice --with-superpowers
# Copy skills and superpowers.
```
