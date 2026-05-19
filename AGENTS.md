# Agents — CodingScaffold

This is the agent-context file for the CodingScaffold project itself. The constraints
below apply to any AI coding agent working on this repo.

## What this project is

A local-first, deterministic scaffold for AI-assisted coding teams. It is **not** a coding
agent and **never** calls a model at runtime. Anything an agent contributes here should
respect that posture.

## Verification commands

Run these before claiming a change is done. Each must pass with exit code 0.

- `uv run ruff check` — lint passes.
- `uv run pytest -q` — full test suite passes (330+ tests as of v0.5.0).

For larger changes, also run the scaffold on itself as a smoke check:

- `coding-scaffold context lint --target .` — must pass with no errors.
- `coding-scaffold eval run --target .` — must pass.

The repo ships an `.coding-scaffold/eval-config.json` that disables the checks for
`policy_exists` and `denied_files_configured` because this repo deliberately ships no
policy pack and no `agent-permissions.json` (see "Deliberately absent" below).

## Project constraints

- **No new runtime dependencies.** `pyproject.toml`'s `dependencies = []` is intentional.
  Dev-only deps go in `[project.optional-dependencies].dev` and must justify their weight.
- **No LLM calls.** The scaffold is deterministic by design; pytest verifies this by
  running offline. Any feature that wants an LLM is the coding tool's responsibility.
- **No network calls.** The only allowed subprocess is `git`. Adding any other network
  egress requires an explicit design discussion in the PR.
- **No telemetry.** Ever.
- **Backwards compatibility.** Every existing CLI command should keep working unless a
  breaking change is explicitly called out in the PR title and the CHANGELOG.

## Commit messages

Plain, descriptive commits. Do not append a `Co-Authored-By: Claude ...` trailer.

## Session traces for bigger changes

For PRs that touch three or more modules, or for any architectural change, start a session
trace so reviewers can follow the steps without re-running the agent in their head:

```bash
coding-scaffold session init --target . --task "Short description"
```

Fill in the structured sections as you work. Reference the trace file in the PR body.

## PR template

This repo ships an agentic-change PR template at
`.github/PULL_REQUEST_TEMPLATE/agentic-change.md`. Use it for any PR with substantial AI
assistance — GitHub offers it via the "Choose a template" picker on the new-PR page.

## Deliberately absent

The scaffold itself does **not** generate or commit:

- `.coding-scaffold/policy/` — this repo IS the policy generator; it does not generate
  policy for its own development. Disabled in `eval-config.json`.
- `.coding-scaffold/agent-permissions.json` — same reasoning. Disabled in `eval-config.json`.
- `.coding-scaffold/mcp-policy.json` and any MCP server config — this project does not
  use MCP. The eval check auto-skips when no MCP config is detected.
- `.coding-scaffold/skills/` — the project does not ship skills for its own contributors.

If a future PR adds any of those, document why in the PR description and update this file.

## Quick reference

| What | Where |
|---|---|
| Build / dependency lock | `pyproject.toml`, `uv.lock` |
| Test suite | `tests/`, run via `uv run pytest -q` |
| Lint config | `[tool.ruff]` in `pyproject.toml` |
| Source modules | `src/coding_scaffold/` |
| Wiki | `docs/docs/wiki/` (Markdown source for rspress; also published to GitHub Pages) |
| Release notes | `CHANGELOG.md` |
| CI | `.github/workflows/ci.yml` — runs ruff + pytest on push to main and on every PR |
