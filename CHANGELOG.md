# Changelog

All notable changes to CodingScaffold are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and the project
aims to follow [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

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

[0.1.0]: https://github.com/JRS1986/CodingScaffold/releases/tag/v0.1.0
