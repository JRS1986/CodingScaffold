# Stability

Every top-level `coding-scaffold` command carries one of three stability markers,
rendered in `--help` next to the command name:

```
COMMANDS (DAILY WORKFLOW):
  session init             [stable]    create a reviewable session trace
  memory capture           [preview]   capture a memory candidate for review
  team push                [preview]   nominate local artifacts upward
```

The marker is a contract about how aggressively the command may change.

## What each marker promises

### `[stable]`

- The flag set, output shape, and exit codes will not change in a backward-incompatible
  way without a major version bump (`0.x → 1.0`) and a deprecation cycle.
- A removed flag is preserved as a hidden alias for at least one minor release with
  a deprecation message.
- The CHANGELOG names every change under a `Deprecated` heading.

Build automation, CI checks, and team docs against `stable` commands without
hesitation.

### `[preview]`

- Feature-complete and tested. May still grow new flags or refine output in a minor
  release.
- Breaking shape changes are possible but called out in the CHANGELOG with a migration
  note.
- Used in production with caution: a `preview` command is on the path to `stable`,
  and the wiki page for that area should note the target release.

Treat `preview` commands like a beta API: depend on them, pin your scaffold version,
and watch the CHANGELOG.

### `[experimental]`

- Fast-moving. May change shape, flag names, or behavior without warning.
- Output formats are not part of the contract; do not parse them in CI.
- Useful for exploration and feedback; not yet suitable as a build dependency.

If you find an `experimental` command load-bearing for your team, open an issue —
graduating to `preview` is a signal we look for.

## Lifecycle

- A new command lands as `experimental` by default.
- It graduates to `preview` once the flag set is settled and at least one team is
  using it.
- It graduates to `stable` once the maintainers commit to the deprecation policy
  above. The graduation lands in a minor release; the CHANGELOG notes it.

## How to read the marker registry

`src/coding_scaffold/cli_stability.py` is the single source of truth. The marker for
a command is whatever appears there; the `--help` text is generated from it.

A test (`tests/test_cli_stability.py`) asserts:
- Every command surfaced in `--help` has a registry entry.
- Every registry entry uses one of `stable | preview | experimental`.

When you move a command between markers, update the registry and add a CHANGELOG
entry under `Stability`.
