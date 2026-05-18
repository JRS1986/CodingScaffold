# Team Rollout

This page is a practical plan for introducing CodingScaffold to a team.

## Pilot Session

Use one real project and one safe issue.

1. Run `coding-scaffold setup run --target <repo>`.
2. Review provider and hardware detection.
3. Generate or confirm `AGENTS.md`, OpenCode config, policy defaults, and starter knowledge.
4. Run OpenCode `/first-session`.
5. Pick one small improvement.
6. Run `/agentic-change`.
7. Review generated files, credentials, provider policy, MCP settings, knowledge provenance, and tests.
8. Capture the workflow as a skill and one knowledge entry.
9. Have a second developer run `team connect` against the shared manifest.

## Team Defaults

Agree on:

- privacy mode
- preferred local runtime
- cloud escalation rules
- default coding adapter
- verification commands
- when to use heavy-lift models
- where shared knowledge lives

Publish those defaults as a team onboarding manifest:

```bash
coding-scaffold team init --target . --team platform-api
```

New joiners should be able to run:

```bash
coding-scaffold team connect --target . --manifest <team-onboarding-repo>
coding-scaffold team connect --target . --manifest <team-onboarding-repo> --dry-run
coding-scaffold team doctor --target .
```

That should expose the shared knowledge base, approved skills, approved agents, policy, config, and
required add-ons before the first agentic coding session.

## Governance

Review these changes like code:

- skills
- agent definitions
- model-routing defaults
- shared knowledge decisions
- workflow automation

## Reviewable Agentic Changes

Two artifacts make AI-assisted PRs reviewable in practice. Generate them once per project; commit
them; ignore them afterwards.

### PR template

```bash
coding-scaffold pr-template init --target .
```

Writes `.github/PULL_REQUEST_TEMPLATE/agentic-change.md`. GitHub auto-detects the
`PULL_REQUEST_TEMPLATE/` directory and offers the template via the "Choose a template" picker
on every new PR, or by linking
`https://github.com/<owner>/<repo>/compare/main...feature-branch?template=agentic-change.md`.

The template asks the operator to disclose: agent/tool used, model/provider, files changed,
commands run, tests run, external tools or MCP servers, data exposure risk, review focus, and
known limitations. It's the discipline that lets reviewers focus on the change instead of
re-running the session in their head.

The command is idempotent — re-running it skips the existing file rather than overwriting it.

### Session traces

```bash
coding-scaffold session init --target . --task "Refactor the foo helper"
# work happens; fill in the structured sections as you go
coding-scaffold session summarize .coding-scaffold/sessions/2026-05-18-agentic-change.md
```

`session init` writes `.coding-scaffold/sessions/YYYY-MM-DD-<slug>.md` (default slug
`agentic-change`; pass `--slug` for a custom one). Same-day collisions get numeric suffixes
(`-2`, `-3`, ...) — the file is never overwritten.

The trace template captures task, plan, files inspected, files changed, commands run, test
results, risks, follow-ups, and reusable knowledge discovered. `session summarize` reads back
the structured fields (bullet counts, test pass/fail) without parsing free-form prose. This
keeps the session trace agent-agnostic — any tool can write into the template; the summary
runs deterministically.

When a session surfaces a reusable skill or a decision worth promoting, link the canonical
home from the `## Reusable Knowledge Discovered` section. The session file itself stays raw
and append-only; promotion happens through the knowledge layer.

## Success Signals

The rollout is working when:

- developers inspect before editing
- generated changes are smaller
- tests are run more consistently
- review findings are caught earlier
- good prompts become skills
- decisions move from chat history into shared knowledge

## Persona Paths

Pick the path that matches the developer you're onboarding. Each path lists who it's for, what
"done" looks like for them, and the smallest command set that gets them there.

### Beginner path — for a junior developer new to agentic coding

**Who:** writes Python or web code, hasn't worked with an autonomous coding agent before. Wants
guardrails, not freedom.

**Success looks like:** after one session, they've inspected the repo with the agent, understood
the test command, and landed one small reviewable change without "magic" edits.

```bash
coding-scaffold setup run --target . --mode beginner
# Review the generated AGENTS.md, .opencode/, and .coding-scaffold/.
opencode  # or: claude
# Inside the agent, run /first-session, then /agentic-change on one small issue.
```

The beginner mode includes a first-project guide and conservative defaults
(`permission.edit: ask`, `share: disabled`). Keep policy at `--scope team` until the developer is
comfortable.

### Control / reproducibility path — for the skeptical senior

**Who:** deep expertise in their domain (firmware, embedded, kernel, etc.). Wants traceability,
no surprise edits, and a way to undo anything the agent did.

**Success looks like:** every agent action is visible in `git diff` and reproducible from the
scaffold files alone. They can disable any provider, any MCP server, and audit what the agent saw.

```bash
coding-scaffold setup run --target . --privacy local-only --tool claude-code
coding-scaffold policy --target . --scope team
coding-scaffold credentials --target . --format env
# Review .claude/settings.json (permission.edit: ask, permission.bash: ask).
# Review .coding-scaffold/policy/*.md for the disabled-providers list.
```

The default policy is strict: `share: disabled`, `permission.edit: ask`,
`permission.bash: ask`. Pass `--relaxed-permissions` only if you deliberately want to
disable the ask-before-edit/bash gate.

Pair with the [Threat Model](Security.md#threat-model) so they see the boundaries explicitly.

### Security review path — for a compliance engineer

**Who:** approves whether the team can use AI coding tools at all. Wants policy defaults,
credential handling, provider constraints, and audit expectations on paper.

**Success looks like:** they can answer "what does this tool generate, what does it not enforce,
and where do real controls live?" using the scaffold's own docs.

```bash
coding-scaffold setup run --target . --tool opencode
coding-scaffold policy --target . --scope company
# Read .coding-scaffold/policy/company.md, opencode.json.new, providers.json.
# Read docs/wiki/Security.md — Threat Model section.
```

The acceptance artifact is the policy diff plus a checklist of which platform controls back it
(identity, network egress, secret scanning, repository protection, CI). The scaffold doesn't
replace any of those; it surfaces what's expected.

### Team-lead path — for a lead establishing shared defaults

**Who:** runs a team where some developers use AI tools privately. Wants AI to become a team
capability with shared prompts, shared knowledge, shared policy.

**Success looks like:** every developer can `team connect` against the same manifest and get the
same generated config, knowledge layer, and policy. New joiners are productive on day one.

```bash
coding-scaffold team init --target . --team platform-api --knowledge-remote <repo-url>
# Customize .coding-scaffold/team-onboarding.json, then commit it.
# Each developer runs:
coding-scaffold team connect --target . --manifest <team-repo>
coding-scaffold team doctor --target .
```

When the manifest changes, every developer runs `team sync` and reviews the diff before merging
imports into their working knowledge.

## Reversible Agentic Work

`session start` creates a Git branch (and optionally a worktree) plus a session-trace file in
one step, recording the start commit so the work is fully reversible:

```bash
# Branch-only (cheap, works in any clean repo):
coding-scaffold session start --target . --slug refactor-foo --task "Refactor the foo helper"

# Worktree mode (full isolation; the agent works in a sibling directory):
coding-scaffold session start --target . --slug refactor-foo --worktree

# During the session:
coding-scaffold session checkpoint -m "extract helper"     # git add -A + commit + record
coding-scaffold session diff                                # what's changed since start
coding-scaffold session summary                             # branch, baseline, checkpoint count

# When you want to bail out:
coding-scaffold session rollback                            # preview only (safe default)
coding-scaffold session rollback --confirm                  # soft reset (keeps changes staged)
coding-scaffold session rollback --confirm --hard           # hard reset (discards changes)
```

The session never auto-pushes, never deletes work without explicit confirmation, and never
operates outside the chosen branch or worktree. The per-session state file
(`*.state.json`) is `.gitignore`d so it doesn't pollute checkpoint commits.

Use **branch-only mode** when the project is in a clean state and you trust the agent to
stay on a single branch. Use **worktree mode** when you want to keep working in the main
checkout while the agent works in a parallel directory — useful for pairing or when the
agent's environment differs from your local one.

`session rollback` is preview-by-default. Without `--confirm` it lists the files that would
be touched and exits. With `--confirm` alone it does a soft reset (your changes stay in the
working tree as staged). With `--confirm --hard` it discards everything since the start
commit. Both flags are required for the destructive path.

## Memory Governance

Memory entries live as reviewable Markdown files under `.coding-scaffold/memory/<class>/`.
Each entry has minimal frontmatter (`class`, `owner`, `created`, `expires`, `source`,
`status`) and free-form body.

Memory classes:

- **`project_fact`** — Stable, source-linked. Things that are unlikely to change.
- **`team_preference`** — Reviewable convention. "We use uv, not poetry."
- **`decision`** — Ideally linked to an ADR or issue.
- **`session_lesson`** — Captured from one agent session. Default 30-day expiry; promote to a
  more durable class before it expires.
- **`failed_attempt`** — Useful but potentially misleading; flag explicitly.
- **`personal_data`** — Restricted. Requires `--allow-personal` to store.
- **`secret`** — Never stored. `memory capture --class secret` is refused outright.

Commands:

```bash
coding-scaffold memory capture --class session_lesson --content "Yarn doesn't work; use npm." \
  --owner @me [--source path/to/note] [--expires 2026-06-01]

coding-scaffold memory review                # list active entries; flag unowned / expiring / expired
coding-scaffold memory promote <id> --to team_preference --owner @platform
coding-scaffold memory expire                # move past-expiry entries to memory/_expired/
coding-scaffold memory audit                 # heuristic scan for secrets / PII; exits 1 on error severity
coding-scaffold memory init                  # optional: write memory config.json
```

`memory capture` refuses content that looks like a secret (AWS/GitHub/OpenAI key patterns,
PEM blocks). `memory audit` runs the same patterns over every existing entry and reports
findings as severity `error`; e-mail and phone-number-shaped strings are reported as
`warning`. The audit is heuristic, not a full scanner — review the findings.

Backend: Markdown only in v1. SQLite, MemPalace, and vector backends are reserved for
future versions; the default stays simple so memory is Git-reviewable.

## Readiness Benchmark

Once the scaffold is in place, run the readiness benchmark to check whether the repo is
prepared for safe agentic coding:

```bash
coding-scaffold eval init    # optional: write .coding-scaffold/eval-config.json
coding-scaffold eval run     # execute all enabled checks
coding-scaffold eval report --cached    # re-print the most recent report
```

The benchmark runs deterministic checks only — no shell execution, no LLM calls. It looks for:

- a detectable build signal (`pyproject.toml`, `package.json`, `Cargo.toml`, …)
- a test command mentioned in the agent-context files
- a lint configuration file (or a `[tool.ruff]` / `[tool.black]` / `[tool.mypy]` section)
- agent instructions (`AGENTS.md`, `CLAUDE.md`, or `llms.txt`)
- a policy pack under `.coding-scaffold/policy/`
- a non-empty deny list in `agent-permissions.json`
- a PR template under `.github/PULL_REQUEST_TEMPLATE/`
- an MCP policy file *if* MCP config is detected
- a session-trace location
- a clean `context lint` result
- a context budget within the configured token limit

`eval run` writes the report to `.coding-scaffold/eval-report.json` and exits non-zero when
any check fails, so the benchmark can gate CI before AI-assisted PRs are accepted.

The benchmark scores readiness; it does *not* measure model intelligence. The point is to
confirm the repo gives the agent enough to work with — not to rank the agent.

## Pilot Metrics

These are measurement templates, not features. Track them manually during the pilot. If a number
moves the wrong way, that's the signal to revisit the scaffold or the policy, not the metric.

| Metric | How to measure | Target after 2 weeks |
| --- | --- | --- |
| Time to first safe agentic change | From `setup run` to the first merged PR generated via `/agentic-change`. | < 1 day for the beginner path; < 2 hours for AI power users. |
| Correct-test-command rate | Of agent sessions that ran a test, what fraction ran the project's actual test command (not a guess). | > 80%. Lower means `AGENTS.md` needs more explicit test guidance. |
| CI pass rate after agentic edits | Of PRs containing `/agentic-change` output, what fraction passed CI on first push. | At least matches non-agentic baseline. Below baseline means policy is too permissive or review is too thin. |
| Reusable skills captured | Count of skill entries committed to `.coding-scaffold/knowledge/skills/` during the pilot. | Two or more from each persona path. Zero means workflows aren't being abstracted. |
| Knowledge entries with `last_reviewed` | Of curated wiki pages under `knowledge/wiki/`, what fraction have a `last_reviewed` value within 90 days. | > 90% by end of pilot. Lower means the knowledge layer is decaying. |
| Reverted agentic changes | Count of merged `/agentic-change` PRs reverted within 7 days. | 0-1. Higher signals the scaffold is letting through changes the team can't validate. |

Run a 30-minute retrospective at the end of the pilot. Surface which metric was easiest to gather,
which was hardest, and whether any persona path under- or over-served the developer.
