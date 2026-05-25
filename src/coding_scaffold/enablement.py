from __future__ import annotations

import re
from pathlib import Path

from .adapters import write_tool_adapter
from .file_ops import write_json, write_text


def write_skill_template(
    target: Path,
    name: str,
    description: str = "",
    adapter: str | None = None,
) -> Path:
    scaffold = _scaffold_dir(target)
    skills_dir = scaffold / "skills"
    skills_dir.mkdir(parents=True, exist_ok=True)
    slug = _slugify(name)
    path = skills_dir / f"{slug}.md"
    if path.exists():
        return path
    write_text(path, _skill_template(name, description), overwrite=False)
    if adapter == "opencode":
        _write_opencode_command(target, slug, name, description)
    return path


def write_orchestration_plan(target: Path, profile: str, adapter: str | None = None) -> Path:
    scaffold = _scaffold_dir(target)
    scaffold.mkdir(parents=True, exist_ok=True)
    plan = _orchestration_profile(profile)
    path = scaffold / "orchestration.json"
    write_json(path, plan)
    if adapter == "opencode":
        write_tool_adapter(target, "opencode")
    return path


def _scaffold_dir(target: Path) -> Path:
    return target.expanduser().resolve() / ".coding-scaffold"


def _slugify(value: str) -> str:
    slug = re.sub(r"[^a-zA-Z0-9]+", "-", value.strip().lower()).strip("-")
    return slug or "project-skill"


def _skill_template(name: str, description: str) -> str:
    summary = description or "Describe the repeatable workflow this skill should teach the agent."
    return f"""# {name}

## When To Use

{summary}

## Context To Load

- README and architecture notes
- relevant source files
- tests or reproduction commands
- generated `.coding-scaffold/` routing and provider notes when model choice matters

## Workflow

1. Inspect context before editing.
2. State the intended change in one short paragraph.
3. Make the smallest useful change.
4. Run the narrowest meaningful verification.
5. Summarize changed files, checks, and residual risk.

## Verification

```bash
# Replace with the smallest command that proves this skill worked.
```

## Guardrails

- Do not touch unrelated files.
- Do not rewrite generated files unless the task is about scaffold output.
- Ask for a stronger model when the task spans architecture, security, or repeated failures.
"""


def _write_opencode_command(target: Path, slug: str, name: str, description: str) -> Path:
    root = target.expanduser().resolve()
    commands = root / ".opencode" / "commands"
    commands.mkdir(parents=True, exist_ok=True)
    path = commands / f"{slug}.md"
    if not path.exists():
        summary = description or f"Run the {name} project skill."
        write_text(
            path,
            f"""Use the project skill `.coding-scaffold/skills/{slug}.md`.

Goal: {summary}

Load the skill, inspect the required context, follow its workflow, and report changed files,
verification, and residual risk.
""",
            overwrite=False,
        )
    return path


def _orchestration_profile(profile: str) -> dict[str, object]:
    profiles = {
        "solo": {
            "profile": "solo",
            "description": "One agent handles the task end to end with explicit checkpoints.",
            "agents": [
                {
                    "name": "Builder",
                    "model_route": "routine",
                    "responsibility": "Inspect, implement, verify, and summarize.",
                }
            ],
            "handoff_rules": [
                "Start with context loading.",
                "Pause before broad refactors or destructive operations.",
                "Escalate to the heavy-lift model after two weak-model failures.",
            ],
        },
        "pair": {
            "profile": "pair",
            "description": "Split implementation and review so one agent challenges the other.",
            "agents": [
                {
                    "name": "Builder",
                    "model_route": "routine",
                    "responsibility": "Make the smallest coherent change and run narrow checks.",
                },
                {
                    "name": "Reviewer",
                    "model_route": "heavy-lift",
                    "responsibility": "Review risks, missing tests, and behavioral regressions.",
                },
            ],
            "handoff_rules": [
                "Builder lists changed files and verification output.",
                "Reviewer leads with findings before summary.",
                "Builder fixes only accepted findings.",
            ],
        },
        "team": {
            "profile": "team",
            "description": "Use multiple specialized agents for larger work with disjoint scopes.",
            "agents": [
                {
                    "name": "Explorer",
                    "model_route": "routine",
                    "responsibility": "Map code paths, dependencies, and test entry points.",
                },
                {
                    "name": "Planner",
                    "model_route": "heavy-lift",
                    "responsibility": "Turn findings into a small implementation plan.",
                },
                {
                    "name": "Implementer",
                    "model_route": "routine",
                    "responsibility": "Own a clearly bounded file or module set.",
                },
                {
                    "name": "Verifier",
                    "model_route": "routine",
                    "responsibility": "Run checks and inspect failures without changing scope.",
                },
            ],
            "handoff_rules": [
                "Give every agent an explicit write scope.",
                "Do not let two agents edit the same file unless one is reviewing only.",
                "Merge results through one accountable maintainer.",
            ],
        },
    }
    return profiles.get(profile, profiles["solo"])
