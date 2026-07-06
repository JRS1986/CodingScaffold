# Tool Adapters

CodingScaffold stays tool-neutral while generating useful native files for current coding agents.
OpenCode is the deepest integration target; Claude Code and Codex are native configuration targets;
OpenClaude, Hermes, and Pi remain lightweight guidance-first connectors.

Adapters are where the scaffold hands off to tools that actually call models. Generating adapter
files does not require an LLM; running an adapter session does.

**Multi-tool projects:** every adapter listed here can be generated alongside
another via `setup run --tool <a> --tool <b>` (or `--tool a,b`). Codex + Claude
Code in the same repo is the most common pair; see
[Getting-Started](./Getting-Started.md#two-tools-in-one-repo).

## OpenCode

OpenCode is the recommended first adapter and the default for most teams today. It has official
install paths, terminal/desktop/IDE surfaces, LSP awareness, multi-session workflows, broad
provider support, local-model support, and GitHub Copilot sign-in.

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

Claude Code uses native project files and settings. CodingScaffold generates the native project
files and team contract, but leaves runtime behavior to the tool:

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

OpenClaude is worth tracking if your team wants a fast-moving, Claude-Code-like community workflow
across OpenAI-compatible APIs, Ollama, GitHub Models, MCP, slash commands, and provider profiles.
Treat it as experimental and review provenance, licensing, and security before standardizing on
it. Support is intentionally lightweight because the project moves quickly:

```bash
coding-scaffold setup tool --tool openclaude
coding-scaffold tools adapt --target ~/dev/my-project --tool openclaude
```

Generated guidance lives in `.coding-scaffold/OPENCLAUDE.md`.

Use `coding-scaffold setup tool --tool both` when a team wants to compare both tools on the same
project.

## Hermes

Hermes support is lightweight project guidance for teams that want a broader autonomous agent
harness around coding work: persistent memory, skills, MCP, messaging, scheduled tasks, and
configurable execution backends.

```bash
coding-scaffold setup tool --tool hermes
coding-scaffold tools adapt --target ~/dev/my-project --tool hermes
```

Generated guidance lives in `.coding-scaffold/HERMES.md`.

Configure Hermes with `hermes setup`, `hermes model`, `hermes tools`, and `hermes env` before
letting it edit a project.

## Pi

Pi support is lightweight project guidance for teams that want a minimal terminal coding harness
with project instructions, slash commands, resumable sessions, and extension points:

```bash
coding-scaffold setup tool --tool pi
coding-scaffold tools adapt --target ~/dev/my-project --tool pi
```

Generated guidance lives in `.coding-scaffold/PI.md`.

Pi loads `AGENTS.md` project instructions; restart Pi or run `/reload` after changing guidance.

## Compatibility Matrix

A capability row marked ✓ means CodingScaffold actively generates configuration for that
capability. A row that names a file or flag means the tool's native surface supports it but the
scaffold leaves the configuration to the tool. A dash means the tool either doesn't support the
capability or CodingScaffold has no opinion about it.

| Capability | OpenCode | Claude Code | Codex | OpenClaude | Hermes | Pi |
| --- | --- | --- | --- | --- | --- | --- |
| Install support | ✓ official script | ✓ npm package | ✓ npm package | ✓ npm package | ✓ official script | ✓ npm package |
| Project instructions | ✓ `AGENTS.md` + scaffold guide | ✓ `CLAUDE.md` | ✓ `AGENTS.md` + `.codex/` | ✓ `OPENCLAUDE.md` | ✓ `HERMES.md` | ✓ `PI.md` + `AGENTS.md` |
| Slash commands / skills | ✓ 4 generated | ✓ 2 generated | skills only | doc-only | doc-only | doc-only |
| Agents / subagents | ✓ explorer / implementer / reviewer | ✓ reviewer | — | — | — | — |
| Permissions / approval | ✓ via policy pack | ✓ via `.claude/settings.json` | tool's own approval mode | — | — | — |
| MCP servers | ✓ disable list in policy | settings + docs | — | tool's own | tool's own | — |
| Local model endpoint | ✓ provider detection | tool's own | tool's own | tool's own | tool's own | tool's own |
| Cloud provider allow/deny | ✓ explicit lists in policy | tool's own | tool's own | tool's own | tool's own | tool's own |
| Static per-command profiles | ✓ in commands | partial (settings) | — | — | — | — |
| Runtime routing (RouteLLM) | ✓ via `tools route` | — | — | — | — | — |
| **CodingScaffold support depth** | **deep** | **native config** | **native config** | guidance | guidance | guidance |

Support-depth definitions:

- **deep**: scaffold generates a full set of config + commands + agents and the tool runtime
  reads them directly. OpenCode is the only deep target today.
- **native config**: scaffold generates files in the tool's official locations (`CLAUDE.md`,
  `AGENTS.md`, `.claude/settings.json`, `.codex/config.toml`) and the tool reads them. Runtime
  control stays with the tool.
- **guidance**: scaffold writes a `<TOOL>.md` brief but the tool's own configuration is required
  to actually run. Use these when the tool is unfamiliar to the team or moves quickly upstream.

Known gaps: runtime model routing is only available where the tool exposes an OpenAI-compatible
backend swap (today: OpenCode via RouteLLM). For other tools the scaffold relies on the tool's own
provider configuration plus `tools select-model` recommendations.

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
