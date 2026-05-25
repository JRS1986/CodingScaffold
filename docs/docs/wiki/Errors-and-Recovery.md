# Errors and Recovery

Every CLI failure path produces the same three lines:

```
error: <one-line cause>
  next: <one concrete recovery step>
  see: <optional wiki link>
```

The format is intentionally minimal: cause first, fix second, documentation
optional. If you see a failure that does **not** follow this shape, that is a
bug — open an issue with the command you ran.

## Common failure modes

### `setup run` reports a missing coding tool

```
error: required tool 'opencode' not found on PATH
  next: install it with `coding-scaffold setup tool --tool opencode --install`
  see: https://jrs1986.github.io/CodingScaffold/wiki/Getting-Started
```

Run the printed install command, or rerun setup with `--install-tools` so the
scaffold installs it as part of the flow.

### `context lint` runs against an empty project

```
error: nothing to lint — no AGENTS.md, no CLAUDE.md, no .coding-scaffold/
  next: run `coding-scaffold setup run --target . --mode beginner` to bootstrap
  see: https://jrs1986.github.io/CodingScaffold/wiki/Context-Hygiene
```

`context lint` only has meaning once at least one agent-context file exists.

### `credentials --format env` template untouched

```
error: .coding-scaffold/.env.example was created but no value was filled in
  next: copy to .coding-scaffold/.env and replace placeholders before retrying
  see: https://jrs1986.github.io/CodingScaffold/wiki/Security
```

Downstream commands that need credentials warn loudly when the template was
created but never populated.

### `eval run` fails on a missing artifact

```
error: eval check 'pr_template' requires .github/PULL_REQUEST_TEMPLATE/agentic-change.md
  next: run `coding-scaffold pr-template init --target .` to create it
  see: https://jrs1986.github.io/CodingScaffold/wiki/Getting-Started
```

Every readiness check that depends on a scaffold artifact names which artifact
is missing and the command that creates it.

### `team sync` finds an incompatible manifest

```
error: team manifest requires scaffold >= 0.6.0, installed 0.5.1
  next: upgrade the scaffold (`pip install -U coding-scaffold`) or pin the manifest
        with `team sync --to-ref <older-sha>`
  see: https://jrs1986.github.io/CodingScaffold/wiki/Team-Sync
```

Versioned manifests refuse to apply across a `min_scaffold_version` boundary
without an explicit override.

## Adding a new failure path

Library and CLI code raise via the shared helper so the format stays stable:

```python
from coding_scaffold.errors import fail_with

fail_with(
    cause="...",
    next_step="run `coding-scaffold ...` to ...",
    link="https://jrs1986.github.io/CodingScaffold/wiki/...",
)
```

A test in `tests/test_errors.py` exercises the helper. Per-command tests for
no-config recovery paths assert the next-step phrase is present in stderr.
