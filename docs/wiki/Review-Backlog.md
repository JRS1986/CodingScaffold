# Review Backlog

This backlog turns the external assessment into implementation tasks. It keeps the near-term north
star narrow: CodingScaffold is the bootstrap and governance layer that makes existing coding agents
usable, safe, and team-aware in real software teams.

## Task Principles

- Prioritize the scaffold vision before broader agent-platform work.
- Treat OpenCode as the deepest integration target.
- Treat Claude Code and Codex as native configuration targets, not runtimes to control.
- Keep routing optional: recommendation for all tools, static profiles where supported, runtime
  routing only through compatible gateways.
- Make knowledge reviewable, owned, sourced, and refreshable before adding more memory backends.

## Priority 1

### P1-01 Sharpen Product Scope And Non-Goals

**Problem:** The project currently reads like several products at once: onboarding wizard, local LLM
setup helper, provider detector, router, adapter generator, wiki generator, policy manager, team
onboarding system, and future orchestration layer.

**Task:** Update README and wiki positioning around one sentence:
CodingScaffold is a local-first onboarding, configuration, and governance scaffold for
AI-assisted software development teams.

**Acceptance criteria:**

- README has a concise "What this is" and "What this is not" section.
- Non-goals explicitly say it is not a new coding agent, not a replacement for Claude Code, Codex,
  OpenCode, Cursor, or Copilot, not an autonomous development platform yet, not a security boundary
  by itself, and not a universal model router.
- Routing is described as one capability inside the scaffold, not the core thesis.
- Wiki home and core concepts use the same north-star language.

**Likely touchpoints:** `README.md`, `docs/wiki/Home.md`, `docs/wiki/Core-Concepts.md`,
`docs/wiki/FAQ.md`.

### P1-02 Reframe Routing As Optional Backend Capability

**Problem:** Complexity-based routing is useful, but it is not defensible as the main product
contribution because dedicated routing frameworks already exist.

**Task:** Introduce a three-level routing model:

- Recommendation: human-readable model choice for all tools.
- Static profiles: different agents or commands use different models, with OpenCode as the best fit.
- Runtime routing: one endpoint routes per prompt through RouteLLM or a gateway-compatible setup.

**Acceptance criteria:**

- Docs consistently state "where supported, configure routing; otherwise provide model-selection
  guidance and tool-native profiles."
- `tools route` docs make RouteLLM explicitly optional and advanced.
- `tools select-model` remains positioned as local deterministic guidance, not request routing.
- Generated guidance for tools without runtime routing points users to profiles or manual model
  choice instead of implying runtime control.

**Likely touchpoints:** `README.md`, `docs/wiki/Model-Selection-and-Providers.md`,
`docs/wiki/Advanced-Workflows.md`, `src/coding_scaffold/writers.py`,
`src/coding_scaffold/adapters.py`.

### P1-03 Add A Native Claude Code Adapter

**Problem:** Claude Code has project-level settings, team-shared config, permissions, hooks, MCP
servers, plugins, and settings scopes. CodingScaffold should generate high-quality native
configuration rather than treat it as implied future support.

**Task:** Add `coding-scaffold tools adapt --tool claude-code`.

**Acceptance criteria:**

- CLI accepts `claude-code` for setup/adapt paths without breaking existing aliases.
- Adapter creates `CLAUDE.md`.
- Adapter creates `.claude/settings.json`.
- Adapter creates `.claude/commands/first-session.md`.
- Adapter creates `.claude/commands/agentic-change.md`.
- Adapter creates `.claude/agents/reviewer.md`.
- Existing files are skipped or refreshed according to the repo's current generated-file behavior.
- Tests cover generated file paths, no-overwrite behavior, and routing/profile hints.
- Docs explain that Claude Code integration is config and knowledge generation, not runtime control.

**Likely touchpoints:** `src/coding_scaffold/cli.py`, `src/coding_scaffold/adapters.py`,
`tests/test_adapters.py`, `tests/test_cli.py`, `README.md`, `docs/wiki/Tool-Adapters.md`.

### P1-04 Add A Native Codex Adapter

**Problem:** Codex reads `AGENTS.md` and layered global/project instructions. CodingScaffold should
generate native project guidance and optional project-local skills.

**Task:** Add `coding-scaffold tools adapt --tool codex`.

**Acceptance criteria:**

- CLI accepts `codex` for setup/adapt paths.
- Adapter creates or refreshes project `AGENTS.md` with the shared team contract.
- Adapter creates `.codex/skills/README.md` and at least one starter skill template or pointer.
- If `.codex/config.toml` is generated, it contains only project-safe guidance and does not store
  secrets or pretend to control unsupported runtime behavior.
- Tests cover generated file paths, no-overwrite behavior, and docs contract.
- Docs explain how Codex differs from OpenCode: guidance-first, not deep routing-first.

**Likely touchpoints:** `src/coding_scaffold/cli.py`, `src/coding_scaffold/adapters.py`,
`src/coding_scaffold/writers.py`, `tests/test_adapters.py`, `tests/test_cli.py`, `README.md`,
`docs/wiki/Tool-Adapters.md`.

### P1-05 Add A Compatibility Matrix

**Problem:** The README lists tools, but it does not make native surfaces, integration depth, and
limitations easy to compare.

**Task:** Add an explicit compatibility matrix for OpenCode, Claude Code, Codex, OpenClaude, Hermes,
and Pi.

**Acceptance criteria:**

- Matrix includes install support, project instructions, commands, agents/subagents, permissions,
  MCP, local models, cloud providers, static profiles, runtime routing, and current support level.
- Matrix distinguishes "generated by CodingScaffold" from "supported by the underlying tool."
- Known limitations are explicit.

**Likely touchpoints:** `README.md`, `docs/wiki/Tool-Adapters.md`.

## Priority 2

### P2-01 Make The Knowledge Lifecycle Explicit

**Problem:** The current knowledge base can create and inspect Markdown structures, but the stronger
wiki vision needs lifecycle mechanics: raw inputs, curated outputs, freshness metadata, provenance,
ownership, review flow, and update policies.

**Task:** Introduce this structure for new knowledge bases:

```text
.coding-scaffold/knowledge/
  raw/
    meetings/
    decisions/
    code-notes/
    incidents/
  wiki/
    architecture.md
    setup.md
    testing.md
    deployment.md
    domain-language.md
    decisions.md
  skills/
  agents/
  index.md
```

**Acceptance criteria:**

- New knowledge generation writes the raw/wiki structure.
- Existing layered folders remain supported or receive a documented migration path.
- Curated wiki pages include frontmatter fields for `scope`, `maturity`, `owner`, `last_reviewed`,
  and `source_refs`.
- Knowledge docs explain raw capture versus curated wiki output.
- Tests cover generated structure and frontmatter.

**Likely touchpoints:** `src/coding_scaffold/knowledge.py`, `tests/test_knowledge.py`,
`docs/wiki/Knowledge-Base.md`, `README.md`.

### P2-02 Add Knowledge Distillation Workflow

**Problem:** A wiki maintained by LLM assistance is not yet a product feature unless updates are
reviewable and provenance-aware.

**Task:** Add `coding-scaffold knowledge distill --target . --source raw --review`.

**Acceptance criteria:**

- Command reads raw knowledge inputs and proposes curated wiki updates.
- In review mode it writes `.new` files or another PR-ready proposal format instead of silently
  overwriting curated wiki pages.
- Proposed pages include `source_refs`.
- Command reports created, updated, skipped, and warning counts.
- Tests cover no-source behavior, proposal writing, and preservation of existing curated pages.

**Likely touchpoints:** `src/coding_scaffold/cli.py`, `src/coding_scaffold/knowledge.py`,
`tests/test_cli.py`, `tests/test_knowledge.py`, `docs/wiki/Knowledge-Base.md`.

### P2-03 Strengthen Knowledge Status Checks

**Problem:** `knowledge status` currently counts scope and maturity, but it does not yet enforce the
metadata needed to keep a team wiki fresh.

**Task:** Extend status checks for curated wiki pages.

**Acceptance criteria:**

- Status flags missing `owner`, `last_reviewed`, and `source_refs` on curated pages.
- Status warns about stale `last_reviewed` values using a documented threshold.
- Status distinguishes raw notes from curated wiki pages.
- JSON output preserves machine-readable warnings.
- Tests cover missing, valid, and stale metadata.

**Likely touchpoints:** `src/coding_scaffold/knowledge.py`, `tests/test_knowledge.py`,
`docs/wiki/Knowledge-Base.md`.

### P2-04 Create A 10-Minute MVP Demo Path

**Problem:** The docs describe many commands, but the value would be clearer with one short path
from empty adoption to useful first agent session.

**Task:** Add a documented demo flow:

1. Run `coding-scaffold setup run` in an existing repo.
2. Detect local hardware and available providers.
3. Generate `AGENTS.md`, OpenCode config, policy defaults, and starter knowledge.
4. Run OpenCode `/first-session`.
5. Have the agent identify test commands, propose a safe improvement, and write a first knowledge
   entry.
6. Have a second developer run `team connect` and receive the same knowledge and policies.

**Acceptance criteria:**

- Demo is documented as the recommended first pilot.
- Commands are copy-pasteable.
- Expected generated files and expected agent outputs are listed.
- Demo includes a "what to review before committing" checklist.
- Optional screenshots or asciinema task is tracked separately if not implemented immediately.

**Likely touchpoints:** `README.md`, `docs/wiki/Getting-Started.md`, `docs/wiki/Team-Rollout.md`,
optional `docs/demo/`.

### P2-05 Add Security And Company-Usage Notes

**Problem:** Policy packs are not security boundaries. Company users need explicit guidance on
credentials, provider use, local/cloud data handling, and review responsibility.

**Task:** Add a security notes page and link it from setup, policy, credentials, and team rollout
docs.

**Acceptance criteria:**

- Notes explain that generated config is guardrail guidance, not enforcement.
- Notes cover credential templates, ignored local secret files, provider allow/deny lists, MCP
  server risk, shared knowledge review, and company policy alignment.
- Docs include a checklist for introducing CodingScaffold in a company repo.

**Likely touchpoints:** `docs/wiki/Security.md`, `docs/wiki/Policy-Packs.md`,
`docs/wiki/Team-Rollout.md`, `README.md`.

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

### P3-05 Add CI, Ruff, And Release Workflow

**Problem:** The repo lists pytest and ruff dev dependencies but needs visible automation for
maintainability and credibility.

**Task:** Add GitHub Actions for tests, linting, and release packaging.

**Acceptance criteria:**

- CI runs `pytest` and `ruff check`.
- CI runs on pull requests and pushes to the main branch.
- Release workflow builds package artifacts.
- README shows the expected local verification commands.

**Likely touchpoints:** `.github/workflows/ci.yml`, `.github/workflows/release.yml`, `README.md`.

### P3-06 Make Dependency Setup Reproducible

**Problem:** The README recommends `uv`, but the repo does not currently include a lockfile or a
documented reproducible dependency policy.

**Task:** Decide and document the dependency workflow.

**Acceptance criteria:**

- Project either commits a `uv.lock` or documents why it intentionally does not.
- README and contributor docs use one primary development setup path.
- CI uses the same setup path.

**Likely touchpoints:** `pyproject.toml`, optional `uv.lock`, `README.md`, CI workflow.

### P3-07 Reproduce And Fix WSL/Python 3.13 Crash

**Problem:** The review references an existing WSL/Python 3.13 crash. This directly affects trust in
cross-platform onboarding.

**Task:** Add a reproduction note or failing test, then fix the crash.

**Acceptance criteria:**

- Issue is reproducible in a test or documented manual reproduction.
- Fix supports WSL and Python 3.13 without regressing Python 3.11.
- Compatibility docs mention tested Python versions and WSL status.

**Likely touchpoints:** `src/coding_scaffold/hardware.py`, `src/coding_scaffold/installers.py`,
tests, `README.md`.

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
