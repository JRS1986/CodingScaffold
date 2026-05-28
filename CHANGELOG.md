# Changelog

All notable changes to CodingScaffold are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and the project
aims to follow [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Removed (breaking)

- **`--tool both`** removed. The CLI now exits 1 with the three-line error
  shape (`error: ... / next: use --tool opencode,openclaude / see: Upgrading`).
  Deprecated in v0.6.0. See [Upgrading](docs/docs/wiki/Upgrading.md).
- **`_normalize_persisted_intake` back-fill helper** removed. A `project.json`
  written by 0.5.x that was never updated through 0.6.x now silently ignores
  its legacy `tool` / `agent` keys and falls back to `DEFAULT_TOOLS`
  (`opencode`). Re-run `coding-scaffold setup run` to regenerate.
- **`IntakeAnswers.agent` property** removed. Use `IntakeAnswers.tools[0]`.
- **Stale `"both"`-handling branches** in `installers.py:build_install_plans`
  and `cli.py:_maybe_setup_knowledge` cleaned up — dead code post-removal.

### Changed

- **`probe_hardware()` is now cached** at
  `$XDG_CACHE_HOME/coding-scaffold/hardware.json` (default `~/.cache/...`)
  with a 1-hour TTL keyed on OS / arch / Python version. Warm-call
  performance: `doctor` 243ms → 78ms median (**3.1×**); `pilot` 235ms →
  79ms (**3.0×**). New `--no-probe-cache` flag on `doctor` / `pilot` /
  `probe` forces a fresh probe (use after installing a new local runtime
  like `ollama`).
- **`CODING_TOOLS` / `VALID_TOOLS` consolidated.** `intake.py` holds the
  canonical tuple; `cli.py` re-exports it as a list for argparse and
  derives `INSTALLABLE_TOOLS`. `VALID_TOOLS = frozenset(CODING_TOOLS)`.
  The drift-detection test that policed the previous duplication is
  replaced with a one-line derivation invariant.

### Tests

- **pytest-xdist enabled** (`addopts = "-n auto"`). Test suite ~22s → **~3s**
  with parallel workers; 637 tests pass.

## [0.6.0] — 2026-05-27

### Added

- **Multi-tool projects: `--tool` accepts a list.** `coding-scaffold setup run
  --tool codex --tool claude-code` (or `--tool codex,claude-code`) generates
  both tools' adapters in a single pass. Supported on `setup run`,
  `tools adapt`, `setup tool`, and `pilot`. Pilot prints a shared setup step
  plus one per-tool agent step.

- **`coding-scaffold tour`** — read-only five-screen walkthrough explaining what the
  tool does, the scaffold artifact families, the doctor/pilot/setup loop, the daily
  session/eval/team workflow, and where to go next. Never writes files; safe right
  after install. Closes [#91](https://github.com/JRS1986/CodingScaffold/issues/91).
- **`--persona` flag on `doctor` and `pilot`** — choose from `beginner` (default),
  `control`, `security`, `team-lead`. Each persona reorders the artifact survey and
  swaps the recommended-commands list for a focused recipe matching the persona's job.
  Persona registry lives at `src/coding_scaffold/personas.py` and is kept in sync
  with the [Team-Rollout](docs/docs/wiki/Team-Rollout.md#persona-paths) wiki page.
  Closes [#90](https://github.com/JRS1986/CodingScaffold/issues/90).
- **Stability markers in `--help`.** Every top-level command now renders a
  `[stable]` / `[preview]` / `[experimental]` marker so teams know what they can
  build on. Contract per marker documented in
  [Stability](docs/docs/wiki/Stability.md). Registry at
  `src/coding_scaffold/cli_stability.py`. Closes
  [#95](https://github.com/JRS1986/CodingScaffold/issues/95).
- **Per-subcommand `--help` descriptions and examples.** Every subcommand
  (`setup run`, `knowledge lint`, `team push`, ...) now prints a one-paragraph
  description, when-to-run guidance, and 1-3 worked examples instead of bare
  argparse output. Registry at `src/coding_scaffold/cli_help.py`. Closes
  [#89](https://github.com/JRS1986/CodingScaffold/issues/89).
- **Doctor rationale lines.** Every artifact `doctor` surveys is rendered with a
  one-line `→ why this matters` rationale, sourced from the shared
  `src/coding_scaffold/artifacts.py` registry so `doctor`, `pilot`, and any future
  onboarding command stay in sync. Closes
  [#87](https://github.com/JRS1986/CodingScaffold/issues/87).
- **`setup update --force` + `min_supported_scaffold_version` field.**
  `.coding-scaffold/scaffold-version.json` now records the minimum scaffold
  version required to safely update the project. `setup update` refuses to run
  when the installed scaffold is older (use `--force` to override after reading
  the migration note). Closes
  [#96](https://github.com/JRS1986/CodingScaffold/issues/96).
- **`setup update` prints a copy-pasteable `.new` reconciliation recipe.** When
  staged `.new` sidecars are produced, the command now prints the `diff -u` /
  merge / delete / `eval` steps inline, plus a link to the upgrade guide.

### Fixed

- **Template renderer no longer leaks `${undefined}` into user files.** Missing
  keys raise `UnresolvedTemplateError` naming the template + key; any
  `${...}` token surviving substitution raises before the file is written.
  `$$` is preserved as the documented escape for a literal `$`. A parametrized
  test renders every template under `templates/{writers,adapters}/` with a
  default context. Fixes [#94](https://github.com/JRS1986/CodingScaffold/issues/94).

### Changed

- **Breaking (single-key removal): `routing.json`, `project.json`, and pilot
  JSON output now carry `tools` (a list) only.** The singular `tool` key is
  gone. Read `tools[0]` if you need a single value. Legacy `project.json`
  files with `tool` are back-filled on read for one release window
  (removed in 0.7.0). See [Upgrading](docs/docs/wiki/Upgrading.md).

- **Unified error message style.** New `src/coding_scaffold/errors.py` exposes
  `fail_with(cause, next_step, link=None)` so CLI failure paths share a
  three-line shape (`error: ... / next: ... / see: ...`). Documented in
  [Errors and Recovery](docs/docs/wiki/Errors-and-Recovery.md). Closes
  [#92](https://github.com/JRS1986/CodingScaffold/issues/92).

### Deprecated

- **`--tool both`** is deprecated and will be removed in 0.7.0. Use
  `--tool opencode,openclaude` instead.

### Documentation

- **New wiki pages**: [Glossary](docs/docs/wiki/Glossary.md) (cold-readable
  vocabulary; linked from `doctor` and `--help` footers — closes
  [#88](https://github.com/JRS1986/CodingScaffold/issues/88));
  [Stability](docs/docs/wiki/Stability.md);
  [Upgrading](docs/docs/wiki/Upgrading.md) (the full upgrade contract:
  `.new` recipe, rollback, version pinning, reading CHANGELOG Breaking notes);
  [Errors and Recovery](docs/docs/wiki/Errors-and-Recovery.md). Wiki index +
  README updated to route to the new pages.
- **Install docs now default to an isolated global CLI.** README, Getting Started, and generated
  project onboarding recommend `uv tool install` or `pipx install` from the GitHub repo so users can
  run `coding-scaffold` from any project without activating the source checkout's virtual
  environment. The clone + editable install path remains documented for contributors.
- **README now answers why CodingScaffold exists alongside one-command agent installers.** The intro
  now highlights adaptive language/tool setup, shared reviewed knowledge, and repeatable team
  workflows before the quick-start commands. Knowledge docs clarify that durable wiki pages should
  be distilled and reviewed, not raw chat transcript dumps.

### Tests

- **Test coverage gap filled** for `file_ops`, `scaffold_version`, `doctor`,
  `pilot`, `session` (full init → start → checkpoint → diff → rollback
  round-trip), and `pr_template`. Test count grew from 351 to 590. Closes
  [#93](https://github.com/JRS1986/CodingScaffold/issues/93).
- **Acceptance-criteria audit** for the team / knowledge / HTML-backend issues
  (#97 – #105) — one test per acceptance bullet, with failure messages naming
  the issue so regressions surface the affected ticket. The deeper mechanics
  coverage stays in `tests/test_team.py` and `tests/test_knowledge.py`.

## [0.5.1] — 2026-05-19

### Fixed

- **`pilot` prints a valid setup recipe when the selected tool is missing.** The generated
  happy-path command now uses `setup run --install-tools` instead of the invalid
  `setup run --install`, with a regression test that parses the printed recipe through
  the real CLI parser. Closes
  [#77](https://github.com/JRS1986/CodingScaffold/issues/77) via
  [#78](https://github.com/JRS1986/CodingScaffold/pull/78).
- **`pilot` readiness no longer says OK when the selected coding tool is missing.**
  The environment summary now includes selected-tool presence in `environment_ok`, so
  first-time users do not see contradictory `Environment OK: yes` and `installed: False`
  signals. Closes [#76](https://github.com/JRS1986/CodingScaffold/issues/76).
- **`doctor` default text output is no longer duplicated.** The structured accessibility
  report is now the default output; the old hardware/provider recommendation snapshot
  is available with `doctor --verbose`. Closes
  [#75](https://github.com/JRS1986/CodingScaffold/issues/75).

### Documentation

- **README and docs site optimized for command discoverability.** The README now includes a
  "Which Command Do I Need?" table, a smaller everyday flow, and a journey-based command
  reference instead of a large undifferentiated command dump.
- **Published docs homepage and wiki index now route readers by need.** The docs front page,
  wiki index, Getting Started, FAQ, Team Rollout, and Team Onboarding pages now emphasize
  `doctor` + `pilot` for first contact, a two-person small-team pilot, and postponing
  advanced features until the team has a concrete need.
- **Stale docs paths and command wording cleaned up.** Updated moved `docs/docs/wiki/...`
  references, clarified `--install-tools`, refreshed the repo's own `AGENTS.md` test-count
  note, and verified visible relative Markdown links.

### Infrastructure (no package changes)

These changes affect the repo's tooling and the published docs site, not the
`coding-scaffold` Python package. No version bump.

- **Docs site live at https://jrs1986.github.io/CodingScaffold/.** Contributed in
  [#68](https://github.com/JRS1986/CodingScaffold/pull/68) by @YanPes: an [rspress](https://rspress.dev)
  static site under `docs/`, with an `llms-full.txt` discoverability plugin so the docs
  surface is also crawlable by LLMs. Wiki content moved from `docs/wiki/` to
  `docs/docs/wiki/` (the rspress content root).
- **Dedicated GitHub Pages workflow.** `.github/workflows/docs.yml` builds rspress on
  every push to `main` (and validates on PRs touching `docs/**`); the deploy job uses
  `actions/configure-pages@v5` with `enablement: true` so the workflow self-bootstraps on
  a fork ([#69](https://github.com/JRS1986/CodingScaffold/pull/69),
  [#72](https://github.com/JRS1986/CodingScaffold/pull/72)).
- **GitHub Actions Node 24 readiness.** `actions/checkout` and `actions/setup-node` bumped
  v4 → v5 ahead of the 2026-06-02 forced cutover, closing
  [#70](https://github.com/JRS1986/CodingScaffold/issues/70) via
  [#71](https://github.com/JRS1986/CodingScaffold/pull/71).
- **rspress `base` path.** Set to `/CodingScaffold/` so the project-page asset URLs resolve
  correctly under the `jrs1986.github.io` apex ([#73](https://github.com/JRS1986/CodingScaffold/pull/73)).

## [0.5.0] — 2026-05-18

### Added

- **Top-level help groups commands by user journey.** `coding-scaffold --help` now opens
  with four labelled sections — **Start here**, **10-minute pilot**, **Daily workflow**,
  and **Advanced / governance** — so a new user can see the smallest useful path before
  the full alphabetical command list. The full reference is still printed below as usual;
  no commands were removed or renamed and every hidden compatibility alias (`init`,
  `wizard`, `setup-tool`, `setup-addon`, `setup-knowledge`, `knowledge-status`,
  `context-budget`, `compress-context`, `orchestrate`, `adapt`, `route`, `select-model`)
  still parses.
- **`coding-scaffold doctor` becomes the accessibility hub.** New module
  `src/coding_scaffold/doctor.py`. The command now accepts `--target` and `--json`,
  surveys 14 scaffold-artifact paths (AGENTS.md, CLAUDE.md, PR template,
  `.coding-scaffold/` and its sub-directories, eval-config, etc.), recommends 1-3
  context-aware next commands (e.g. an empty repo gets `pilot` + `setup run`; a partially
  set-up repo gets `pr-template init` or `session init`), and explicitly names the
  advanced surfaces (`policy`, `mcp`, `skills`, `memory`, `team`, `permissions write`,
  `tools route` / `workflow` / `orchestrate`) under "Ignore for now (advanced)". The
  original hardware/provider snapshot still prints below the new structured output for
  continuity.
- **`coding-scaffold pilot --target . --tool opencode`.** New module
  `src/coding_scaffold/pilot.py`. A safe guided wrapper that runs only read-only local
  checks (Python version, `git` on PATH, the chosen tool's binary on PATH, credentials
  in env, local-runtime CLIs) and then prints the exact three-step recipe tailored to
  your environment. Never installs anything. Never writes files. The printed recipe may
  include install flags such as `--install-tools`, but the user makes that call. Supports all six tools
  (`opencode`, `claude-code`, `codex`, `openclaude`, `hermes`, `pi`) and `--json` output.

### Documentation

- README adds a "30-Second Start" block at the top with the three commands a new user
  needs today (`doctor`, `pilot`, then follow the recipe).
- `docs/docs/wiki/Getting-Started.md` adds a "Smallest Useful Path" section that names the
  same three commands and explicitly tells readers what to ignore for now.

## [0.4.2] — 2026-05-18

### Added

- **Dogfooded baseline on the scaffold's own repo.** Adds an `AGENTS.md` at the repo root
  documenting the real maintainer workflow (verification commands, no-runtime-dependency
  rule, no-LLM-calls, no-network constraint, commit-message convention, session-trace
  usage for larger changes). Generates `.github/PULL_REQUEST_TEMPLATE/agentic-change.md`
  via the scaffold's own `pr-template init` command. Ships a narrow
  `.coding-scaffold/eval-config.json` that runs the readiness benchmark as a smoke check
  while disabling `policy_exists` and `denied_files_configured` — this repo deliberately
  ships no policy pack and no `agent-permissions.json`. The `mcp_policy` check auto-skips
  because no MCP servers are detected. Result: `coding-scaffold eval run --target .`
  reports 9/9 checks passed on the scaffold's own repo.

### Fixed

- **`eval mcp_policy_exists_if_mcp_detected` no longer fires on file presence alone.**
  The check previously treated any of `opencode.json`, `.claude/settings.json`,
  `.claude/settings.local.json`, or `.codex/config.toml` existing as "MCP in use", which
  false-flagged Claude Code installs that ship a `settings.local.json` containing no MCP
  entries. The check now uses `scan_mcp` and only fires when at least one MCP server is
  actually parsed from a config. One new regression test in `tests/test_eval_harness.py`.

## [0.4.1] — 2026-05-18

### Fixed

- **Eval `test_command_detected` no longer falsely passes on a repo with no agent-context
  files.** The check previously relied on the absence of the linter's
  `missing-build-test-commands` finding, but that finding only fires when context files
  exist. An empty repo therefore showed the contradictory pair "no agent-context files"
  + "recognizable test commands mentioned." The check now scans the agent-context files
  directly with word-boundary-aware token matching so short tokens like `ci` don't match
  inside `precise` or `decision`. Three new regression tests in
  `tests/test_eval_harness.py`.
- **MCP `server-not-approved` now fires under the default policy.** The scanner previously
  short-circuited the unapproved-server check when `approved_servers` was empty, which
  silently allowed every detected server under the generated default policy
  (`unapproved_servers: "deny"` with an empty allowlist). The check now tracks the policy
  posture: `deny` produces severity `error`, `requires_approval` produces severity
  `warning`, and a permissive default stays informational. Three new regression tests in
  `tests/test_mcp.py`.
- **Lockfile refreshed.** `uv.lock` was still recording `coding-scaffold v0.1.0` despite
  the v0.4.0 release tag. Re-locked so `uv sync` no longer produces an accidental local
  diff on first run.

## [0.4.0] — 2026-05-18

### Added

- **Codex `.codex/config.toml` parsing for `mcp scan`.** The MCP scanner now reads
  Codex's TOML configuration in addition to `opencode.json` and `.claude/settings.json`.
  Supports the canonical `[mcp_servers.<name>]` form and the legacy `[mcp.<name>]` form
  as a fallback. Malformed TOML is reported as a warning, not a crash. Uses stdlib
  `tomllib` — no new dependencies.
- **Reversible agentic work (`coding-scaffold session start` / `checkpoint` / `diff` / `rollback` / `summary`).**
  `start` creates a Git branch (or a worktree with `--worktree`) and records the start commit;
  `checkpoint` does `git add -A && git commit` and updates the session state; `diff` shows
  the change set since the start commit (including untracked files); `rollback` is
  preview-by-default — `--confirm` alone does a soft reset (preserves your changes staged),
  `--confirm --hard` discards them; `summary` prints branch + baseline + checkpoint count +
  files-changed. The session never auto-pushes, never deletes work without explicit
  confirmation, and the per-session `*.state.json` is git-ignored so it doesn't pollute
  checkpoint commits. See
  [Team Rollout / Reversible Agentic Work](docs/docs/wiki/Team-Rollout.md#reversible-agentic-work).
- **Memory governance (`coding-scaffold memory capture` / `review` / `promote` / `expire` /
  `audit` / `init`).** Memory entries are reviewable Markdown files under
  `.coding-scaffold/memory/<class>/` with frontmatter (`class`, `owner`, `created`,
  `expires`, `source`, `status`). Memory classes follow the maintainer brief:
  `project_fact`, `team_preference`, `decision`, `session_lesson` (default 30-day TTL),
  `failed_attempt`, `personal_data` (requires `--allow-personal`), `secret` (always refused).
  `capture` refuses content that looks like a secret (AWS / GitHub / OpenAI key patterns,
  PEM blocks). `audit` runs the same patterns over every existing entry plus PII heuristics
  (email, phone-shaped strings) and exits non-zero on `error` severity. Markdown is the v1
  backend; sqlite / mempalace / vector are reserved for future versions. See
  [Team Rollout / Memory Governance](docs/docs/wiki/Team-Rollout.md#memory-governance).

## [0.3.0] — 2026-05-18

### Added

- **Machine-readable agent permissions (`coding-scaffold permissions write`).** Writes
  `.coding-scaffold/agent-permissions.json` with the canonical permission shape — filesystem
  read/write/deny patterns, shell-command allowlist + approval-required list, network defaults,
  and MCP defaults. Idempotent; pass `--force` to regenerate. The `shell.allowed` list is
  lightly project-aware (Python projects get `pytest`/`ruff`, Node projects get `npm test`,
  etc.). See [Security / Machine-Readable Permissions](docs/docs/wiki/Security.md#machine-readable-permissions-artifact).
- **MCP governance (`coding-scaffold mcp policy init` / `scan` / `snapshot` / `diff`).**
  Reviewable team policy at `.coding-scaffold/mcp-policy.json`. The scanner inspects known
  MCP-config locations (`opencode.json`, `.claude/settings.json`) and flags remote servers,
  unpinned npm packages, risky launchers (curl-pipe-shell, sudo, bash -c), broad filesystem
  access (root / home), unapproved servers, denied servers, and review-required capabilities.
  `snapshot` + `diff` together let you commit a known-good state and detect drift in CI.
  `mcp diff` exits non-zero when anything changed. No commands are executed; no network
  calls. See [Security / MCP Governance](docs/docs/wiki/Security.md#mcp-governance).
- **Reviewable skill packs (`coding-scaffold skills new` / `lint` / `approve` / `export`).**
  Each skill lives at `.coding-scaffold/skills/<name>/` with `SKILL.md`, `manifest.json`,
  optional `scripts/` and `tests/`, and a `CHECKSUM` file frozen at approval time.
  `skills lint` flags broad "always use this" language, hidden-instruction phrases,
  undeclared capabilities (network / shell / credential), missing required sections, invalid
  manifest fields, placeholder owners, and drift since the recorded checksum.
  `skills export` bundles a skill into a `tar.gz` for sharing. See
  [Security / Skill Pack Governance](docs/docs/wiki/Security.md#skill-pack-governance).
- **Readiness benchmark (`coding-scaffold eval init` / `run` / `report`).** Deterministic
  checks that score how prepared a repo is for safe agentic coding: detectable build/test/lint
  signals, agent instructions present, policy pack present, non-empty deny list, PR template
  present, MCP policy present when MCP is detected, session-trace location available, context
  lint clean, and context budget under the limit. No model-intelligence benchmark — purely
  observable artifacts. `eval run` writes `.coding-scaffold/eval-report.json` and exits
  non-zero when any check fails, so it can gate CI. See
  [Team Rollout / Readiness Benchmark](docs/docs/wiki/Team-Rollout.md#readiness-benchmark).
- **Agent-context linter (`coding-scaffold context lint`).** Deterministic, heuristic-only
  checker for `AGENTS.md`, `CLAUDE.md`, `llms.txt`, and the `.coding-scaffold/` guidance
  docs. Flags vague rules without verifiers, dangerous shell recommendations
  (`chmod 777`, force-push without lease, `--no-verify`, piping `curl` to a shell), duplicate
  rules across files, contradictory rules, missing build/test commands for the detected
  project type, beginner-hostile MCP/orchestration leads, tooling conflicts (e.g. instructions
  say `use yarn` but the repo commits `package-lock.json`), and excessive context length.
  Output is JSON-friendly via `--json` and exits non-zero on `error` severity so it can gate
  CI. No LLM calls.
- **`coding-scaffold context explain`** — read-only summary of the agent-context surface
  (rule counts, detected verifiers, mentioned advanced concepts, project-type signal).
  Useful for spot-checking before adding more guidance.
- **Per-session traces (`coding-scaffold session init` / `session summarize`).** `init`
  writes `.coding-scaffold/sessions/YYYY-MM-DD-<slug>.md` from a structured template; same-day
  collisions get numeric suffixes; files are never overwritten. `summarize` reads back
  structured fields (bullet counts, test pass/fail) deterministically — no agent-transcript
  parsing in v1.
- **Agentic PR template (`coding-scaffold pr-template init`).** Writes
  `.github/PULL_REQUEST_TEMPLATE/agentic-change.md`, which GitHub picks up automatically. The
  template asks the operator to disclose agent/tool used, model/provider, files changed,
  commands run, tests run, external tools or MCP servers, data exposure risk, and review
  focus. Idempotent — re-running skips an existing file rather than overwriting.

### Documentation

- New section in [Context Hygiene](docs/docs/wiki/Context-Hygiene.md#lint-agent-context-files)
  explaining what the linter catches.
- New section in [Team Rollout](docs/docs/wiki/Team-Rollout.md#reviewable-agentic-changes) showing
  the PR-template + session-trace flow end to end.

## [0.2.0] — 2026-05-18

### Added

- **Foam knowledge backend.** `coding-scaffold knowledge create --backend foam` generates a
  self-contained VS Code workspace under `.coding-scaffold/knowledge/` with an extensions
  recommendation for `foam.foam-vscode`, Foam workspace settings, note templates under
  `.foam/templates/`, and a `FOAM.md` entry note. Foam is MIT-licensed and runs entirely in
  VS Code — a commercial-friendly alternative to Obsidian for organizations that don't want
  the paid Obsidian Commercial license. See
  [Knowledge Base / Foam](docs/docs/wiki/Knowledge-Base.md#foam).

### Fixed

- **Knowledge index case-collision hardening.** Stale `index.md` reference in the generated
  `AGENTS.md` cleaned up; the golden-output tests gained an automatic `_casefold_collisions`
  guard so any future case-sensitive vs case-insensitive filesystem mismatch is caught at test
  time, not in Linux CI after the fact.
- **Misleading `setup tool --install` example.** The README block previously showed OpenCode
  twice (with and without `--install`) while Hermes and Pi appeared only once. Rewritten so
  every tool is listed once for the validate-and-configure form and `--install` is shown once
  as a universal modifier — it's a flag on `setup tool` itself, not OpenCode-specific.
- **Non-existent `policy --strict` flag** removed from the control-and-reproducibility persona
  path. Default policy is already strict; `--relaxed-permissions` is documented as the opt-out.

### Changed

- **Compatibility matrix dedup.** The README compatibility table was diverging from the
  canonical 11-row capability matrix in `docs/docs/wiki/Tool-Adapters.md`. Replaced with a quick-scan
  tool → support-depth strip that links to the canonical version, eliminating two-source drift.

### Documentation

- 14 audit findings reconciled between code and docs: knowledge-tree listings completed in
  README and Knowledge-Base.md to match what `knowledge.py` actually writes (`decisions/`,
  `sessions/`, `sharing/`, and the layered scopes); `.coding-scaffold/team/sources/` added to
  the outputs inventory; Claude Code and Codex added to the installer sentence;
  `INDEX.md` casing corrected throughout.
- **Review-Backlog reorganized.** Twelve items delivered as of v0.1.0 moved into a
  `Delivered as of v0.1.0` section at the top of `docs/docs/wiki/Review-Backlog.md` so the priority
  sections actually reflect remaining work.
- **`--share` and `--relaxed-permissions` flags surfaced** in `docs/docs/wiki/Policy-Packs.md` with
  an example and a one-line explanation of each option.
- **Wiki-style `[[X]]` links converted to relative Markdown** in `Home.md`, `_Sidebar.md`,
  `Policy-Packs.md`, and `Knowledge-Base.md` so the docs render correctly when browsing
  `docs/docs/wiki/` in the repo on GitHub.

### Housekeeping

- `.gitignore` entries added for `.claude/settings.local.json` and `.claude/worktrees/` so
  agent-tool artifacts don't accidentally land in the repo.

## [0.1.0] — 2026-05-18

First tagged release. The scaffold is positioned for a controlled team pilot, not yet for
enterprise-wide governance. See [Team-Rollout / Persona Paths](docs/docs/wiki/Team-Rollout.md#persona-paths)
for the supported entry points.

### Added — core scaffold

- Guided setup (`setup run`) with hardware probe, provider detection, and deterministic
  model-selection guidance via `tools select-model`.
- Tool adapters for OpenCode (deep), Claude Code (native config), Codex (native config),
  OpenClaude / Hermes / Pi (guidance). Full capability matrix in
  [docs/docs/wiki/Tool-Adapters.md](docs/docs/wiki/Tool-Adapters.md#compatibility-matrix).
- Optional add-ons: `llmfit`, `routellm`, `open-multi-agent`, `obsidian`,
  `caveman-compression`. Each is installed only on explicit `setup addon` invocation.
- Policy packs (`policy --scope team|company`) that generate reviewable defaults for sharing,
  permissions, MCP servers, and provider allow/deny lists.
- Credential templates (`credentials --format env|json`) that never write secret values.
- Team-onboarding manifest workflow: `team init`, `team connect`, `team sync`, `team doctor`.
  Imports land under `.coding-scaffold/team/sources/` and never overwrite a user's curated
  `.coding-scaffold/knowledge/` tree.
- Context compression (`context compress`) with built-in and optional Caveman engines, plus
  budget inspection (`context budget`).
- Knowledge layers (raw, wiki, skills, agents, sharing) with status checks for `owner`,
  `last_reviewed`, maturity, and `source_refs`.
- Safe regeneration via `setup update`: drift in generated content is staged as `.new` next to
  user-edited files; the version file only advances for files actually written to destination.

### Added — operations

- GitHub Actions CI: `ruff` + `pytest` on push to `main` and on every PR.
- Reproducible installs via `uv` with a committed `uv.lock`. Classic `pip install -e ".[dev]"`
  remains supported.
- `coding-scaffold setup tool` validates and (with consent) installs OpenCode, Claude Code,
  Codex, OpenClaude, Hermes, or Pi. Install scripts run with a 300-second timeout and captured
  output in non-interactive mode.

### Security posture

- Azure endpoint and deployment values are redacted from serialized config (`providers.json`,
  adapter JSON) because the subdomain typically encodes tenant identity. Real values live only
  in `.env.local`.
- Team-manifest imports are confined to `.coding-scaffold/team/sources/<kind>/<slug>/`. Local
  paths and `file://` remotes require `--allow-local`. Cloned repos retain `.git` inside a
  hidden `_repo` subdirectory so subsequent syncs use `git pull --ff-only`.
- Local model runtimes are probed for endpoint reachability before being marked available;
  having the CLI on `PATH` is no longer sufficient.
- Policy `_merge_opencode_config` deep-merges `mcp.<server>` and `permission.<scope>` and stages
  the result as `opencode.json.new` when an existing `opencode.json` is present.
- Context compression no longer strips articles (`the | a | an`) from prose, which previously
  corrupted identifiers inside inline code spans and link targets.
- The threat model is documented in [docs/docs/wiki/Security.md](docs/docs/wiki/Security.md#threat-model).

### Known limitations

- The scaffold is reviewable guidance, not a security boundary. Enforcement belongs to the
  underlying coding tool, identity layer, network controls, repository protection rules, and CI.
- Runtime model routing is only available for OpenCode (via RouteLLM). Other tools rely on
  their own provider configuration plus `tools select-model` recommendations.
- The `setup update` 3-way merge currently has one deferred test scenario; see the open
  refactor backlog ([#1](https://github.com/JRS1986/CodingScaffold/issues/1),
  [#2](https://github.com/JRS1986/CodingScaffold/issues/2),
  [#7](https://github.com/JRS1986/CodingScaffold/issues/7),
  [#8](https://github.com/JRS1986/CodingScaffold/issues/8)) for the longer-running work.

### Platforms

- macOS, Linux, and WSL on Python 3.11, 3.12, and 3.13. Earlier Python versions are not
  supported. Windows native (outside WSL) works for documentation generation but not for tool
  installation — use WSL for the full flow.

[0.5.1]: https://github.com/JRS1986/CodingScaffold/releases/tag/v0.5.1
[0.5.0]: https://github.com/JRS1986/CodingScaffold/releases/tag/v0.5.0
[0.4.2]: https://github.com/JRS1986/CodingScaffold/releases/tag/v0.4.2
[0.4.1]: https://github.com/JRS1986/CodingScaffold/releases/tag/v0.4.1
[0.4.0]: https://github.com/JRS1986/CodingScaffold/releases/tag/v0.4.0
[0.3.0]: https://github.com/JRS1986/CodingScaffold/releases/tag/v0.3.0
[0.2.0]: https://github.com/JRS1986/CodingScaffold/releases/tag/v0.2.0
[0.1.0]: https://github.com/JRS1986/CodingScaffold/releases/tag/v0.1.0
