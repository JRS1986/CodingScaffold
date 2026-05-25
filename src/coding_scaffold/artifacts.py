"""Single source of truth for scaffold artifacts and the rationale behind each one.

`doctor`, `pilot`, and any future onboarding command consume this registry instead of
duplicating their own artifact tables. The `why` line answers \"what does this unlock?\"
in <100 chars so a first-time reader can interpret `doctor` output without leaving the CLI.

Add a new artifact here, not in `doctor.py`.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Artifact:
    """A scaffold artifact `doctor`/`pilot` can recommend, with a short rationale."""

    key: str
    relative_path: str
    why: str

    def __post_init__(self) -> None:
        if len(self.why) > 100:
            raise ValueError(
                f"Artifact rationale for {self.key!r} is {len(self.why)} chars; keep under 100."
            )


ARTIFACTS: tuple[Artifact, ...] = (
    Artifact(
        key="AGENTS.md",
        relative_path="AGENTS.md",
        why="Codex reads this first; without it the agent has no project rules.",
    ),
    Artifact(
        key="CLAUDE.md",
        relative_path="CLAUDE.md",
        why="Claude Code reads this first; project rules and links to local context.",
    ),
    Artifact(
        key="pr_template",
        relative_path=".github/PULL_REQUEST_TEMPLATE/agentic-change.md",
        why="Makes every agentic change reviewable in the same shape across the team.",
    ),
    Artifact(
        key=".coding-scaffold/",
        relative_path=".coding-scaffold",
        why="Holds project-local scaffold config: routing, providers, sessions, knowledge.",
    ),
    Artifact(
        key="knowledge_base",
        relative_path=".coding-scaffold/knowledge",
        why="Shared, reviewable team notes; replaces tribal knowledge in chat history.",
    ),
    Artifact(
        key="sessions_dir",
        relative_path=".coding-scaffold/sessions",
        why="Per-change traces; enables rollback and reviewable agentic edits.",
    ),
    Artifact(
        key="policy_pack",
        relative_path=".coding-scaffold/policy",
        why="Provider/MCP/runtime rules; lets you enforce 'no internet at runtime'.",
    ),
    Artifact(
        key="permissions_json",
        relative_path=".coding-scaffold/agent-permissions.json",
        why="Tool allowlist for agents; defaults to read-only until you opt in.",
    ),
    Artifact(
        key="mcp_policy",
        relative_path=".coding-scaffold/mcp-policy.json",
        why="MCP server allow/deny rules; governs which integrations the agent may use.",
    ),
    Artifact(
        key="skills_dir",
        relative_path=".coding-scaffold/skills",
        why="Reusable skill packs the agent can load on demand; reviewable in git.",
    ),
    Artifact(
        key="memory_dir",
        relative_path=".coding-scaffold/memory",
        why="Captured agent memory entries; reviewed and promoted before they take effect.",
    ),
    Artifact(
        key="eval_config",
        relative_path=".coding-scaffold/eval-config.json",
        why="Readiness benchmark config; `eval run` validates the project is set up.",
    ),
    Artifact(
        key="pyproject.toml",
        relative_path="pyproject.toml",
        why="Python project marker; doctor uses this to tailor language-specific guidance.",
    ),
    Artifact(
        key="package.json",
        relative_path="package.json",
        why="Node project marker; doctor uses this to tailor language-specific guidance.",
    ),
)


_INDEX: dict[str, Artifact] = {a.key: a for a in ARTIFACTS}


def artifact_keys() -> tuple[str, ...]:
    """Stable, ordered list of artifact keys — matches the order shown by `doctor`."""

    return tuple(a.key for a in ARTIFACTS)


def get_artifact(key: str) -> Artifact:
    """Look up an artifact by key. Raises KeyError if missing — callers should pass a
    key from ``artifact_keys()``."""

    return _INDEX[key]


def rationale_for(key: str) -> str:
    """Convenience for `get_artifact(key).why`."""

    return _INDEX[key].why
