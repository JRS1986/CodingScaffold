# Glossary

One paragraph per term. Read this first if any CodingScaffold output uses a word you
have not seen before. Each entry links to the wiki page that goes deeper.

## adapter

A small, native-format integration that teaches a specific coding tool how to behave
inside this project. `tools adapt --tool opencode` writes OpenCode-shaped files;
`--tool claude-code` writes the Claude-Code shape; and so on. Adapters are generated,
reviewable, and have no runtime. See [Tool-Adapters](./Tool-Adapters.md).

## agentic change

A code change planned or written with help from an AI coding agent (OpenCode, Claude
Code, Codex, …). CodingScaffold's `session` command + `agentic-change.md` PR template
exist so these changes ship with the same shape as any other PR. See
[Getting-Started](./Getting-Started.md).

## artifact

A file or directory CodingScaffold knows about: `AGENTS.md`, `.coding-scaffold/policy/`,
`PR template`, eval config, sessions directory, knowledge base. `doctor` surveys
artifacts; the canonical list with rationale lives in
[`src/coding_scaffold/artifacts.py`](https://github.com/JRS1986/CodingScaffold/blob/main/src/coding_scaffold/artifacts.py).

## context

The bytes that go into the agent's input window for a single turn: the prompt, project
rules, file excerpts, knowledge notes, prior messages. `context budget` estimates the
size; `context lint` checks the files; `context compress` writes safer sidecars. See
[Context-Hygiene](./Context-Hygiene.md).

## doctor

`coding-scaffold doctor` — the accessibility hub. Surveys what is set up, recommends
1–3 next commands, and explicitly says which advanced surfaces a beginner can ignore.
Never installs or writes; always safe to run.

## eval

A small readiness benchmark: `eval init` creates the config, `eval run` exercises it,
`eval report` summarizes. It validates that the scaffold is set up — not that the model
is good. See [Getting-Started](./Getting-Started.md).

## knowledge base

A team-shared, reviewable corpus of notes under `.coding-scaffold/knowledge/`. Multiple
backends are supported (markdown, obsidian, foam, mempalace, html). Layered by scope
(team/department/unit/company) and maturity (raw → curated wiki). See
[Knowledge-Base](./Knowledge-Base.md).

## maturity

The lifecycle stage of a knowledge note: `raw` (captured but unreviewed), `wiki`
(curated for the team), and the layered scopes (team/department/unit/company).
`knowledge promote` moves notes between maturity levels with an audit trail.

## MCP

Model Context Protocol — a way for an agent to talk to external integrations (Slack,
Notion, your bug tracker). `mcp policy`, `mcp scan`, `mcp snapshot`, `mcp diff`
govern which integrations the project allows. See [Security](./Security.md).

## memory

Reviewable memory entries the agent can recall: `memory capture` proposes one,
`memory review` accepts/rejects, `memory promote` moves it between maturity classes,
`memory audit` lists what is in effect. Distinct from knowledge: memory is short
runtime hints; knowledge is shared documentation.

## orchestration

A multi-step recipe a tool can drive (`tools orchestrate`). Distinct from a single
prompt: orchestration plans the steps, picks a model per step, and tracks results.

## persona

A target user shape: `beginner`, `control-and-reproducibility`, `security-review`,
`team-lead`. Used by `doctor --persona` / `pilot --persona` to surface a focused
recipe instead of the full firehose. Personas are documented in
[Team-Rollout](./Team-Rollout.md).

## pilot

`coding-scaffold pilot --target . --tool <name>` — read-only guided wrapper. Probes
the local environment and prints the exact 10-minute happy-path commands. Never
installs and never writes files. The printed recipe is what the user actually runs.

## policy pack

Files under `.coding-scaffold/policy/` that encode the team's non-negotiables:
allowed providers, network rules, model selection floors, MCP allowlist. See
[Policy-Packs](./Policy-Packs.md).

## provider

A source of model inference: a local runtime (Ollama, LM Studio) or a cloud API
(Anthropic, OpenAI, …). `probe` lists what is available; `routing.json` describes
how the project routes between them.

## routing

The plan for which model handles which class of request: `weak_model` (fast/cheap),
`strong_model` (high-quality), plus the endpoint and policy. Stored in
`.coding-scaffold/routing.json`.

## scaffold artifact

See [artifact](#artifact).

## scaffold version

A SHA256 snapshot of every generated file written by setup, stored in
`.coding-scaffold/scaffold-version.json`. `setup update` uses it to tell unchanged
files (safe to rewrite) from user-edited files (write a `.new` sidecar instead).

## session trace

A reviewable Markdown file under `.coding-scaffold/sessions/` recording a single
agentic change: task, commands run, diff, follow-ups. Powers reversibility:
`session checkpoint`, `session diff`, `session rollback`.

## skill

A reusable scoped instruction the agent loads on demand: a Markdown file under
`.coding-scaffold/skills/<name>/` with a `SKILL.md`, optional helpers, and an
approved checksum. `skills new`, `skills lint`, `skills approve`, `skills export`.
See [Skills-and-Agents](./Skills-and-Agents.md).

## stability marker

A label rendered in `--help` next to each command name: `[stable]`, `[preview]`,
`[experimental]`. Tells experienced teams what they can build infrastructure around.
The contract per marker lives in [Stability](./Stability.md).

## strong model

The model class used for high-quality output (planning, review, hard reasoning).
Set in `routing.json`. The pilot recipe avoids picking one for the user — that is
the team's call.

## team manifest

A JSON file (`team-onboarding.json`) shipped from a team repo that defines shared
policy, skills, knowledge sources, and version requirements. `team connect` /
`team sync` apply it; `team push` nominates local artifacts upward; `team doctor`
shows the effective merged view. See [Team-Sync](./Team-Sync.md).

## weak model

The model class used for fast/cheap calls (extraction, classification, format
conversion). Set in `routing.json`.
