# Review Backlog

This backlog turns the external assessment into implementation tasks. It keeps the near-term north
star narrow: CodingScaffold is the bootstrap and governance layer that makes existing coding agents
usable, safe, and team-aware in real software teams.

## Delivered as of v0.1.0

The items below were on this backlog and have shipped. Kept here so the design intent stays
linkable — see the cross-references for where the work landed.

- **P1-01 Sharpen Product Scope And Non-Goals** — README "What This Is" / "What This Is Not"
  sections; wiki [Home](index.md), [Core Concepts](Core-Concepts.md), and [FAQ](FAQ.md) use the
  same north-star language.
- **P1-02 Reframe Routing As Optional Backend Capability** — three-level routing model is
  documented in [Model Selection and Providers](Model-Selection-and-Providers.md) and reflected
  in adapter generation.
- **P1-03 Add A Native Claude Code Adapter** — `coding-scaffold tools adapt --tool claude-code`
  generates `CLAUDE.md`, `.claude/settings.json`, slash commands, and the reviewer subagent.
- **P1-04 Add A Native Codex Adapter** — `coding-scaffold tools adapt --tool codex` generates
  `AGENTS.md`, `.codex/config.toml`, and `.codex/skills/`.
- **P1-05 Add A Compatibility Matrix** — [Tool Adapters / Compatibility Matrix](Tool-Adapters.md#compatibility-matrix)
  with 11 capabilities × 6 tools and support-depth labels.
- **P2-01 Make The Knowledge Lifecycle Explicit** — raw/wiki/decisions/sessions structure plus
  layered folders (`team` / `department` / `unit` / `company`) are now generated; see
  [Knowledge Base](Knowledge-Base.md).
- **P2-02 Add Knowledge Distillation Workflow** — `coding-scaffold knowledge distill --target .
  --source raw --review` writes `.new` proposals under `knowledge/wiki/`.
- **P2-03 Strengthen Knowledge Status Checks** — `knowledge status` flags missing `owner`,
  `last_reviewed`, `source_refs`, and warns on stale `last_reviewed` past 180 days.
- **P2-04 Create A 10-Minute MVP Demo Path** — documented in
  [Getting Started](Getting-Started.md#first-pilot-in-ten-minutes) and the
  [Getting Started first-pilot section](Getting-Started.md#first-pilot-in-ten-minutes).
- **P2-05 Add Security And Company-Usage Notes** — [Security](Security.md) page with company
  checklist, credentials, policy packs, shared knowledge, and a full threat model.
- **P3-05 Add CI, Ruff, And Release Workflow** — `.github/workflows/ci.yml` runs `ruff check`
  + `pytest` on PR and push to `main`; v0.1.0 tagged and released.
- **P3-06 Make Dependency Setup Reproducible** — `uv.lock` is committed; README documents the
  `uv sync --extra dev` path; CI uses the same.
- **P3-07 Reproduce And Fix WSL/Python 3.13 Crash** — fixed in commit `86c05a0`; tracked as
  GitHub issue #28 (closed).

The items below are still in flight. They remain prioritized as originally specified.

## Task Principles

- Prioritize the scaffold vision before broader agent-platform work.
- Treat OpenCode as the deepest integration target.
- Treat Claude Code and Codex as native configuration targets, not runtimes to control.
- Keep routing optional: recommendation for all tools, static profiles where supported, runtime
  routing only through compatible gateways.
- Make knowledge reviewable, owned, sourced, and refreshable before adding more memory backends.

## Priority 3

### P3-01 Refactor CLI Dispatch

**Problem:** CLI command setup and dispatch are large enough to make future adapter and knowledge
commands harder to add safely.

**Task:** Split parser construction and command execution into smaller command groups.

**Acceptance criteria:**

- `build_parser` remains testable.
- Command handlers are grouped by domain: setup, tools, knowledge, context, team, policy.
- Existing command aliases keep working.
- CLI tests pass without changing user-facing behavior unless documented.

**Likely touchpoints:** `src/coding_scaffold/cli.py`, `tests/test_cli.py`.

### P3-02 Extract Shared File-Write And Template Helpers

**Problem:** Adapter, knowledge, policy, and writer modules each have related file-writing patterns.
Duplication makes generated-file behavior easier to drift.

**Task:** Create shared helpers for write, collect-if-absent, JSON write, skipped-file reporting, and
template rendering where useful.

**Acceptance criteria:**

- No behavior change for generated files.
- Tests cover overwrite versus skip behavior through public functions.
- Helper names make generated-file safety explicit.

**Likely touchpoints:** `src/coding_scaffold/writers.py`, `src/coding_scaffold/adapters.py`,
`src/coding_scaffold/knowledge.py`, `src/coding_scaffold/policy.py`, tests.

### P3-03 Add Golden-File Tests For Scaffold Output

**Problem:** The project has good unit tests, but generated scaffold outputs need stable regression
coverage.

**Task:** Add golden-file tests for representative setup/adapt/knowledge outputs.

**Acceptance criteria:**

- A sample intake fixture generates deterministic output.
- Golden tests cover `.coding-scaffold/AGENTS.md`, model-selection guidance, OpenCode adapter files,
  and knowledge structure.
- Test update process is documented.

**Likely touchpoints:** `tests/fixtures/`, `tests/test_writers.py`, `tests/test_adapters.py`,
`tests/test_knowledge.py`.

### P3-04 Add Integration Tests On A Sample Repo

**Problem:** Individual modules are tested, but the core promise is an end-to-end scaffold in an
existing repo.

**Task:** Add integration tests that run setup commands against a minimal sample project.

**Acceptance criteria:**

- Test runs `setup run` or equivalent non-interactive flow against a temporary repo.
- Test verifies generated files, no secret leakage, and idempotent update behavior.
- Test covers at least one adapter and knowledge backend.

**Likely touchpoints:** `tests/test_cli.py`, `tests/fixtures/sample_repo/`.

### P3-08 Add Docs Media For The MVP Demo

**Problem:** Screenshots or terminal recordings would make the 10-minute path more credible for
colleagues evaluating the project.

**Task:** Add either screenshots or an asciinema recording for the MVP demo.

**Acceptance criteria:**

- Media shows setup, generated files, and first-session handoff.
- Docs include text alternatives or a transcript.
- Media does not expose secrets, real customer code, or private provider configuration.

**Likely touchpoints:** `docs/demo/`, `docs/wiki/Getting-Started.md`, `docs/wiki/Team-Rollout.md`.

## Later Platform Work

These are intentionally later. They should not block the scaffold MVP:

- richer workflow orchestration beyond generated OpenCode commands
- automatic wiki refresh scheduling
- hosted team policy distribution
- runtime router evaluation harnesses
- deeper multi-agent execution backends
- enterprise identity and policy enforcement
