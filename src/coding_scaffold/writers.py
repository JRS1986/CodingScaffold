from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

from .hardware import HardwareProfile
from .intake import IntakeAnswers
from .model_catalog import ROUTELLM_MF_DEFAULT_THRESHOLD
from .providers import Provider
from .router import RoutingPlan


@dataclass(frozen=True)
class ScaffoldManifest:
    scaffold_dir: Path
    files: list[Path]


def write_scaffold(
    target: Path,
    intake: IntakeAnswers,
    hardware: HardwareProfile,
    providers: list[Provider],
    routing: RoutingPlan,
) -> ScaffoldManifest:
    target.mkdir(parents=True, exist_ok=True)
    scaffold_dir = target / ".coding-scaffold"
    scaffold_dir.mkdir(exist_ok=True)

    files = [
        _write_json(scaffold_dir / "project.json", intake.to_dict()),
        _write_json(scaffold_dir / "hardware.json", hardware.to_dict()),
        _write_json(scaffold_dir / "providers.json", [provider.to_dict() for provider in providers]),
        _write_json(scaffold_dir / "routing.json", routing.to_dict()),
        _write_json(scaffold_dir / "model-selection.json", _model_selection_json(routing)),
        _write_json(scaffold_dir / "opencode.json", _opencode_config(routing)),
        _write_json(scaffold_dir / "openclaude.json", _openclaude_config(routing)),
        _write_text(scaffold_dir / "routellm.config.yaml", _routellm_yaml(routing)),
        _write_text(scaffold_dir / ".gitignore", _scaffold_gitignore()),
        _write_text(scaffold_dir / ".env.example", _env_example()),
        _write_json(scaffold_dir / "credentials.example.json", _credentials_example()),
        _write_text(scaffold_dir / "CREDENTIALS.md", _credentials_md()),
        _write_text(scaffold_dir / "MODEL_SELECTION.md", _model_selection_md()),
        _write_text(scaffold_dir / "TOOLS.md", _tools_md()),
        _write_text(scaffold_dir / "ORCHESTRATION.md", _orchestration_md()),
        _write_json(scaffold_dir / "orchestration.json", _orchestration_json()),
        _write_text(scaffold_dir / "skills" / "README.md", _skills_readme()),
        _write_text(scaffold_dir / "FIRST_SESSION.md", _first_session_md()),
        _write_text(scaffold_dir / "GETTING_STARTED.md", _getting_started_md(intake, routing)),
        _write_text(scaffold_dir / "SKILLS.md", _skills_md()),
        _write_text(scaffold_dir / "AGENTS.md", _agents_md(intake, routing)),
    ]
    if intake.mode == "beginner":
        files.append(_write_text(scaffold_dir / "BEGINNER_PATH.md", _beginner_path_md(intake, routing)))
    return ScaffoldManifest(scaffold_dir=scaffold_dir, files=files)


def _write_json(path: Path, payload: object) -> Path:
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return path


def _write_text(path: Path, payload: str) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(payload, encoding="utf-8")
    return path


def _opencode_config(routing: RoutingPlan) -> dict[str, object]:
    return {
        "providerHints": {
            "local": {
                "endpoint": routing.local_endpoint,
                "model": routing.weak_model,
            },
            "strong": {
                "provider": routing.cloud_provider or "local",
                "model": routing.strong_model,
            },
        },
        "nativeAdapter": {
            "command": "coding-scaffold adapt --target . --tool opencode",
            "writes": ["opencode.json", ".opencode/agents/*.md", ".opencode/commands/*.md"],
        },
        "routing": routing.to_dict(),
    }


def _openclaude_config(routing: RoutingPlan) -> dict[str, object]:
    return {
        "profiles": [
            {
                "name": "local",
                "base_url": routing.local_endpoint,
                "model": routing.weak_model,
            },
            {
                "name": "strong",
                "provider": routing.cloud_provider or "local",
                "model": routing.strong_model,
            },
        ],
        "default_profile": "local",
    }


def _routellm_yaml(routing: RoutingPlan) -> str:
    strong = routing.strong_model or routing.weak_model or "replace-me-strong-model"
    weak = routing.weak_model or strong
    return "\n".join(
        [
            "routers:",
            "  - mf",
            f"strong_model: {strong}",
            f"weak_model: {weak}",
            f"threshold: {ROUTELLM_MF_DEFAULT_THRESHOLD}",
            "providers:",
            "  local:",
            f"    base_url: {routing.local_endpoint or 'http://127.0.0.1:11434/v1'}",
            "",
        ]
    )


def _model_selection_json(routing: RoutingPlan) -> dict[str, object]:
    return {
        "default_mode": "recommend",
        "auto_mode": {
            "command": "coding-scaffold select-model --target . --mode auto --prompt '...'",
            "meaning": "select a route without asking each time; still prints the decision",
        },
        "routes": {
            "routine": {
                "model": routing.weak_model,
                "provider": "local-first",
                "use_for": ["small edits", "tests", "docs", "explanations", "formatting"],
            },
            "heavy-lift": {
                "model": routing.strong_model,
                "provider": routing.cloud_provider or "local",
                "model_family": routing.cloud_model_family or "local",
                "use_for": ["architecture", "security", "migrations", "reviews", "multi-file work"],
            },
        },
        "provider_abstraction": {
            "provider": "where the request is sent, for example Azure AI or OpenAI",
            "model_family": "what kind of model is behind it, for example OpenAI or Anthropic",
            "deployment": "provider-specific deployment name, kept outside prompts and skills",
        },
    }


def _scaffold_gitignore() -> str:
    return """.env.local
credentials.local.json
*.secret.*
"""


def _env_example() -> str:
    return """# Copy to .coding-scaffold/.env.local and fill only what you use.
# Never commit .env.local.

OPENAI_API_KEY=
ANTHROPIC_API_KEY=
AZURE_OPENAI_API_KEY=
AZURE_OPENAI_ENDPOINT=
AZURE_OPENAI_DEPLOYMENT=
AZURE_AI_API_KEY=
AZURE_AI_ENDPOINT=
AZURE_AI_MODEL=
AZURE_AI_MODEL_FAMILY=
AZURE_AI_SERVICES_KEY=
AZURE_AI_SERVICES_ENDPOINT=
AZURE_COGNITIVE_SERVICES_KEY=
AZURE_COGNITIVE_SERVICES_ENDPOINT=
OPENROUTER_API_KEY=
GROQ_API_KEY=
GEMINI_API_KEY=
GOOGLE_API_KEY=
GITHUB_TOKEN=
GH_TOKEN=
"""


def _credentials_example() -> dict[str, str]:
    return {
        "OPENAI_API_KEY": "",
        "ANTHROPIC_API_KEY": "",
        "AZURE_OPENAI_API_KEY": "",
        "AZURE_OPENAI_ENDPOINT": "",
        "AZURE_OPENAI_DEPLOYMENT": "",
        "AZURE_AI_API_KEY": "",
        "AZURE_AI_ENDPOINT": "",
        "AZURE_AI_MODEL": "",
        "AZURE_AI_MODEL_FAMILY": "",
        "AZURE_AI_SERVICES_KEY": "",
        "AZURE_AI_SERVICES_ENDPOINT": "",
        "AZURE_COGNITIVE_SERVICES_KEY": "",
        "AZURE_COGNITIVE_SERVICES_ENDPOINT": "",
        "OPENROUTER_API_KEY": "",
        "GROQ_API_KEY": "",
        "GEMINI_API_KEY": "",
        "GOOGLE_API_KEY": "",
        "GITHUB_TOKEN": "",
        "GH_TOKEN": "",
    }


def _credentials_md() -> str:
    return """# Local Credentials

Credentials are intentionally local. The scaffold writes examples and an ignore file, but it never
asks you to paste real keys into committed project files.

## Recommended Path

Create a local env file:

```bash
coding-scaffold credentials --target . --format env
```

Then fill `.coding-scaffold/.env.local` with only the providers you intend to use.

For JSON-based tooling:

```bash
coding-scaffold credentials --target . --format json
```

This creates `.coding-scaffold/credentials.local.json`.

## Supported Keys

- `OPENAI_API_KEY`
- `ANTHROPIC_API_KEY`
- `AZURE_OPENAI_API_KEY`, `AZURE_OPENAI_ENDPOINT`, and optional `AZURE_OPENAI_DEPLOYMENT`
- `AZURE_AI_API_KEY`, `AZURE_AI_ENDPOINT`, optional `AZURE_AI_MODEL`, and optional
  `AZURE_AI_MODEL_FAMILY`
- Azure AI Services or Cognitive Services aliases: `AZURE_AI_SERVICES_KEY`,
  `AZURE_AI_SERVICES_ENDPOINT`, `AZURE_COGNITIVE_SERVICES_KEY`, and
  `AZURE_COGNITIVE_SERVICES_ENDPOINT`
- `OPENROUTER_API_KEY`
- `GROQ_API_KEY`
- `GEMINI_API_KEY` or `GOOGLE_API_KEY`
- `GITHUB_TOKEN` or `GH_TOKEN`

## Safety Rules

- Do not commit `.env.local` or `credentials.local.json`.
- Prefer project-local credentials over shell-global exports when comparing providers.
- Use `coding-scaffold probe --target .` to verify which providers appear configured.
- If a provider offers device login, prefer that over long-lived plaintext keys.

## Azure Model Families

Azure is treated as a provider endpoint, not a model family. If your Azure gateway serves OpenAI
models, set `AZURE_OPENAI_*` or set `AZURE_AI_MODEL_FAMILY=openai`. If it serves Anthropic models,
set `AZURE_AI_MODEL_FAMILY=anthropic`. Skills and agents can then ask for `routine` or
`heavy-lift` without caring whether the request travels through Azure, OpenAI directly, Anthropic
directly, or a local OpenAI-compatible endpoint.
"""


def _model_selection_md() -> str:
    return """# Model Selection

Model selection is the small decision before the big token spend: should this prompt use the
routine route or the heavy-lift route?

Run a recommendation:

```bash
coding-scaffold select-model --target . --prompt "Review this migration for rollback risks."
```

Use auto mode when you do not want to choose each time:

```bash
coding-scaffold select-model --target . --mode auto --prompt "Fix this failing formatter test."
```

The command does not call a model. It reads the task text, classifies the risk, and returns the
recommended route, provider, model family, model or deployment, confidence, and reasons.

## Provider Abstraction

Keep these concepts separate:

- provider: where the request goes, such as local Ollama, OpenAI, Anthropic, Azure OpenAI, or Azure AI
- model family: what kind of model answers, such as OpenAI, Anthropic, Google, or local
- deployment: provider-specific name, especially common in Azure

This matters because an Azure endpoint can serve OpenAI-family or Anthropic-family models depending
on how the organization configured it. Skills should ask for a capability like `routine` or
`heavy-lift`, not hard-code one vendor's model name.

## Prompt Profiles

- routine-coding: short edits, tests, docs, explanations, formatting, and small fixes
- complex-change: architecture, security, migrations, reviews, orchestration, incidents, or long prompts
- standard-change: normal work with no obvious heavy-lift signal

If the recommendation feels wrong, treat that as a manual override: inspect context and pick the
safer route.
"""


def _tools_md() -> str:
    return """# Coding Tool Adapters

CodingScaffold stays tool-neutral. It writes hints for current tools, but the project should remain
easy to adapt when new coding agents appear.

## OpenCode

Best default when you want the most mature open workflow today. OpenCode has an official installer,
terminal/desktop/IDE surfaces, broad provider support through models.dev, local model support, LSP
awareness, multi-session workflows, and GitHub Copilot sign-in. It is a good first adapter for teams
that want stability and a visible ecosystem.

Install:

```bash
coding-scaffold setup-tool --tool opencode
```

Use `coding-scaffold setup-tool --tool opencode --install` when you intentionally want the CLI to
install a missing tool without a second prompt, for example in a prepared dev container.

Generate OpenCode-native config:

```bash
coding-scaffold adapt --target . --tool opencode
```

This writes `opencode.json`, `.opencode/agents/`, and `.opencode/commands/`. Then run:

```bash
opencode
```

Recommended first prompt inside OpenCode:

```text
/first-session
```

## OpenClaude

Useful when you want to explore a fast-moving Claude-Code-like workflow with multiple providers,
OpenAI-compatible APIs, Ollama, GitHub Models, slash commands, MCP, and provider profiles. Treat it
as experimental: it is an unofficial community project, so evaluate licensing, provenance, security,
and team comfort before standardizing on it.

Install:

```bash
coding-scaffold setup-tool --tool openclaude
```

Use this scaffold with OpenClaude:

```bash
openclaude
```

Inside OpenClaude, run `/provider` and use `.coding-scaffold/openclaude.json` as the project hint.

## RouteLLM

RouteLLM is optional advanced routing, not the default onboarding path. Use it when you want an
OpenAI-compatible local router endpoint between a weak/routine model and a strong/heavy-lift model.

```bash
coding-scaffold setup-addon --target . --addon routellm
coding-scaffold route --target . --backend routellm
```

Read `.coding-scaffold/ROUTELLM.md` before starting the server; some routers require an
`OPENAI_API_KEY` for embeddings even when one routed model is local.

## Open Multi-Agent

Open Multi-Agent is optional advanced workflow automation, not the first onboarding step. Use it
when a skill has proven useful in OpenCode and should become a repeatable TypeScript workflow,
backend job, or CI-like check.

```bash
coding-scaffold setup-addon --target . --addon open-multi-agent
coding-scaffold workflow --target . --backend open-multi-agent
```

This writes `.coding-scaffold/OPEN_MULTI_AGENT.md`,
`.coding-scaffold/open-multi-agent.team.json`, and
`examples/open-multi-agent/team-coding-workflow.ts`. Start in plan-only mode and review the task
DAG, permissions, traces, and verification signals before allowing execution.

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
"""


def _orchestration_json() -> dict[str, object]:
    return {
        "default_profile": "pair",
        "profiles": {
            "solo": "One agent, explicit checkpoints.",
            "pair": "Builder plus reviewer.",
            "team": "Explorer, planner, implementer, verifier with disjoint scopes.",
        },
        "routing": {
            "routine": "Use the selected local/routine model.",
            "heavy-lift": "Use the stronger routed model for architecture, security, and review.",
        },
    }


def _orchestration_md() -> str:
    return """# Agent Orchestration

Agent orchestration is the difference between "ask a model" and "run a controlled coding workflow".
In this scaffold it is not a separate runtime. It generates native OpenCode agents and commands
where possible, and keeps generic JSON/Markdown notes for other tools.

## Profiles

### Solo

Use for small tasks. One agent inspects, edits, verifies, and summarizes. Keep checkpoints explicit.

```bash
coding-scaffold orchestrate --target . --profile solo
```

### Pair

Use for normal feature work. A builder makes the change; a reviewer looks for regressions, missing
tests, and unclear behavior. This is the default because it catches more without adding much process.

```bash
coding-scaffold orchestrate --target . --profile pair
```

### Team

Use for larger changes. Split into explorer, planner, implementer, and verifier roles. Give each
agent a clear scope and avoid overlapping file ownership.

```bash
coding-scaffold orchestrate --target . --profile team
```

Add `--adapter none` if you only want the generic `.coding-scaffold/orchestration.json` file.

## Good Handoffs

- State the task and non-goals.
- Assign file or module ownership.
- Name the model route: routine or heavy-lift.
- Include the exact verification command.
- Summarize changed files and residual risk.

## First Useful Loop

Inside OpenCode:

```text
/first-session
/agentic-change
```

The first command builds context without editing. The second runs a small explorer -> implementer ->
reviewer loop so the user sees the difference between a coding assistant and an agentic workflow.

## Repeatable Workflow Backend

When an interactive workflow has proven itself, generate an optional Open Multi-Agent backend:

```bash
coding-scaffold workflow --target . --backend open-multi-agent
```

Use this for repeatable automation, not discovery. Keep discovery and skill validation in OpenCode;
move to Open Multi-Agent only when the team wants a reviewed, observable TypeScript workflow.

## When To Escalate

Use the heavy-lift route for architecture, migrations, security-sensitive code, production incident
debugging, or when the routine route fails twice.
"""


def _skills_readme() -> str:
    return """# Project Skills

Project skills are reusable instructions for work your team repeats often: release reviews,
database migrations, frontend QA, API contract changes, incident analysis, or dependency upgrades.
They are how a team turns one person's good prompt into shared engineering acceleration.

Create one with an OpenCode command bridge:

```bash
coding-scaffold skill --target . --adapter opencode --name "Release Review" --description "Review a release candidate before tagging."
```

This writes `.coding-scaffold/skills/release-review.md` and `.opencode/commands/release-review.md`.
Keep skills short and procedural. Review them like code: run them on real work, check the output,
and update the skill when it misses context or suggests unsafe steps.
"""


def _agents_md(intake: IntakeAnswers, routing: RoutingPlan) -> str:
    return f"""# Coding Agent Notes

Tone: efficient engineering toolset with clear, practical onboarding

Project language: {intake.language}
Project target: {intake.project_target}
Existing codebase: {intake.existing_codebase}
Privacy mode: {intake.privacy}
Guidance mode: {intake.mode}

## Operating Contract

- Inspect the project before editing.
- Keep changes small, tested, and reversible.
- Do not collect or write API keys into this repository.
- Prefer local inference unless the task explicitly needs cloud quality and credentials are available.
- Keep generated guidance direct, neutral, and project-focused.

## Model Routing

- Routine model: `{routing.weak_model}`
- Heavy-lift model: `{routing.strong_model}`
- Route threshold: `{routing.route_threshold}`
- Cloud provider: `{routing.cloud_provider or "none"}`
- Cloud model family: `{routing.cloud_model_family or "none"}`

## Skill Habits

- Context first: read the tree, README, tests, and config before asking an LLM for edits.
- Prompt small: ask for one inspectable change or one bounded plan.
- Verify locally: run the narrowest meaningful test before broad checks.
- Review like a maintainer: ask what could break, what is untested, and what changed.
- Route deliberately: local for routine work, stronger model for architecture or repeated failure.

## Orchestration Habits

- Solo for narrow changes.
- Pair for normal implementation plus review.
- Team for broad work with disjoint file ownership.
- Never let multiple agents edit the same file without an explicit maintainer merge step.

## Communication Habits

- Routing recheck: pause and reassess when an answer feels off.
- Change checkpoint: pause before migrations, dependency upgrades, or broad refactors.
- Explicit handoff: state assumptions, commands, expected signals, and next steps.
- Small change, fast test, clear rollback.
"""


def _getting_started_md(intake: IntakeAnswers, routing: RoutingPlan) -> str:
    selected_tool = intake.agent or "opencode"
    setup_hint = (
        "Validate or install the selected coding environment with "
        f"`coding-scaffold setup-tool --tool {selected_tool}`."
        if selected_tool != "manual"
        else "Use your manually selected coding environment and keep its config next to this scaffold."
    )
    return f"""# Getting Started

This scaffold is meant to be cloned, installed into a local venv, and run as a setup wizard inside
the project you want to prepare for AI-assisted coding.

The goal is not just "better autocomplete." The goal is a controlled workflow where agents inspect,
plan, edit, verify, review, and preserve the best team habits as reusable skills.

## Fast Path

```bash
git clone <this-repo> coding-scaffold
cd coding-scaffold
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -e ".[dev]"
coding-scaffold wizard --target /path/to/your/project
```

On WSL/Linux the flow is the same. On Windows PowerShell outside WSL, activate with
`.venv\\Scripts\\Activate.ps1`.

## What The Wizard Did Here

Project language: `{intake.language}`
Project target: `{intake.project_target}`
Privacy mode: `{intake.privacy}`
Coding environment: `{intake.agent}`
Guidance mode: `{intake.mode}`
Routine model: `{routing.weak_model}`
Heavy-lift model: `{routing.strong_model}`

## Daily Use

1. {setup_hint}
2. Start OpenCode with `opencode`, OpenClaude with `openclaude`, or your manually selected tool.
3. Run `/first-session` to inspect without editing.
4. Run `/agentic-change` for one small explorer -> implementer -> reviewer loop.
5. Read the verification output and review findings yourself.
6. Recheck the route when an answer feels wrong: restate the task, add context, or use the stronger model.
7. Ask `coding-scaffold select-model --target . --prompt "..."` when the right model route is unclear.
8. Configure local provider keys with `CREDENTIALS.md`.
9. Use `coding-scaffold setup-addon --target . --addon llmfit` for deeper hardware-aware model sizing.
10. Create repeatable project skills with `coding-scaffold skill --target . --adapter opencode --name "..."`.
11. Create shared team memory with `coding-scaffold knowledge --target .`.
12. Improve skills when they miss context, overreach, or fail to verify correctly.
13. Graduate proven skills into Open Multi-Agent workflows with `coding-scaffold setup-addon --target . --addon open-multi-agent` and `coding-scaffold workflow --target . --backend open-multi-agent`.
"""


def _first_session_md() -> str:
    return """# First Agentic Coding Session

This walkthrough is designed to make the difference from autocomplete obvious.

## 1. Start With Context, Not Edits

```bash
opencode
```

Inside OpenCode:

```text
/first-session
```

Expected result: the agent identifies the project shape, run command, test command, key files,
risks, and one safe improvement. It should not edit yet.

## 2. Run One Small Agentic Loop

```text
/agentic-change
```

Expected result:

- explorer maps the relevant files
- implementer makes a bounded change
- verification runs
- reviewer challenges the result
- you get changed files, checks, findings, and follow-up

## 3. Capture The Habit As A Skill

If the workflow helped, make it reusable:

```bash
coding-scaffold skill --target . --adapter opencode --name "Small Safe Improvement"
```

Skills are team leverage. They let peers reuse a good engineering habit without relying on memory or
a long prompt copied from chat history.
"""


def _skills_md() -> str:
    return """# AI Coding Skills

These are practical skills for using local and routed LLMs as an efficient coding toolset.

A skill is a reusable senior-engineer habit. It tells the agent what context to load, what workflow
to follow, how to verify, and what not to touch. Good skills make peers faster because they encode
the team's judgment, not just a prompt.

## Context Loading

Tell the agent what to read before it edits:

- README and architecture docs
- package files and test config
- the smallest relevant source files
- failing test output or reproduction steps

Prompt example:

```text
Inspect the README, pyproject, and tests before editing. Then explain the smallest safe change.
```

## Bounded Implementation

Ask for one slice at a time:

- one bug
- one file cluster
- one command path
- one failing test

## Verification

Use the agent to run checks, but keep the signal concrete:

```text
Run the narrowest relevant test first. If it passes, run the broader check.
```

## Review

Ask for code-review mode before merging:

```text
Review this change for regressions, missing tests, and confusing behavior. Findings first.
```

## Routing

Use local models for routine edits, explanations, and test fixes. Route to the stronger model for
architecture, migrations, security, multi-file refactors, or when the local answer fails twice.

## Writing A Project Skill

A useful skill is short and procedural:

- When to use it
- What files to inspect
- The step-by-step workflow
- How to verify
- What not to do

Create a template:

```bash
coding-scaffold skill --target . --name "Release Review" --description "Review a release candidate before tagging."
```

The template is written to `.coding-scaffold/skills/`.

## Useful Starter Skills

- Release Review: check changelog, tests, migration notes, and rollback.
- Dependency Upgrade: inspect breaking changes, update lockfiles, run compatibility checks.
- API Contract Change: update schema, tests, docs, and clients together.
- Frontend QA: verify responsive layout, accessibility labels, and visual regressions.
- Incident Review: reconstruct timeline, root cause, mitigation, and follow-up tasks.

## Validate Skills

- Run the skill on a small real change.
- Check whether it loaded the right files.
- Check whether verification was specific enough.
- Ask a teammate to review the output.
- Update the skill when it misses an important project convention.

## Graduate Proven Skills

When a skill consistently helps, turn it into repeatable automation:

```bash
coding-scaffold workflow --target . --backend open-multi-agent
```

Use the generated Open Multi-Agent example as a starting point for reviewed TypeScript workflows
that peers can run, inspect, and improve without tying the team to one vendor.
"""


def _beginner_path_md(intake: IntakeAnswers, routing: RoutingPlan) -> str:
    return f"""# Beginner Path: Your First AI-Enabled Coding Project

This guide helps you complete one careful AI-assisted coding session without handing the whole
project to an agent at once.

## 1. Inspect The Project

Goal: understand what you have before asking an AI to change it.

```bash
coding-scaffold probe
```

Then ask your coding agent:

```text
Inspect this project and tell me the language, test command, run command, and risky areas. Do not edit yet.
```

## 2. Check Model And Privacy Defaults

Goal: use local models for routine work when possible.

Routine model: `{routing.weak_model}`
Heavy-lift model: `{routing.strong_model}`
Privacy mode: `{intake.privacy}`

If an answer seems vague or overconfident, run a route recheck:

```text
Restate the task, list the exact files you inspected, and suggest the smallest next step.
```

## 3. Make One Small Change

Goal: complete a tiny, reviewable improvement.

Ask:

```text
Pick one small improvement in this project. Explain it first, then implement it, then run the narrowest test.
```

## 4. Pause Before Broad Changes

Goal: learn when to pause.

Pause before migrations, broad refactors, dependency upgrades, generated code rewrites, or anything
that changes public behavior. Make a checkpoint and ask for a plan before edits.

## 5. Keep The Habit

Goal: build a repeatable habit.

Small change. Fast test. Clear rollback. Short review.
"""
