# Tool Adapters

CodingScaffold stays tool-neutral while generating useful native files for current coding agents.

Adapters are where the scaffold hands off to tools that actually call models. Generating adapter
files does not require an LLM; running an adapter session does.

## OpenCode

OpenCode is the recommended first adapter.

```bash
curl -fsSL https://opencode.ai/install | bash
coding-scaffold adapt --target ~/dev/my-project --tool opencode
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
npm install -g @gitlawb/openclaude
coding-scaffold adapt --target ~/dev/my-project --tool openclaude
```

Generated guidance lives in `.coding-scaffold/OPENCLAUDE.md`.

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
