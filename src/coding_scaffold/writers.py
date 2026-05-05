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
5. Check `SKILLS.md` when you want to teach the agent a repeatable workflow.
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
