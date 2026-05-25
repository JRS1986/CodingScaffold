# Coding Tool Adapters

CodingScaffold stays tool-neutral. It writes hints for current tools, but the project should remain
easy to adapt when new coding agents appear. OpenCode is the deepest integration target. Claude
Code and Codex are native configuration targets. OpenClaude, Hermes, and Pi remain lightweight
guidance-first connectors.

## OpenCode

Best default when you want the most mature open workflow today. OpenCode has an official installer,
terminal/desktop/IDE surfaces, broad provider support through models.dev, local model support, LSP
awareness, multi-session workflows, and GitHub Copilot sign-in. It is a good first adapter for teams
that want stability and a visible ecosystem.

Install:

```bash
coding-scaffold setup tool --tool opencode
```

Use `coding-scaffold setup tool --tool opencode --install` when you intentionally want the CLI to
install a missing tool without a second prompt, for example in a prepared dev container.

Generate OpenCode-native config:

```bash
coding-scaffold tools adapt --target . --tool opencode
```

This writes `opencode.json`, `.opencode/agents/`, and `.opencode/commands/`. Then run:

```bash
opencode
```

Recommended first prompt inside OpenCode:

```text
/first-session
```

## Claude Code

Use when a team wants Claude Code's native project settings, permissions, commands, MCP, and
subagents while keeping CodingScaffold as the shared team contract.

Install or validate:

```bash
coding-scaffold setup tool --tool claude-code
```

Generate Claude Code-native project files:

```bash
coding-scaffold tools adapt --target . --tool claude-code
```

This writes `CLAUDE.md`, `.claude/settings.json`, `.claude/commands/`, and `.claude/agents/`.
Use Claude Code's own runtime settings and `/model` controls for actual model selection.

## Codex

Use when a team wants Codex to read project instructions and project-local skills while keeping
credentials and runtime behavior in Codex's native controls.

Install or validate:

```bash
coding-scaffold setup tool --tool codex
```

Generate Codex-native project files:

```bash
coding-scaffold tools adapt --target . --tool codex
```

This writes `AGENTS.md`, `.codex/config.toml`, and `.codex/skills/`.

## OpenClaude

Useful when you want to explore a fast-moving Claude-Code-like workflow with multiple providers,
OpenAI-compatible APIs, Ollama, GitHub Models, slash commands, MCP, and provider profiles. Treat it
as experimental: it is an unofficial community project, so evaluate licensing, provenance, security,
and team comfort before standardizing on it.

Install:

```bash
coding-scaffold setup tool --tool openclaude
```

Use this scaffold with OpenClaude:

```bash
openclaude
```

Inside OpenClaude, run `/provider` and use `.coding-scaffold/openclaude.json` as the project hint.

## Hermes

Useful when you want a broader autonomous agent harness around coding work: persistent memory,
skills, MCP, messaging integrations, scheduled automations, and selectable execution backends.
Treat it as a powerful workflow runner: configure its model, tools, environment, and backend before
letting it edit a project.

Install or validate:

```bash
coding-scaffold setup tool --tool hermes
```

Generate Hermes project guidance:

```bash
coding-scaffold tools adapt --target . --tool hermes
```

This writes `.coding-scaffold/HERMES.md`. Start with `hermes setup`, then run `hermes` from the
project directory.

## Pi

Useful when you want a minimal terminal coding harness with small core behavior, project
instructions from `AGENTS.md`, slash commands, resumable sessions, prompt templates, skills, and
TypeScript extension points.

Install or validate:

```bash
coding-scaffold setup tool --tool pi
```

Generate Pi project guidance:

```bash
coding-scaffold tools adapt --target . --tool pi
```

This writes `.coding-scaffold/PI.md`. Start Pi from the project directory with `pi`, authenticate
with `/login` or environment variables, and run `/reload` after changing project instructions.

## Compatibility Matrix

| Tool | Generated files | Native surface | CodingScaffold stance |
| --- | --- | --- | --- |
| OpenCode | config, agents, commands | providers, local models, permissions, agents | deep/default integration |
| Claude Code | `CLAUDE.md`, settings, commands, reviewer | settings, permissions, MCP, subagents | native config, no runtime control |
| Codex | `AGENTS.md`, config, skills | layered instructions, approvals, local CLI | native guidance, no runtime control |
| OpenClaude | adapter guide | profiles, MCP, slash commands | lightweight guidance |
| Hermes | adapter guide | memory, skills, MCP, backend choices | lightweight guidance |
| Pi | adapter guide | instructions, sessions, extensions | lightweight guidance |

## RouteLLM

RouteLLM is optional advanced routing, not the default onboarding path. Use it when you want an
OpenAI-compatible local router endpoint between a weak/routine model and a strong/heavy-lift model.

```bash
coding-scaffold setup addon --target . --addon routellm
coding-scaffold tools route --target . --backend routellm
```

Read `.coding-scaffold/ROUTELLM.md` before starting the server; some routers require an
`OPENAI_API_KEY` for embeddings even when one routed model is local.

## Open Multi-Agent

Open Multi-Agent is optional advanced workflow automation, not the first onboarding step. Use it
when a skill has proven useful in OpenCode and should become a repeatable TypeScript workflow,
backend job, or CI-like check.

```bash
coding-scaffold setup addon --target . --addon open-multi-agent
coding-scaffold tools workflow --target . --backend open-multi-agent
```

This writes `.coding-scaffold/OPEN_MULTI_AGENT.md`,
`.coding-scaffold/open-multi-agent.team.json`, and
`examples/open-multi-agent/team-coding-workflow.ts`. Start in plan-only mode and review the task
DAG, permissions, traces, and verification signals before allowing execution.

## Context Budget And Compression

Large context can make agent sessions less precise. Check the budget before loading broad team
knowledge, then compress optional reference notes only as sidecars:

```bash
coding-scaffold context budget --target . --source team
coding-scaffold context compress --target . --source knowledge
```

Use `.caveman.md` sidecars for reference-heavy sessions. The default compressor is built in. Install
`caveman-compression` only when you want to try the upstream engine with
`coding-scaffold context compress --target . --source knowledge --engine caveman`.
Keep original Markdown, policies, requirements, and active code as the source of truth.

## Adding The Next Tool

New agents will keep appearing. Add one by creating a new adapter file in `.coding-scaffold/`, then
document:

- install command
- credential source
- local model endpoint format
- project-rule file support
- how to run plan/read-only mode
- how to run build/edit mode
- how to verify edits
