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
- `deprecated`   — still works, but scheduled for removal in the release named in the
                   deprecation warning. Switch to the documented replacement now.

Add new commands here, not in `cli.py`. Tests assert every command in `--help` has
an entry.
"""

from __future__ import annotations

STABILITY_LEVELS: tuple[str, ...] = ("stable", "preview", "experimental", "deprecated")


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
    "tour": "preview",
    "skill": "stable",
    # Hidden flat aliases. Deprecated in 0.8.0; removal planned for 0.9.0.
    # Use the canonical grouped form (see _FLAT_ALIAS_CANONICAL in cli.py).
    "init": "deprecated",
    "wizard": "deprecated",
    "knowledge-status": "deprecated",
    "context-budget": "deprecated",
    "compress-context": "deprecated",
    "orchestrate": "deprecated",
    "setup-tool": "deprecated",
    "setup-addon": "deprecated",
    "setup-knowledge": "deprecated",
    "adapt": "deprecated",
    "route": "deprecated",
    "select-model": "deprecated",
    "workflow": "deprecated",
    "update": "deprecated",
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
