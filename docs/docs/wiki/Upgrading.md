# Upgrading CodingScaffold

`coding-scaffold setup update` refreshes the generated files in
`.coding-scaffold/` (plus `AGENTS.md`, `CLAUDE.md`, etc.) without losing your
edits. This page explains the contract end-to-end so the upgrade path is
predictable.

## TL;DR

1. Upgrade the tool itself:
   ```bash
   uv tool upgrade coding-scaffold    # or: pipx upgrade coding-scaffold
   ```
2. Rerun `setup update` in each project:
   ```bash
   coding-scaffold setup update --target .
   ```
3. If `.new` files were written, follow the printed reconciliation recipe
   (also shown below).
4. Commit the result. Re-run `coding-scaffold eval run` to confirm health.

## What `setup update` does step-by-step

`setup update` is **idempotent**, **safe by default**, and **never destroys
user edits**. The flow:

1. Reads `.coding-scaffold/scaffold-version.json` (the SHA256 snapshot of every
   file the scaffold has ever written).
2. Refuses to run if the installed scaffold version is older than the project's
   recorded `min_supported_scaffold_version` (see [Version pinning](#version-pinning)
   below). Pass `--force` to bypass after reading the migration note.
3. Rebuilds every generated file into a temporary directory using the current
   intake + provider + routing inputs.
4. For each generated file:
   - **Doesn't exist on disk** → write it. (You can safely delete files you
     don't want; the next update will recreate them. To permanently exclude a
     file, drop it from the writer set in your fork — there is no per-file
     opt-out yet.)
   - **Exists, matches snapshot, matches new** → skip. Nothing to do.
   - **Exists, matches snapshot, differs from new** → silent rewrite. The
     scaffold knows you didn't touch it, so the upstream version wins.
   - **Exists, differs from snapshot** → user edited it. Write the new version
     as a `<file>.new` sidecar; leave your file alone.
5. Refresh `scaffold-version.json` to reflect the new authoritative shape.

## The `.new` workflow

When `setup update` writes `<file>.new`, your edits to `<file>` are preserved
and an upstream version sits next to it for you to merge. The reconciliation
recipe (which `setup update` prints when `.new` files are produced):

```bash
# 1. Diff the pair so you can see what changed upstream:
diff -u .coding-scaffold/foo.json .coding-scaffold/foo.json.new

# 2. Merge the upstream changes into your edited file by hand.
#    (Or pull both into your editor's three-way merge tool.)

# 3. Delete the .new sidecar once you're done:
rm .coding-scaffold/foo.json.new

# 4. Re-run eval to confirm the project is healthy:
coding-scaffold eval run --target .
```

Do **not** blindly `mv foo.new foo` — that throws away your edits, defeating
the whole point of `.new`. Always merge.

If you're confident the upstream version is the right starting point and your
edits should be re-derived from scratch, the deliberate workflow is:

```bash
git diff -- .coding-scaffold/foo.json     # capture your edits in your head
mv .coding-scaffold/foo.json.new .coding-scaffold/foo.json
# re-apply your edits on top, then:
coding-scaffold eval run --target .
```

## How to roll back

`setup update` writes a new git-trackable shape. If something is wrong:

```bash
# Discard everything the update touched:
git restore .coding-scaffold/ AGENTS.md CLAUDE.md  # add other paths if needed
git status                                          # confirm clean

# Pin to the previous scaffold version so the next `setup update` doesn't
# re-apply the same change:
uv tool install 'coding-scaffold==0.5.1'            # or your previous version
# or: pipx install --force 'coding-scaffold==0.5.1'
```

There is no built-in rollback; git is the safety net. Run `setup update` only
on a clean working tree so `git restore` is always sufficient.

## Files you deleted on purpose

If you intentionally delete a generated file (e.g., you don't want `tools.md`),
the next `setup update` recreates it. CodingScaffold has no per-project opt-out
yet; track this in your team manifest if it matters. The recommended pattern:

1. Delete the file.
2. Run `setup update`. The file comes back.
3. Either accept it (it's harmless if unused) or re-delete and add a project
   policy note explaining why.

## Version pinning

`scaffold-version.json` carries a `min_supported_scaffold_version` field
(default: the version of CodingScaffold that wrote the file). `setup update`
refuses to run if the installed scaffold is older than this floor.

Example failure:

```
error: this project was last updated with CodingScaffold 0.6.0, but 0.5.1 is installed.
  next: upgrade the scaffold (`pip install -U coding-scaffold` or
        `uv tool upgrade coding-scaffold`), or rerun with `--force` after
        reading the migration note.
  see: https://jrs1986.github.io/CodingScaffold/wiki/Upgrading
```

This catches the case where a teammate updates the project with a newer
scaffold but a CI job or another machine still has an older version pinned.
Bypass with `--force` only after confirming the older scaffold's writers can
produce the project shape you actually want.

## Reading the CHANGELOG for breaking changes

The CHANGELOG groups changes by release. Look for these sections:

- **Breaking** — anything that changes the *shape* of generated files (renamed
  keys, removed sections, file moves). When `setup update` runs across a
  Breaking boundary, it always produces `.new` files for the affected outputs;
  read the Breaking section to know what the merge should look like.
- **Deprecated** — features that still work but are scheduled for removal.
  Plan to migrate before the next major bump.
- **Stability** — commands moved between `stable`/`preview`/`experimental`
  markers. See [Stability](./Stability.md) for what each marker promises.

A worked example: if 0.6.0's CHANGELOG says "Renamed `policy.network.allow`
to `policy.network.allowlist`", and your update produced
`.coding-scaffold/policy/network.json.new`, the diff will show exactly that
rename. Merge by renaming the key in your edited file and dropping the
sidecar.

## Breaking change in 0.6.0 — singular `tool` JSON key removed

`routing.json`, `project.json`, and the pilot JSON output used to carry a
singular `tool` key. These are gone — only `tools` (a list) remains. The
migration is a one-line change for any script that read them:

```python
# Before
config["tool"]            # "codex"

# After
config["tools"][0]        # "codex"
```

Legacy `project.json` files written by 0.5.x (with `tool` instead of `tools`)
are back-filled when `setup update` reads them, so existing projects upgrade
cleanly. The back-fill is removed in 0.7.0.

## Breaking change in 0.7.0 — `--tool both` removed

`--tool both` was deprecated in 0.6.0 and is removed in 0.7.0. The CLI rejects
it with the standard three-line error block:

```
error: `--tool both` was removed in 0.7.0
  next: use `--tool opencode,openclaude` instead
  see: https://jrs1986.github.io/CodingScaffold/wiki/Upgrading
```

Update scripts that still use it:

```bash
# Before
coding-scaffold setup run --tool both

# After
coding-scaffold setup run --tool opencode,openclaude
```

The `_normalize_persisted_intake` back-fill helper (which migrated legacy
`project.json` files carrying the singular `tool` key on read) is also gone.
A `project.json` written by 0.5.x that was never updated through 0.6.x will
now have its `tool`/`agent` fields silently ignored; the project falls back
to `DEFAULT_TOOLS` (`opencode`). Run `coding-scaffold setup run` once to
regenerate with the modern shape.

## When `setup update` is not the right tool

- **First-time setup** → use `setup run`, not `setup update`. `update` needs an
  existing scaffold to compare against.
- **Switching tools** (e.g., from OpenCode to Claude Code) → run
  `setup run --target . --tool claude-code` to regenerate the adapter set
  cleanly. `setup update` keeps your old tool's files alongside.
- **A breaking-change scenario you want to redo from scratch** → delete
  `.coding-scaffold/` and rerun `setup run`. Read the relevant CHANGELOG
  Breaking section first.
