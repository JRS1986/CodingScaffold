# Tool Adapters

CodingScaffold stays tool-neutral while generating useful native files for current coding agents.
OpenCode is the deepest integration target; Claude Code and Codex are native configuration targets;
OpenClaude, Hermes, and Pi remain lightweight guidance-first connectors.

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

## Claude Code

Claude Code uses native project files and settings:

```bash
coding-scaffold setup tool --tool claude-code
coding-scaffold tools adapt --target ~/dev/my-project --tool claude-code
```

Generated files include:

- `CLAUDE.md`
- `.claude/settings.json`
- `.claude/commands/first-session.md`
- `.claude/commands/agentic-change.md`
- `.claude/agents/reviewer.md`

CodingScaffold does not control the Claude Code runtime. Use Claude Code's own settings, model
selection, permissions, hooks, MCP, and authentication.

## Codex

Codex uses project instructions and conservative project-local guidance:

```bash
coding-scaffold setup tool --tool codex
coding-scaffold tools adapt --target ~/dev/my-project --tool codex
```

Generated files include:

- `AGENTS.md`
- `.codex/config.toml`
- `.codex/skills/README.md`
- `.codex/skills/first-session.md`

CodingScaffold does not store OpenAI credentials or control Codex execution. Use Codex's native
model and approval-mode controls.

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

## Compatibility Matrix

| Tool | Generated files | Native surface | CodingScaffold stance |
| --- | --- | --- | --- |
| OpenCode | config, agents, commands | providers, local models, permissions, agents | deep/default integration |
| Claude Code | `CLAUDE.md`, settings, commands, reviewer | settings, permissions, MCP, subagents | native config, no runtime control |
| Codex | `AGENTS.md`, config, skills | layered instructions, approvals, local CLI | native guidance, no runtime control |
| OpenClaude | adapter guide | profiles, MCP, slash commands | lightweight guidance |
| Hermes | adapter guide | memory, skills, MCP, backend choices | lightweight guidance |
| Pi | adapter guide | instructions, sessions, extensions | lightweight guidance |

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
