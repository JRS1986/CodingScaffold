# Tool Adapters

CodingScaffold stays tool-neutral while generating useful native files for current coding agents.

Adapters are where the scaffold hands off to tools that actually call models. Generating adapter
files does not require an LLM; running an adapter session does.

## OpenCode

OpenCode is the recommended first adapter.

```bash
coding-scaffold setup tool --tool opencode
coding-scaffold tools adapt --target ~/dev/my-project --tool opencode
```

Generated files include:

- `opencode.json`
- `.opencode/agents/reviewer.md`
- `.opencode/agents/explorer.md`
- `.opencode/agents/implementer.md`
- `.opencode/commands/first-session.md`
- `.opencode/commands/agentic-change.md`
- `.opencode/commands/review.md`
- `.opencode/commands/recheck-route.md`

Before running `/first-session`, make sure OpenCode can reach at least one model through its own
provider setup, a local OpenAI-compatible endpoint, GitHub Copilot sign-in, or cloud credentials.

For company or team defaults, generate a policy pack:

```bash
coding-scaffold policy --target ~/dev/my-project --scope company
```

This can set `share: disabled`, add policy instructions, ask before edit/bash actions, disable
named MCP servers, and add provider allow/deny lists in `opencode.json`.

## OpenClaude

OpenClaude support is intentionally lightweight because the project moves quickly:

```bash
coding-scaffold setup tool --tool openclaude
coding-scaffold tools adapt --target ~/dev/my-project --tool openclaude
```

Generated guidance lives in `.coding-scaffold/OPENCLAUDE.md`.

Use `coding-scaffold setup tool --tool both` when a team wants to compare both tools on the same
project.

## Hermes

Hermes support is lightweight project guidance for teams that want a broader autonomous agent
harness around coding work:

```bash
coding-scaffold setup tool --tool hermes
coding-scaffold tools adapt --target ~/dev/my-project --tool hermes
```

Generated guidance lives in `.coding-scaffold/HERMES.md`.

Configure Hermes with `hermes setup`, `hermes model`, `hermes tools`, and `hermes env` before
letting it edit a project.

## Pi

Pi support is lightweight project guidance for teams that want a minimal terminal coding harness:

```bash
coding-scaffold setup tool --tool pi
coding-scaffold tools adapt --target ~/dev/my-project --tool pi
```

Generated guidance lives in `.coding-scaffold/PI.md`.

Pi loads `AGENTS.md` project instructions; restart Pi or run `/reload` after changing guidance.

## Optional Tooling

Tool adapters are the coding surface. Add-ons support model sizing, routing, team automation, and
knowledge navigation:

```bash
coding-scaffold setup addon --target ~/dev/my-project --addon llmfit
coding-scaffold setup addon --target ~/dev/my-project --addon routellm
coding-scaffold setup addon --target ~/dev/my-project --addon open-multi-agent
coding-scaffold setup addon --target ~/dev/my-project --addon obsidian
coding-scaffold setup addon --target ~/dev/my-project --addon caveman-compression
```

## Adding Another Tool

When adding a new adapter, document:

- install command
- credential source
- local endpoint format
- project-rule support
- read-only mode
- edit mode
- verification flow
- how to share skills and agents
