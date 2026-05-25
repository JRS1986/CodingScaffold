"""Persona definitions used by `doctor --persona` and `pilot --persona`.

A persona is a target user shape (beginner, control-and-reproducibility,
security-review, team-lead). Each persona has:
- a focus area (one-line description of what this person cares about today),
- an ordered list of artifact keys (from ``artifacts.py``) to surface in `doctor`,
- an ordered list of recommended next commands tailored to that focus.

Personas live in one file so `doctor` and `pilot` cannot drift apart; both consume
the same registry. The wiki page `Team-Rollout.md` documents the same set; a test
asserts the names match.
"""

from __future__ import annotations

from dataclasses import dataclass

from .artifacts import artifact_keys


@dataclass(frozen=True)
class Persona:
    """A persona's surface area: what they look at first and run next."""

    key: str
    title: str
    focus: str
    artifact_keys: tuple[str, ...]
    next_commands: tuple[str, ...]
    ignore_for_now: tuple[str, ...]


BEGINNER = Persona(
    key="beginner",
    title="Beginner",
    focus="First useful agentic change inside a real repo.",
    artifact_keys=(
        "AGENTS.md",
        "CLAUDE.md",
        "pr_template",
        ".coding-scaffold/",
        "sessions_dir",
        "eval_config",
    ),
    next_commands=(
        "coding-scaffold pilot --target . --tool opencode  "
        "# print the 10-minute happy path",
        "coding-scaffold setup run --target . --mode beginner  "
        "# guided setup once the pilot makes sense",
        "coding-scaffold pr-template init --target .  "
        "# adds the agentic-change PR template",
    ),
    ignore_for_now=(
        "policy", "mcp", "skills", "memory", "team",
        "permissions write", "tools route", "tools workflow", "tools orchestrate",
    ),
)


CONTROL_AND_REPRODUCIBILITY = Persona(
    key="control",
    title="Control & Reproducibility",
    focus="Pin model routing, make every change reviewable, never lose work.",
    artifact_keys=(
        ".coding-scaffold/",
        "sessions_dir",
        "pr_template",
        "eval_config",
        "AGENTS.md",
        "CLAUDE.md",
        "knowledge_base",
    ),
    next_commands=(
        "coding-scaffold session init --target . --task 'first agentic change'  "
        "# every change starts in a reviewable session trace",
        "coding-scaffold eval init --target .  "
        "# readiness benchmark config so 'good shape' is measurable",
        "coding-scaffold context budget --target .  "
        "# know the context size before sending it to a model",
    ),
    ignore_for_now=(
        "skills", "tools orchestrate", "tools workflow",
    ),
)


SECURITY_REVIEW = Persona(
    key="security",
    title="Security Review",
    focus="Provider/MCP/permission rules; what the agent is and isn't allowed to do.",
    artifact_keys=(
        "policy_pack",
        "mcp_policy",
        "permissions_json",
        "eval_config",
        ".coding-scaffold/",
        "AGENTS.md",
        "CLAUDE.md",
    ),
    next_commands=(
        "coding-scaffold policy --target .  "
        "# encode provider/network/MCP allow-deny rules",
        "coding-scaffold permissions write --target . --mode read-only  "
        "# default to a read-only tool allowlist",
        "coding-scaffold mcp policy init --target .  "
        "# MCP server allow/deny rules with safe defaults",
        "coding-scaffold mcp scan --target .  "
        "# inventory MCP servers currently configured",
        "coding-scaffold eval run --target .  "
        "# confirm the policy bundle is enforceable",
    ),
    ignore_for_now=(
        "knowledge_base", "memory", "skills",
        "tools route", "tools workflow", "tools orchestrate",
    ),
)


TEAM_LEAD = Persona(
    key="team-lead",
    title="Team Lead",
    focus="Shared norms across the team: manifest, skills, knowledge, onboarding.",
    artifact_keys=(
        ".coding-scaffold/",
        "knowledge_base",
        "skills_dir",
        "memory_dir",
        "policy_pack",
        "AGENTS.md",
        "CLAUDE.md",
    ),
    next_commands=(
        "coding-scaffold team init --target .  "
        "# starter team-onboarding.json manifest",
        "coding-scaffold knowledge create --backend markdown --target .  "
        "# shared, reviewable team knowledge base",
        "coding-scaffold skills new --name release-review --target .  "
        "# first reusable skill the team can build on",
        "coding-scaffold team doctor --target .  "
        "# effective config + provenance once a manifest is in place",
    ),
    ignore_for_now=(
        "tools route", "tools workflow", "tools orchestrate",
    ),
)


PERSONAS: dict[str, Persona] = {
    p.key: p
    for p in (BEGINNER, CONTROL_AND_REPRODUCIBILITY, SECURITY_REVIEW, TEAM_LEAD)
}

DEFAULT_PERSONA: str = BEGINNER.key


def get_persona(key: str) -> Persona:
    """Look up a persona by key. Raises KeyError on unknown personas — callers
    should validate against ``PERSONAS`` first."""

    return PERSONAS[key]


def persona_keys() -> tuple[str, ...]:
    return tuple(PERSONAS)


# Sanity check at import time so a typo in artifact_keys is caught immediately.
def _validate() -> None:
    known = set(artifact_keys())
    for persona in PERSONAS.values():
        unknown = set(persona.artifact_keys) - known
        if unknown:
            raise ValueError(
                f"Persona {persona.key!r} references unknown artifacts: {sorted(unknown)}"
            )


_validate()
