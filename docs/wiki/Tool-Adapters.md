# Tool Adapters

CodingScaffold stays tool-neutral while generating useful native files for current coding agents.

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

