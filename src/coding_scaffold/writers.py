from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

from .hardware import HardwareProfile
from .intake import IntakeAnswers
from .providers import Provider
from .router import RoutingPlan
from .theme import FESTO_TN_AI


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
    _remove_stale_frontend_preview(scaffold_dir)

    files = [
        _write_json(scaffold_dir / "project.json", intake.to_dict()),
        _write_json(scaffold_dir / "hardware.json", hardware.to_dict()),
        _write_json(scaffold_dir / "providers.json", [provider.to_dict() for provider in providers]),
        _write_json(scaffold_dir / "routing.json", routing.to_dict()),
        _write_json(scaffold_dir / "theme.json", FESTO_TN_AI.to_dict()),
        _write_json(scaffold_dir / "opencode.json", _opencode_config(routing)),
        _write_json(scaffold_dir / "openclaude.json", _openclaude_config(routing)),
        _write_text(scaffold_dir / "routellm.config.yaml", _routellm_yaml(routing)),
        _write_text(scaffold_dir / ".gitignore", _scaffold_gitignore()),
        _write_text(scaffold_dir / ".env.example", _env_example()),
        _write_json(scaffold_dir / "credentials.example.json", _credentials_example()),
        _write_text(scaffold_dir / "CREDENTIALS.md", _credentials_md()),
        _write_text(scaffold_dir / "TOOLS.md", _tools_md()),
        _write_text(scaffold_dir / "ORCHESTRATION.md", _orchestration_md()),
        _write_json(scaffold_dir / "orchestration.json", _orchestration_json()),
        _write_text(scaffold_dir / "skills" / "README.md", _skills_readme()),
        _write_text(scaffold_dir / "GETTING_STARTED.md", _getting_started_md(intake, routing)),
        _write_text(scaffold_dir / "SKILLS.md", _skills_md()),
        _write_text(scaffold_dir / "THEME.md", _theme_md()),
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


def _remove_stale_frontend_preview(scaffold_dir: Path) -> None:
    for name in ("index.html", "theme.css"):
        path = scaffold_dir / name
        if path.exists():
            path.unlink()


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
            "threshold: 0.11593",
            "providers:",
            "  local:",
            f"    base_url: {routing.local_endpoint or 'http://127.0.0.1:11434/v1'}",
            "",
        ]
    )


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
- `OPENROUTER_API_KEY`
- `GROQ_API_KEY`
- `GEMINI_API_KEY` or `GOOGLE_API_KEY`
- `GITHUB_TOKEN` or `GH_TOKEN`

## Safety Rules

- Do not commit `.env.local` or `credentials.local.json`.
- Prefer project-local credentials over shell-global exports when comparing providers.
- Use `coding-scaffold probe --target .` to verify which providers appear configured.
- If a provider offers device login, prefer that over long-lived plaintext keys.
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
curl -fsSL https://opencode.ai/install | bash
```

Alternatives include npm, Bun, pnpm, Yarn, Homebrew, and paru depending on your platform.

Use this scaffold with OpenCode:

```bash
opencode
```

Then point OpenCode at the provider/model hints in `.coding-scaffold/opencode.json` and the project
rules in `.coding-scaffold/AGENTS.md`.

## OpenClaude

Useful when you want to explore a fast-moving Claude-Code-like workflow with multiple providers,
OpenAI-compatible APIs, Ollama, GitHub Models, slash commands, MCP, and provider profiles. Treat it
as experimental: it is an unofficial community project, so evaluate licensing, provenance, security,
and team comfort before standardizing on it.

Install:

```bash
npm install -g @gitlawb/openclaude
```

Use this scaffold with OpenClaude:

```bash
openclaude
```

Inside OpenClaude, run `/provider` and use `.coding-scaffold/openclaude.json` as the project hint.

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
Use it when a task is too broad for one uninterrupted prompt or when review quality matters.

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

## Good Handoffs

- State the task and non-goals.
- Assign file or module ownership.
- Name the model route: routine or heavy-lift.
- Include the exact verification command.
- Summarize changed files and residual risk.

## When To Escalate

Use the heavy-lift route for architecture, migrations, security-sensitive code, production incident
debugging, or when the routine route fails twice.
"""


def _skills_readme() -> str:
    return """# Project Skills

Project skills are reusable instructions for work your team repeats often: release reviews,
database migrations, frontend QA, API contract changes, incident analysis, or dependency upgrades.

Create one with:

```bash
coding-scaffold skill --target . --name "Release Review" --description "Review a release candidate before tagging."
```

Keep skills short and procedural. A good skill tells the agent when to use it, which context to
load, the workflow to follow, how to verify, and what not to touch.
"""


def _agents_md(intake: IntakeAnswers, routing: RoutingPlan) -> str:
    return f"""# Coding Agent Notes

Tone: efficient engineering toolset with optional Festo Coding Challenge flavor

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
- Use Challenge-style copy only in beginner guidance or onboarding docs.

## Model Routing

- Routine model: `{routing.weak_model}`
- Heavy-lift model: `{routing.strong_model}`
- Route threshold: `{routing.route_threshold}`
- Cloud provider: `{routing.cloud_provider or "none"}`

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

## Pop-Culture Signal Words

- ROUTE-42: routing sanity check when an answer feels off.
- Great Scott: checkpoint before timeline-risk changes such as migrations or broad refactors.
- Protocol-droid clarity: handoffs must state assumptions, commands, and expected signals.
- This is the way: small change, fast test, clear rollback.
"""


def _getting_started_md(intake: IntakeAnswers, routing: RoutingPlan) -> str:
    return f"""# Getting Started

This scaffold is meant to be cloned, installed into a local venv, and run as a setup wizard inside
the project you want to prepare for AI-assisted coding.

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
Guidance mode: `{intake.mode}`
Routine model: `{routing.weak_model}`
Heavy-lift model: `{routing.strong_model}`

## Daily Use

1. Ask the agent to inspect before editing.
2. Keep prompts scoped to one change or one question.
3. Run tests through the agent, but read failures yourself.
4. Use ROUTE-42 when an answer feels wrong: restate the task, add context, or route to the stronger model.
5. Configure local provider keys with `CREDENTIALS.md`.
6. Install a coding adapter from `TOOLS.md`.
7. Create repeatable project skills with `coding-scaffold skill --target . --name "..."`.
8. Create an agent plan with `coding-scaffold orchestrate --target . --profile pair`.
"""


def _skills_md() -> str:
    return """# AI Coding Skills

These are practical skills for using local and routed LLMs as an efficient coding toolset.

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
"""


def _beginner_path_md(intake: IntakeAnswers, routing: RoutingPlan) -> str:
    return f"""# Beginner Path: Your First AI-Enabled Coding Project

You open the project and the terminal hums awake. A small companion, Pneumon, blinks at the edge of
the prompt. The archive is not asking you to solve everything at once. It is asking for the first
stable signal.

## Challenge 1: Wake The Project

Goal: understand what you have before asking an AI to change it.

```bash
coding-scaffold probe
```

Then ask your coding agent:

```text
Inspect this project and tell me the language, test command, run command, and risky areas. Do not edit yet.
```

## Challenge 2: Stabilize The Local Crystal

Goal: use local models for routine work when possible.

Routine model: `{routing.weak_model}`
Heavy-lift model: `{routing.strong_model}`
Privacy mode: `{intake.privacy}`

If The Glitch appears as a vague answer, use ROUTE-42:

```text
ROUTE-42: restate the task, list the exact files you inspected, and suggest the smallest next step.
```

## Challenge 3: Make One Small Change

Goal: complete a tiny, reviewable improvement.

Ask:

```text
Pick one small improvement in this project. Explain it first, then implement it, then run the narrowest test.
```

## Challenge 4: Great Scott Gate

Goal: learn when to pause.

Say "Great Scott" before migrations, broad refactors, dependency upgrades, generated code rewrites,
or anything that changes public behavior. Make a checkpoint and ask for a plan before edits.

## Challenge 5: This Is The Way

Goal: build a repeatable habit.

Small change. Fast test. Clear rollback. Short review.
"""


def _theme_md() -> str:
    theme = FESTO_TN_AI
    references = "\n".join(f"- {item}" for item in theme.reference_bits)
    return f"""# Voice And Onboarding Style

The scaffold is an efficient coding enablement tool first. The Festo Coding Challenge voice is
reserved for beginner onboarding, workshop material, and optional narrative guides.

## Voice

{theme.voice}

## How To Use The Style

- Use second person for beginner guidance.
- Keep experienced-user docs direct and operational.
- Turn practical tasks into short challenge beats only when that lowers anxiety or improves recall.
- Do not turn config files, routing plans, or provider docs into fiction.

## Signal References

{references}
"""
