# Context Hygiene

Agentic coding gets better when the model sees the right context, not the most context.
CodingScaffold adds a small guardrail around this: estimate the context budget, compress optional
reference material, and start a fresh session when the current one has become too loaded.

## Why This Matters

Long-context models are useful, but they do not magically make every token equally valuable.
Important facts can get buried, old assumptions can keep steering the conversation, and a session
that has accumulated too much history can start answering the project it remembers instead of the
project in front of it.

The practical rule is:

- load task-specific context first
- keep policy and requirements uncompressed unless reviewed
- compress reference notes only as sidecars
- start a fresh session for a new task when the current context is too large or stale

This should not be left entirely to the model or the coding tool. The scaffold can catch obvious
risk earlier because it knows the project layout, team knowledge folders, and generated sidecars.

## Check The Budget

```bash
coding-scaffold context budget --target ~/dev/my-project --source knowledge
```

Defaults:

- warn above 100,000 estimated tokens
- warn above 40% of the configured context window
- estimate original files by default and ignore `.caveman.md` sidecars
- inspect `.coding-scaffold/knowledge` for `--source knowledge`
- inspect knowledge, skills, policy, and agents for `--source team`

Machine-readable output is available for CI or team checks:

```bash
coding-scaffold context budget --target ~/dev/my-project --source team --json
```

Use a warning as a prompt to narrow the task, retrieve fewer files, compress support notes, or open
a fresh coding session.

Estimate a sidecar-first session after compression:

```bash
coding-scaffold context budget --target ~/dev/my-project --source knowledge --prefer compressed
```

Use `--prefer both` only when you intentionally want to measure the full stored corpus.

## Compression Sidecars

The default compressor is built into CodingScaffold and works offline:

```bash
coding-scaffold context compress --target ~/dev/my-project --source knowledge
```

`context compress --source team` compresses knowledge, skills, and OpenCode agent notes, but skips
`.coding-scaffold/policy` by default because policy text is reviewed config where exact wording can
matter.

Caveman Compression is available as an optional experimental engine:

```bash
coding-scaffold setup addon --target ~/dev/my-project --addon caveman-compression
coding-scaffold context compress --target ~/dev/my-project --source knowledge --engine caveman
```

This writes files like:

```text
.coding-scaffold/knowledge/decisions/api-contract.md
.coding-scaffold/knowledge/decisions/api-contract.caveman.md
```

The original Markdown remains the source of truth. The `.caveman.md` file is optional agent input
for token-constrained sessions.

## What To Compress

Good candidates:

- long session summaries
- background architecture notes
- decision history
- glossary material
- repeated project explanations

Avoid by default:

- security policy
- legal or compliance text
- acceptance criteria
- active code
- migration steps
- anything where exact wording matters

## Team Operating Rule

For shared knowledge, do not auto-promote compressed notes upward through company, unit,
department, and team layers. Promote the original reviewed Markdown by pull request. Regenerate
sidecars after merge.

A useful team ritual is:

```bash
coding-scaffold knowledge status --target .
coding-scaffold context budget --target . --source team
coding-scaffold context compress --target . --source knowledge
```

Run it before large refactors, onboarding sessions, and workflow demos. It keeps the agent's memory
useful without pretending that every old token deserves a seat at the table.

## Lint Agent-Context Files

Agent-context files (`AGENTS.md`, `CLAUDE.md`, `llms.txt`, and the `.coding-scaffold/`
guidance docs) are the primary way an agent learns the project's rules. Long or vague
instructions make sessions worse, not better. CodingScaffold ships a deterministic linter
that flags common problems:

```bash
coding-scaffold context lint --target .
coding-scaffold context lint --target . --json    # CI-friendly output
```

The linter is heuristic and never calls a model. It catches:

- **Vague rules** — phrases like `clean code`, `best practices`, `professional` without
  naming a verifier on the same line.
- **Dangerous recommendations** — `chmod 777`, `rm -rf /`, `git push --force` (without
  `--force-with-lease`), `--no-verify`, piping `curl` to a shell. These get severity
  `error`.
- **Duplicate rules across files** — the same instruction in `AGENTS.md` and `CLAUDE.md`
  is a drift risk; pick one canonical home and link from the other.
- **Contradictory rules** — `always run tests` paired with `skip tests`, `use yarn` paired
  with `use npm`, etc.
- **Missing build/test commands** — if the project looks like Python, Node, Rust, Go,
  Ruby, PHP, or CMake but none of the context files mention a recognizable test command,
  agents will guess (badly).
- **Beginner-hostile guidance** — leading with MCP, multi-agent orchestration, hooks, or
  RouteLLM before mentioning a single test command.
- **Tooling conflicts** — instructions say `use yarn` but the repo commits `package-lock.json`,
  etc.
- **Excessive length** — over ~2000 tokens per file. Move long sections out to linked docs.

The exit code is `1` when there is at least one `error` finding, so `context lint` can gate
PRs in CI.

Use the companion command to see what's currently in your context surface:

```bash
coding-scaffold context explain --target .
```

This is read-only — it reports rule counts, detected verifiers, mentioned advanced concepts,
and the project-type signal the linter uses. Useful for spot-checking before adding more
guidance.
