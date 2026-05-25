"""Stability markers for CLI commands.

Each top-level command (and a few load-bearing subcommands) is annotated with a
stability level so experienced teams know what they can build on. Markers render
inside `--help` next to the command name; the wiki page `Stability.md` defines
what each marker promises.

- `stable`       — backward compatible. Breaking changes require a major-version bump
                   and a deprecation cycle.
- `preview`      — feature-complete but the shape may shift in a minor release. Used
                   in production with caution; the wiki notes when each command will
                   move to `stable`.
- `experimental` — fast-moving. May change without warning. Use for exploration; do
                   not build automation around it yet.

Add new commands here, not in `cli.py`. Tests assert every command in `--help` has
an entry.
"""

from __future__ import annotations

STABILITY_LEVELS: tuple[str, ...] = ("stable", "preview", "experimental")


# Top-level commands (the ones surfaced in `coding-scaffold --help`).
COMMAND_STABILITY: dict[str, str] = {
    "probe": "stable",
    "setup": "stable",
    "credentials": "stable",
    "knowledge": "preview",
    "context": "preview",
    "session": "stable",
    "memory": "preview",
    "pr-template": "stable",
    "permissions": "preview",
    "mcp": "preview",
    "skills": "preview",
    "eval": "preview",
    "team": "preview",
    "policy": "preview",
    "tools": "stable",
    "doctor": "stable",
    "pilot": "stable",
    "skill": "stable",
    # Hidden flat aliases. Same stability as the canonical group.
    "init": "stable",
    "wizard": "stable",
    "knowledge-status": "preview",
    "context-budget": "preview",
    "compress-context": "preview",
    "orchestrate": "experimental",
    "setup-tool": "stable",
    "setup-addon": "stable",
    "setup-knowledge": "preview",
    "adapt": "stable",
    "route": "experimental",
    "select-model": "stable",
    "workflow": "experimental",
    "update": "stable",
}


def marker_for(command: str) -> str:
    """Return ``[stable]`` / ``[preview]`` / ``[experimental]``.

    Falls back to ``[preview]`` for commands missing from the registry so that
    adding a command doesn't immediately break `--help`; tests still flag the
    omission so the new command gets a real entry.
    """

    level = COMMAND_STABILITY.get(command, "preview")
    return f"[{level}]"


def annotate(help_text: str, command: str) -> str:
    """Prefix the help string with the stability marker.

    The marker comes first so the visible width is consistent across commands.
    """

    return f"{marker_for(command)} {help_text}"
