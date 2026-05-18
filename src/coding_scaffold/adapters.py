from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

from .file_ops import collect_json, collect_text, write_json, write_text
from .model_catalog import ROUTELLM_MF_DEFAULT_THRESHOLD
from .routing_io import load_routing_payload


@dataclass(frozen=True)
class AdapterResult:
    files: list[Path]
    skipped: list[Path]


def write_tool_adapter(target: Path, tool: str) -> AdapterResult:
    root = target.expanduser().resolve()
    files: list[Path] = []
    skipped: list[Path] = []
    routing = load_routing_payload(root)
    tools = ["opencode", "openclaude"] if tool == "both" else [tool]
    for selected in tools:
        if selected == "opencode":
            result = _write_opencode(root, routing)
        elif selected == "claude-code":
            result = _write_claude_code(root, routing)
        elif selected == "codex":
            result = _write_codex(root, routing)
        elif selected == "openclaude":
            result = _write_openclaude(root, routing)
        elif selected == "hermes":
            result = _write_hermes(root, routing)
        elif selected == "pi":
            result = _write_pi(root, routing)
        else:
            result = AdapterResult([], [])
        files.extend(result.files)
        skipped.extend(result.skipped)
    return AdapterResult(files, skipped)


def write_route_backend(target: Path, backend: str) -> AdapterResult:
    if backend != "routellm":
        return AdapterResult([], [])
    root = target.expanduser().resolve()
    scaffold = root / ".coding-scaffold"
    scaffold.mkdir(parents=True, exist_ok=True)
    routing = load_routing_payload(root)
    files = [
        write_text(scaffold / "ROUTELLM.md", _routellm_md(routing), overwrite=True),
        write_text(scaffold / "routellm.config.yaml", _routellm_yaml(routing), overwrite=True),
    ]
    return AdapterResult(files, [])


def write_workflow_backend(target: Path, backend: str) -> AdapterResult:
    if backend != "open-multi-agent":
        return AdapterResult([], [])
    root = target.expanduser().resolve()
    scaffold = root / ".coding-scaffold"
    examples = root / "examples" / "open-multi-agent"
    scaffold.mkdir(parents=True, exist_ok=True)
    examples.mkdir(parents=True, exist_ok=True)
    routing = load_routing_payload(root)
    files = [
        write_text(scaffold / "OPEN_MULTI_AGENT.md", _open_multi_agent_md(routing), overwrite=True),
        write_json(scaffold / "open-multi-agent.team.json", _open_multi_agent_team(routing)),
        write_text(examples / "team-coding-workflow.ts", _open_multi_agent_example(), overwrite=True),
    ]
    return AdapterResult(files, [])


def _write_opencode(root: Path, routing: dict[str, object]) -> AdapterResult:
    files: list[Path] = []
    skipped: list[Path] = []
    opencode_json = root / "opencode.json"
    config = {
        "$schema": "https://opencode.ai/config.json",
        "default_agent": "plan",
        "share": "disabled",
    }
    collect_text(files, skipped, opencode_json, json.dumps(config, indent=2) + "\n")

    agents = root / ".opencode" / "agents"
    commands = root / ".opencode" / "commands"
    collect_text(files, skipped, agents / "reviewer.md", _opencode_reviewer(routing))
    collect_text(files, skipped, agents / "explorer.md", _opencode_explorer())
    collect_text(files, skipped, agents / "implementer.md", _opencode_implementer(routing))
    collect_text(files, skipped, commands / "first-session.md", _opencode_first_session())
    collect_text(files, skipped, commands / "agentic-change.md", _opencode_agentic_change())
    collect_text(files, skipped, commands / "review.md", _opencode_review_command())
    collect_text(files, skipped, commands / "recheck-route.md", _opencode_recheck_route())
    return AdapterResult(files, skipped)


def _write_claude_code(root: Path, routing: dict[str, object]) -> AdapterResult:
    files: list[Path] = []
    skipped: list[Path] = []
    collect_text(files, skipped, root / "CLAUDE.md", _claude_md(routing))
    collect_json(files, skipped, root / ".claude" / "settings.json", _claude_settings())
    collect_text(
        files,
        skipped,
        root / ".claude" / "commands" / "first-session.md",
        _claude_first_session(),
    )
    collect_text(
        files,
        skipped,
        root / ".claude" / "commands" / "agentic-change.md",
        _claude_agentic_change(),
    )
    collect_text(files, skipped, root / ".claude" / "agents" / "reviewer.md", _claude_reviewer(routing))
    return AdapterResult(files, skipped)


def _write_codex(root: Path, routing: dict[str, object]) -> AdapterResult:
    files: list[Path] = []
    skipped: list[Path] = []
    collect_text(files, skipped, root / "AGENTS.md", _codex_agents_md(routing))
    collect_text(files, skipped, root / ".codex" / "skills" / "README.md", _codex_skills_readme())
    collect_text(files, skipped, root / ".codex" / "skills" / "first-session.md", _codex_first_session_skill())
    collect_text(files, skipped, root / ".codex" / "config.toml", _codex_config_toml())
    return AdapterResult(files, skipped)


def _write_openclaude(root: Path, routing: dict[str, object]) -> AdapterResult:
    scaffold = root / ".coding-scaffold"
    scaffold.mkdir(parents=True, exist_ok=True)
    path = scaffold / "OPENCLAUDE.md"
    return AdapterResult([write_text(path, _openclaude_md(routing), overwrite=True)], [])


def _write_hermes(root: Path, routing: dict[str, object]) -> AdapterResult:
    scaffold = root / ".coding-scaffold"
    scaffold.mkdir(parents=True, exist_ok=True)
    path = scaffold / "HERMES.md"
    return AdapterResult([write_text(path, _hermes_md(routing), overwrite=True)], [])


def _write_pi(root: Path, routing: dict[str, object]) -> AdapterResult:
    scaffold = root / ".coding-scaffold"
    scaffold.mkdir(parents=True, exist_ok=True)
    path = scaffold / "PI.md"
    return AdapterResult([write_text(path, _pi_md(routing), overwrite=True)], [])


def _model(routing: dict[str, object], key: str, fallback: str) -> str:
    value = routing.get(key)
    return str(value) if value else fallback


def _opencode_reviewer(routing: dict[str, object]) -> str:
    model = _model(routing, "strong_model", "use-global-model")
    return f"""---
description: Reviews code for regressions, missing tests, security issues, and maintainability.
mode: subagent
model: {model}
tools:
  write: false
  edit: false
---

You are the review agent. Lead with findings ordered by severity. Reference files and lines when
possible. Do not modify files. Focus on behavior, test coverage, security, data handling, and
maintainer clarity.
"""


def _opencode_explorer() -> str:
    return """---
description: Read-only codebase exploration and context loading.
mode: subagent
tools:
  write: false
  edit: false
---

You are the explorer agent. Map relevant files, commands, dependencies, and risks. Do not edit.
Return concise findings and the smallest useful next context to inspect.
"""


def _opencode_implementer(routing: dict[str, object]) -> str:
    model = _model(routing, "weak_model", "use-global-model")
    return f"""---
description: Implements small, bounded changes and runs narrow verification.
mode: subagent
model: {model}
---

You are the implementer agent. Own only the assigned files or module. Keep edits small, run the
narrowest meaningful check, and summarize changed files plus residual risk.
"""


def _opencode_first_session() -> str:
    return """This is the first agentic coding session for this project.

Do not edit yet.

1. Inspect the README, package/config files, test configuration, and main source directories.
2. Identify the language, package manager, run command, and test command.
3. Explain the main code paths and any obvious risk areas.
4. Propose one safe, small improvement that can be implemented and verified quickly.
5. Recommend whether the next step should use the explorer, implementer, or reviewer agent.

End with the exact prompt I should run next.
"""


def _opencode_agentic_change() -> str:
    return """Run a small agentic coding loop.

1. Use the explorer agent to inspect the relevant files and confirm the smallest safe scope.
2. Use the implementer agent to make only that change.
3. Run the narrowest meaningful verification.
4. Use the reviewer agent to look for regressions, missing tests, and unclear behavior.
5. Summarize changed files, checks, review findings, and any follow-up.
"""


def _opencode_review_command() -> str:
    return """Review the current change for regressions, missing tests, security issues, and unclear behavior.
Findings first. Do not edit files unless explicitly asked after the review.
"""


def _opencode_recheck_route() -> str:
    return """The current answer or plan feels off. Re-inspect the relevant files, state assumptions,
choose whether this should use the routine or heavy-lift model, and propose the smallest next step.
"""


def _claude_md(routing: dict[str, object]) -> str:
    weak = _model(routing, "weak_model", "choose-a-routine-model")
    strong = _model(routing, "strong_model", "choose-a-heavy-lift-model")
    return f"""# Claude Code Project Guide

This project uses CodingScaffold as a local-first onboarding, configuration, and governance layer
for AI-assisted development. Claude Code should use this file as project memory, not as a runtime
router.

## Team Contract

- Inspect before editing.
- Keep changes bounded to the requested task.
- Prefer reviewed Markdown knowledge in `.coding-scaffold/knowledge/`.
- Keep credentials in local ignored files or Claude Code's secure auth flow.
- Ask before broad rewrites, dependency changes, destructive commands, or cloud/provider changes.

## Model Guidance

- Routine/profile model: `{weak}`
- Heavy-lift/review model: `{strong}`

Use Claude Code's native `/model`, settings, and account configuration for actual model selection.
CodingScaffold only provides guidance and shared project context here.

## First Session

Run `/first-session` and wait for the repository map, test commands, risk areas, and one safe
proposed improvement before making edits.
"""


def _claude_settings() -> dict[str, object]:
    return {
        "permissions": {
            "defaultMode": "ask",
            "deny": [
                ".coding-scaffold/.env.local",
                ".coding-scaffold/credentials.local.json",
                "**/.env",
                "**/.env.*",
            ],
        },
        "includeCoAuthoredBy": False,
    }


def _claude_first_session() -> str:
    return """Inspect this repository without editing.

1. Read README, package/config files, test configuration, AGENTS.md or CLAUDE.md, and the main source directories.
2. Identify the language, package manager, run command, and test command.
3. Summarize the main code paths and risk areas.
4. Find the relevant CodingScaffold knowledge index, if present.
5. Propose one safe improvement that can be implemented and verified quickly.

End with the exact next prompt to run.
"""


def _claude_agentic_change() -> str:
    return """Run a small, reviewable coding loop.

1. Confirm the smallest safe scope and files.
2. Make only the requested change.
3. Run the narrowest meaningful verification.
4. Review the diff for regressions, missing tests, secrets, and unclear behavior.
5. Summarize changed files, checks, findings, and follow-up.
"""


def _claude_reviewer(routing: dict[str, object]) -> str:
    model = _model(routing, "strong_model", "use-current-claude-code-model")
    return f"""---
name: reviewer
description: Reviews code for regressions, missing tests, security issues, and maintainability.
model: {model}
tools: Read, Grep, Glob, Bash
---

You are the review agent for this project. Do not modify files. Lead with findings ordered by
severity, reference files and lines when possible, and focus on behavior, test coverage, secrets,
data handling, permissions, and maintainer clarity.
"""


def _codex_agents_md(routing: dict[str, object]) -> str:
    weak = _model(routing, "weak_model", "choose-a-routine-model")
    strong = _model(routing, "strong_model", "choose-a-heavy-lift-model")
    return f"""# Codex Project Guide

CodingScaffold configures shared project guidance for Codex. It does not replace Codex, control
Codex runtime behavior, or store credentials.

## Operating Rules

- Inspect before editing and keep changes bounded.
- Use suggest/read-only behavior for unfamiliar areas and reviews.
- Prefer local-first workflows unless the task explicitly needs cloud quality and credentials are available.
- Keep secrets in ignored local files or provider auth flows, never in generated scaffold files.
- Review generated knowledge, adapters, and policy changes like code.

## Model Guidance

- Routine/profile model: `{weak}`
- Heavy-lift/review model: `{strong}`

Use Codex's native model and approval-mode controls for actual execution. Treat these values as
team guidance for choosing routine versus heavy-lift work.

## Knowledge

Start with `.coding-scaffold/knowledge/index.md` or `.coding-scaffold/knowledge/INDEX.md` when it
exists. Curated wiki pages are preferred over raw notes.
"""


def _codex_skills_readme() -> str:
    return """# Codex Skills

Project-local skills capture repeatable workflows that Codex should follow. Keep them short,
reviewable, and tied to real project checks.

Suggested starter:

- `first-session.md`: inspect before editing and propose one safe improvement.
"""


def _codex_first_session_skill() -> str:
    return """# First Session

Use when Codex is starting work in this repository for the first time.

1. Inspect README, package/config files, tests, and main source directories.
2. Identify run and test commands.
3. Summarize main code paths and risk areas.
4. Read the CodingScaffold knowledge index if present.
5. Propose one safe improvement before editing.
"""


def _codex_config_toml() -> str:
    return """# Project-local CodingScaffold guidance for Codex.
# Do not store secrets here. Use Codex, OpenAI, or provider auth flows for credentials.

approval_mode = "suggest"
"""


def _openclaude_md(routing: dict[str, object]) -> str:
    weak = _model(routing, "weak_model", "choose-a-routine-model")
    strong = _model(routing, "strong_model", "choose-a-heavy-lift-model")
    return f"""# OpenClaude Adapter

OpenClaude support is intentionally lightweight because the project moves quickly. Use this as a
profile checklist rather than a locked config format.

## Install

```bash
npm install -g @gitlawb/openclaude
openclaude
```

## Suggested Profiles

- Routine/editing model: `{weak}`
- Heavy-lift/review model: `{strong}`
- Local endpoint: use Ollama or another OpenAI-compatible endpoint when available.

Inside OpenClaude, run `/provider` and configure the provider profile to match these values. Keep
real API keys in `.coding-scaffold/.env.local` or the tool's secure login flow, not in committed
files.
"""


def _hermes_md(routing: dict[str, object]) -> str:
    weak = _model(routing, "weak_model", "choose-a-routine-model")
    strong = _model(routing, "strong_model", "choose-a-heavy-lift-model")
    return f"""# Hermes Adapter

Hermes is a broader autonomous agent harness with terminal backends, skills, memory, MCP, and
messaging integrations. Use it as a project-aware coding harness only after its tool permissions,
runtime backend, and model profile are configured deliberately.

## Install

```bash
curl -fsSL https://raw.githubusercontent.com/NousResearch/hermes-agent/main/scripts/install.sh | bash
hermes setup
hermes
```

If your environment prefers Python isolation, use `pipx install hermes-agent`.

## Suggested Profiles

- Routine/editing model: `{weak}`
- Heavy-lift/review model: `{strong}`
- Local endpoint: use Ollama, vLLM, llama.cpp, or another OpenAI-compatible endpoint when available.

Run `hermes model`, `hermes tools`, and `hermes env` before the first project session. Keep project
guidance in `AGENTS.md` and `.coding-scaffold/AGENTS.md`, and keep real API keys in
`.coding-scaffold/.env.local` or Hermes' own credential flow, not in committed files.

## First Project Prompt

```text
Inspect this repository without editing. Identify the language, run command, test command, main
code paths, and one small safe improvement. Then wait for confirmation before changing files.
```
"""


def _pi_md(routing: dict[str, object]) -> str:
    weak = _model(routing, "weak_model", "choose-a-routine-model")
    strong = _model(routing, "strong_model", "choose-a-heavy-lift-model")
    return f"""# Pi Adapter

Pi is a minimal terminal coding harness. It loads `AGENTS.md`/`CLAUDE.md` project instructions,
supports slash commands and sessions, and can be extended with TypeScript extensions, skills,
prompt templates, themes, and Pi packages.

## Install

```bash
npm install -g @earendil-works/pi-coding-agent
pi
```

## Suggested Profiles

- Routine/editing model: `{weak}`
- Heavy-lift/review model: `{strong}`
- Local endpoint: use an OpenAI-compatible local endpoint when available.

Authenticate with `/login` for subscription providers or API-key providers, or set environment
variables from `.coding-scaffold/.env.local` before launching `pi`. Restart Pi or run `/reload`
after changing project instruction files.

## First Project Prompt

```text
Summarize this repository, tell me how to run its checks, and recommend one small safe change. Do
not edit files yet.
```
"""


def _routellm_yaml(routing: dict[str, object]) -> str:
    strong = _model(routing, "strong_model", "replace-me-strong-model")
    weak = _model(routing, "weak_model", "replace-me-weak-model")
    return "\n".join(
        [
            "routers:",
            "  - mf",
            f"strong_model: {strong}",
            f"weak_model: {weak}",
            f"threshold: {ROUTELLM_MF_DEFAULT_THRESHOLD}",
            "",
        ]
    )


def _routellm_md(routing: dict[str, object]) -> str:
    strong = _model(routing, "strong_model", "replace-me-strong-model")
    weak = _model(routing, "weak_model", "replace-me-weak-model")
    return f"""# RouteLLM

RouteLLM is optional. Use it when you want an OpenAI-compatible local routing server that decides
between a weak/routine model and a strong/heavy-lift model.

## When It Helps

- You have a cheap or local routine model and a stronger model.
- You want tools to call one endpoint while routing happens behind the scenes.
- You want to experiment with cost/quality thresholds.

## Install

```bash
python -m pip install "routellm[serve,eval]"
```

## Important Caveat

The commonly recommended `mf` router currently requires `OPENAI_API_KEY` for embeddings, even when
one of the routed models is local. Keep that key local in `.coding-scaffold/.env.local`.

## Start A Router Server

```bash
python -m routellm.openai_server \\
  --routers mf \\
  --strong-model {strong} \\
  --weak-model {weak}
```

RouteLLM's OpenAI-compatible server defaults to port `6060`. Point OpenCode, OpenClaude, or another
OpenAI-compatible client at that endpoint, then use a model value such as
`router-mf-{ROUTELLM_MF_DEFAULT_THRESHOLD}`.
"""


def _open_multi_agent_team(routing: dict[str, object]) -> dict[str, object]:
    routine = _model(routing, "weak_model", "choose-routine-model")
    heavy = _model(routing, "strong_model", "choose-heavy-lift-model")
    return {
        "backend": "open-multi-agent",
        "intent": "Turn validated local agentic workflows into repeatable TypeScript automation.",
        "install": "npm install @jackchen_me/open-multi-agent",
        "agents": [
            {
                "name": "explorer",
                "model": routine,
                "tools": ["file_read", "grep", "glob"],
                "responsibility": "Map relevant files, commands, dependencies, and risks.",
            },
            {
                "name": "planner",
                "model": heavy,
                "tools": ["file_read", "grep"],
                "responsibility": "Break the goal into a small task DAG with explicit verification.",
            },
            {
                "name": "implementer",
                "model": routine,
                "tools": ["bash", "file_read", "file_write", "file_edit", "grep"],
                "responsibility": "Make bounded edits and run narrow checks.",
            },
            {
                "name": "reviewer",
                "model": heavy,
                "tools": ["file_read", "grep"],
                "responsibility": "Review for regressions, missing tests, security, and maintainability.",
            },
        ],
        "recommended_flow": [
            "Validate the workflow interactively in OpenCode first.",
            "Create or update a project skill.",
            "Generate this backend when the workflow is worth repeating.",
            "Run planOnly before letting agents execute.",
            "Review traces and outputs before adopting in CI or backend automation.",
        ],
    }


def _open_multi_agent_md(routing: dict[str, object]) -> str:
    routine = _model(routing, "weak_model", "choose-routine-model")
    heavy = _model(routing, "strong_model", "choose-heavy-lift-model")
    return f"""# Open Multi-Agent

Open Multi-Agent is an optional advanced workflow backend. Use it after your team has validated an
agentic workflow interactively and wants to run it repeatedly from a TypeScript backend, script, or
CI-like automation.

## Why It Fits

- Open source and TypeScript-native.
- Goal-to-task-DAG orchestration with independent tasks running in parallel.
- Multiple model providers, including OpenAI-compatible local endpoints.
- MCP support, token budgets, retries, context strategies, and tracing hooks.
- `planOnly` mode lets you inspect the task DAG before execution.

## When To Use

Use OpenCode for the first human-in-the-loop coding sessions. Use Open Multi-Agent when the team
wants to automate a proven workflow: dependency review, API contract checks, release review,
security triage, migration planning, or other repeatable engineering processes.

## Install

```bash
npm install @jackchen_me/open-multi-agent
```

## Generated Files

- `.coding-scaffold/open-multi-agent.team.json`: team roles and model routes.
- `examples/open-multi-agent/team-coding-workflow.ts`: starter TypeScript workflow.

## Suggested Model Routes

- Routine model: `{routine}`
- Heavy-lift model: `{heavy}`

## Safe Adoption Path

1. Run `/first-session` and `/agentic-change` in OpenCode.
2. Capture the useful workflow as a skill.
3. Generate this backend with `coding-scaffold workflow --target . --backend open-multi-agent`.
4. Run the generated TypeScript example in plan-only mode first.
5. Add execution only after a maintainer reviews the task DAG and permissions.

This is the point where agentic coding becomes internal tooling: not one-off prompts, but repeatable,
observable workflows your peers can run and improve.
"""


def _open_multi_agent_example() -> str:
    return """import { OpenMultiAgent } from '@jackchen_me/open-multi-agent'
import type { AgentConfig } from '@jackchen_me/open-multi-agent'

const explorer: AgentConfig = {
  name: 'explorer',
  model: process.env.ROUTINE_MODEL ?? 'replace-me-routine-model',
  systemPrompt: 'Map relevant files, commands, dependencies, and risks. Do not edit.',
  tools: ['file_read', 'grep', 'glob'],
}

const planner: AgentConfig = {
  name: 'planner',
  model: process.env.HEAVY_LIFT_MODEL ?? 'replace-me-heavy-lift-model',
  systemPrompt: 'Break the goal into a small task DAG with explicit verification.',
  tools: ['file_read', 'grep'],
}

const implementer: AgentConfig = {
  name: 'implementer',
  model: process.env.ROUTINE_MODEL ?? 'replace-me-routine-model',
  systemPrompt: 'Make bounded edits only after scope is clear. Run narrow checks.',
  tools: ['bash', 'file_read', 'file_write', 'file_edit', 'grep'],
}

const reviewer: AgentConfig = {
  name: 'reviewer',
  model: process.env.HEAVY_LIFT_MODEL ?? 'replace-me-heavy-lift-model',
  systemPrompt: 'Review for regressions, missing tests, security, and maintainability. Do not edit.',
  tools: ['file_read', 'grep'],
}

const goal =
  process.argv.slice(2).join(' ') ||
  'Inspect this repository and propose one safe, small improvement with verification.'

const orchestrator = new OpenMultiAgent({
  defaultModel: process.env.HEAVY_LIFT_MODEL ?? 'replace-me-heavy-lift-model',
  onProgress: (event) => console.log(event.type, event.agent ?? event.task ?? ''),
})

const team = orchestrator.createTeam('coding-scaffold-team', {
  name: 'coding-scaffold-team',
  agents: [explorer, planner, implementer, reviewer],
  sharedMemory: true,
})

const planOnly = process.env.PLAN_ONLY !== '0'
const result = await orchestrator.runTeam(team, goal, { planOnly })

console.log(JSON.stringify({
  success: result.success,
  planOnly,
  totalTokenUsage: result.totalTokenUsage,
  tasks: result.tasks,
}, null, 2))
"""
