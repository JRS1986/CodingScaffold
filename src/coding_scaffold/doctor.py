"""`coding-scaffold doctor` — accessibility hub.

Surveys the scaffold artifacts present in a target project, identifies what's missing for
common pilot workflows, and recommends the next 1-3 commands the user should run. Also says
which advanced features can be ignored for now.

All checks are read-only and deterministic. No commands are executed; the only side effect
is reading file existence and a few environment variables.
"""

from __future__ import annotations

import os
import sys
from dataclasses import dataclass
from pathlib import Path

from .artifacts import ARTIFACTS, rationale_for
from .hardware import probe_hardware
from .personas import DEFAULT_PERSONA, PERSONAS, get_persona
from .pr_template import PR_TEMPLATE_RELATIVE


@dataclass(frozen=True)
class DoctorReport:
    target: str
    artifacts: dict[str, bool]
    next_steps: list[str]
    ignore_for_now: list[str]
    notes: list[str]
    persona: str = DEFAULT_PERSONA

    def to_dict(self) -> dict[str, object]:
        return {
            "target": self.target,
            "persona": self.persona,
            "artifacts": dict(self.artifacts),
            "next_steps": list(self.next_steps),
            "ignore_for_now": list(self.ignore_for_now),
            "notes": list(self.notes),
        }


# Advanced surfaces a first-time user can safely ignore. Doctor explicitly says so to
# keep the early mental model small.
ADVANCED_FOR_NOW: tuple[str, ...] = (
    "policy",
    "mcp",
    "skills",
    "memory",
    "team",
    "permissions write",
    "tools route",
    "tools workflow",
    "tools orchestrate",
)


def run_doctor(
    target: Path | None = None,
    *,
    persona: str = DEFAULT_PERSONA,
) -> DoctorReport:
    """Build a structured DoctorReport for the given target (default cwd).

    When ``persona`` is set, the recommendation list and the ignore-for-now list
    come from the persona registry instead of the beginner default. The artifacts
    section still surveys the full registry so the user sees a complete picture;
    persona-specific artifacts are highlighted by the ordering coming from
    ``Persona.artifact_keys`` when present.
    """

    if persona not in PERSONAS:
        raise ValueError(
            f"Unknown persona {persona!r}. Choose from: {', '.join(PERSONAS)}."
        )

    root = (target or Path.cwd()).expanduser().resolve()
    artifacts = _survey_artifacts(root)
    notes = _system_notes()
    if persona == DEFAULT_PERSONA:
        next_steps = _recommend_next_steps(artifacts)
        ignore = list(ADVANCED_FOR_NOW)
    else:
        focus = get_persona(persona)
        next_steps = list(focus.next_commands)[:3]
        ignore = list(focus.ignore_for_now)
        artifacts = _reorder_for_persona(artifacts, focus.artifact_keys)
        notes = [f"Persona: {focus.title} — {focus.focus}", *notes]
    return DoctorReport(
        target=str(root),
        artifacts=artifacts,
        next_steps=next_steps,
        ignore_for_now=ignore,
        notes=notes,
        persona=persona,
    )


def _reorder_for_persona(
    artifacts: dict[str, bool], priority: tuple[str, ...]
) -> dict[str, bool]:
    """Put persona-relevant artifact keys first; preserve the rest in registry order."""

    seen: set[str] = set()
    ordered: dict[str, bool] = {}
    for key in priority:
        if key in artifacts:
            ordered[key] = artifacts[key]
            seen.add(key)
    for key, value in artifacts.items():
        if key not in seen:
            ordered[key] = value
    return ordered


def _survey_artifacts(root: Path) -> dict[str, bool]:
    """File-existence survey. Keys are stable for golden tests / --json consumers.

    Order and key set come from `artifacts.ARTIFACTS` so the registry is the single
    source of truth.
    """

    pr_template_glob_present = (root / ".github" / "PULL_REQUEST_TEMPLATE").exists() and any(
        (root / ".github" / "PULL_REQUEST_TEMPLATE").iterdir()
    )

    presence: dict[str, bool] = {}
    for artifact in ARTIFACTS:
        if artifact.key == "pr_template":
            presence[artifact.key] = (
                pr_template_glob_present or (root / PR_TEMPLATE_RELATIVE).exists()
            )
            continue
        presence[artifact.key] = (root / artifact.relative_path).exists()
    return presence


def _system_notes() -> list[str]:
    """Local environment notes that influence which next step is useful."""

    notes: list[str] = []
    hardware = probe_hardware()
    notes.append(f"OS: {hardware.os_name}")
    py = sys.version_info
    notes.append(f"Python: {py.major}.{py.minor}.{py.micro}")
    if hardware.is_wsl:
        notes.append("Environment: WSL detected")
    if hardware.llmfit_available:
        notes.append("llmfit: available")

    env_keys = ("OPENAI_API_KEY", "ANTHROPIC_API_KEY", "GITHUB_TOKEN")
    found = [k for k in env_keys if os.environ.get(k)]
    if found:
        notes.append(f"Credentials in env: {', '.join(found)}")
    else:
        notes.append("Credentials in env: none (fine for local-only use)")

    # Don't run the full provider probe here — it's slow and the user can run
    # `coding-scaffold probe` for the detailed picture.
    notes.append("Run `coding-scaffold probe` for the full provider/hardware report.")
    return notes


def _recommend_next_steps(artifacts: dict[str, bool]) -> list[str]:
    """1-3 recommended commands, tailored to what's present.

    The recommendations are intentionally short and ordered: each step naturally enables the
    next one. They never recommend an advanced governance command first.
    """

    steps: list[str] = []
    has_agents = artifacts.get("AGENTS.md") or artifacts.get("CLAUDE.md")
    has_scaffold = artifacts.get(".coding-scaffold/")
    has_pr_template = artifacts.get("pr_template")
    has_eval_config = artifacts.get("eval_config")

    if not has_agents and not has_scaffold:
        steps.append(
            "coding-scaffold pilot --target . --tool opencode  "
            "# print the 10-minute happy path tailored to this repo"
        )
        steps.append(
            "coding-scaffold setup run --target . --mode beginner  "
            "# guided setup once the pilot recipe makes sense"
        )
        return steps

    if not has_agents:
        steps.append(
            "coding-scaffold setup run --target . --mode beginner  "
            "# guided setup will write AGENTS.md and the OpenCode config"
        )

    if not has_pr_template:
        steps.append(
            "coding-scaffold pr-template init --target .  "
            "# adds .github/PULL_REQUEST_TEMPLATE/agentic-change.md"
        )

    if has_agents and not has_eval_config:
        steps.append(
            "coding-scaffold eval init --target .  "
            "# optional readiness-benchmark config; then `eval run`"
        )

    if has_agents and has_pr_template:
        steps.append(
            "coding-scaffold session init --target . --task \"first agentic change\"  "
            "# create a reviewable session trace before editing"
        )

    if not steps:
        steps.append(
            "coding-scaffold eval run --target .  "
            "# everything looks set up; the readiness benchmark confirms it"
        )

    # Trim to at most 3 recommendations so the output stays scannable.
    return steps[:3]


def format_doctor_text(report: DoctorReport) -> str:
    """Render the report as human-readable text. Deterministic for golden tests."""

    lines: list[str] = []
    lines.append(f"CodingScaffold doctor — {report.target}")
    lines.append("")
    lines.append("Scaffold artifacts:")
    # Widest key sets the column for the rationale line so output stays aligned.
    key_width = max((len(k) for k in report.artifacts), default=0)
    for key, present in report.artifacts.items():
        mark = "[x]" if present else "[ ]"
        lines.append(f"  {mark} {key.ljust(key_width)}  -> {rationale_for(key)}")
    lines.append("")
    lines.append("Glossary: https://jrs1986.github.io/CodingScaffold/wiki/Glossary")
    lines.append("")
    if report.notes:
        lines.append("System:")
        for note in report.notes:
            lines.append(f"  - {note}")
        lines.append("")
    lines.append("Recommended next steps:")
    if report.next_steps:
        for i, step in enumerate(report.next_steps, start=1):
            lines.append(f"  {i}. {step}")
    else:
        lines.append("  (no recommendations)")
    lines.append("")
    lines.append("Ignore for now (advanced):")
    lines.append(f"  {', '.join(report.ignore_for_now)}")
    lines.append("")
    lines.append("Terms: https://jrs1986.github.io/CodingScaffold/wiki/Glossary")
    return "\n".join(lines)
