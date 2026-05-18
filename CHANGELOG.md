# Changelog

All notable changes to CodingScaffold are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and the project
aims to follow [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added

- **Machine-readable agent permissions (`coding-scaffold permissions write`).** Writes
  `.coding-scaffold/agent-permissions.json` with the canonical permission shape — filesystem
  read/write/deny patterns, shell-command allowlist + approval-required list, network defaults,
  and MCP defaults. Idempotent; pass `--force` to regenerate. The `shell.allowed` list is
  lightly project-aware (Python projects get `pytest`/`ruff`, Node projects get `npm test`,
  etc.). See [Security / Machine-Readable Permissions](docs/wiki/Security.md#machine-readable-permissions-artifact).
- **MCP governance (`coding-scaffold mcp policy init` / `scan` / `snapshot` / `diff`).**
  Reviewable team policy at `.coding-scaffold/mcp-policy.json`. The scanner inspects known
  MCP-config locations (`opencode.json`, `.claude/settings.json`) and flags remote servers,
  unpinned npm packages, risky launchers (curl-pipe-shell, sudo, bash -c), broad filesystem
  access (root / home), unapproved servers, denied servers, and review-required capabilities.
  `snapshot` + `diff` together let you commit a known-good state and detect drift in CI.
  `mcp diff` exits non-zero when anything changed. No commands are executed; no network
  calls. See [Security / MCP Governance](docs/wiki/Security.md#mcp-governance).
- **Reviewable skill packs (`coding-scaffold skills new` / `lint` / `approve` / `export`).**
  Each skill lives at `.coding-scaffold/skills/<name>/` with `SKILL.md`, `manifest.json`,
  optional `scripts/` and `tests/`, and a `CHECKSUM` file frozen at approval time.
  `skills lint` flags broad "always use this" language, hidden-instruction phrases,
  undeclared capabilities (network / shell / credential), missing required sections, invalid
  manifest fields, placeholder owners, and drift since the recorded checksum.
  `skills export` bundles a skill into a `tar.gz` for sharing. See
  [Security / Skill Pack Governance](docs/wiki/Security.md#skill-pack-governance).
- **Readiness benchmark (`coding-scaffold eval init` / `run` / `report`).** Deterministic
  checks that score how prepared a repo is for safe agentic coding: detectable build/test/lint
  signals, agent instructions present, policy pack present, non-empty deny list, PR template
  present, MCP policy present when MCP is detected, session-trace location available, context
  lint clean, and context budget under the limit. No model-intelligence benchmark — purely
  observable artifacts. `eval run` writes `.coding-scaffold/eval-report.json` and exits
  non-zero when any check fails, so it can gate CI. See
  [Team Rollout / Readiness Benchmark](docs/wiki/Team-Rollout.md#readiness-benchmark).
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

- New section in [Context Hygiene](docs/wiki/Context-Hygiene.md#lint-agent-context-files)
  explaining what the linter catches.
- New section in [Team Rollout](docs/wiki/Team-Rollout.md#reviewable-agentic-changes) showing
  the PR-template + session-trace flow end to end.

## [0.2.0] — 2026-05-18

### Added

- **Foam knowledge backend.** `coding-scaffold knowledge create --backend foam` generates a
  self-contained VS Code workspace under `.coding-scaffold/knowledge/` with an extensions
  recommendation for `foam.foam-vscode`, Foam workspace settings, note templates under
  `.foam/templates/`, and a `FOAM.md` entry note. Foam is MIT-licensed and runs entirely in
  VS Code — a commercial-friendly alternative to Obsidian for organizations that don't want
  the paid Obsidian Commercial license. See
  [Knowledge Base / Foam](docs/wiki/Knowledge-Base.md#foam).

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
  canonical 11-row capability matrix in `docs/wiki/Tool-Adapters.md`. Replaced with a quick-scan
  tool → support-depth strip that links to the canonical version, eliminating two-source drift.

### Documentation

- 14 audit findings reconciled between code and docs: knowledge-tree listings completed in
  README and Knowledge-Base.md to match what `knowledge.py` actually writes (`decisions/`,
  `sessions/`, `sharing/`, and the layered scopes); `.coding-scaffold/team/sources/` added to
  the outputs inventory; Claude Code and Codex added to the installer sentence;
  `INDEX.md` casing corrected throughout.
- **Review-Backlog reorganized.** Twelve items delivered as of v0.1.0 moved into a
  `Delivered as of v0.1.0` section at the top of `docs/wiki/Review-Backlog.md` so the priority
  sections actually reflect remaining work.
- **`--share` and `--relaxed-permissions` flags surfaced** in `docs/wiki/Policy-Packs.md` with
  an example and a one-line explanation of each option.
- **Wiki-style `[[X]]` links converted to relative Markdown** in `Home.md`, `_Sidebar.md`,
  `Policy-Packs.md`, and `Knowledge-Base.md` so the docs render correctly when browsing
  `docs/wiki/` in the repo on GitHub.

### Housekeeping

- `.gitignore` entries added for `.claude/settings.local.json` and `.claude/worktrees/` so
  agent-tool artifacts don't accidentally land in the repo.

## [0.1.0] — 2026-05-18

First tagged release. The scaffold is positioned for a controlled team pilot, not yet for
enterprise-wide governance. See [Team-Rollout / Persona Paths](docs/wiki/Team-Rollout.md#persona-paths)
for the supported entry points.

### Added — core scaffold

- Guided setup (`setup run`) with hardware probe, provider detection, and deterministic
  model-selection guidance via `tools select-model`.
- Tool adapters for OpenCode (deep), Claude Code (native config), Codex (native config),
  OpenClaude / Hermes / Pi (guidance). Full capability matrix in
  [docs/wiki/Tool-Adapters.md](docs/wiki/Tool-Adapters.md#compatibility-matrix).
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
- The threat model is documented in [docs/wiki/Security.md](docs/wiki/Security.md#threat-model).

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

[0.2.0]: https://github.com/JRS1986/CodingScaffold/releases/tag/v0.2.0
[0.1.0]: https://github.com/JRS1986/CodingScaffold/releases/tag/v0.1.0
