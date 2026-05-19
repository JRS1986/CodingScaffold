# Code Review Batch 1 — Design Decisions

**Date:** 2026-05-18
**Scope:** Resolve four coupled issue clusters surfaced by the project-wide code
review. The mechanical-fix batch is already merged on
`integration/review-batch-1`; this spec covers the remaining design-bearing
work.

## North star

CodingScaffold is the local-first onboarding, configuration, and governance
scaffold for AI-assisted software development teams. Every decision below
biases toward three properties teams actually need:

1. **Reviewable** — generated content never silently overwrites user content.
2. **Cross-platform predictable** — macOS, Linux, and WSL produce the same
   output.
3. **Trust boundaries explicit** — third-party content is named as such and
   confined to a known location.

## Cluster A — Azure endpoint classification

**Issues resolved:** #31 (Critical), #35 (Important).

**Decision:** Always-secret. Azure endpoint, deployment, model, and
model-family values are treated as secrets — never written to committable
scaffold artifacts.

### Mechanism

1. `src/coding_scaffold/credentials.py` keeps the Azure endpoint/deployment
   env names in `SECRET_ENV_NAMES`. Add an explicit list constant
   `AZURE_NONKEY_ENV_NAMES` so the classification is documented in code:

   ```python
   AZURE_NONKEY_ENV_NAMES = (
       "AZURE_OPENAI_ENDPOINT",
       "AZURE_OPENAI_DEPLOYMENT",
       "AZURE_AI_ENDPOINT",
       "AZURE_AI_MODEL",
       "AZURE_AI_MODEL_FAMILY",
       "AZURE_AI_SERVICES_ENDPOINT",
       "AZURE_COGNITIVE_SERVICES_ENDPOINT",
   )
   ```

   `SECRET_ENV_NAMES` becomes the union of API-key names + `AZURE_NONKEY_ENV_NAMES`.
   Source of truth, not a behavioral change yet.

2. `src/coding_scaffold/providers.py` — extend the `Provider` dataclass with
   a `redact_fields: tuple[str, ...] = ()` attribute (default empty for
   non-Azure providers). `_azure_openai_provider` and `_azure_ai_provider`
   populate it with the field names whose values came from
   `AZURE_NONKEY_ENV_NAMES` (typically `("endpoint", "deployment")`).
   `Provider.to_dict()` replaces those fields with the string
   `"<configured locally; see .env.local>"`. The in-memory `Provider` object
   keeps the real value for routing / status messages — only the serialized
   form is redacted.

3. `src/coding_scaffold/writers.py` — every adapter writer (`opencode.json`,
   `openclaude.json`, `hermes.json`, `pi.json`, `routing.json`) routes Azure
   endpoint references through the same redaction helper. The adapter still
   emits the env-var name (e.g. `${AZURE_OPENAI_ENDPOINT}`) so the runtime
   resolves it from `.env.local` at agent-start time.

4. `CREDENTIALS.md` (generated) gets a new paragraph explaining that Azure
   endpoint and deployment names are treated as sensitive by default because
   the subdomain typically encodes tenant identity.

### Tests

- `tests/test_providers.py` — `Provider.to_dict()` returns the placeholder
  string when the env source is in `AZURE_NONKEY_ENV_NAMES`.
- `tests/test_writers.py` — `providers.json` and each adapter JSON contain
  zero `https://*.openai.azure.com` substrings when `AZURE_OPENAI_ENDPOINT` is
  set in the test environment.
- `tests/test_credentials.py` — `.env.local` and `credentials.local.json`
  templates contain every Azure non-key var.

### Backward compatibility

For users who already committed `providers.json` with real endpoints: a
one-line CHANGELOG entry plus a note in `CREDENTIALS.md` ("if you previously
generated providers.json with Azure endpoints, regenerate or redact"). No
automatic migration — the regeneration path is `coding-scaffold update`,
which already exists and stages `.new` files.

## Cluster B — team.py sync trust boundary

**Issues resolved:** #30 (Critical), #36 (Important), #43 (Minor).

**Decision:** Layered + safe. Sync only writes to
`.coding-scaffold/team/sources/<slug>/`. The user-curated
`.coding-scaffold/knowledge/` tree is sacrosanct and never touched by `team
sync`. Clones are kept as full git checkouts in a hidden
`team/sources/<slug>/_repo` subdir to enable fast-forward pulls.

### Mechanism

1. **Folder layout** (current scaffold already places team imports under
   `.coding-scaffold/team/sources/<kind>/<slug>/`; this design hardens that
   invariant):

   ```
   .coding-scaffold/
     knowledge/          ← user-owned. team sync never writes here.
     team/
       sources/
         knowledge/<slug>/    ← extracted markdown content from a team source
           _repo/             ← full git checkout (with .git intact)
           *.md               ← copied out of _repo for agent consumption
         policy/<slug>/...
   ```

2. **`team.py` rewrite** — `_sync_team_payload` no longer accepts a
   `destination` that resolves into `knowledge/`. If a manifest's
   `knowledge.path` resolves under `knowledge/`, sync emits a structured error
   and aborts that source (other sources continue).

3. **Clone strategy** — `_clone_or_pull` becomes:
   - `git clone` into `team/sources/<kind>/<slug>/_repo` (preserving `.git`).
   - Subsequent runs use `git -C _repo pull --ff-only`. Non-ff failures are
     reported as warnings — never `rm -rf`.
   - After clone/pull, `_copy_markdown` walks `_repo` and copies `*.md` (and
     manifest-allowed extensions) to the parent directory, where agents read
     them.
   - `_remove_nested_git` is deleted — `.git` lives inside `_repo` and never
     gets exposed to the agent walker because the walker is rooted one level
     up.

4. **Remote validation** — `_resolve_manifest` rejects remotes that match
   none of: `https://`, `http://` (warn — discouraged), `git@host:`,
   `ssh://`. `file://` and bare relative paths require an explicit
   `--allow-local` flag passed to `team connect` / `team sync`. Local
   directory remotes (existing behavior via `Path(remote).exists()`) become
   gated behind the same flag. Existing tests that use local-path remotes
   are updated to pass `--allow-local` so they keep exercising the
   local-path code path; this is a one-line change per test.

5. **Trust boundary doc** — `docs/wiki/Team-Onboarding.md` gets a short
   "Trust model" section: team manifest content is third-party input; the
   user is responsible for review before linking it from their own knowledge
   tree.

### Tests

- `team sync` against a local-path remote does not touch
  `.coding-scaffold/knowledge/`, even when that directory contains files.
- Two successive `team sync` runs against a git URL use `git pull --ff-only`
  on the second run (assert via a stub git binary or a check that `_repo`
  retains its `.git` directory).
- `team connect` against `file:///tmp/foo` without `--allow-local` returns a
  failure with a recognizable error message.
- `team sync` against a source containing a submodule does not leak nested
  `.git` directories into the agent-readable path (regression for #43).

### Backward compatibility

Existing checkouts have `team/sources/<slug>/` with no `_repo`. On first
sync after upgrade, the old slug folder is moved aside to
`<slug>.legacy-<date>/` and a fresh clone runs. The user sees a one-line
notice and can delete the legacy folder when ready. No data destruction.

## Cluster C — compress-context article stripping

**Issues resolved:** #32 (Critical).

**Decision:** Drop the heuristic. The `\b(the|a|an)\b` substitution is
removed entirely.

### Mechanism

`src/coding_scaffold/context.py:270` — delete the line. Adjacent
`filler-word` and `in order to / it is important to / please note that`
substitutions are kept (those are safer because they don't match identifier
fragments). Whitespace normalization (`re.sub(r"\s+", " ", ...)`) is kept.

### Tests

`tests/test_context.py` — assert that a document containing the literal
inline-code identifier `` `the-prod-route` `` and the link
`[the docs](./the-docs)` survives compression unchanged in those specific
spans. Existing compression tests stay green.

### Rationale

Article-stripping saves on the order of 1-2% of tokens in typical
prose-heavy notes but breaks identifiers in agent-facing knowledge whenever a
note uses backtick-wrapped names. The compressed sidecars are what agents
read — correctness dominates.

## Cluster D — policy.merge_opencode_config

**Issues resolved:** #39 (Important).

**Decision:** Stage `.new` + deep merge. Output is written to
`opencode.json.new` when an existing `opencode.json` is present, consistent
with the `updater.refresh_scaffold` idiom. The merge itself becomes a deep
merge for known nested keys.

### Mechanism

1. New helper `src/coding_scaffold/file_ops.py::deep_merge_mapping(base,
   overlay, deep_keys)` — for each key in `deep_keys`, if both `base[key]`
   and `overlay[key]` are mappings, merge recursively; otherwise prefer
   overlay. Other keys use shallow `overlay over base`.

2. `policy._merge_opencode_config` uses `deep_keys = ("mcp", "permission")`.
   This preserves user-defined MCP servers (`mcp.<server-name>`) when the
   policy pack only sets adjacent server names, and preserves per-scope
   `permission` entries.

3. When `opencode.json` exists, the merged result is written to
   `opencode.json.new`. The function returns a structured result with a
   `staged: bool` flag so the CLI can print
   `"Staged opencode.json.new — review and mv when ready."`. When the file
   does not exist, the function writes `opencode.json` directly (same as
   today).

4. No automatic backup files (`.bak`) — the `.new` flow already provides the
   review gate. Keeping the surface small.

### Tests

- Existing `mcp.<server>` entries survive a policy merge when the policy pack
  only defines `mcp.<other-server>`.
- When `opencode.json` exists, the result lands in `opencode.json.new` and
  the original is untouched.
- When `opencode.json` does not exist, the result lands in `opencode.json`
  directly.
- `permission.<scope>` user entries survive when policy adds adjacent scopes.

### Backward compatibility

Users who run `coding-scaffold policy` regularly will see a one-time
`.new` staging the next time they upgrade. The CLI tells them how to accept.
No silent change.

## Cross-cutting: order of operations

The four clusters touch four different modules; the integration risk is low.
Implement in this order to maximize parallel review:

1. **Cluster C** (smallest, 1-line deletion + 1 test). Land first.
2. **Cluster A** (provider redaction). Isolated to `providers.py`,
   `credentials.py`, `writers.py`. Land second.
3. **Cluster D** (policy deep-merge + `.new` staging). Isolated to
   `policy.py` + `file_ops.py`. Land third.
4. **Cluster B** (team sync rewrite). Largest. Land last so the legacy-folder
   migration runs against an otherwise-known-good state.

Each cluster ends with a passing `uv run ruff check && uv run pytest` and is
committable independently.

## Out-of-scope (deliberately deferred)

These were surfaced in the review but are not part of this design:

- #34 updater version-file advancement (mechanical, fits a follow-up batch
  alongside #40/#41/#42/#48).
- #40 intake repo walk caps (performance, mechanical).
- #41 cli.team subparser refactor (mechanical, overlaps #7).
- #42 RouteLLM YAML quoting (mechanical, pick `json.dumps`).
- #48 parallel CLI argument trees (overlaps existing #7).

These can fan out to a second batch of parallel agents once this design's
implementation lands.

## Verification gates

- `uv run ruff check` clean.
- `uv run pytest` green (including the new regression tests per cluster).
- CI on Linux green (the case-collision fix from `cc2d126` on the integration
  branch should already clear the existing failing run; this is verified once
  the PR is opened).
